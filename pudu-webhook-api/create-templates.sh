#!/bin/bash

echo "🚀 Creating template files for multi-region deployment..."

# Create the credentials.yaml.template
echo "📝 Creating rds/credentials.yaml.template..."
cat > rds/credentials.yaml.template << 'EOF'
---
database:
  host: "${RDS_HOST}"
  secret_name: "${RDS_SECRET_NAME}"
  region_name: "${AWS_REGION}"
EOF

# Create the main .env.template
echo "📝 Creating .env.template..."
cat > .env.template << 'EOF'
# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Pudu Configuration
PUDU_CALLBACK_CODE=${PUDU_CALLBACK_CODE}
PUDU_API_KEY=your_api_key_here

# Logging
LOG_LEVEL=INFO
LOG_FILE=pudu_callbacks.log

# Notification API Configuration
NOTIFICATION_API_HOST=${NOTIFICATION_API_HOST}
NOTIFICATION_API_ENDPOINT=/notification-api/robot/notification/send
ICONS_CONFIG_PATH=icons.yaml

# Main database for robot resolution
MAIN_DATABASE=ry-vue
EOF

# Create the notifications .env.template
echo "📝 Creating notifications/.env.template..."
cat > notifications/.env.template << 'EOF'
# Notification API Configuration
NOTIFICATION_API_HOST=${NOTIFICATION_API_HOST}
NOTIFICATION_API_ENDPOINT=/notification-api/robot/notification/send

# Icon Configuration
ICONS_CONFIG_PATH=icons.yaml

# Logging Configuration
LOG_LEVEL=INFO
EOF

# Backup existing files if they exist
if [ -f "rds/credentials.yaml" ]; then
    echo "💾 Backing up existing credentials.yaml to credentials.yaml.backup"
    cp rds/credentials.yaml rds/credentials.yaml.backup
fi

if [ -f ".env" ]; then
    echo "💾 Backing up existing .env to .env.backup"
    cp .env .env.backup
fi

if [ -f "notifications/.env" ]; then
    echo "💾 Backing up existing notifications/.env to notifications/.env.backup"
    cp notifications/.env notifications/.env.backup
fi

if [ -f ".env" ]; then
    echo "💾 Backing up existing root .env to .env.backup"
    cp .env .env.backup
fi

echo ""
echo "✅ Template files created successfully!"
echo ""
echo "📁 Created files:"
echo "   - rds/credentials.yaml.template"
echo "   - .env.template"
echo "   - notifications/.env.template"
echo ""
echo "🔧 Next steps:"
echo "   1. Make setup script executable: chmod +x setup-environment.sh"
echo "   2. Run setup for your target region: ./setup-environment.sh us-east-1"
echo "   3. Deploy: make deploy-container"