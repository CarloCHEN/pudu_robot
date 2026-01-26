#!/bin/bash

# Container-based deployment script for Pudu Robot Work Location Lambda
# Run this from the pudu_robot root directory

set -e

# Configuration
FUNCTION_NAME="pudu-robot-work-location"
REGION=${1:-us-east-2}
ROLE_NAME="pudu-robot-work-location-lambda-role"
PYTHON_VERSION="3.9"

# Customer configuration for work location service
# Updated by setup_lambda.sh (sed); override manually if needed.
ROBOT_LOCATION_CUSTOMERS="university_of_florida"

# Docker/ECR Configuration
ECR_REPO_NAME="pudu-robot-work-location"
IMAGE_TAG="latest"

echo "🚀 Deploying Pudu Robot Work Location Lambda with Container Images..."

# Check if we're in the right directory
if [ ! -d "src/pudu" ]; then
    echo "❌ Please run from pudu_robot root directory (where src/pudu exists)"
    exit 1
fi

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Step 1: Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --region $REGION)
echo "🔍 Using AWS Account: $ACCOUNT_ID"

# Step 2: Create ECR repository if it doesn't exist
echo "📦 Setting up ECR repository..."
if ! aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $REGION >/dev/null 2>&1; then
    echo "Creating ECR repository: $ECR_REPO_NAME"
    aws ecr create-repository \
        --repository-name $ECR_REPO_NAME \
        --region $REGION >/dev/null
fi

ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}"
echo "📦 ECR URI: $ECR_URI"

# Prepare environment variables as JSON file to ensure comma-separated values are preserved
cat > /tmp/work_location_env.json << EOF
{
  "Variables": {
    "ROBOT_API_CUSTOMERS": "${ROBOT_LOCATION_CUSTOMERS}",
    "ROBOT_LOCATION_CUSTOMERS": "${ROBOT_LOCATION_CUSTOMERS}"
  }
}
EOF

# Step 3: Build and push Docker image
echo "🐳 Building Docker image..."

# Create updated requirements.txt for container
cat > requirements_work_location.txt << EOF
# Core AWS dependencies
boto3>=1.34.0
botocore>=1.34.0

# Database connectivity
pymysql>=1.1.0
sqlalchemy>=2.0.0

# Data processing
pandas>=2.0.0
numpy>=1.24.0

# Configuration and utilities
pyyaml>=6.0.0
python-dotenv>=1.0.0
python-dateutil>=2.8.0

# Timezone handling
tzlocal>=5.0

# HTTP requests
requests>=2.31.0

# Image processing - full OpenCV for containers
Pillow>=10.0.0
opencv-python>=4.8.0

# Arrow for efficient data processing
pyarrow>=12.0.0,<18.0.0
EOF

# Create Dockerfile for work location service
cat > Dockerfile.work_location << 'EOF'
# Use AWS Lambda Python runtime as base
FROM public.ecr.aws/lambda/python:3.9

# Install system dependencies for OpenCV and image processing
RUN yum update -y && \
    yum install -y \
    libX11 \
    libXext \
    libXrender \
    libSM \
    libICE \
    libGL \
    libglib2.0-0 \
    && yum clean all

# Copy requirements and install Python dependencies
COPY requirements_work_location.txt ${LAMBDA_TASK_ROOT}/requirements.txt
RUN pip install -r requirements.txt

# Copy source code
COPY src/pudu/ ${LAMBDA_TASK_ROOT}/pudu/
COPY lambda/work_location_lambda_function.py ${LAMBDA_TASK_ROOT}/lambda_function.py
COPY src/pudu/configs/database_config.yaml ${LAMBDA_TASK_ROOT}/

# Copy credential files
COPY credentials.yaml ${LAMBDA_TASK_ROOT}/
RUN mkdir -p ${LAMBDA_TASK_ROOT}/pudu/rds/
COPY src/pudu/rds/credentials.yaml ${LAMBDA_TASK_ROOT}/pudu/rds/

# Set the CMD to your handler
CMD ["lambda_function.lambda_handler"]
EOF

# Build the Docker image
echo "🏗️ Building Docker image for AWS Lambda (linux/amd64)..."
docker build --platform linux/amd64 -f Dockerfile.work_location -t $ECR_REPO_NAME:$IMAGE_TAG .

# Step 4: Login to ECR and push image
echo "🔐 Logging into ECR..."
ECR_REGISTRY="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

if [ $? -ne 0 ]; then
    echo "❌ ECR login failed"
    exit 1
fi

echo "📤 Pushing image to ECR..."
echo "🔍 Tagging: $ECR_REPO_NAME:$IMAGE_TAG -> $ECR_URI"
docker tag $ECR_REPO_NAME:$IMAGE_TAG $ECR_URI

echo "🔍 Pushing: $ECR_URI"
docker push "$ECR_URI"

if [ $? -ne 0 ]; then
    echo "❌ ECR push failed"
    exit 1
fi

echo "✅ Image pushed successfully"

# Step 5: Create IAM role with permissions
echo "🔐 Setting up IAM role with permissions..."
if ! aws iam get-role --role-name $ROLE_NAME --region $REGION >/dev/null 2>&1; then
    echo "Creating IAM role..."
    aws iam create-role \
        --role-name $ROLE_NAME \
        --region $REGION \
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
        --region $REGION \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --region $REGION \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole

    echo "⏳ Waiting for role to propagate..."
    sleep 15
fi

ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text --region $REGION)

# Create Secrets Manager policy for the Lambda role
echo "🔐 Setting up Secrets Manager permissions..."
SECRETS_POLICY_DOC=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret"
            ],
            "Resource": [
                "arn:aws:secretsmanager:us-east-1:${ACCOUNT_ID}:secret:rds!*",
                "arn:aws:secretsmanager:us-east-2:${ACCOUNT_ID}:secret:rds!*",
                "arn:aws:secretsmanager:us-west-1:${ACCOUNT_ID}:secret:rds!*",
                "arn:aws:secretsmanager:us-west-2:${ACCOUNT_ID}:secret:rds!*"
            ]
        }
    ]
}
EOF
)

# Create and attach Secrets Manager policy
aws iam put-role-policy \
    --role-name $ROLE_NAME \
    --policy-name "SecretsManagerPolicy" \
    --policy-document "$SECRETS_POLICY_DOC" \
    --region $REGION >/dev/null

echo "✅ Secrets Manager permissions configured for multiple regions"

# S3 permissions for archival
echo "🔧 Setting up S3 permissions..."
S3_POLICY_DOC=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:PutObjectAcl",
                "s3:DeleteObject"
            ],
            "Resource": [
                "arn:aws:s3:::pudu-robot-transforms-*/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket",
                "s3:GetBucketLocation"
            ],
            "Resource": [
                "arn:aws:s3:::pudu-robot-transforms-*"
            ]
        }
    ]
}
EOF
)

aws iam put-role-policy \
    --role-name $ROLE_NAME \
    --policy-name "S3ArchivalPolicy" \
    --policy-document "$S3_POLICY_DOC" \
    --region $REGION >/dev/null

echo "✅ S3 permissions configured for archival"

# Step 6: Deploy Lambda function with container image
echo "🔧 Deploying Lambda function with container image..."
echo "👥 Work location customers: $ROBOT_LOCATION_CUSTOMERS"

if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION >/dev/null 2>&1; then
    echo "Checking existing function package type..."
    CURRENT_PACKAGE_TYPE=$(aws lambda get-function --function-name $FUNCTION_NAME --region $REGION --query 'Configuration.PackageType' --output text)

    if [ "$CURRENT_PACKAGE_TYPE" = "Zip" ]; then
        echo "⚠️ Existing function uses ZIP package type, but we need Image type"
        echo "🗑️ Deleting existing function to recreate with container image..."

        # Remove EventBridge target first
        aws events remove-targets \
            --rule pudu-robot-work-location-1min-schedule \
            --ids "1" \
            --region $REGION >/dev/null 2>&1 || true

        # Delete the function
        aws lambda delete-function \
            --function-name $FUNCTION_NAME \
            --region $REGION

        echo "⏳ Waiting for function deletion to complete..."
        sleep 10

        echo "Creating new function with container image..."
        aws lambda create-function \
            --function-name $FUNCTION_NAME \
            --role $ROLE_ARN \
            --code ImageUri=$ECR_URI \
            --package-type Image \
            --timeout 300 \
            --memory-size 1024 \
            --environment file:///tmp/work_location_env.json \
            --description "Pudu Robot Work Location Service with 30-day Archival (Container)" \
            --region $REGION || {
            echo "❌ Lambda creation failed"
            echo "Role ARN: $ROLE_ARN"
            echo "Image URI: $ECR_URI"
            exit 1
        }
    else
        echo "Updating existing container-based function..."
        # Update function code to use container image
        aws lambda update-function-code \
            --function-name $FUNCTION_NAME \
            --image-uri $ECR_URI \
            --region $REGION

        echo "⏳ Waiting for code update to complete..."
        aws lambda wait function-updated --function-name $FUNCTION_NAME --region $REGION

        echo "Updating function configuration..."
        aws lambda update-function-configuration \
            --function-name $FUNCTION_NAME \
            --timeout 300 \
            --memory-size 1024 \
            --environment file:///tmp/work_location_env.json \
            --region $REGION
    fi
else
    echo "Creating new function with container image..."
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --role $ROLE_ARN \
        --code ImageUri=$ECR_URI \
        --package-type Image \
        --timeout 300 \
        --memory-size 1024 \
        --description "Pudu Robot Work Location Service with 30-day Archival (Container)" \
        --region $REGION || {
        echo "❌ Lambda creation failed"
        echo "Role ARN: $ROLE_ARN"
        echo "Image URI: $ECR_URI"
        exit 1
    }
fi

# Step 7: Set up EventBridge schedule for 1-minute intervals
echo "📅 Setting up EventBridge schedule for 1-minute intervals..."
aws events put-rule \
    --name pudu-robot-work-location-1min-schedule \
    --schedule-expression "rate(1 minute)" \
    --description "Trigger Pudu robot work location service every 1 minute" \
    --state ENABLED \
    --region $REGION >/dev/null

# Step 8: Add Lambda permission for EventBridge
aws lambda add-permission \
    --function-name $FUNCTION_NAME \
    --statement-id pudu-robot-work-location-eventbridge-permission \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn arn:aws:events:$REGION:$ACCOUNT_ID:rule/pudu-robot-work-location-1min-schedule \
    --region $REGION \
    >/dev/null 2>&1 || echo "Permission already exists"

# Step 9: Add Lambda as EventBridge target
aws events put-targets \
    --rule pudu-robot-work-location-1min-schedule \
    --targets "Id"="1","Arn"="arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$FUNCTION_NAME" \
    --region $REGION >/dev/null

echo ""
echo "✅ Work Location Lambda deployment completed successfully!"
echo ""
echo "📊 Function Details:"
echo "   Function Name: $FUNCTION_NAME"
echo "   Region: $REGION"
echo "   Package Type: Image"
echo "   Image URI: $ECR_URI"
echo "   Memory: 1024 MB"
echo "   Schedule: Every 1 minute"
echo "   Logs: /aws/lambda/$FUNCTION_NAME"
echo "   Retention: 30 days per robot"
echo ""
echo "🔧 Useful Commands:"
echo "   Test: aws lambda invoke --function-name $FUNCTION_NAME --region $REGION test-output.json && cat test-output.json"
echo "   Logs: aws logs tail /aws/lambda/$FUNCTION_NAME --region $REGION --follow"
echo "   Disable: aws events disable-rule --name pudu-robot-work-location-1min-schedule --region $REGION"
echo "   Enable: aws events enable-rule --name pudu-robot-work-location-1min-schedule --region $REGION"
echo "   Update Image: docker build --platform linux/amd64 -f Dockerfile.work_location -t $ECR_REPO_NAME:$IMAGE_TAG . && docker tag $ECR_REPO_NAME:$IMAGE_TAG $ECR_URI && docker push $ECR_URI && aws lambda update-function-code --function-name $FUNCTION_NAME --image-uri $ECR_URI --region $REGION"
echo ""
echo "🗺️ Your work location service now runs every minute with 30-day data retention!"

# Cleanup temporary files
rm -f requirements_work_location.txt
rm -f Dockerfile.work_location
rm -f /tmp/work_location_env.json