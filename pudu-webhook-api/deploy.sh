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
    exit 1
fi

if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo "❌ AWS_ACCOUNT_ID not set. Please run setup first."
    exit 1
fi

REGISTRY_NAME="robot-webhook"
TAG="${TAG:-latest}"

echo "🚀 Starting Full Deployment to region: $AWS_REGION"
echo "📦 AWS Account: $AWS_ACCOUNT_ID"
echo "🏷️  Registry: $REGISTRY_NAME"
echo "🔖 Tag: $TAG"
echo ""

# Step 1: Login to ECR
echo "=========================================="
echo "Step 1: Logging in to ECR in $AWS_REGION"
echo "=========================================="
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

if [ $? -ne 0 ]; then
    echo "❌ ECR login failed!"
    exit 1
fi

# Step 2: Create ECR repository if it doesn't exist
echo ""
echo "=========================================="
echo "Step 2: Creating ECR repository (if needed)"
echo "=========================================="
aws ecr describe-repositories --repository-names $REGISTRY_NAME --region $AWS_REGION > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "📦 Creating ECR repository: $REGISTRY_NAME"
    aws ecr create-repository \
        --repository-name $REGISTRY_NAME \
        --region $AWS_REGION \
        --image-scanning-configuration scanOnPush=true \
        --encryption-configuration encryptionType=AES256

    if [ $? -eq 0 ]; then
        echo "✅ ECR repository created successfully"
    else
        echo "❌ Failed to create ECR repository"
        exit 1
    fi
else
    echo "✅ ECR repository already exists"
fi

# Step 3: Build Docker image
echo ""
echo "=========================================="
echo "Step 3: Building Docker image"
echo "=========================================="
docker build --no-cache --platform=linux/amd64 \
    -t "$REGISTRY_NAME:$TAG" \
    -f Dockerfile ..

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed!"
    exit 1
fi
echo "✅ Docker image built successfully"

# Step 4: Tag and push image to ECR
echo ""
echo "=========================================="
echo "Step 4: Pushing image to ECR"
echo "=========================================="
docker tag "$REGISTRY_NAME:$TAG" "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REGISTRY_NAME:$TAG"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REGISTRY_NAME:$TAG"

if [ $? -ne 0 ]; then
    echo "❌ Docker push failed!"
    exit 1
fi
echo "✅ Image pushed to ECR successfully"

# Step 5: Deploy infrastructure with Terraform
echo ""
echo "=========================================="
echo "Step 5: Deploying ECS infrastructure with Terraform"
echo "=========================================="

# Check if terraform directory exists
if [ ! -d "terraform" ]; then
    echo "❌ Terraform directory not found!"
    exit 1
fi

cd terraform

# Initialize Terraform (only if not already initialized)
if [ ! -d ".terraform" ]; then
    echo "🔧 Initializing Terraform..."
    terraform init
    if [ $? -ne 0 ]; then
        echo "❌ Terraform init failed!"
        cd ..
        exit 1
    fi
fi

# Select the appropriate tfvars file based on region
TFVARS_FILE="${AWS_REGION}.tfvars"

if [ ! -f "$TFVARS_FILE" ]; then
    echo "❌ Terraform variables file not found: $TFVARS_FILE"
    cd ..
    exit 1
fi

echo "📋 Using variables file: $TFVARS_FILE"

# Run terraform plan
echo ""
echo "🔍 Running Terraform plan..."
terraform plan -var-file="$TFVARS_FILE" -out=tfplan

if [ $? -ne 0 ]; then
    echo "❌ Terraform plan failed!"
    cd ..
    exit 1
fi

# Apply terraform changes
echo ""
echo "🚀 Applying Terraform changes..."
terraform apply tfplan

if [ $? -ne 0 ]; then
    echo "❌ Terraform apply failed!"
    cd ..
    exit 1
fi

# Clean up plan file
rm -f tfplan

# Force ECS to pull new image and restart service
echo ""
echo "🔄 Forcing ECS service to use new image..."
ECS_CLUSTER=$(terraform output -raw ecs_cluster_name 2>/dev/null)
ECS_SERVICE=$(terraform output -raw ecs_service_name 2>/dev/null)

if [ -z "$ECS_CLUSTER" ] || [ -z "$ECS_SERVICE" ]; then
    echo "⚠️  Could not get ECS names from Terraform output, using defaults"
    ECS_CLUSTER="robot-webhook-cluster-${AWS_REGION}"
    ECS_SERVICE="robot-webhook-service"
fi

aws ecs update-service \
    --cluster "$ECS_CLUSTER" \
    --service "$ECS_SERVICE" \
    --force-new-deployment \
    --region "$AWS_REGION" > /dev/null 2>&1

# Get outputs
echo ""
echo "=========================================="
echo "📊 Deployment Information"
echo "=========================================="
terraform output -json > ../deployment-output.json

ALB_URL=$(terraform output -raw alb_url 2>/dev/null)
PUDU_ENDPOINT=$(terraform output -json webhook_endpoints 2>/dev/null | grep -o '"pudu_webhook"[^"]*"[^"]*' | cut -d'"' -f4)
GAS_ENDPOINT=$(terraform output -json webhook_endpoints 2>/dev/null | grep -o '"gas_webhook"[^"]*"[^"]*' | cut -d'"' -f4)
HEALTH_ENDPOINT=$(terraform output -json webhook_endpoints 2>/dev/null | grep -o '"health_check"[^"]*"[^"]*' | cut -d'"' -f4)

cd ..

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "=========================================="
echo "🌐 Application URLs (SAVE THESE!)"
echo "=========================================="
echo "Load Balancer: $ALB_URL"
echo ""
echo "📋 Webhook Endpoints:"
echo "  Pudu:  $PUDU_ENDPOINT"
echo "  Gas:   $GAS_ENDPOINT"
echo "  Health: $HEALTH_ENDPOINT"
echo ""
echo "📁 Full deployment details saved to: deployment-output.json"
echo ""
echo "🔍 To view logs:"
echo "   aws logs tail /ecs/robot-webhook-$AWS_REGION --follow --region $AWS_REGION"
echo ""
echo "🔄 To update environment variables:"
echo "   1. Edit terraform/${AWS_REGION}.tfvars"
echo "   2. Run: ./deploy.sh"
echo ""