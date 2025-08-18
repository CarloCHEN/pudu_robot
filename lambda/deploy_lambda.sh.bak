#!/bin/bash

# Simplified deployment script for Pudu Robot Pipeline Lambda with Support Ticket notifications
# Run this from the pudu_robot root directory

set -e

# Configuration
FUNCTION_NAME="pudu-robot-pipeline"
REGION="us-east-2"
ROLE_NAME="pudu-robot-lambda-role"
PYTHON_VERSION="3.9"

# Icon Configuration
ICONS_CONFIG_PATH="icons.yaml"

# Notification API Configuration
NOTIFICATION_API_HOST="alb-notice-1223048054.us-east-2.elb.amazonaws.com"
NOTIFICATION_API_ENDPOINT="/notification-api/robot/notification/send"

# SNS Configuration - CHANGE THIS EMAIL TO YOUR ACTUAL EMAIL
NOTIFICATION_EMAIL="jiaxu.chen@foxxusa.com"  # ⚠️ CHANGE THIS TO YOUR EMAIL

# SNS Topic Name (only one topic needed)
SUPPORT_TOPIC_NAME="pudu-robot-support-tickets"

echo "🚀 Deploying Pudu Robot Pipeline Lambda with Support Ticket notifications..."

# Validate email configuration
if [[ "$NOTIFICATION_EMAIL" == "your-email@example.com" ]]; then
    echo "❌ Please update the email address in the configuration section before deploying!"
    echo "   NOTIFICATION_EMAIL: $NOTIFICATION_EMAIL"
    exit 1
fi

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
cp "${PROJECT_ROOT}/src/pudu/notifications/icons.yaml" ./
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
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --region $REGION)
echo "🔍 Using AWS Account: $ACCOUNT_ID"

# Step 6: Create SNS Topic for Support Tickets
echo "📧 Setting up SNS topic for support ticket notifications..."

# Create topic (returns existing ARN if already exists)
SUPPORT_TOPIC_ARN=$(aws sns create-topic --name "$SUPPORT_TOPIC_NAME" --query 'TopicArn' --output text --region $REGION)

# Set topic attributes for better email formatting
aws sns set-topic-attributes \
    --topic-arn "$SUPPORT_TOPIC_ARN" \
    --attribute-name DisplayName \
    --attribute-value "Pudu Robot Support Tickets" \
    --region $REGION >/dev/null

echo "📧 Support Topic ARN: $SUPPORT_TOPIC_ARN"

# Check if email is already subscribed
existing_subscription=$(aws sns list-subscriptions-by-topic \
    --topic-arn "$SUPPORT_TOPIC_ARN" \
    --query "Subscriptions[?Endpoint=='$NOTIFICATION_EMAIL' && Protocol=='email'].SubscriptionArn" \
    --output text \
    --region $REGION)

if [ -z "$existing_subscription" ] || [ "$existing_subscription" = "None" ]; then
    echo "📧 Subscribing $NOTIFICATION_EMAIL to support ticket notifications..."
    aws sns subscribe \
        --topic-arn "$SUPPORT_TOPIC_ARN" \
        --protocol email \
        --notification-endpoint "$NOTIFICATION_EMAIL" \
        --region $REGION >/dev/null
    echo "✅ Email subscription created (confirmation required)"
else
    echo "✅ Email already subscribed: $existing_subscription"
fi

# Step 7: Create IAM role with SNS permissions
echo "🔐 Setting up IAM role with SNS permissions..."
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

# Function to safely create or update IAM policy statements
create_or_update_policy() {
    local policy_name="$1"
    local policy_document="$2"

    echo "🔍 Checking existing policy: $policy_name"

    # Check if policy already exists
    if aws iam get-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-name "$policy_name" \
        --region $REGION >/dev/null 2>&1; then

        echo "🔄 Policy exists, updating: $policy_name"
        # Policy exists, we'll update it (this replaces, but we'll make it comprehensive)
    else
        echo "📝 Creating new policy: $policy_name"
    fi

    # Return the policy document as-is
    echo "$policy_document"
}

# Create SNS policy for the Lambda role
echo "📧 Setting up SNS permissions..."
SNS_POLICY_DOC=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "sns:Publish",
                "sns:GetTopicAttributes"
            ],
            "Resource": [
                "${SUPPORT_TOPIC_ARN}"
            ]
        }
    ]
}
EOF
)

# Create and attach SNS policy
aws iam put-role-policy \
    --role-name $ROLE_NAME \
    --policy-name "SupportTicketSNSPolicy" \
    --policy-document "$SNS_POLICY_DOC" \
    --region $REGION >/dev/null

ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text --region $REGION)

# Create Secrets Manager policy for the Lambda role
echo "🔐 Setting up Secrets Manager permissions..."

# Build comprehensive secrets policy with all regions and patterns
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

# Function to add additional permissions safely
add_additional_permissions() {
    local service="$1"
    local actions="$2"
    local resources="$3"
    local policy_name="${service}AdditionalPolicy"

    echo "➕ Adding additional $service permissions..."

    ADDITIONAL_POLICY_DOC=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": $actions,
            "Resource": $resources
        }
    ]
}
EOF
)

    aws iam put-role-policy \
        --role-name $ROLE_NAME \
        --policy-name "$policy_name" \
        --policy-document "$ADDITIONAL_POLICY_DOC" \
        --region $REGION >/dev/null

    echo "✅ Additional $service permissions added"
}

# Example: Add additional permissions if needed
# Uncomment and modify as needed:
# add_additional_permissions "S3" '["s3:GetObject", "s3:PutObject"]' '["arn:aws:s3:::my-bucket/*"]'
# add_additional_permissions "DynamoDB" '["dynamodb:GetItem", "dynamodb:PutItem"]' '["arn:aws:dynamodb:'$REGION':'$ACCOUNT_ID':table/my-table"]'

# Step 8: Deploy Lambda function with environment variables
echo "🔧 Deploying Lambda function..."

# Prepare environment variables with SNS topic ARN
ENV_VARS="Variables={SUPPORT_TICKET_SNS_TOPIC_ARN=${SUPPORT_TOPIC_ARN},NOTIFICATION_API_HOST=${NOTIFICATION_API_HOST},NOTIFICATION_API_ENDPOINT=${NOTIFICATION_API_ENDPOINT},ICONS_CONFIG_PATH=${ICONS_CONFIG_PATH}}"

if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION >/dev/null 2>&1; then
    echo "Updating existing function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://pudu-robot-pipeline.zip \
        --region $REGION

    echo "⏳ Waiting for code update to complete..."
    aws lambda wait function-updated --function-name $FUNCTION_NAME --region $REGION

    echo "Updating function configuration..."
    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --runtime python${PYTHON_VERSION} \
        --timeout 900 \
        --memory-size 1024 \
        --environment "$ENV_VARS" \
        --region $REGION
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
        --environment "$ENV_VARS" \
        --description "Pudu Robot Data Pipeline with Support Ticket Monitoring" \
        --region $REGION || {
        echo "❌ Lambda creation failed"
        echo "Role ARN: $ROLE_ARN"
        echo "ZIP size: $(ls -lh pudu-robot-pipeline.zip)"
        exit 1
    }
fi

echo "🔧 Environment Variables:"
echo "   📧 SNS Topic: $SUPPORT_TOPIC_ARN"
echo "   🌐 API Host: $NOTIFICATION_API_HOST"
echo "   📡 API Endpoint: $NOTIFICATION_API_ENDPOINT"
echo "   🎨 Icons Config: $ICONS_CONFIG_PATH"

# Step 9: Set up EventBridge schedule
echo "📅 Setting up EventBridge schedule..."
aws events put-rule \
    --name pudu-robot-5min-schedule \
    --schedule-expression "rate(5 minutes)" \
    --description "Trigger Pudu robot data pipeline every 5 minutes" \
    --state ENABLED \
    --region $REGION >/dev/null

# Step 10: Add Lambda permission for EventBridge
aws lambda add-permission \
    --function-name $FUNCTION_NAME \
    --statement-id pudu-robot-eventbridge-permission \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn arn:aws:events:$REGION:$ACCOUNT_ID:rule/pudu-robot-5min-schedule \
    --region $REGION \
    >/dev/null 2>&1 || echo "Permission already exists"

# Step 11: Add Lambda as EventBridge target
aws events put-targets \
    --rule pudu-robot-5min-schedule \
    --targets "Id"="1","Arn"="arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$FUNCTION_NAME" \
    --region $REGION >/dev/null

# Cleanup
cd "$PROJECT_ROOT"
rm -rf /tmp/lambda_deploy

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "📊 Function Details:"
echo "   Function Name: $FUNCTION_NAME"
echo "   Region: $REGION"
echo "   Runtime: Python ${PYTHON_VERSION}"
echo "   Schedule: Every 5 minutes"
echo "   Logs: /aws/lambda/$FUNCTION_NAME"
echo ""
echo "📧 Support Ticket Notifications:"
echo "   🎫 Topic: $SUPPORT_TOPIC_ARN"
echo "   📧 Email: $NOTIFICATION_EMAIL"
echo ""
echo "⚠️  IMPORTANT: Check your email for SNS subscription confirmation!"
echo ""
echo "🔧 Useful Commands:"
echo "   Test: aws lambda invoke --function-name $FUNCTION_NAME --region $REGION test-output.json && cat test-output.json"
echo "   Logs: aws logs tail /aws/lambda/$FUNCTION_NAME --region $REGION --follow"
echo "   Disable: aws events disable-rule --name pudu-robot-5min-schedule --region $REGION"
echo "   Enable: aws events enable-rule --name pudu-robot-5min-schedule --region $REGION"
echo ""
echo "🎫 Your pipeline now monitors support tickets and sends notifications!"