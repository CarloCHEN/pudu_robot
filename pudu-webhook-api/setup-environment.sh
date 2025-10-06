#!/bin/bash

ENVIRONMENT=${1:-us-east-2}
BRAND=${2:-pudu}  # NEW: Support brand parameter

echo "🚀 Setting up Webhook API environment for: $ENVIRONMENT (Brand: $BRAND)"

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

# Validate brand
case $BRAND in
  "pudu"|"gas")
    echo "✅ Valid brand: $BRAND"
    ;;
  *)
    echo "❌ Unknown brand: $BRAND"
    echo "Available brands: pudu, gas"
    exit 1
    ;;
esac

echo "📋 Configuration for $ENVIRONMENT:"
echo "   Brand: $BRAND"
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
echo "📝 Generating deployment .env file for $BRAND..."
cat > .env << EOF
AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID
AWS_REGION=$AWS_REGION
REGISTRY_NAME=foxx_monitor_${BRAND}_webhook_api
TAG=latest

# Application Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Brand Configuration
BRAND=$BRAND

# Pudu Configuration
PUDU_CALLBACK_CODE=${PUDU_CALLBACK_CODE:-actual_pudu_callback_code_here}
PUDU_API_KEY=your_api_key_here

# Gas Configuration
GAS_CALLBACK_CODE=${GAS_CALLBACK_CODE:-actual_gas_callback_code_here}

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

echo ""
echo "✅ Environment setup complete for $ENVIRONMENT (Brand: $BRAND)"
echo ""
echo "📁 Generated files:"
echo "   - .env (deployment and application config)"
echo "   - notifications/.env"
echo "   - rds/credentials.yaml"
echo ""
echo "🔧 Next steps:"
echo "   1. Update ${BRAND^^}_CALLBACK_CODE in environment or .env file"
echo "   2. Run: make deploy-container"
echo ""

# Show generated file contents for verification
echo "📋 Generated .env:"
head -20 .env
echo ""

echo "📋 Generated notifications/.env:"
cat notifications/.env
echo ""

echo "📋 Generated rds/credentials.yaml:"
cat rds/credentials.yaml