#!/bin/bash

# Enhanced Lambda multi-region setup script with database config updates
ENVIRONMENT=${1:-us-east-2}

echo "🚀 Setting up Lambda for: $ENVIRONMENT"

# Define region-specific variables including transform databases and S3 buckets
case $ENVIRONMENT in
  "us-east-1")
    export AWS_REGION="us-east-1"
    export NOTIFICATION_API_HOST="alb-streamnexus-demo-775802511.us-east-1.elb.amazonaws.com"
    export RDS_HOST="database-1.cpakuqeqgh9q.us-east-1.rds.amazonaws.com"
    export RDS_SECRET_NAME="rds!db-ef989dd0-975a-4c33-ab17-69f8ef4e03a1"
    export TRANSFORM_DB="foxx_irvine_office"
    export S3_BUCKET="pudu-robot-transforms-foxx-irvine-office-845829-us-east-1"
    ;;
  "us-east-2")
    export AWS_REGION="us-east-2"
    export NOTIFICATION_API_HOST="alb-notice-1223048054.us-east-2.elb.amazonaws.com"
    export RDS_HOST="nexusiq-web-prod-database.cpgi0kcaa8wn.us-east-2.rds.amazonaws.com"
    export RDS_SECRET_NAME="rds!db-12d35fce-6171-4db1-a7e1-c75f1503ffed"
    export TRANSFORM_DB="university_of_florida"
    export S3_BUCKET="pudu-robot-transforms-university-of-florida-889717-us-east-2"
    ;;
  *)
    echo "❌ Unknown environment: $ENVIRONMENT"
    exit 1
    ;;
esac

echo "📋 Configuration: $AWS_REGION, $NOTIFICATION_API_HOST"
echo "🔧 Transform Database: $TRANSFORM_DB"
echo "📦 S3 Bucket: $S3_BUCKET"

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

# Update database_config.yaml with region-specific settings
CONFIG_FILE="src/pudu/configs/database_config.yaml"

if [ -f "$CONFIG_FILE" ]; then
    echo "📝 Updating database configuration for $AWS_REGION..."

    # Create backup
    cp "$CONFIG_FILE" "${CONFIG_FILE}.backup"

    # Update transform_supported_databases
    if grep -q "transform_supported_databases:" "$CONFIG_FILE"; then
        echo "🔧 Updating transform_supported_databases..."
        # Replace the database name in transform_supported_databases section
        sed -i '' "/transform_supported_databases:/,/^[^ ]/ {
            s/- \"[^\"]*\"/- \"$TRANSFORM_DB\"/
        }" "$CONFIG_FILE"
    else
        echo "➕ Adding transform_supported_databases..."
        # Add transform_supported_databases at the top
        sed -i '' "1i\\
transform_supported_databases:\\
  - \"$TRANSFORM_DB\"\\
" "$CONFIG_FILE"
    fi

    # Update region
    if grep -q "^region:" "$CONFIG_FILE"; then
        echo "🌍 Updating region..."
        sed -i '' "s/^region: .*/region: \"$AWS_REGION\"/" "$CONFIG_FILE"
    else
        echo "➕ Adding region..."
        # Add region after transform_supported_databases
        sed -i '' "/transform_supported_databases:/,/^[^ ]/ {
            /^[^ ]/i\\
region: \"$AWS_REGION\"\\

        }" "$CONFIG_FILE"
    fi

    # Update or add s3_config section
    if grep -q "s3_config:" "$CONFIG_FILE"; then
        echo "📦 Updating s3_config..."

        # Create temporary file with new s3_config
        cat > /tmp/new_s3_config << EOF
s3_config:
  region: "$AWS_REGION"
  buckets:
    $TRANSFORM_DB: "$S3_BUCKET"

EOF

        # Use awk to replace the s3_config section
        awk '
        BEGIN { in_s3_config = 0; replacement_done = 0 }
        /^s3_config:/ {
            if (!replacement_done) {
                system("cat /tmp/new_s3_config")
                replacement_done = 1
            }
            in_s3_config = 1
            next
        }
        /^[a-zA-Z_]/ && in_s3_config {
            in_s3_config = 0
            print $0
            next
        }
        !in_s3_config { print $0 }
        ' "$CONFIG_FILE" > "${CONFIG_FILE}.tmp" && mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"

        # Clean up
        rm -f /tmp/new_s3_config

    else
        echo "➕ Adding s3_config..."
        # Append s3_config to the end
        cat >> "$CONFIG_FILE" << EOF

s3_config:
  region: "$AWS_REGION"
  buckets:
    $TRANSFORM_DB: "$S3_BUCKET"

EOF
    fi

    echo "✅ Updated database configuration successfully"

    # Show what was changed
    echo ""
    echo "📋 Current configuration in $CONFIG_FILE:"
    echo "🔧 Transform Database: $(grep -A1 'transform_supported_databases:' "$CONFIG_FILE" | grep '- ' | sed 's/.*- "\(.*\)".*/\1/')"
    echo "🌍 Region: $(grep '^region:' "$CONFIG_FILE" | sed 's/region: "\(.*\)"/\1/')"
    echo "📦 S3 Bucket: $(grep -A3 'buckets:' "$CONFIG_FILE" | grep "$TRANSFORM_DB" | sed 's/.*: "\(.*\)"/\1/')"

else
    echo "⚠️ Database config file not found: $CONFIG_FILE"
    echo "💡 Creating basic configuration..."

    # Create the config file
    cat > "$CONFIG_FILE" << EOF
---
transform_supported_databases:
  - "$TRANSFORM_DB"
region: "$AWS_REGION"

s3_config:
  region: "$AWS_REGION"
  buckets:
    $TRANSFORM_DB: "$S3_BUCKET"

# Main control database (hardcoded)
main_database: "ry-vue"

# List of databases that need notifications (can include dynamic ones)
notification_needed:
  - "project"
EOF

    echo "✅ Created basic database configuration"
fi

echo ""
echo "✅ Lambda configured for $ENVIRONMENT"
echo "🚀 Next steps:"
echo "   1. Run S3 setup: python src/pudu/services/setup_s3_buckets.py --region $AWS_REGION"
echo "   2. Run deployment: ./lambda/deploy_lambda.sh"