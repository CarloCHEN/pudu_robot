#!/bin/bash

# setup-alb.sh - Create ALB and Target Group for Report API

# Load environment variables
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
else
    echo "❌ .env file not found. Run setup first."
    exit 1
fi

echo "🚀 Setting up ALB for Report API in $AWS_REGION"

# Configuration
ALB_NAME="monitor-report-api-alb"
TARGET_GROUP_NAME="monitor-report-api-targets"
SECURITY_GROUP_NAME="monitor-report-api-alb-sg"

# Get default VPC and subnets
echo "🔍 Finding VPC and subnets..."
VPC_ID=$(aws ec2 describe-vpcs --region $AWS_REGION --filters "Name=is-default,Values=true" --query 'Vpcs[0].VpcId' --output text)
if [ "$VPC_ID" = "None" ] || [ -z "$VPC_ID" ]; then
    echo "❌ No default VPC found. Please create one or specify VPC ID manually."
    exit 1
fi

SUBNET_IDS=$(aws ec2 describe-subnets --region $AWS_REGION --filters "Name=vpc-id,Values=$VPC_ID" "Name=default-for-az,Values=true" --query 'Subnets[].SubnetId' --output text)
SUBNET_ARRAY=($SUBNET_IDS)

if [ ${#SUBNET_ARRAY[@]} -lt 2 ]; then
    echo "❌ Need at least 2 subnets in different AZs. Found: ${#SUBNET_ARRAY[@]}"
    exit 1
fi

echo "✅ Using VPC: $VPC_ID"
echo "✅ Using Subnets: ${SUBNET_IDS// /, }"

# Create security group for ALB
echo "🔒 Creating security group for ALB..."
SG_ID=$(aws ec2 create-security-group \
    --region $AWS_REGION \
    --group-name $SECURITY_GROUP_NAME \
    --description "Security group for Monitor Report API ALB" \
    --vpc-id $VPC_ID \
    --query 'GroupId' --output text 2>/dev/null)

if [ $? -ne 0 ]; then
    # Security group might already exist
    SG_ID=$(aws ec2 describe-security-groups \
        --region $AWS_REGION \
        --filters "Name=group-name,Values=$SECURITY_GROUP_NAME" "Name=vpc-id,Values=$VPC_ID" \
        --query 'SecurityGroups[0].GroupId' --output text)
    echo "✅ Using existing security group: $SG_ID"
else
    echo "✅ Created security group: $SG_ID"
fi

# Add rules to security group (allow HTTP from anywhere)
echo "🔒 Adding security group rules..."
aws ec2 authorize-security-group-ingress \
    --region $AWS_REGION \
    --group-id $SG_ID \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0 2>/dev/null

aws ec2 authorize-security-group-ingress \
    --region $AWS_REGION \
    --group-id $SG_ID \
    --protocol tcp \
    --port 8000 \
    --cidr 0.0.0.0/0 2>/dev/null

# Create ALB
echo "⚖️ Creating Application Load Balancer..."
ALB_ARN=$(aws elbv2 create-load-balancer \
    --region $AWS_REGION \
    --name $ALB_NAME \
    --subnets ${SUBNET_IDS} \
    --security-groups $SG_ID \
    --scheme internet-facing \
    --type application \
    --ip-address-type ipv4 \
    --query 'LoadBalancers[0].LoadBalancerArn' --output text 2>/dev/null)

if [ $? -ne 0 ]; then
    # ALB might already exist
    ALB_ARN=$(aws elbv2 describe-load-balancers \
        --region $AWS_REGION \
        --names $ALB_NAME \
        --query 'LoadBalancers[0].LoadBalancerArn' --output text 2>/dev/null)

    if [ "$ALB_ARN" = "None" ] || [ -z "$ALB_ARN" ]; then
        echo "❌ Failed to create or find ALB"
        exit 1
    fi
    echo "✅ Using existing ALB: $ALB_ARN"
else
    echo "✅ Created ALB: $ALB_ARN"
fi

# Get ALB DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers \
    --region $AWS_REGION \
    --load-balancer-arns $ALB_ARN \
    --query 'LoadBalancers[0].DNSName' --output text)

# Create Target Group
echo "🎯 Creating Target Group..."
TARGET_GROUP_ARN=$(aws elbv2 create-target-group \
    --region $AWS_REGION \
    --name $TARGET_GROUP_NAME \
    --protocol HTTP \
    --port 8000 \
    --vpc-id $VPC_ID \
    --health-check-enabled \
    --health-check-path '/api/reports/health' \
    --health-check-interval-seconds 30 \
    --health-check-timeout-seconds 5 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3 \
    --target-type ip \
    --query 'TargetGroups[0].TargetGroupArn' --output text 2>/dev/null)

if [ $? -ne 0 ]; then
    # Target group might already exist
    TARGET_GROUP_ARN=$(aws elbv2 describe-target-groups \
        --region $AWS_REGION \
        --names $TARGET_GROUP_NAME \
        --query 'TargetGroups[0].TargetGroupArn' --output text 2>/dev/null)

    if [ "$TARGET_GROUP_ARN" = "None" ] || [ -z "$TARGET_GROUP_ARN" ]; then
        echo "❌ Failed to create or find Target Group"
        exit 1
    fi
    echo "✅ Using existing Target Group: $TARGET_GROUP_ARN"
else
    echo "✅ Created Target Group: $TARGET_GROUP_ARN"
fi

# Create Listener
echo "👂 Creating ALB Listener..."
LISTENER_ARN=$(aws elbv2 create-listener \
    --region $AWS_REGION \
    --load-balancer-arn $ALB_ARN \
    --protocol HTTP \
    --port 80 \
    --default-actions Type=forward,TargetGroupArn=$TARGET_GROUP_ARN \
    --query 'Listeners[0].ListenerArn' --output text 2>/dev/null)

if [ $? -ne 0 ]; then
    echo "ℹ️ Listener might already exist, continuing..."
fi

# Save configuration to file
echo "💾 Saving ALB configuration..."
cat > alb-config.env << EOF
# ALB Configuration
ALB_NAME=$ALB_NAME
ALB_ARN=$ALB_ARN
ALB_DNS_NAME=$ALB_DNS
TARGET_GROUP_NAME=$TARGET_GROUP_NAME
TARGET_GROUP_ARN=$TARGET_GROUP_ARN
SECURITY_GROUP_ID=$SG_ID
VPC_ID=$VPC_ID
EOF

echo ""
echo "🎉 ALB Setup Complete!"
echo "================================"
echo "🌐 Fixed API Endpoint: http://$ALB_DNS"
echo "🎯 Target Group ARN: $TARGET_GROUP_ARN"
echo "⚖️ Load Balancer ARN: $ALB_ARN"
echo ""
echo "📋 API URLs for your developers:"
echo "   Health Check: http://$ALB_DNS/api/reports/health"
echo "   Generate Report: http://$ALB_DNS/api/reports/generate"
echo "   Report Status: http://$ALB_DNS/api/reports/status/{request_id}"
echo ""
echo "⚠️ Note: ALB may take 2-3 minutes to become active"
echo "💡 Next step: Run 'make deploy-with-alb' to deploy ECS service with ALB integration"