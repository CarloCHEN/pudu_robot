#!/bin/bash

# cleanup-failed-deployment.sh - Clean up partial deployments

# Load environment variables
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
else
    echo "❌ .env file not found."
    exit 1
fi

echo "🧹 Cleaning up failed deployment in $AWS_REGION"

# Configuration
CLUSTER_NAME="monitor-report-api-cluster"
SERVICE_NAME="monitor-report-api-service"
TASK_DEFINITION_NAME="monitor-report-api-task"

# Clean up ECS service (if it exists but failed)
echo "🗑️ Cleaning up ECS service..."
aws ecs describe-services --region $AWS_REGION --cluster $CLUSTER_NAME --services $SERVICE_NAME >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "Deleting ECS service..."
    aws ecs update-service --region $AWS_REGION --cluster $CLUSTER_NAME --service $SERVICE_NAME --desired-count 0 >/dev/null 2>&1
    aws ecs delete-service --region $AWS_REGION --cluster $CLUSTER_NAME --service $SERVICE_NAME >/dev/null 2>&1
    echo "✅ ECS service cleanup attempted"
else
    echo "ℹ️ No ECS service to clean up"
fi

# Clean up ECS cluster (if empty)
echo "🗑️ Cleaning up ECS cluster..."
aws ecs describe-clusters --region $AWS_REGION --clusters $CLUSTER_NAME >/dev/null 2>&1
if [ $? -eq 0 ]; then
    # Check if cluster has any services
    SERVICE_COUNT=$(aws ecs describe-clusters --region $AWS_REGION --clusters $CLUSTER_NAME --query 'clusters[0].activeServicesCount' --output text 2>/dev/null)
    if [ "$SERVICE_COUNT" = "0" ]; then
        echo "Deleting empty ECS cluster..."
        aws ecs delete-cluster --region $AWS_REGION --cluster $CLUSTER_NAME >/dev/null 2>&1
        echo "✅ ECS cluster deleted"
    else
        echo "ℹ️ ECS cluster has active services, keeping it"
    fi
else
    echo "ℹ️ No ECS cluster to clean up"
fi

# List task definitions (don't delete, they're versioned)
echo "📋 Task definitions (kept for reference):"
aws ecs list-task-definitions --region $AWS_REGION --family-prefix $TASK_DEFINITION_NAME --query 'taskDefinitionArns' --output table 2>/dev/null || echo "None found"

# Clean up security groups (check if they're in use)
echo "🔒 Cleaning up security groups..."
ECS_SG_NAME="monitor-report-api-ecs-sg"

# Get ECS security group ID
ECS_SG_ID=$(aws ec2 describe-security-groups \
    --region $AWS_REGION \
    --filters "Name=group-name,Values=$ECS_SG_NAME" \
    --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null)

if [ "$ECS_SG_ID" != "None" ] && [ ! -z "$ECS_SG_ID" ]; then
    # Check if security group is attached to any network interfaces
    ATTACHED_ENI=$(aws ec2 describe-network-interfaces \
        --region $AWS_REGION \
        --filters "Name=group-id,Values=$ECS_SG_ID" \
        --query 'NetworkInterfaces[0].NetworkInterfaceId' --output text 2>/dev/null)

    if [ "$ATTACHED_ENI" = "None" ] || [ -z "$ATTACHED_ENI" ]; then
        echo "Deleting unused ECS security group..."
        aws ec2 delete-security-group --region $AWS_REGION --group-id $ECS_SG_ID 2>/dev/null
        echo "✅ ECS security group deleted"
    else
        echo "⚠️ ECS security group still in use, keeping it"
    fi
else
    echo "ℹ️ No ECS security group to clean up"
fi

echo ""
echo "🎯 After cleanup, you can retry deployment with:"
echo "   make deploy-with-alb"
echo ""
echo "🔍 Or start completely fresh with:"
echo "   make clean-config"
echo "   make deploy-us-east-1-alb"