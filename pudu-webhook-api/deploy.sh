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

# Get brand from environment (default to pudu for backward compatibility)
BRAND=${BRAND:-pudu}

echo "🚀 Deploying ${BRAND} Webhook API to region: $AWS_REGION"
echo "📦 Using AWS Account: $AWS_ACCOUNT_ID"
echo "🏷️ Registry Name: $REGISTRY_NAME"
echo "🔖 Tag: $TAG"
echo "🤖 Brand: $BRAND"

echo "🔐 Logging in to ECR in $AWS_REGION"
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

echo "🏗️ Building ${BRAND} Webhook API image"
# Build from the current directory but use parent context for full project access
# Pass BRAND as build arg for potential Dockerfile customization
docker build --no-cache --platform=linux/amd64 \
    --build-arg BRAND="$BRAND" \
    -t "$REGISTRY_NAME" \
    -f Dockerfile ..

# Check if build was successful
if [ $? -ne 0 ]; then
    echo "❌ Docker build failed!"
    exit 1
fi

echo "🏷️ Tagging image for $AWS_REGION"
docker tag "$REGISTRY_NAME:$TAG" "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REGISTRY_NAME:$TAG"

echo "📤 Pushing image to ECR in $AWS_REGION"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REGISTRY_NAME:$TAG"

echo "✅ ${BRAND} Webhook API deployment complete!"
echo "📍 Image pushed to: $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REGISTRY_NAME:$TAG"
echo ""
echo "🔧 To test the API locally:"
echo "   docker run -p 8000:8000 --env-file .env $REGISTRY_NAME:$TAG"
echo ""
echo "📋 API endpoints:"
echo "   POST /api/$BRAND/webhook - Process $BRAND robot callbacks"
echo "   GET  /api/$BRAND/webhook/health - Health check for $BRAND"
echo "   GET  /api/webhook/health - General health check"