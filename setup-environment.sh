#!/bin/bash

ENVIRONMENT=${1:-us-east-2}

echo "🚀 Setting up environment for: $ENVIRONMENT"

# Define region-specific variables
case $ENVIRONMENT in
  "us-east-1")
    export AWS_REGION="us-east-1"
    export AWS_ACCOUNT_ID="908027373537"
    export RDS_HOST="database-1.cpakuqeqgh9q.us-east-1.rds.amazonaws.com"
    export RDS_SECRET_NAME="rds!db-ef989dd0-975a-4c33-ab17-69f8ef4e03a1"
    export NOTIFICATION_API_HOST="alb-streamnexus-demo-775802511.us-east-1.elb.amazonaws.com"
    ;;
  "us-east-2")
    export AWS_REGION="us-east-2"
    export AWS_ACCOUNT_ID="908027373537"
    export RDS_HOST="nexusiq-web-prod-database.cpgi0kcaa8wn.us-east-2.rds.amazonaws.com"
    export RDS_SECRET_NAME="rds!db-12d35fce-6171-4db1-a7e1-c75f1503ffed"
    export NOTIFICATION_API_HOST="alb-notice-1223048054.us-east-2.elb.amazonaws.com"
    ;;
  *)
    echo "❌ Unknown environment: $ENVIRONMENT"
    echo "Available environments: us-east-1, us-east-2"
    exit 1
    ;;
esac

echo "📋 Configuration for $ENVIRONMENT:"
echo "   AWS_REGION: $AWS_REGION"
echo "   RDS_HOST: $RDS_HOST"
echo "   NOTIFICATION_API_HOST: $NOTIFICATION_API_HOST"
echo ""

# Check if required commands exist
if ! command -v envsubst &> /dev/null; then
    echo "❌ envsubst command not found. Please install gettext package:"
    echo "   macOS: brew install gettext"
    echo "   Ubuntu/Debian: sudo apt-get install gettext-base"
    echo "   CentOS/RHEL: sudo yum install gettext"
    exit 1
fi

# Generate .env file for root directory
echo "📝 Generating .env file for root directory..."
cat > .env << EOF
AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID
AWS_REGION=$AWS_REGION
EOF

# Check if template files exist
if [ ! -f "pudu-webhook-api/.env.template" ]; then
    echo "❌ Template file pudu-webhook-api/.env.template not found!"
    echo "Please create the template file first."
    exit 1
fi

if [ ! -f "pudu-webhook-api/notifications/.env.template" ]; then
    echo "❌ Template file pudu-webhook-api/notifications/.env.template not found!"
    echo "Please create the template file first."
    exit 1
fi

if [ ! -f "pudu-webhook-api/rds/credentials.yaml.template" ]; then
    echo "❌ Template file pudu-webhook-api/rds/credentials.yaml.template not found!"
    echo "Please create the template file first."
    exit 1
fi

# Set PUDU_CALLBACK_CODE - you need to replace this with your actual callback code
export PUDU_CALLBACK_CODE="${PUDU_CALLBACK_CODE:-actual_callback_code_here}"

# Generate .env file for pudu-webhook-api
echo "📝 Generating pudu-webhook-api/.env file..."
envsubst < pudu-webhook-api/.env.template > pudu-webhook-api/.env

# Generate .env file for notifications
echo "📝 Generating pudu-webhook-api/notifications/.env file..."
envsubst < pudu-webhook-api/notifications/.env.template > pudu-webhook-api/notifications/.env

# Generate credentials.yaml
echo "📝 Generating pudu-webhook-api/rds/credentials.yaml file..."
envsubst < pudu-webhook-api/rds/credentials.yaml.template > pudu-webhook-api/rds/credentials.yaml

echo ""
echo "✅ Environment setup complete for $ENVIRONMENT"
echo ""
echo "📁 Generated files:"
echo "   - .env"
echo "   - pudu-webhook-api/.env"
echo "   - pudu-webhook-api/notifications/.env"
echo "   - pudu-webhook-api/rds/credentials.yaml"
echo ""
echo "🔧 Next steps:"
echo "   1. Update PUDU_CALLBACK_CODE in the script or set it as environment variable"
echo "   2. Verify AWS_ACCOUNT_ID in the script"
echo "   3. Run: make deploy-container"
echo ""

# Show generated file contents for verification
echo "📋 Generated .env (root):"
cat .env
echo ""

echo "📋 Generated pudu-webhook-api/.env:"
head -10 pudu-webhook-api/.env
echo ""

echo "📋 Generated pudu-webhook-api/notifications/.env:"
cat pudu-webhook-api/notifications/.env
echo ""

echo "📋 Generated pudu-webhook-api/rds/credentials.yaml:"
cat pudu-webhook-api/rds/credentials.yaml