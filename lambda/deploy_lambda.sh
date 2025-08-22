#!/bin/bash

# Container-based deployment script for Pudu Robot Pipeline Lambda with Support Ticket notifications
# Run this from the pudu_robot root directory

set -e

# Configuration
FUNCTION_NAME="pudu-robot-pipeline"
REGION=${1:-us-east-2}
ROLE_NAME="pudu-robot-lambda-role"
PYTHON_VERSION="3.9"

# Docker/ECR Configuration
ECR_REPO_NAME="pudu-robot-pipeline"
IMAGE_TAG="latest"

# Icon Configuration
ICONS_CONFIG_PATH="icons.yaml"

# Notification API Configuration
NOTIFICATION_API_HOST="alb-notice-1223048054.us-east-2.elb.amazonaws.com"
NOTIFICATION_API_ENDPOINT="/notification-api/robot/notification/send"

# SNS Configuration - CHANGE THIS EMAIL TO YOUR ACTUAL EMAIL
NOTIFICATION_EMAIL="jiaxu.chen@foxxusa.com"  # ⚠️ CHANGE THIS TO YOUR EMAIL

# SNS Topic Name (only one topic needed)
SUPPORT_TOPIC_NAME="pudu-robot-support-tickets"

echo "🚀 Deploying Pudu Robot Pipeline Lambda with Container Images..."

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

# Step 3: Build and push Docker image
echo "🐳 Building Docker image..."

# Create updated requirements.txt for container
cat > requirements_container.txt << EOF
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
EOF

# Create Dockerfile if it doesn't exist
if [ ! -f "Dockerfile" ]; then
    cat > Dockerfile << 'EOF'
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
COPY requirements_container.txt ${LAMBDA_TASK_ROOT}/requirements.txt
RUN pip install -r requirements.txt

# Copy source code
COPY src/pudu/ ${LAMBDA_TASK_ROOT}/pudu/
COPY lambda/robot_lambda_function.py ${LAMBDA_TASK_ROOT}/lambda_function.py
COPY src/pudu/configs/database_config.yaml ${LAMBDA_TASK_ROOT}/
COPY src/pudu/notifications/icons.yaml ${LAMBDA_TASK_ROOT}/

# Copy credential files
COPY credentials.yaml ${LAMBDA_TASK_ROOT}/
RUN mkdir -p ${LAMBDA_TASK_ROOT}/pudu/rds/
COPY src/pudu/rds/credentials.yaml ${LAMBDA_TASK_ROOT}/pudu/rds/

# Set the CMD to your handler
CMD ["lambda_function.lambda_handler"]
EOF
    echo "✅ Created Dockerfile"
fi

# Build the Docker image
echo "🏗️ Building Docker image for AWS Lambda (linux/amd64)..."
docker build --platform linux/amd64 -t $ECR_REPO_NAME:$IMAGE_TAG .

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

# Step 5: Create SNS Topic for Support Tickets
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

# Step 6: Create IAM role with permissions
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

# S3 permissions
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
    --policy-name "S3TransformBucketsPolicy" \
    --policy-document "$S3_POLICY_DOC" \
    --region $REGION >/dev/null

echo "✅ S3 permissions configured for transform buckets"

# Example: Add additional permissions if needed
# Uncomment and modify as needed:
# add_additional_permissions "S3" '["s3:GetObject", "s3:PutObject"]' '["arn:aws:s3:::my-bucket/*"]'
# add_additional_permissions "DynamoDB" '["dynamodb:GetItem", "dynamodb:PutItem"]' '["arn:aws:dynamodb:'$REGION':'$ACCOUNT_ID':table/my-table"]'

# Step 7: Deploy Lambda function with container image
echo "🔧 Deploying Lambda function with container image..."

# Prepare environment variables
ENV_VARS="Variables={SUPPORT_TICKET_SNS_TOPIC_ARN=${SUPPORT_TOPIC_ARN},NOTIFICATION_API_HOST=${NOTIFICATION_API_HOST},NOTIFICATION_API_ENDPOINT=${NOTIFICATION_API_ENDPOINT},ICONS_CONFIG_PATH=${ICONS_CONFIG_PATH}}"

if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION >/dev/null 2>&1; then
    echo "Checking existing function package type..."
    CURRENT_PACKAGE_TYPE=$(aws lambda get-function --function-name $FUNCTION_NAME --region $REGION --query 'Configuration.PackageType' --output text)

    if [ "$CURRENT_PACKAGE_TYPE" = "Zip" ]; then
        echo "⚠️ Existing function uses ZIP package type, but we need Image type"
        echo "🗑️ Deleting existing function to recreate with container image..."

        # Remove EventBridge target first
        aws events remove-targets \
            --rule pudu-robot-5min-schedule \
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
            --timeout 900 \
            --memory-size 2048 \
            --environment "$ENV_VARS" \
            --description "Pudu Robot Data Pipeline with Support Ticket Monitoring (Container)" \
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
            --timeout 900 \
            --memory-size 2048 \
            --environment "$ENV_VARS" \
            --region $REGION
    fi
else
    echo "Creating new function with container image..."
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --role $ROLE_ARN \
        --code ImageUri=$ECR_URI \
        --package-type Image \
        --timeout 900 \
        --memory-size 2048 \
        --environment "$ENV_VARS" \
        --description "Pudu Robot Data Pipeline with Support Ticket Monitoring (Container)" \
        --region $REGION || {
        echo "❌ Lambda creation failed"
        echo "Role ARN: $ROLE_ARN"
        echo "Image URI: $ECR_URI"
        exit 1
    }
fi

echo "🔧 Environment Variables:"
echo "   📧 SNS Topic: $SUPPORT_TOPIC_ARN"
echo "   🌐 API Host: $NOTIFICATION_API_HOST"
echo "   📡 API Endpoint: $NOTIFICATION_API_ENDPOINT"
echo "   🎨 Icons Config: $ICONS_CONFIG_PATH"

# Step 8: Set up EventBridge schedule
echo "📅 Setting up EventBridge schedule..."
aws events put-rule \
    --name pudu-robot-5min-schedule \
    --schedule-expression "rate(5 minutes)" \
    --description "Trigger Pudu robot data pipeline every 5 minutes" \
    --state ENABLED \
    --region $REGION >/dev/null

# Step 9: Add Lambda permission for EventBridge
aws lambda add-permission \
    --function-name $FUNCTION_NAME \
    --statement-id pudu-robot-eventbridge-permission \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn arn:aws:events:$REGION:$ACCOUNT_ID:rule/pudu-robot-5min-schedule \
    --region $REGION \
    >/dev/null 2>&1 || echo "Permission already exists"

# Step 10: Add Lambda as EventBridge target
aws events put-targets \
    --rule pudu-robot-5min-schedule \
    --targets "Id"="1","Arn"="arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$FUNCTION_NAME" \
    --region $REGION >/dev/null

echo ""
echo "✅ Container deployment completed successfully!"
echo ""
echo "📊 Function Details:"
echo "   Function Name: $FUNCTION_NAME"
echo "   Region: $REGION"
echo "   Package Type: Image"
echo "   Image URI: $ECR_URI"
echo "   Memory: 2048 MB"
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
echo "   Update Image: docker build --platform linux/amd64 -t $ECR_REPO_NAME:$IMAGE_TAG . && docker tag $ECR_REPO_NAME:$IMAGE_TAG $ECR_URI && docker push $ECR_URI && aws lambda update-function-code --function-name $FUNCTION_NAME --image-uri $ECR_URI --region $REGION"
echo ""
echo "🎫 Your containerized pipeline now monitors support tickets and sends notifications!"

# Cleanup temporary files
rm -f requirements_container.txt