#!/bin/bash

# quick-deploy.sh - Fast redeploy for code changes (assumes ALB already exists)

# Load environment variables
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
else
    echo "❌ .env file not found. Run setup first."
    exit 1
fi

# Load ALB configuration
if [ -f "alb-config.env" ]; then
    set -a
    source alb-config.env
    set +a
else
    echo "❌ ALB configuration not found. This is for existing ALB setups only."
    echo "💡 For first-time setup, run: make deploy-us-east-1-alb"
    exit 1
fi

echo "🚀 Quick redeploy to existing ALB setup"
echo "Region: $AWS_REGION"
echo "ALB: $ALB_DNS_NAME"

# Configuration
CLUSTER_NAME="monitor-report-api-cluster"
SERVICE_NAME="monitor-report-api-service"

# Build and push new image
echo "📦 Building and pushing updated image..."
bash deploy.sh

if [ $? -ne 0 ]; then
    echo "❌ Failed to build and push image"
    exit 1
fi

# Force new deployment (ECS will pull the latest image)
echo "🔄 Forcing ECS service update..."
aws ecs update-service \
    --region $AWS_REGION \
    --cluster $CLUSTER_NAME \
    --service $SERVICE_NAME \
    --force-new-deployment >/dev/null

if [ $? -ne 0 ]; then
    echo "❌ Failed to update ECS service"
    exit 1
fi

echo "⏳ Waiting for deployment to complete..."
aws ecs wait services-stable --region $AWS_REGION --cluster $CLUSTER_NAME --services $SERVICE_NAME

# Check service status
RUNNING_COUNT=$(aws ecs describe-services \
    --region $AWS_REGION \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --query 'services[0].runningCount' --output text)

echo ""
echo "🎉 Quick Deployment Complete!"
echo "============================"
echo "🌐 API Endpoint: http://$ALB_DNS_NAME"
echo "🏃 Running Tasks: $RUNNING_COUNT"
echo ""
echo "🧪 Test your changes:"
echo "   curl http://$ALB_DNS_NAME/api/reports/health"
echo ""
echo "⏱️  Total time: ~2-3 minutes (much faster than full setup!)"