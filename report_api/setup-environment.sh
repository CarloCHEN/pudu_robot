#!/bin/bash

ENVIRONMENT=${1:-us-east-2}

echo "🚀 Setting up Report API environment for: $ENVIRONMENT"

# Define region-specific variables
case $ENVIRONMENT in
  "us-east-1")
    export AWS_REGION="us-east-1"
    export AWS_ACCOUNT_ID="908027373537"
    export S3_REPORTS_BUCKET="monitor-reports-test-archive"
    export RDS_HOST="database-1.cpakuqeqgh9q.us-east-1.rds.amazonaws.com"
    export RDS_SECRET_NAME="rds!db-ef989dd0-975a-4c33-ab17-69f8ef4e03a1"
    ;;
  "us-east-2")
    export AWS_REGION="us-east-2"
    export AWS_ACCOUNT_ID="908027373537"
    export S3_REPORTS_BUCKET="monitor-reports-archive"
    export RDS_HOST="nexusiq-web-prod-database.cpgi0kcaa8wn.us-east-2.rds.amazonaws.com"
    export RDS_SECRET_NAME="rds!db-12d35fce-6171-4db1-a7e1-c75f1503ffed"
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
echo "   S3_REPORTS_BUCKET: $S3_REPORTS_BUCKET"
echo "   RDS_HOST: $RDS_HOST"
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
echo "📝 Generating .env file..."
cat > .env << EOF
AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID
AWS_REGION=$AWS_REGION
S3_REPORTS_BUCKET=$S3_REPORTS_BUCKET
REGISTRY_NAME=foxx_monitor_report_api
TAG=latest
EOF

# Check if template files exist, create if needed
if [ ! -f ".env.template" ]; then
    echo "📝 Creating .env.template..."
    cat > .env.template << 'EOF'
# AWS Configuration
AWS_REGION=${AWS_REGION}
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID}
S3_REPORTS_BUCKET=${S3_REPORTS_BUCKET}

# Application Configuration
PORT=8000
HOST=0.0.0.0
LOG_LEVEL=info

# Database Configuration (from existing project)
DATABASE_CONFIG_PATH=/app/src/pudu/configs/database_config.yaml
RDS_HOST=${RDS_HOST}
RDS_SECRET_NAME=${RDS_SECRET_NAME}

# Container Configuration
REGISTRY_NAME=foxx_monitor_report_api
TAG=latest
EOF
fi

# Update src/pudu/rds/credentials.yaml
cat > ../src/pudu/rds/credentials.yaml << EOF
---
database:
  host: "$RDS_HOST"
  secret_name: "$RDS_SECRET_NAME"
  region_name: "$AWS_REGION"
EOF

# Generate application .env file
echo "📝 Generating application .env file..."
envsubst < .env.template > app.env

# Generate database configuration
echo "📝 Generating database configuration..."
envsubst < database_config.yaml.template > database_config.yaml

echo ""
echo "✅ Environment setup complete for $ENVIRONMENT"
echo ""
echo "📁 Generated files:"
echo "   - .env (for deployment)"
echo "   - app.env (for application)"
echo "   - database_config.yaml (for database connections)"
echo ""
echo "🔧 Next steps:"
echo "   1. Review generated configuration files"
echo "   2. Run: make deploy-container"
echo ""

# Show generated file contents for verification
echo "📋 Generated .env (root):"
cat .env
echo ""

echo "📋 Generated app.env:"
head -10 app.env
echo ""
