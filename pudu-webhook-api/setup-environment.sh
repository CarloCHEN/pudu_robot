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
echo "   AWS_ACCOUNT_ID: $AWS_ACCOUNT_ID"
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

# Generate .env file for root directory (deployment variables)
echo "📝 Generating deployment .env file..."
cat > .env << EOF
AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID
AWS_REGION=$AWS_REGION
REGISTRY_NAME=foxx_monitor_pudu_webhook_api
TAG=latest

# Application Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Pudu Configuration
PUDU_CALLBACK_CODE=${PUDU_CALLBACK_CODE:-actual_callback_code_here}
PUDU_API_KEY=your_api_key_here

# Logging
LOG_LEVEL=INFO
LOG_FILE=pudu_callbacks.log

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

echo ""
echo "✅ Environment setup complete for $ENVIRONMENT"
echo ""
echo "📁 Generated files:"
echo "   - .env (deployment and application config)"
echo "   - notifications/.env"
echo "   - rds/credentials.yaml"
echo ""
echo "🔧 Next steps:"
echo "   1. Update PUDU_CALLBACK_CODE in the script or set it as environment variable"
echo "   2. Verify AWS_ACCOUNT_ID in the script"
echo "   3. Run: make deploy-container"
echo ""

# Show generated file contents for verification
echo "📋 Generated .env:"
head -15 .env
echo ""

echo "📋 Generated notifications/.env:"
cat notifications/.env
echo ""

echo "📋 Generated rds/credentials.yaml:"
cat rds/credentials.yaml