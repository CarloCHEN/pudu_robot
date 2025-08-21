#!/bin/bash

# Container-based deployment script - modified from your existing deploy_lambda.sh
# ONLY changes: ZIP → Container image, everything else stays the same

set -e

# Configuration
FUNCTION_NAME="pudu-robot-pipeline"
REGION="us-east-2"
ROLE_NAME="pudu-robot-lambda-role"
PYTHON_VERSION="3.9"

# All your existing configuration (UNCHANGED)
ICONS_CONFIG_PATH="icons.yaml"
NOTIFICATION_API_HOST="alb-notice-1223048054.us-east-2.elb.amazonaws.com"
NOTIFICATION_API_ENDPOINT="/notification-api/robot/notification/send"
NOTIFICATION_EMAIL="jiaxu.chen@foxxusa.com"
SUPPORT_TOPIC_NAME="pudu-robot-support-tickets"

echo "🚀 Deploying Pudu Robot Pipeline Lambda as Container Image..."

# Validate email configuration
if [[ "$NOTIFICATION_EMAIL" == "your-email@example.com" ]]; then
    echo "❌ Please update the email address in the configuration section before deploying!"
    exit 1
fi

# Check directory
if [ ! -d "src/pudu" ]; then
    echo "❌ Please run from pudu_robot root directory (where src/pudu exists)"
    exit 1
fi

# NEW: Container setup
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --region $REGION)
ECR_REPOSITORY="pudu-robot-pipeline"
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPOSITORY}"
IMAGE_TAG="latest"

echo "🐳 Container setup:"
echo "   Account: $ACCOUNT_ID"
echo "   Repository: $ECR_REPOSITORY"
echo "   Image: $ECR_URI:$IMAGE_TAG"

# NEW: Create ECR repository if needed
echo "📦 Setting up ECR repository..."
aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $REGION >/dev/null 2>&1 || {
    echo "Creating ECR repository..."
    aws ecr create-repository --repository-name $ECR_REPOSITORY --region $REGION >/dev/null
}

# NEW: ECR login
echo "🔐 Logging into ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URI

# NEW: Build Docker image
echo "🔨 Building Docker image..."
docker build -t $ECR_REPOSITORY:$IMAGE_TAG .

# NEW: Tag and push image
echo "📤 Pushing image to ECR..."
docker tag $ECR_REPOSITORY:$IMAGE_TAG $ECR_URI:$IMAGE_TAG
docker push $ECR_URI:$IMAGE_TAG

# ALL SNS/IAM SETUP STAYS EXACTLY THE SAME
echo "📧 Setting up SNS topic for support ticket notifications..."

SUPPORT_TOPIC_ARN=$(aws sns create-topic --name "$SUPPORT_TOPIC_NAME" --query 'TopicArn' --output text --region $REGION)

aws sns set-topic-attributes \
    --topic-arn "$SUPPORT_TOPIC_ARN" \
    --attribute-name DisplayName \
    --attribute-value "Pudu Robot Support Tickets" \
    --region $REGION >/dev/null

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

# IAM SETUP STAYS EXACTLY THE SAME
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

# ALL POLICY CREATION STAYS THE SAME
echo "📧 Setting up comprehensive permissions..."

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

aws iam put-role-policy \
    --role-name $ROLE_NAME \
    --policy-name "SupportTicketSNSPolicy" \
    --policy-document "$SNS_POLICY_DOC" \
    --region $REGION >/dev/null

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

aws iam put-role-policy \
    --role-name $ROLE_NAME \
    --policy-name "SecretsManagerPolicy" \
    --policy-document "$SECRETS_POLICY_DOC" \
    --region $REGION >/dev/null

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

ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text --region $REGION)

# ONLY CHANGE: Lambda deployment now uses container image
echo "🔧 Deploying Lambda function with container image..."

ENV_VARS="Variables={SUPPORT_TICKET_SNS_TOPIC_ARN=${SUPPORT_TOPIC_ARN},NOTIFICATION_API_HOST=${NOTIFICATION_API_HOST},NOTIFICATION_API_ENDPOINT=${NOTIFICATION_API_ENDPOINT},ICONS_CONFIG_PATH=${ICONS_CONFIG_PATH}}"

if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION >/dev/null 2>&1; then
    echo "Updating existing function with new container image..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --image-uri $ECR_URI:$IMAGE_TAG \
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
else
    echo "Creating new function with container image..."
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --role $ROLE_ARN \
        --code ImageUri=$ECR_URI:$IMAGE_TAG \
        --package-type Image \
        --timeout 900 \
        --memory-size 2048 \
        --environment "$ENV_VARS" \
        --description "Pudu Robot Data Pipeline - Container Version with Support Ticket Monitoring" \
        --region $REGION || {
        echo "❌ Lambda creation failed"
        echo "Role ARN: $ROLE_ARN"
        echo "Image URI: $ECR_URI:$IMAGE_TAG"
        exit 1
    }
fi

# ALL EVENTBRIDGE SETUP STAYS THE SAME
echo "📅 Setting up EventBridge schedule..."
aws events put-rule \
    --name pudu-robot-5min-schedule \
    --schedule-expression "rate(5 minutes)" \
    --description "Trigger Pudu robot data pipeline every 5 minutes" \
    --state ENABLED \
    --region $REGION >/dev/null

aws lambda add-permission \
    --function-name $FUNCTION_NAME \
    --statement-id pudu-robot-eventbridge-permission \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn arn:aws:events:$REGION:$ACCOUNT_ID:rule/pudu-robot-5min-schedule \
    --region $REGION \
    >/dev/null 2>&1 || echo "Permission already exists"

aws events put-targets \
    --rule pudu-robot-5min-schedule \
    --targets "Id"="1","Arn"="arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$FUNCTION_NAME" \
    --region $REGION >/dev/null

echo ""
echo "✅ Container deployment completed successfully!"
echo ""
echo "📊 Function Details:"
echo "   Function Name: $FUNCTION_NAME"
echo "   Package Type: Image"
echo "   Image URI: $ECR_URI:$IMAGE_TAG"
echo "   Region: $REGION"
echo "   Memory: 2048MB (increased for container)"
echo "   Schedule: Every 5 minutes"
echo ""
echo "📧 Support Ticket Notifications:"
echo "   🎫 Topic: $SUPPORT_TOPIC_ARN"
echo "   📧 Email: $NOTIFICATION_EMAIL"
echo ""
echo "🔧 Useful Commands:"
echo "   Test: aws lambda invoke --function-name $FUNCTION_NAME --region $REGION test-output.json && cat test-output.json"
echo "   Logs: aws logs tail /aws/lambda/$FUNCTION_NAME --region $REGION --follow"
echo "   Disable: aws events disable-rule --name pudu-robot-5min-schedule --region $REGION"
echo "   Enable: aws events enable-rule --name pudu-robot-5min-schedule --region $REGION"
echo ""
echo "🎉 Your OpenCV issue is now solved with container images!"