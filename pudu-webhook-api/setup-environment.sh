#!/bin/bash

ENVIRONMENT=${1:-us-east-2}

echo "🚀 Setting up Webhook API environment for: $ENVIRONMENT"

# Define region-specific variables
case $ENVIRONMENT in
  "us-east-1")
    export AWS_REGION="us-east-1"
    export AWS_ACCOUNT_ID="908027373537"
    export RDS_HOST="database-1.cpakuqeqgh9q.us-east-1.rds.amazonaws.com"
    export RDS_SECRET_NAME="rds!db-ef989dd0-975a-4c33-ab17-69f8ef4e03a1"
    export NOTIFICATION_API_HOST="alb-streamnexus-demo-775802511.us-east-1.elb.amazonaws.com"
    export PUDU_CALLBACK_CODE="vFpG5Ga9o8NqdymFLicLfJVfqj6JU50qQYCs"
    export GAS_CALLBACK_CODE="378c0111-5d5d-4bdc-9cc5-e3d7bd3494d3"
    ;;
  "us-east-2")
    export AWS_REGION="us-east-2"
    export AWS_ACCOUNT_ID="908027373537"
    export RDS_HOST="nexusiq-web-prod-database.cpgi0kcaa8wn.us-east-2.rds.amazonaws.com"
    export RDS_SECRET_NAME="rds!db-12d35fce-6171-4db1-a7e1-c75f1503ffed"
    export NOTIFICATION_API_HOST="alb-notice-1223048054.us-east-2.elb.amazonaws.com"
    export PUDU_CALLBACK_CODE="1vQ6MfUxqyoGMRQ9nK8C4pSkg1Qsa3Vpq"
    export GAS_CALLBACK_CODE=""  # Not available for us-east-2
    ;;
  *)
    echo "❌ Unknown environment: $ENVIRONMENT"
    echo "Available environments: us-east-1, us-east-2"
    exit 1
    ;;
esac

echo "📋 Configuration for $ENVIRONMENT:"
echo "   AWS_REGION: $AWS_REGION"
echo "   AWS_ACCOUNT_ID: $AWS_ACCOUNT_ID"
echo "   RDS_HOST: $RDS_HOST"
echo "   NOTIFICATION_API_HOST: $NOTIFICATION_API_HOST"
echo "   PUDU_CALLBACK_CODE: ${PUDU_CALLBACK_CODE:0:10}... (${#PUDU_CALLBACK_CODE} chars)"
if [ -z "$GAS_CALLBACK_CODE" ]; then
  echo "   GAS_CALLBACK_CODE: (empty - not configured for this region)"
else
  echo "   GAS_CALLBACK_CODE: ${GAS_CALLBACK_CODE:0:10}... (${#GAS_CALLBACK_CODE} chars)"
fi
echo ""

# Check if required commands exist
if ! command -v envsubst &> /dev/null; then
    echo "❌ envsubst command not found. Please install gettext package:"
    echo "   macOS: brew install gettext"
    echo "   Ubuntu/Debian: sudo apt-get install gettext-base"
    echo "   CentOS/RHEL: sudo yum install gettext"
    exit 1
fi

# Generate .env file for root directory (deployment variables)
echo "📝 Generating deployment .env file..."
cat > .env << EOF
AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID
AWS_REGION=$AWS_REGION
REGISTRY_NAME=foxx-monitor-webhook-api
TAG=latest

# Application Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Pudu Configuration
PUDU_CALLBACK_CODE=$PUDU_CALLBACK_CODE
PUDU_API_KEY=your_api_key_here

# Gas Configuration
GAS_CALLBACK_CODE=$GAS_CALLBACK_CODE

# Logging
LOG_LEVEL=INFO
LOG_FILE=robot_callbacks.log

# Notification API Configuration
NOTIFICATION_API_HOST=$NOTIFICATION_API_HOST
NOTIFICATION_API_ENDPOINT=/notification-api/robot/notification/send
ICONS_CONFIG_PATH=icons.yaml

# Main database for robot resolution
MAIN_DATABASE=ry-vue
EOF

# Check if template files exist, create if needed
if [ ! -f "notifications/.env.template" ]; then
    echo "📝 Creating notifications/.env.template..."
    mkdir -p notifications
    cat > notifications/.env.template << 'EOF'
# Notification API Configuration
NOTIFICATION_API_HOST=${NOTIFICATION_API_HOST}
NOTIFICATION_API_ENDPOINT=/notification-api/robot/notification/send
ICONS_CONFIG_PATH=icons.yaml
EOF
fi

if [ ! -f "rds/credentials.yaml.template" ]; then
    echo "📝 Creating rds/credentials.yaml.template..."
    mkdir -p rds
    cat > rds/credentials.yaml.template << 'EOF'
# RDS Configuration for Webhook API
host: ${RDS_HOST}
port: 3306
secret_name: ${RDS_SECRET_NAME}
region: ${AWS_REGION}
EOF
fi

# Generate notification .env file
echo "📝 Generating notifications/.env file..."
envsubst < notifications/.env.template > notifications/.env

# Generate credentials.yaml
echo "📝 Generating rds/credentials.yaml file..."
envsubst < rds/credentials.yaml.template > rds/credentials.yaml

# Create terraform directory if it doesn't exist
if [ ! -d "terraform" ]; then
    echo "📁 Creating terraform directory..."
    mkdir -p terraform
fi

# Verify that Terraform configuration files exist
echo ""
echo "🔍 Verifying Terraform configuration..."
REQUIRED_TF_FILES=("terraform/main.tf" "terraform/variables.tf" "terraform/outputs.tf" "terraform/backend.tf")
MISSING_FILES=()

for file in "${REQUIRED_TF_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    echo "⚠️  Warning: The following Terraform files are missing:"
    for file in "${MISSING_FILES[@]}"; do
        echo "   - $file"
    done
    echo ""
    echo "Please ensure all Terraform configuration files are in place before deploying."
else
    echo "✅ All Terraform configuration files present"
fi

# Check if tfvars file exists for this region
if [ ! -f "terraform/${AWS_REGION}.tfvars" ]; then
    echo "⚠️  Warning: terraform/${AWS_REGION}.tfvars not found"
    echo "   The deploy script will fail without this file."
else
    echo "✅ Terraform variables file found: terraform/${AWS_REGION}.tfvars"
fi

echo ""
echo "✅ Environment setup complete for $ENVIRONMENT"
echo ""
echo "📁 Generated files:"
echo "   - .env (deployment and application config)"
echo "   - notifications/.env"
echo "   - rds/credentials.yaml"
echo ""
echo "🔧 Next steps:"
echo "   1. Ensure Terraform files are in terraform/ directory"
echo "   2. Run: ./deploy.sh"
echo "   3. Save the ALB URL from deployment output"
echo ""
echo "🔄 To update callback codes later:"
echo "   1. Edit terraform/${AWS_REGION}.tfvars"
echo "   2. Run: ./deploy.sh (will update ECS task environment)"
echo ""

# Show generated file contents for verification
echo "📋 Generated .env (first 15 lines):"
head -15 .env
echo ""