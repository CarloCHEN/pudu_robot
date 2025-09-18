#!/bin/bash

# deploy-with-alb.sh - Deploy ECS service with ALB integration

# Load environment variables
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
else
    echo "❌ .env file not found. Run setup first."
    exit 1
fi

# Load ALB configuration
if [ -f "alb-config.env" ]; then
    set -a
    source alb-config.env
    set +a
else
    echo "❌ ALB configuration not found. Run 'make setup-alb' first."
    exit 1
fi

echo "🚀 Deploying Report API with ALB integration"
echo "Region: $AWS_REGION"
echo "ALB DNS: $ALB_DNS_NAME"

# Configuration
CLUSTER_NAME="monitor-report-api-cluster"
SERVICE_NAME="monitor-report-api-service"
TASK_DEFINITION_NAME="monitor-report-api-task"
EXECUTION_ROLE_NAME="ecsTaskExecutionRole"

# First, build and push the image (reuse existing deploy.sh logic)
echo "📦 Building and pushing Docker image..."
bash deploy.sh

if [ $? -ne 0 ]; then
    echo "❌ Failed to build and push image"
    exit 1
fi

# Get or create ECS cluster EARLY
echo "🏗️ Setting up ECS cluster..."
CLUSTER_EXISTS=$(aws ecs describe-clusters --region $AWS_REGION --clusters $CLUSTER_NAME --query 'clusters[0].status' --output text 2>/dev/null)

if [ "$CLUSTER_EXISTS" = "ACTIVE" ]; then
    echo "✅ Using existing cluster: $CLUSTER_NAME"
elif [ "$CLUSTER_EXISTS" = "INACTIVE" ]; then
    echo "⚠️ Cluster exists but is INACTIVE, deleting and recreating..."
    aws ecs delete-cluster --region $AWS_REGION --cluster $CLUSTER_NAME
    sleep 5

    echo "Creating fresh ECS cluster: $CLUSTER_NAME"
    aws ecs create-cluster --region $AWS_REGION --cluster-name $CLUSTER_NAME
    sleep 10

    # Verify cluster was created
    CLUSTER_STATUS=$(aws ecs describe-clusters --region $AWS_REGION --clusters $CLUSTER_NAME --query 'clusters[0].status' --output text 2>/dev/null)
    if [ "$CLUSTER_STATUS" != "ACTIVE" ]; then
        echo "❌ Failed to create ECS cluster. Status: $CLUSTER_STATUS"
        exit 1
    fi
    echo "✅ ECS cluster recreated and active"
elif [ "$CLUSTER_EXISTS" = "None" ] || [ -z "$CLUSTER_EXISTS" ]; then
    echo "Creating ECS cluster: $CLUSTER_NAME"
    aws ecs create-cluster --region $AWS_REGION --cluster-name $CLUSTER_NAME

    # Wait a moment for cluster to be ready
    echo "⏳ Waiting for cluster to be ready..."
    sleep 10

    # Verify cluster was created
    CLUSTER_STATUS=$(aws ecs describe-clusters --region $AWS_REGION --clusters $CLUSTER_NAME --query 'clusters[0].status' --output text 2>/dev/null)
    if [ "$CLUSTER_STATUS" != "ACTIVE" ]; then
        echo "❌ Failed to create ECS cluster. Status: $CLUSTER_STATUS"
        exit 1
    fi
    echo "✅ ECS cluster created and active"
else
    echo "⚠️ Cluster in unexpected state: $CLUSTER_EXISTS"
    echo "Deleting and recreating cluster..."
    aws ecs delete-cluster --region $AWS_REGION --cluster $CLUSTER_NAME 2>/dev/null || true
    sleep 5

    echo "Creating fresh ECS cluster: $CLUSTER_NAME"
    aws ecs create-cluster --region $AWS_REGION --cluster-name $CLUSTER_NAME
    sleep 10

    # Verify cluster was created
    CLUSTER_STATUS=$(aws ecs describe-clusters --region $AWS_REGION --clusters $CLUSTER_NAME --query 'clusters[0].status' --output text 2>/dev/null)
    if [ "$CLUSTER_STATUS" != "ACTIVE" ]; then
        echo "❌ Failed to create ECS cluster. Status: $CLUSTER_STATUS"
        exit 1
    fi
    echo "✅ ECS cluster recreated and active"
fi

# Get execution role ARN
echo "🔐 Setting up ECS execution role..."
# Get or create task execution role AND task role
EXECUTION_ROLE_ARN=$(aws iam get-role --role-name $EXECUTION_ROLE_NAME --query 'Role.Arn' --output text 2>/dev/null)
if [ "$EXECUTION_ROLE_ARN" = "None" ] || [ -z "$EXECUTION_ROLE_ARN" ]; then
    echo "❌ ECS Task Execution Role not found. Creating..."

    # Create trust policy
    cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

    # Create role
    aws iam create-role \
        --role-name $EXECUTION_ROLE_NAME \
        --assume-role-policy-document file://trust-policy.json

    # Attach managed policy
    aws iam attach-role-policy \
        --role-name $EXECUTION_ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

    # Get the ARN
    EXECUTION_ROLE_ARN=$(aws iam get-role --role-name $EXECUTION_ROLE_NAME --query 'Role.Arn' --output text)

    # Clean up
    rm trust-policy.json
fi

# Create or get task role (for application permissions)
TASK_ROLE_NAME="monitor-report-api-task-role"
TASK_ROLE_ARN=$(aws iam get-role --role-name $TASK_ROLE_NAME --query 'Role.Arn' --output text 2>/dev/null)

if [ "$TASK_ROLE_ARN" = "None" ] || [ -z "$TASK_ROLE_ARN" ]; then
    echo "🔐 Creating task role for RDS and S3 access..."

    # Create trust policy
    cat > task-trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

    # Create task role
    aws iam create-role \
        --role-name $TASK_ROLE_NAME \
        --assume-role-policy-document file://task-trust-policy.json

    # Create custom policy for RDS and S3 access
    cat > task-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rds:DescribeDBInstances",
        "rds:DescribeDBClusters",
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret",
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": "*"
    }
  ]
}
EOF

    # Create and attach policy
    aws iam put-role-policy \
        --role-name $TASK_ROLE_NAME \
        --policy-name "MonitorReportApiPolicy" \
        --policy-document file://task-policy.json

    # Get the ARN
    TASK_ROLE_ARN=$(aws iam get-role --role-name $TASK_ROLE_NAME --query 'Role.Arn' --output text)

    # Clean up
    rm task-trust-policy.json task-policy.json
    echo "✅ Created task role: $TASK_ROLE_ARN"
else
    echo "✅ Using existing task role: $TASK_ROLE_ARN"
fi

echo "✅ Using execution role: $EXECUTION_ROLE_ARN"
echo "✅ Using task role: $TASK_ROLE_ARN"

# Create task definition
echo "📋 Creating ECS task definition..."
cat > task-definition.json << EOF
{
  "family": "$TASK_DEFINITION_NAME",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "$EXECUTION_ROLE_ARN",
  "taskRoleArn": "$TASK_ROLE_ARN",
  "containerDefinitions": [
    {
      "name": "monitor-report-api",
      "image": "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REGISTRY_NAME:$TAG",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "environment": [
        {"name": "AWS_DEFAULT_REGION", "value": "$AWS_REGION"},
        {"name": "AWS_REGION", "value": "$AWS_REGION"},
        {"name": "S3_REPORTS_BUCKET", "value": "$S3_REPORTS_BUCKET"},
        {"name": "PORT", "value": "8000"},
        {"name": "HOST", "value": "0.0.0.0"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/monitor-report-api",
          "awslogs-region": "$AWS_REGION",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/api/reports/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
EOF

# Create CloudWatch log group
aws logs create-log-group --region $AWS_REGION --log-group-name "/ecs/monitor-report-api" 2>/dev/null || true

# Register task definition
TASK_DEF_ARN=$(aws ecs register-task-definition \
    --region $AWS_REGION \
    --cli-input-json file://task-definition.json \
    --query 'taskDefinition.taskDefinitionArn' --output text)

echo "✅ Registered task definition: $TASK_DEF_ARN"

# Get subnets and create security group for ECS service
echo "🔒 Setting up ECS service security group..."
ECS_SG_NAME="monitor-report-api-ecs-sg"
ECS_SG_ID=$(aws ec2 create-security-group \
    --region $AWS_REGION \
    --group-name $ECS_SG_NAME \
    --description "Security group for Monitor Report API ECS service" \
    --vpc-id $VPC_ID \
    --query 'GroupId' --output text 2>/dev/null)

if [ $? -ne 0 ]; then
    # Security group might already exist
    ECS_SG_ID=$(aws ec2 describe-security-groups \
        --region $AWS_REGION \
        --filters "Name=group-name,Values=$ECS_SG_NAME" "Name=vpc-id,Values=$VPC_ID" \
        --query 'SecurityGroups[0].GroupId' --output text)
    echo "✅ Using existing ECS security group: $ECS_SG_ID"
else
    echo "✅ Created ECS security group: $ECS_SG_ID"
fi

# Allow ALB to access ECS service
aws ec2 authorize-security-group-ingress \
    --region $AWS_REGION \
    --group-id $ECS_SG_ID \
    --protocol tcp \
    --port 8000 \
    --source-group $SECURITY_GROUP_ID 2>/dev/null

# Get subnets and format them properly
echo "🔍 Getting subnets for ECS service..."
SUBNET_IDS=$(aws ec2 describe-subnets --region $AWS_REGION --filters "Name=vpc-id,Values=$VPC_ID" "Name=default-for-az,Values=true" --query 'Subnets[].SubnetId' --output text)

# Convert space-separated to comma-separated for JSON
SUBNET_JSON=$(echo $SUBNET_IDS | tr ' ' '\n' | sed 's/^/"/; s/$/"/; $!s/$/,/' | tr -d '\n')
SUBNET_JSON="[$SUBNET_JSON]"

echo "✅ Using subnets: $SUBNET_IDS"
echo "✅ Subnet JSON: $SUBNET_JSON"

# Create or update ECS service
echo "🚀 Creating/updating ECS service..."

# Double-check cluster exists before creating service
echo "🔍 Verifying cluster exists before service creation..."
CLUSTER_STATUS=$(aws ecs describe-clusters --region $AWS_REGION --clusters $CLUSTER_NAME --query 'clusters[0].status' --output text 2>/dev/null)

if [ "$CLUSTER_STATUS" = "INACTIVE" ]; then
    echo "⚠️ Cluster is INACTIVE, deleting and recreating..."
    aws ecs delete-cluster --region $AWS_REGION --cluster $CLUSTER_NAME
    sleep 5

    echo "Creating fresh cluster..."
    aws ecs create-cluster --region $AWS_REGION --cluster-name $CLUSTER_NAME
    sleep 10

    CLUSTER_STATUS=$(aws ecs describe-clusters --region $AWS_REGION --clusters $CLUSTER_NAME --query 'clusters[0].status' --output text 2>/dev/null)
fi

if [ "$CLUSTER_STATUS" != "ACTIVE" ]; then
    echo "❌ Cluster not ready. Status: $CLUSTER_STATUS"
    echo "📋 Available clusters:"
    aws ecs list-clusters --region $AWS_REGION --query 'clusterArns' --output table
    exit 1
fi
echo "✅ Cluster verified: $CLUSTER_NAME (Status: $CLUSTER_STATUS)"

# Create ECS service (skip the update logic for now since service doesn't exist)
echo "Creating new ECS service..."

# Create the service with proper JSON
cat > service-config.json << EOF
{
    "serviceName": "$SERVICE_NAME",
    "taskDefinition": "$TASK_DEF_ARN",
    "desiredCount": 1,
    "launchType": "FARGATE",
    "networkConfiguration": {
        "awsvpcConfiguration": {
            "subnets": $SUBNET_JSON,
            "securityGroups": ["$ECS_SG_ID"],
            "assignPublicIp": "ENABLED"
        }
    },
    "loadBalancers": [
        {
            "targetGroupArn": "$TARGET_GROUP_ARN",
            "containerName": "monitor-report-api",
            "containerPort": 8000
        }
    ]
}
EOF

aws ecs create-service \
    --region $AWS_REGION \
    --cluster $CLUSTER_NAME \
    --cli-input-json file://service-config.json

if [ $? -ne 0 ]; then
    echo "❌ Failed to create ECS service"
    cat service-config.json
    exit 1
fi

# Clean up temp file
rm service-config.json

# Clean up temporary files
rm task-definition.json 2>/dev/null || true

# Wait for service to be stable (only if service exists)
echo "⏳ Checking if service was created successfully..."
aws ecs describe-services --region $AWS_REGION --cluster $CLUSTER_NAME --services $SERVICE_NAME >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Service exists, waiting for it to become stable..."
    aws ecs wait services-stable --region $AWS_REGION --cluster $CLUSTER_NAME --services $SERVICE_NAME

    # Check service status
    RUNNING_COUNT=$(aws ecs describe-services \
        --region $AWS_REGION \
        --cluster $CLUSTER_NAME \
        --services $SERVICE_NAME \
        --query 'services[0].runningCount' --output text)
else
    echo "❌ Service was not created successfully"
    exit 1
fi

echo ""
echo "🎉 Deployment Complete!"
echo "========================"
echo "🌐 Fixed API Endpoint: http://$ALB_DNS_NAME"
echo "🏃 Running Tasks: $RUNNING_COUNT"
echo "🎯 Target Group: $TARGET_GROUP_NAME"
echo ""
echo "📋 API URLs for your developers:"
echo "   Health Check: http://$ALB_DNS_NAME/api/reports/health"
echo "   Generate Report: http://$ALB_DNS_NAME/api/reports/generate"
echo "   Report Status: http://$ALB_DNS_NAME/api/reports/status/{request_id}"
echo ""
echo "⚠️ Note: It may take 2-3 minutes for health checks to pass"
echo "🧪 Test with: curl http://$ALB_DNS_NAME/api/reports/health"