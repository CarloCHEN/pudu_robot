#!/bin/bash

# Load environment variables from .env if not already set
if [ -f ".env" ]; then
    set -a  # Automatically export all variables
    source .env
    set +a  # Turn off automatic export
fi

# Check if required environment variables are set
if [ -z "$AWS_REGION" ]; then
    echo "❌ AWS_REGION not set. Please run setup first."
    echo "Debug: .env file contents:"
    cat .env 2>/dev/null || echo "No .env file found"
    exit 1
fi

if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo "❌ AWS_ACCOUNT_ID not set. Please run setup first."
    echo "Debug: .env file contents:"
    cat .env 2>/dev/null || echo "No .env file found"
    exit 1
fi

if [ -z "$REGISTRY_NAME" ]; then
    echo "❌ REGISTRY_NAME not set."
    exit 1
fi

if [ -z "$TAG" ]; then
    TAG="latest"
fi

echo "🚀 Deploying Report API to region: $AWS_REGION"
echo "📦 Using AWS Account: $AWS_ACCOUNT_ID"
echo "🏷️  Registry Name: $REGISTRY_NAME"
echo "🔖 Tag: $TAG"
echo "🪣 S3 Reports Bucket: $S3_REPORTS_BUCKET"

echo "🔐 Logging in to ECR in $AWS_REGION"
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

echo "🏗️ Building Report API image"
# Build from the report_api directory but include parent context for src/ access
docker build --no-cache --platform=linux/amd64 -t $REGISTRY_NAME -f Dockerfile ..

echo "🏷️ Tagging image for $AWS_REGION"
docker tag $REGISTRY_NAME:$TAG $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REGISTRY_NAME:$TAG

echo "📤 Pushing image to ECR in $AWS_REGION"
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REGISTRY_NAME:$TAG

echo "✅ Report API deployment complete!"
echo "📍 Image pushed to: $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REGISTRY_NAME:$TAG"
echo "🪣 Reports will be stored in: $S3_REPORTS_BUCKET"
echo ""
echo "🔧 To test the API locally:"
echo "   docker run -p 8000:8000 --env-file app.env $REGISTRY_NAME:$TAG"
echo ""
echo "📋 API endpoints:"
echo "   POST /api/reports/generate - Generate report"
echo "   GET  /api/reports/status/{request_id} - Check status"
echo "   GET  /api/reports/health - Health check"