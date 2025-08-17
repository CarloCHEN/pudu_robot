#!/bin/bash

# Simple script to deploy both webhook and lambda to a region
REGION=${1:-us-east-2}

echo "🚀 Deploying Lambda services to $REGION"

# Step 1: Run setup script
echo "🔧 Running setup..."
if ./lambda/setup_lambda.sh "$REGION"; then
    echo "✅ Setup completed successfully"
else
    echo "❌ Setup failed — aborting deployment"
    exit 1
fi

# Step 2: Deploy Lambda (only if setup succeeded)
echo "🚀 Deploying Lambda..."
if ./lambda/deploy_lambda.sh "$REGION"; then
    echo "✅ Lambda deployed to $REGION"
else
    echo "❌ Lambda deployment failed"
    exit 1
fi

echo "🎉 All services deployed to $REGION!"
echo ""
echo "📍 Resources created:"
echo "   Lambda: arn:aws:lambda:$REGION:908027373537:function:pudu-robot-pipeline"