#!/bin/bash

# Clean deployment script for Pudu Robot Pipeline Lambda
# Run this from the pudu_robot root directory

set -e

# Configuration
FUNCTION_NAME="pudu-robot-pipeline"
REGION="us-east-1"
ROLE_NAME="pudu-robot-lambda-role"
PYTHON_VERSION="3.9"  # Changed from 3.8 to 3.9 to match Lambda runtime

echo "🚀 Deploying Pudu Robot Pipeline Lambda..."

# Check if we're in the right directory
if [ ! -d "src/pudu" ]; then
    echo "❌ Please run from pudu_robot root directory (where src/pudu exists)"
    exit 1
fi

# Step 1: Create deployment package
echo "📦 Creating deployment package..."
PROJECT_ROOT=$(pwd)
rm -rf /tmp/lambda_deploy
mkdir -p /tmp/lambda_deploy
cd /tmp/lambda_deploy

# Copy source code
cp -r "${PROJECT_ROOT}/src/pudu" ./
cp "${PROJECT_ROOT}/lambda/robot_lambda_function.py" ./lambda_function.py
cp "${PROJECT_ROOT}/src/pudu/configs/database_config.yaml" ./
cp "${PROJECT_ROOT}/credentials.yaml" ./ 2>/dev/null || echo "⚠️ credentials.yaml not found, skipping"

# Copy RDS credential files if they exist
if [ -f "${PROJECT_ROOT}/src/pudu/rds/credentials.yaml" ]; then
    mkdir -p pudu/rds/
    cp "${PROJECT_ROOT}/src/pudu/rds/credentials.yaml" ./pudu/rds/
fi

# Step 2: Install dependencies
echo "📦 Installing clean dependencies for Lambda..."

# CRITICAL: Install packages specifically for Lambda's Linux environment and Python version
# This ensures binary compatibility with Lambda's runtime

# Core AWS packages
pip install boto3 botocore -t . --quiet

# Database packages
pip install pymysql sqlalchemy -t . --quiet

# Configuration and utility packages
pip install pyyaml python-dotenv -t . --quiet
pip install python-dateutil pytz tzlocal -t . --quiet
pip install requests -t . --quiet

# Install pandas and numpy with platform-specific wheels for Lambda
# Using manylinux2014_x86_64 which is compatible with Lambda's Amazon Linux 2
pip install \
    --platform manylinux2014_x86_64 \
    --target . \
    --implementation cp \
    --python-version ${PYTHON_VERSION} \
    --only-binary=:all: \
    --upgrade \
    pandas==1.5.3 numpy==1.24.3 2>/dev/null || {

    echo "⚠️ Platform-specific install failed, trying manylinux2010..."
    pip install \
        --platform manylinux2010_x86_64 \
        --target . \
        --implementation cp \
        --python-version ${PYTHON_VERSION} \
        --only-binary=:all: \
        --upgrade \
        pandas==1.5.3 numpy==1.24.3 2>/dev/null || {

        echo "⚠️ Both platform-specific installs failed. Trying with explicit index..."
        pip install \
            --index-url https://pypi.org/simple/ \
            --platform manylinux2014_x86_64 \
            --target . \
            --implementation cp \
            --python-version ${PYTHON_VERSION} \
            --only-binary=:all: \
            pandas==1.5.3 numpy==1.24.3
    }
}

echo "✅ Installed all packages for Python ${PYTHON_VERSION}"

# Step 3: Clean up to reduce size
echo "🧹 Cleaning up package..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true
find . -path "*/tests" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.md" -delete 2>/dev/null || true
find . -name "LICENSE*" -delete 2>/dev/null || true
find . -name "*.so.avx2" -delete 2>/dev/null || true  # Remove AVX2 optimized files if present

# Remove unnecessary numpy files to reduce size
rm -rf numpy/tests 2>/dev/null || true
rm -rf pandas/tests 2>/dev/null || true

# Step 4: Create ZIP package
echo "🗜️ Creating ZIP package..."
zip -r pudu-robot-pipeline.zip . -q -x "*/__pycache__/*" "*.pyc" "*.pyo"

# Check package size
ZIP_SIZE=$(stat -f%z pudu-robot-pipeline.zip 2>/dev/null || stat -c%s pudu-robot-pipeline.zip)
ZIP_SIZE_MB=$((ZIP_SIZE / 1024 / 1024))
echo "📦 ZIP size: ${ZIP_SIZE_MB}MB"

if [ $ZIP_SIZE -gt 52428800 ]; then  # 50MB
    echo "❌ Package too large (${ZIP_SIZE_MB}MB). Reducing further..."
    rm -rf boto3/docs botocore/docs 2>/dev/null || true
    find . -name "*.dist-info" -type d -exec rm -rf {} + 2>/dev/null || true

    # Additional cleanup for large packages
    rm -rf numpy/doc 2>/dev/null || true
    rm -rf pandas/io/tests 2>/dev/null || true
    find . -name "test_*.py" -delete 2>/dev/null || true

    rm pudu-robot-pipeline.zip
    zip -r pudu-robot-pipeline.zip . -q -x "*/__pycache__/*" "*.pyc" "*.pyo" "*/tests/*" "*/docs/*"

    ZIP_SIZE_MB=$(( $(stat -f%z pudu-robot-pipeline.zip 2>/dev/null || stat -c%s pudu-robot-pipeline.zip) / 1024 / 1024))
    echo "📦 Reduced ZIP size: ${ZIP_SIZE_MB}MB"
fi

# Step 5: Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "🔍 Using AWS Account: $ACCOUNT_ID"

# Step 6: Create IAM role if needed
echo "🔐 Setting up IAM role..."
if ! aws iam get-role --role-name $ROLE_NAME >/dev/null 2>&1; then
    echo "Creating IAM role..."
    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document '{
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }' >/dev/null

    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole

    echo "⏳ Waiting for role to propagate..."
    sleep 15
fi

ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)

# Step 7: Deploy Lambda function
echo "🔧 Deploying Lambda function..."
if aws lambda get-function --function-name $FUNCTION_NAME >/dev/null 2>&1; then
    echo "Updating existing function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://pudu-robot-pipeline.zip

    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --runtime python${PYTHON_VERSION} \
        --timeout 900 \
        --memory-size 1024
else
    echo "Creating new function..."
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime python${PYTHON_VERSION} \
        --role $ROLE_ARN \
        --handler lambda_function.lambda_handler \
        --zip-file "fileb://pudu-robot-pipeline.zip" \
        --timeout 900 \
        --memory-size 1024 \
        --description "Pudu Robot Data Pipeline - runs every 5 minutes" || {
        echo "❌ Lambda creation failed"
        echo "Role ARN: $ROLE_ARN"
        echo "ZIP size: $(ls -lh pudu-robot-pipeline.zip)"
        exit 1
    }
fi

# Step 8: Set up EventBridge schedule
echo "📅 Setting up EventBridge schedule..."
aws events put-rule \
    --name pudu-robot-5min-schedule \
    --schedule-expression "rate(5 minutes)" \
    --description "Trigger Pudu robot data pipeline every 5 minutes" \
    --state ENABLED >/dev/null

# Step 9: Add Lambda permission for EventBridge
aws lambda add-permission \
    --function-name $FUNCTION_NAME \
    --statement-id pudu-robot-eventbridge-permission \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn arn:aws:events:$REGION:$ACCOUNT_ID:rule/pudu-robot-5min-schedule \
    >/dev/null 2>&1 || echo "Permission already exists"

# Step 10: Add Lambda as EventBridge target
aws events put-targets \
    --rule pudu-robot-5min-schedule \
    --targets "Id"="1","Arn"="arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$FUNCTION_NAME" >/dev/null

# Cleanup
cd "$PROJECT_ROOT"
rm -rf /tmp/lambda_deploy

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "📊 Function Details:"
echo "   Function Name: $FUNCTION_NAME"
echo "   Runtime: Python ${PYTHON_VERSION}"
echo "   Schedule: Every 5 minutes"
echo "   Logs: /aws/lambda/$FUNCTION_NAME"
echo ""
echo "🔧 Useful Commands:"
echo "   Test: aws lambda invoke --function-name $FUNCTION_NAME test-output.json && cat test-output.json"
echo "   Logs: aws logs tail /aws/lambda/$FUNCTION_NAME --follow"
echo "   Disable: aws events disable-rule --name pudu-robot-5min-schedule"
echo "   Enable: aws events enable-rule --name pudu-robot-5min-schedule"
echo ""
echo "🎉 Your pipeline is now running every 5 minutes!"