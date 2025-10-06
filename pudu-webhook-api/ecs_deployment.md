# Multi-Brand, Multi-Region ECS Deployment Guide

Complete guide for deploying Pudu and Gas robot webhook services to AWS ECS across multiple regions.

## 📋 Quick Reference

### Available Deployment Commands

```bash
# Pudu Deployments
make deploy-us-east-1-pudu    # Deploy Pudu to us-east-1
make deploy-us-east-2-pudu    # Deploy Pudu to us-east-2

# Gas Deployments
make deploy-us-east-1-gas     # Deploy Gas to us-east-1
make deploy-us-east-2-gas     # Deploy Gas to us-east-2

# Legacy (defaults to Pudu)
make deploy-us-east-1         # Same as deploy-us-east-1-pudu
make deploy-us-east-2         # Same as deploy-us-east-2-pudu
```

## 🚀 Initial Setup (First Time Only)

### Step 1: Create Template Files

```bash
# Make scripts executable
chmod +x create-templates.sh
chmod +x setup-environment.sh
chmod +x deploy.sh

# Generate template files
./create-templates.sh
```

This creates:
- `rds/credentials.yaml.template`
- `.env.template`
- `notifications/.env.template`

### Step 2: Configure Secrets

Edit `setup-environment.sh` to add your secrets:

```bash
# Find and replace these values:
# 1. AWS_ACCOUNT_ID (if different from 908027373537)
# 2. Add your callback codes:

# Add these lines in the appropriate region sections:
export PUDU_CALLBACK_CODE="your-actual-pudu-callback-code"
export GAS_CALLBACK_CODE="your-actual-gas-callback-code"
```

Or set as environment variables before running setup:

```bash
export PUDU_CALLBACK_CODE="your-pudu-code"
export GAS_CALLBACK_CODE="your-gas-code"
```

## 📦 Deployment Workflows

### Workflow 1: Deploy Single Brand to Single Region

```bash
# Deploy Pudu to us-east-2 (staging)
make deploy-us-east-2-pudu

# Deploy Gas to us-east-1 (production)
make deploy-us-east-1-gas
```

**What happens:**
1. Cleans any existing config files
2. Generates brand-specific config for selected region
3. Builds Docker image with brand configuration
4. Tags image as `foxx_monitor_<brand>_webhook_api:latest`
5. Pushes to ECR in selected region

### Workflow 2: Deploy Both Brands to Same Region

```bash
# Deploy both to us-east-2
make deploy-us-east-2-pudu
make deploy-us-east-2-gas

# Deploy both to us-east-1
make deploy-us-east-1-pudu
make deploy-us-east-1-gas
```

**Result:** Two separate ECR images in same region:
- `foxx_monitor_pudu_webhook_api:latest`
- `foxx_monitor_gas_webhook_api:latest`

### Workflow 3: Deploy Same Brand to Multiple Regions

```bash
# Deploy Pudu to both regions
make deploy-us-east-1-pudu
make deploy-us-east-2-pudu

# Deploy Gas to both regions
make deploy-us-east-1-gas
make deploy-us-east-2-gas
```

**Result:** Same brand deployed to two regions with region-specific configurations.

### Workflow 4: Step-by-Step Deployment (Manual Control)

```bash
# 1. Setup configuration only
make setup-us-east-2-gas

# 2. Verify what was generated
make verify-config

# 3. Check configuration variables
make print-vars

# 4. Deploy when ready
make deploy-container
```

## 🔍 Configuration Management

### Check Current Configuration

```bash
# Show current brand and region
make verify-config

# Output example:
# ✅ .env exists
# Brand: gas
# AWS Region: us-east-2
# Notification Host: NOTIFICATION_API_HOST=alb-notice-1223048054.us-east-2.elb.amazonaws.com
```

### Switch Configuration Without Deploying

```bash
# Switch to Gas in us-east-1
make setup-us-east-1-gas

# Switch to Pudu in us-east-2
make setup-us-east-2-pudu

# Verify the switch
make verify-config
```

### View All Configuration Variables

```bash
make print-vars

# Output:
# BRAND=gas
# APP_NAME=foxx_monitor_gas_webhook_api
# AWS_REGION=us-east-2
# AWS_ACCOUNT_ID=908027373537
# REGISTRY_NAME=foxx_monitor_gas_webhook_api
```

## 📁 Generated Configuration Files

Each setup command generates these files:

### Root `.env`
```bash
AWS_ACCOUNT_ID=908027373537
AWS_REGION=us-east-2
REGISTRY_NAME=foxx_monitor_gas_webhook_api
TAG=latest
BRAND=gas
PUDU_CALLBACK_CODE=your-pudu-code
GAS_CALLBACK_CODE=your-gas-code
# ... other configs
```

### `notifications/.env`
```bash
NOTIFICATION_API_HOST=alb-notice-1223048054.us-east-2.elb.amazonaws.com
NOTIFICATION_API_ENDPOINT=/notification-api/robot/notification/send
ICONS_CONFIG_PATH=icons.yaml
```

### `rds/credentials.yaml`
```yaml
host: nexusiq-web-prod-database.cpgi0kcaa8wn.us-east-2.rds.amazonaws.com
port: 3306
secret_name: rds!db-12d35fce-6171-4db1-a7e1-c75f1503ffed
region: us-east-2
```

## 🏗️ ECS Task Setup

### Step 1: Create Task Definition

Create separate task definitions for each brand:

**Task Definition Names:**
- `pudu-webhook-us-east-1`
- `pudu-webhook-us-east-2`
- `gas-webhook-us-east-1`
- `gas-webhook-us-east-2`

**Configuration:**
```json
{
  "family": "gas-webhook-us-east-2",
  "containerDefinitions": [{
    "name": "gas-webhook",
    "image": "908027373537.dkr.ecr.us-east-2.amazonaws.com/foxx_monitor_gas_webhook_api:latest",
    "portMappings": [{"containerPort": 8000, "protocol": "tcp"}],
    "environment": [
      {"name": "HOST", "value": "0.0.0.0"},
      {"name": "PORT", "value": "8000"},
      {"name": "BRAND", "value": "gas"},
      {"name": "GAS_CALLBACK_CODE", "value": "your-gas-callback-code"},
      {"name": "DEBUG", "value": "false"},
      {"name": "LOG_LEVEL", "value": "INFO"}
    ]
  }]
}
```

### Step 2: Create ECS Service

**Service Names:**
- `pudu-webhook-service-useast1`
- `pudu-webhook-service-useast2`
- `gas-webhook-service-useast1`
- `gas-webhook-service-useast2`

**Configuration:**
- **Desired count**: 1 (or more for high availability)
- **Launch type**: Fargate
- **Platform version**: LATEST
- **Network mode**: awsvpc

### Step 3: Configure Load Balancer (Optional)

For production deployments, create ALB with brand-specific target groups:

**Target Groups:**
- `pudu-webhook-tg-useast1`
- `gas-webhook-tg-useast1`

**ALB Rules:**
- Path `/api/pudu/*` → Pudu target group
- Path `/api/gas/*` → Gas target group

## 🧪 Testing Deployments

### Test Each Brand Endpoint

```bash
# Get public IP or ALB DNS
PUBLIC_IP="13.220.117.7"

# Test Pudu endpoint
curl http://$PUBLIC_IP:8000/api/pudu/webhook/health

# Expected response:
{
  "status": "healthy",
  "brand": "pudu",
  "endpoint": "/api/pudu/webhook",
  "configuration": {
    "brand": "pudu",
    "method": "header",
    "key": "callbackcode"
  }
}

# Test Gas endpoint
curl http://$PUBLIC_IP:8000/api/gas/webhook/health

# Expected response:
{
  "status": "healthy",
  "brand": "gas",
  "endpoint": "/api/gas/webhook",
  "configuration": {
    "brand": "gas",
    "method": "body",
    "key": "appId"
  }
}
```

### Test Webhook Functionality

```bash
# Test Pudu callback
curl -X POST http://$PUBLIC_IP:8000/api/pudu/webhook \
  -H "Content-Type: application/json" \
  -H "CallbackCode: your-pudu-code" \
  -d '{
    "callback_type": "robotStatus",
    "data": {"sn": "PUDU-001", "run_status": "ONLINE", "timestamp": 1640995800}
  }'

# Test Gas callback
curl -X POST http://$PUBLIC_IP:8000/api/gas/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "appId": "your-gas-code",
    "messageTypeId": 1,
    "payload": {
      "serialNumber": "GAS-001",
      "content": {"incidentId": "123", "incidentLevel": "H2"}
    },
    "messageTimestamp": 1715740800000
  }'
```

## 🔧 Advanced Usage

### Local Testing Before Deployment

```bash
# Build locally for specific brand
make setup-us-east-2-gas
make build-local

# Run locally
make run-local

# Test locally
make test-api
```

### Deploy to Custom Region

To add a new region (e.g., `eu-west-1`), edit `setup-environment.sh`:

```bash
"eu-west-1")
  export AWS_REGION="eu-west-1"
  export AWS_ACCOUNT_ID="908027373537"
  export RDS_HOST="your-eu-rds-host"
  export RDS_SECRET_NAME="your-eu-secret"
  export NOTIFICATION_API_HOST="your-eu-notification-host"
  ;;
```

Then add Makefile targets:

```makefile
setup-eu-west-1-pudu: clean-config
	./setup-environment.sh eu-west-1 pudu

deploy-eu-west-1-pudu: setup-eu-west-1-pudu deploy-container
```

## 🧹 Cleanup Commands

```bash
# Clean configuration files
make clean-config

# Clean Docker images
make clean-docker

# Start fresh
make clean-config clean-docker
```

## 📊 Monitoring Multi-Brand Deployments

### CloudWatch Log Groups

Separate log groups for each brand:
- `/ecs/pudu-webhook-useast1`
- `/ecs/pudu-webhook-useast2`
- `/ecs/gas-webhook-useast1`
- `/ecs/gas-webhook-useast2`

### View Brand-Specific Logs

```bash
# Pudu logs
aws logs tail /ecs/pudu-webhook-useast2 --follow

# Gas logs
aws logs tail /ecs/gas-webhook-useast1 --follow

# Filter for errors
aws logs filter-log-events \
  --log-group-name /ecs/gas-webhook-useast1 \
  --filter-pattern "ERROR"
```

## 🚨 Troubleshooting

### Issue: Wrong Brand Configuration

```bash
# Check which brand is configured
make verify-config

# If wrong, clean and reconfigure
make clean-config
make setup-us-east-2-gas
```

### Issue: Verification Fails

```bash
# Check environment variables in task definition
aws ecs describe-task-definition \
  --task-definition gas-webhook-useast2 \
  --query 'taskDefinition.containerDefinitions[0].environment'

# Ensure correct callback code is set:
# {"name": "GAS_CALLBACK_CODE", "value": "correct-code"}
```

### Issue: Database Connection Fails

```bash
# Check RDS credentials
cat rds/credentials.yaml

# Ensure task has correct IAM permissions for Secrets Manager
# Ensure security group allows MySQL traffic from ECS
```

### Issue: Deployment to Wrong Region

```bash
# Verify current region
grep AWS_REGION .env

# If wrong, reconfigure
make setup-<correct-region>-<correct-brand>
make deploy-container
```

## 📝 Deployment Checklist

Before deploying to production:

- [ ] Secrets configured in `setup-environment.sh` or environment
- [ ] Correct region selected (`us-east-1` vs `us-east-2`)
- [ ] Correct brand selected (`pudu` vs `gas`)
- [ ] Database credentials updated in `credentials.yaml.template`
- [ ] Notification host configured for region
- [ ] ECS task definition created with correct image URI
- [ ] Security groups allow traffic (port 8000 inbound, MySQL outbound)
- [ ] IAM role has Secrets Manager permissions
- [ ] CloudWatch log group created
- [ ] Health check endpoint tested
- [ ] Webhook endpoint tested with sample data

## 🎯 Common Deployment Patterns

### Pattern 1: Staging → Production

```bash
# 1. Deploy to staging (us-east-2)
make deploy-us-east-2-gas

# 2. Test thoroughly
curl http://staging-ip:8000/api/gas/webhook/health

# 3. Deploy to production (us-east-1)
make deploy-us-east-1-gas

# 4. Verify production
curl http://prod-ip:8000/api/gas/webhook/health
```

### Pattern 2: Blue-Green Deployment

```bash
# 1. Deploy new version to "green" environment
make deploy-us-east-1-gas

# 2. Run both versions simultaneously
# Keep old "blue" ECS service running
# Create new "green" ECS service with new image

# 3. Test green environment
curl http://green-alb:8000/api/gas/webhook/health

# 4. Switch traffic using ALB weighted target groups
# Blue: 90%, Green: 10%
# Monitor for errors

# 5. Gradually shift traffic
# Blue: 50%, Green: 50%
# Blue: 10%, Green: 90%
# Blue: 0%, Green: 100%

# 6. Decommission blue environment
```

### Pattern 3: Multi-Region Active-Active

```bash
# Deploy same brand to both regions
make deploy-us-east-1-pudu
make deploy-us-east-2-pudu

# Use Route53 for geo-routing or latency-based routing
# Each region handles callbacks independently
# Database writes to region-specific RDS or shared RDS
```

### Pattern 4: Brand-Specific Regions

```bash
# Pudu in production (us-east-1)
make deploy-us-east-1-pudu

# Gas in staging (us-east-2)
make deploy-us-east-2-gas

# Different brands, different regions
# Independent deployments and monitoring
```

## 🔐 Security Best Practices

### Secrets Management

**Option 1: Environment Variables (Current)**
```bash
# In setup-environment.sh or .env
PUDU_CALLBACK_CODE=your-secret-code
GAS_CALLBACK_CODE=your-secret-code
```

**Option 2: AWS Secrets Manager (Recommended for Production)**

```bash
# Store secrets
aws secretsmanager create-secret \
  --name /robot-webhook/pudu/callback-code \
  --secret-string "your-pudu-code" \
  --region us-east-1

aws secretsmanager create-secret \
  --name /robot-webhook/gas/callback-code \
  --secret-string "your-gas-code" \
  --region us-east-1
```

Update ECS task definition:
```json
{
  "secrets": [
    {
      "name": "PUDU_CALLBACK_CODE",
      "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:/robot-webhook/pudu/callback-code"
    },
    {
      "name": "GAS_CALLBACK_CODE",
      "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:/robot-webhook/gas/callback-code"
    }
  ]
}
```

### Network Security

```bash
# ECS Security Group (Inbound)
Port 8000: Allow from ALB security group only (not 0.0.0.0/0)

# ECS Security Group (Outbound)
Port 3306: Allow to RDS security group (MySQL)
Port 443: Allow to 0.0.0.0/0 (for Secrets Manager, Notifications)

# RDS Security Group (Inbound)
Port 3306: Allow from ECS security group only
```

### IAM Permissions

**ECS Task Execution Role:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

**ECS Task Role:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:*:*:secret:/robot-webhook/*",
        "arn:aws:secretsmanager:*:*:secret:rds!*"
      ]
    }
  ]
}
```

## 📈 Scaling and Performance

### Auto Scaling Configuration

**Target Tracking Scaling (Recommended):**
```json
{
  "TargetValue": 70.0,
  "PredefinedMetricSpecification": {
    "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
  },
  "ScaleInCooldown": 300,
  "ScaleOutCooldown": 60
}
```

**Min/Max Tasks:**
- **Development**: Min=1, Max=2
- **Staging**: Min=1, Max=3
- **Production**: Min=2, Max=10

### Resource Allocation by Brand

**Pudu (Lower Frequency):**
- CPU: 0.25 vCPU
- Memory: 0.5 GB
- Tasks: 1-2

**Gas (Higher Frequency + Reports):**
- CPU: 0.5 vCPU
- Memory: 1 GB
- Tasks: 2-5

### Performance Monitoring

```bash
# Monitor CPU utilization
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=gas-webhook-service-useast1 \
  --start-time 2025-10-03T00:00:00Z \
  --end-time 2025-10-03T23:59:59Z \
  --period 3600 \
  --statistics Average

# Monitor memory utilization
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name MemoryUtilization \
  --dimensions Name=ServiceName,Value=gas-webhook-service-useast1 \
  --start-time 2025-10-03T00:00:00Z \
  --end-time 2025-10-03T23:59:59Z \
  --period 3600 \
  --statistics Average
```

## 🔔 Alerting and Monitoring

### CloudWatch Alarms

**1. Service Health Alarm**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name gas-webhook-unhealthy-useast1 \
  --alarm-description "Gas webhook service unhealthy" \
  --metric-name HealthyHostCount \
  --namespace AWS/ApplicationELB \
  --statistic Average \
  --period 60 \
  --threshold 1 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 2
```

**2. Task Count Alarm**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name gas-webhook-no-tasks-useast1 \
  --alarm-description "No tasks running for Gas webhook" \
  --metric-name RunningTaskCount \
  --namespace ECS/ContainerInsights \
  --statistic Average \
  --period 60 \
  --threshold 1 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=ServiceName,Value=gas-webhook-service-useast1
```

**3. Database Write Failures**
```bash
aws logs put-metric-filter \
  --log-group-name /ecs/gas-webhook-useast1 \
  --filter-name DatabaseWriteErrors \
  --filter-pattern "[time, request_id, level=ERROR*, msg=\"*database*\"]" \
  --metric-transformations \
    metricName=DatabaseErrors,\
    metricNamespace=RobotWebhook/Gas,\
    metricValue=1
```

### Monitoring Dashboard

Create a CloudWatch dashboard for each brand:

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "title": "Gas Webhook - Request Count",
        "metrics": [
          ["AWS/ApplicationELB", "RequestCount", {"stat": "Sum"}]
        ]
      }
    },
    {
      "type": "metric",
      "properties": {
        "title": "Gas Webhook - Response Time",
        "metrics": [
          ["AWS/ApplicationELB", "TargetResponseTime", {"stat": "Average"}]
        ]
      }
    },
    {
      "type": "log",
      "properties": {
        "title": "Gas Webhook - Recent Errors",
        "query": "SOURCE '/ecs/gas-webhook-useast1' | fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 20"
      }
    }
  ]
}
```

## 🆘 Disaster Recovery

### Backup Strategy

**1. Configuration Backups**
```bash
# Backup current configuration
make print-vars > config-backup-$(date +%Y%m%d).txt
cp .env .env.backup-$(date +%Y%m%d)
cp configs/gas/config.yaml configs/gas/config.yaml.backup-$(date +%Y%m%d)
```

**2. Database Backups**
- Enable automated RDS snapshots (daily)
- Retain snapshots for 30 days
- Test restore process monthly

**3. ECR Image Backups**
```bash
# Tag production images
docker pull 908027373537.dkr.ecr.us-east-1.amazonaws.com/foxx_monitor_gas_webhook_api:latest
docker tag foxx_monitor_gas_webhook_api:latest foxx_monitor_gas_webhook_api:prod-backup-$(date +%Y%m%d)
docker push 908027373537.dkr.ecr.us-east-1.amazonaws.com/foxx_monitor_gas_webhook_api:prod-backup-$(date +%Y%m%d)
```

### Recovery Procedures

**Scenario 1: Service Degradation**
```bash
# 1. Check service health
aws ecs describe-services \
  --cluster robot-webhook-cluster \
  --services gas-webhook-service-useast1

# 2. Check task health
aws ecs list-tasks \
  --cluster robot-webhook-cluster \
  --service-name gas-webhook-service-useast1

# 3. Force new deployment
aws ecs update-service \
  --cluster robot-webhook-cluster \
  --service gas-webhook-service-useast1 \
  --force-new-deployment
```

**Scenario 2: Complete Service Failure**
```bash
# 1. Deploy to backup region
make deploy-us-east-2-gas

# 2. Update DNS/Route53 to point to backup region
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch file://failover-to-useast2.json

# 3. Investigate primary region issues
# 4. Restore primary region
# 5. Failback when ready
```

**Scenario 3: Database Corruption**
```bash
# 1. Stop all webhook services to prevent further writes
aws ecs update-service \
  --cluster robot-webhook-cluster \
  --service gas-webhook-service-useast1 \
  --desired-count 0

# 2. Restore RDS from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier robot-webhook-db-restored \
  --db-snapshot-identifier robot-webhook-db-snapshot-20251003

# 3. Update credentials.yaml with new endpoint
# 4. Redeploy services
make deploy-us-east-1-gas

# 5. Verify data integrity
# 6. Resume normal operations
```

## 📚 Additional Resources

### Documentation Links

- **AWS ECS Documentation**: https://docs.aws.amazon.com/ecs/
- **AWS ECR Documentation**: https://docs.aws.amazon.com/ecr/
- **Fargate Pricing**: https://aws.amazon.com/fargate/pricing/
- **CloudWatch Logs**: https://docs.aws.amazon.com/cloudwatch/

### Internal Documentation

- **Brand Configuration Guide**: `README.md#adding-new-robot-brands`
- **Field Mapping Reference**: `configs/*/config.yaml`
- **Database Schema**: Check with DBA team
- **Notification System**: `notifications/README.md`

### Support Contacts

- **DevOps Team**: devops@company.com
- **Database Team**: dba@company.com
- **Robot Integration**: robot-integration@company.com

## 📝 Deployment History Template

Keep track of deployments:

```markdown
## Deployment History

### 2025-10-03 - Gas Webhook US-East-1
- **Brand**: Gas
- **Region**: us-east-1
- **Image**: foxx_monitor_gas_webhook_api:latest
- **Task Definition**: gas-webhook-useast1:3
- **Deployed By**: engineer@company.com
- **Status**: ✅ Success
- **Notes**: Initial Gas deployment to production

### 2025-09-28 - Pudu Webhook US-East-2
- **Brand**: Pudu
- **Region**: us-east-2
- **Image**: foxx_monitor_pudu_webhook_api:latest
- **Task Definition**: pudu-webhook-useast2:5
- **Deployed By**: engineer@company.com
- **Status**: ✅ Success
- **Notes**: Updated field mappings for new Pudu API
```

## ✅ Final Checklist

Before considering deployment complete:

**Pre-Deployment:**
- [ ] Configuration files generated and verified
- [ ] Secrets properly configured
- [ ] Database accessible from ECS
- [ ] Security groups configured
- [ ] IAM roles created with correct permissions

**Deployment:**
- [ ] Image built and pushed to ECR
- [ ] ECS task definition created/updated
- [ ] ECS service created with correct task definition
- [ ] Load balancer configured (if applicable)
- [ ] Auto-scaling policies configured

**Post-Deployment:**
- [ ] Health check endpoint returns 200
- [ ] Brand-specific health check passes
- [ ] Webhook endpoint accepts test callbacks
- [ ] Database writes confirmed
- [ ] Notifications working (if applicable)
- [ ] CloudWatch logs streaming
- [ ] CloudWatch alarms created
- [ ] Monitoring dashboard created
- [ ] Documentation updated
- [ ] Team notified

**Ongoing:**
- [ ] Monitor logs for first 24 hours
- [ ] Review metrics weekly
- [ ] Update secrets quarterly
- [ ] Test disaster recovery procedures monthly
- [ ] Review and update documentation as needed
