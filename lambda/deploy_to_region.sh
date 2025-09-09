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

# Step 2: Deploy Main Lambda (only if setup succeeded)
echo "🚀 Deploying Main Lambda..."
if ./lambda/deploy_lambda.sh "$REGION"; then
    echo "✅ Main Lambda deployed to $REGION"
else
    echo "❌ Main Lambda deployment failed"
    exit 1
fi

# Step 3: Deploy Work Location Lambda
echo "🗺️ Deploying Work Location Lambda..."
if ./lambda/deploy_work_location_lambda.sh "$REGION"; then
    echo "✅ Work Location Lambda deployed to $REGION"
else
    echo "❌ Work Location Lambda deployment failed"
    exit 1
fi

echo "🎉 All services deployed to $REGION!"
echo ""
echo "📍 Resources created:"
echo "   Main Lambda: arn:aws:lambda:$REGION:908027373537:function:pudu-robot-pipeline"
echo "   Work Location Lambda: arn:aws:lambda:$REGION:908027373537:function:pudu-robot-work-location"