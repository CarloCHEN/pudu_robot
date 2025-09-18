#!/bin/bash

# check-alb-status.sh - Monitor ALB and ECS service status

# Load environment variables
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

# Load ALB configuration
if [ -f "alb-config.env" ]; then
    set -a
    source alb-config.env
    set +a
else
    echo "❌ ALB configuration not found."
    exit 1
fi

echo "🔍 ALB and ECS Service Status Check"
echo "=================================="
echo "Region: $AWS_REGION"
echo "ALB DNS: $ALB_DNS_NAME"
echo ""

# Check ALB status
echo "⚖️ ALB Status:"
ALB_STATE=$(aws elbv2 describe-load-balancers \
    --region $AWS_REGION \
    --load-balancer-arns $ALB_ARN \
    --query 'LoadBalancers[0].State.Code' --output text 2>/dev/null)

if [ "$ALB_STATE" = "active" ]; then
    echo "   ✅ ALB is active"
else
    echo "   ❌ ALB state: $ALB_STATE"
fi

# Check target group health
echo ""
echo "🎯 Target Group Health:"
HEALTHY_TARGETS=$(aws elbv2 describe-target-health \
    --region $AWS_REGION \
    --target-group-arn $TARGET_GROUP_ARN \
    --query 'length(TargetHealthDescriptions[?TargetHealth.State==`healthy`])' --output text 2>/dev/null)

TOTAL_TARGETS=$(aws elbv2 describe-target-health \
    --region $AWS_REGION \
    --target-group-arn $TARGET_GROUP_ARN \
    --query 'length(TargetHealthDescriptions)' --output text 2>/dev/null)

echo "   Healthy: $HEALTHY_TARGETS/$TOTAL_TARGETS targets"

if [ "$HEALTHY_TARGETS" -gt 0 ]; then
    echo "   ✅ At least one healthy target"
else
    echo "   ❌ No healthy targets"
    echo ""
    echo "🔍 Target Details:"
    aws elbv2 describe-target-health \
        --region $AWS_REGION \
        --target-group-arn $TARGET_GROUP_ARN \
        --query 'TargetHealthDescriptions[].{Target:Target.Id,State:TargetHealth.State,Reason:TargetHealth.Reason}' \
        --output table 2>/dev/null
fi

# Check ECS service status
echo ""
echo "🏗️ ECS Service Status:"
CLUSTER_NAME="monitor-report-api-cluster"
SERVICE_NAME="monitor-report-api-service"

RUNNING_COUNT=$(aws ecs describe-services \
    --region $AWS_REGION \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --query 'services[0].runningCount' --output text 2>/dev/null)

DESIRED_COUNT=$(aws ecs describe-services \
    --region $AWS_REGION \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --query 'services[0].desiredCount' --output text 2>/dev/null)

if [ "$RUNNING_COUNT" = "$DESIRED_COUNT" ] && [ "$RUNNING_COUNT" -gt 0 ]; then
    echo "   ✅ Service is healthy: $RUNNING_COUNT/$DESIRED_COUNT tasks running"
else
    echo "   ⚠️ Service status: $RUNNING_COUNT/$DESIRED_COUNT tasks running"
fi

# Test API endpoint
echo ""
echo "🧪 API Health Check:"
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://$ALB_DNS_NAME/api/reports/health" 2>/dev/null)

if [ "$HTTP_STATUS" = "200" ]; then
    echo "   ✅ API is responding (HTTP $HTTP_STATUS)"
    echo ""
    echo "📋 API Response:"
    curl -s "http://$ALB_DNS_NAME/api/reports/health" | python -m json.tool 2>/dev/null || echo "   (Could not parse JSON response)"
else
    echo "   ❌ API not responding (HTTP $HTTP_STATUS)"
fi

echo ""
echo "🌐 Public Endpoints:"
echo "   Health: http://$ALB_DNS_NAME/api/reports/health"
echo "   Generate: http://$ALB_DNS_NAME/api/reports/generate"
echo "   Status: http://$ALB_DNS_NAME/api/reports/status/{request_id}"

# Show recent ECS events if there are issues
if [ "$RUNNING_COUNT" != "$DESIRED_COUNT" ] || [ "$HEALTHY_TARGETS" -eq 0 ]; then
    echo ""
    echo "🔍 Recent ECS Service Events:"
    aws ecs describe-services \
        --region $AWS_REGION \
        --cluster $CLUSTER_NAME \
        --services $SERVICE_NAME \
        --query 'services[0].events[:5].{Time:createdAt,Message:message}' \
        --output table 2>/dev/null
fi