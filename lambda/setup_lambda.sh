#!/bin/bash

# Simple Lambda multi-region setup script
ENVIRONMENT=${1:-us-east-2}

echo "🚀 Setting up Lambda for: $ENVIRONMENT"

# Define region-specific variables
case $ENVIRONMENT in
  "us-east-1")
    export AWS_REGION="us-east-1"
    export NOTIFICATION_API_HOST="alb-streamnexus-demo-775802511.us-east-1.elb.amazonaws.com"
    export RDS_HOST="database-1.cpakuqeqgh9q.us-east-1.rds.amazonaws.com"
    export RDS_SECRET_NAME="rds!db-ef989dd0-975a-4c33-ab17-69f8ef4e03a1"
    ;;
  "us-east-2")
    export AWS_REGION="us-east-2"
    export NOTIFICATION_API_HOST="alb-notice-1223048054.us-east-2.elb.amazonaws.com"
    export RDS_HOST="nexusiq-web-prod-database.cpgi0kcaa8wn.us-east-2.rds.amazonaws.com"
    export RDS_SECRET_NAME="rds!db-12d35fce-6171-4db1-a7e1-c75f1503ffed"
    ;;
  *)
    echo "❌ Unknown environment: $ENVIRONMENT"
    exit 1
    ;;
esac

echo "📋 Configuration: $AWS_REGION, $NOTIFICATION_API_HOST"

# Update lambda/deploy_lambda.sh - replace region lines properly
cp lambda/deploy_lambda.sh lambda/deploy_lambda.sh.bak

# Use more robust sed that handles any previous region
sed -i '' \
  -e "s/REGION=\"us-east-[12]\"/REGION=\"$AWS_REGION\"/" \
  -e "s/alb-[^\"]*\.elb\.amazonaws\.com/$NOTIFICATION_API_HOST/" \
  lambda/deploy_lambda.sh

echo "📝 Updated lambda/deploy_lambda.sh for $AWS_REGION"

# Update src/pudu/rds/credentials.yaml
cat > src/pudu/rds/credentials.yaml << EOF
---
database:
  host: "$RDS_HOST"
  secret_name: "$RDS_SECRET_NAME"
  region_name: "$AWS_REGION"
EOF

# Update src/pudu/notifications/.env
cat > src/pudu/notifications/.env << EOF
# Notification API Configuration
NOTIFICATION_API_HOST=$NOTIFICATION_API_HOST
NOTIFICATION_API_ENDPOINT=/notification-api/robot/notification/send

# Icon Configuration
ICONS_CONFIG_PATH=icons.yaml

# Logging Configuration
LOG_LEVEL=INFO
EOF

echo "✅ Lambda configured for $ENVIRONMENT"
echo "🚀 Run: ./lambda/deploy_lambda.sh"