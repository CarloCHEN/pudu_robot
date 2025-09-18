# Robot Management Report API

An asynchronous FastAPI service for generating robot management reports and storing them in AWS S3.

## Overview

This API provides asynchronous report generation capabilities for robot management data, with automatic upload to region-specific S3 buckets. Multiple users can generate reports simultaneously without blocking each other.

### Features

- **Async Report Generation**: Non-blocking report generation using FastAPI background tasks
- **Multi-Region Support**: Automatic S3 bucket selection based on AWS region
- **Fixed URL via ALB**: Application Load Balancer provides permanent endpoint that never changes
- **Status Tracking**: Real-time status updates for report generation requests
- **S3 Integration**: Automatic upload to configured S3 buckets with organized folder structure
- **Report History**: Retrieve historical reports for customers
- **Health Monitoring**: Built-in health check endpoints

## Architecture

```
report_api/
├── main.py                              # FastAPI application
├── Dockerfile                           # Container configuration
├── requirements.txt                     # Python dependencies
├── setup-environment.sh                # Environment setup script
├── setup-alb.sh                        # ALB infrastructure setup
├── deploy-with-alb.sh                  # ECS deployment with ALB
├── quick-deploy.sh                     # Fast redeploy for code changes
├── deploy.sh                           # Docker image deployment
├── Makefile                            # Build automation with ALB support
└── README.md                           # This file

src/pudu/reporting/services/
└── report_delivery_service.py          # Updated async delivery service (region-aware)
```

## S3 Bucket Configuration

The API automatically selects S3 buckets based on AWS region:

- **us-east-1**: `monitor-reports-test-archive`
- **us-east-2**: `monitor-reports-archive` (default)

Reports are organized in S3 as:
```
reports/{database_name}/{year}/{month}/{timestamp}_robot_performance_report.html
```

## Quick Start

### 1. Setup Environment with ALB (Recommended)

Choose your target region and deploy with fixed URL:

```bash
# Navigate to report_api directory
cd report_api

# Complete ALB setup for us-east-1 (one command)
make deploy-us-east-1-alb

# Complete ALB setup for us-east-2 (one command)
make deploy-us-east-2-alb
```

This creates:
- `.env` - Deployment variables
- `app.env` - Application environment variables
- `alb-config.env` - ALB configuration
- Application Load Balancer with fixed URL
- ECS service connected to ALB

### 2. Daily Development (Code Changes)

```bash
# Fast redeploy after code changes (2-3 minutes)
make quick-deploy

# Check service status
make status

# Test API
make test-api
```

### 3. Legacy Deployment (Changing IP)

```bash
# For us-east-2 (production)
make setup-us-east-2

# For us-east-1 (test)
make setup-us-east-1

# Deploy
make deploy-container
```

### 4. Test Locally

```bash
# Install dependencies
make install-deps

# Test with Python directly
make test-local

# Test with Docker locally
make run-local

# Check if API is responding
make test-api
```

## API Endpoints

### Fixed URL (ALB)
After ALB setup, your API will be available at a fixed URL like:
```
http://monitor-report-api-alb-1071100458.us-east-1.elb.amazonaws.com
```

This URL **never changes** regardless of deployments!

### Generate Report
```http
POST /api/reports/generate
Content-Type: application/json

{
  "database_name": "customer-123",
  "form_data": {
    "service": "robot-management",
    "contentCategories": ["robot-status", "cleaning-tasks", "performance"],
    "timeRange": "last-30-days",
    "detailLevel": "detailed",
    "delivery": "in-app",
    "schedule": "immediate",
    "mainKey": 1,
    "reportName": "Customer Report",
    "outputFormat": "html",
    "location": {
      "country": "us",
      "state": "fl",
      "city": "gainesville",
      "building": ""
    },
    "robot": {
      "name": "",
      "serialNumber": ""
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "request_id": "uuid-here",
  "message": "Report generation started",
  "status": "queued"
}
```

### Check Report Status
```http
GET /api/reports/status/{request_id}
```

**Response (Processing):**
```json
{
  "success": true,
  "request_id": "uuid-here",
  "status": "processing",
  "report_url": null,
  "metadata": null
}
```

**Response (Completed):**
```json
{
  "success": true,
  "request_id": "uuid-here",
  "status": "completed",
  "report_url": "https://monitor-reports-archive.s3.us-east-2.amazonaws.com/reports/customer-123/2024/01/20240115_143022_robot_performance_report.html",
  "metadata": {
    "generation_time": "2024-01-15T14:30:22",
    "robots_included": 5,
    "detail_level": "detailed"
  }
}
```

### Health Check
```http
GET /api/reports/health
```

### Report History
```http
GET /api/reports/history/{database_name}?limit=50
```

### Delete Report
```http
DELETE /api/reports/delete?database_name=customer-123&report_key=reports/customer-123/2024/01/file.html
```

## Development

### Prerequisites

- Python 3.9+
- Docker
- AWS CLI configured with proper permissions
- Access to target S3 buckets and RDS instances

### Local Development Setup

1. **Clone and navigate:**
   ```bash
   cd report_api
   ```

2. **Install dependencies:**
   ```bash
   make install-deps
   ```

3. **Setup environment with ALB:**
   ```bash
   make deploy-us-east-1-alb  # Creates fixed URL
   ```

4. **Verify configuration:**
   ```bash
   make verify-config
   make status  # Check ALB and service health
   ```

5. **Test S3 access:**
   ```bash
   make check-bucket
   ```

6. **For local development:**
   ```bash
   make test-local
   ```

7. **Test API endpoints:**
   ```bash
   make test-api  # Tests ALB endpoint
   ```

### Docker Development

1. **Build image:**
   ```bash
   make build-local
   ```

2. **Run container:**
   ```bash
   make run-local
   ```

3. **Test container:**
   ```bash
   curl http://localhost:8000/api/reports/health
   ```

## Deployment Guide

### ALB Deployment (Recommended)

The ALB deployment provides a **fixed URL that never changes**:

```bash
# Complete setup and deployment to us-east-1 with fixed URL
make deploy-us-east-1-alb

# Complete setup and deployment to us-east-2 with fixed URL
make deploy-us-east-2-alb

# Quick redeploy for code changes (existing ALB) - Note: it will deploy to the last deployed region (take care!)
make quick-deploy
```

Benefits:
- ✅ Fixed URL - developers never need to update endpoints
- ✅ Zero downtime deployments
- ✅ Automatic health checks
- ✅ Load balancing ready

### Legacy Deployment (Changing IP)

```bash
# Complete setup and deployment to us-east-2
make deploy-us-east-2

# Complete setup and deployment to us-east-1
make deploy-us-east-1
```

⚠️ **Warning**: This method gives you a new IP address each deployment.

### Manual ALB Setup Steps

1. **Setup environment:**
   ```bash
   ./setup-environment.sh us-east-1
   ```

2. **Create ALB infrastructure:**
   ```bash
   ./setup-alb.sh
   ```

3. **Deploy ECS with ALB:**
   ```bash
   ./deploy-with-alb.sh
   ```

### ECS Task Configuration

When deploying to ECS, ensure these environment variables are set:

```bash
AWS_REGION=us-east-1
AWS_DEFAULT_REGION=us-east-1
S3_REPORTS_BUCKET=monitor-reports-test-archive
DATABASE_CONFIG_PATH=/app/database_config.yaml
PORT=8000
HOST=0.0.0.0
```

The API will automatically:
- Select the correct S3 bucket based on `AWS_REGION`
- Configure database connections
- Set up proper AWS SDK clients

## Testing

### API Testing

**Note**: Replace `monitor-report-api-alb-1071100458.us-east-1.elb.amazonaws.com` with your actual ALB DNS name from deployment output.

```bash
# Single building report in foxx_irvine_office
curl -X POST http://monitor-report-api-alb-2063783635.us-east-2.elb.amazonaws.com/api/reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "database_name": "foxx_irvine_office",
    "mainKey": 1,
    "form_data": {
      "service": "robot-management",
      "location": {
        "country": "us",
        "state": "fl",
        "city": "gainesville",
        "building": ["Building 43 Marston Science Library", "Building 205 Dental Science"]
      },
      "contentCategories": ["charging-performance", "cleaning-performance", "resource-utilization", "financial-performance"],
      "reportName": "UF Single Building Report",
      "outputFormat": "html",
      "timeRange": "custom",
      "customStartDate": "2025-09-01",
      "customEndDate": "2025-09-12",
      "detailLevel": "detailed"
    }
  }'

# Multiple buildings report in university_of_florida
curl -X POST http://monitor-report-api-alb-2063783635.us-east-2.elb.amazonaws.com/api/reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "database_name": "university_of_florida",
    "mainKey": 1,
    "form_data": {
      "service": "robot-management",
      "location": {
        "country": "us",
        "state": "fl",
        "city": "gainesville",
        "building": ["Building 43 Marston Science Library", "Building 205 Dental Science"]
      },
      "contentCategories": ["charging-performance", "cleaning-performance", "resource-utilization", "financial-performance"],
      "reportName": "UF Multiple Buildings Report",
      "outputFormat": "pdf",
      "timeRange": "custom",
      "customStartDate": "2025-09-01",
      "customEndDate": "2025-09-12",
      "detailLevel": "detailed"
    }
  }'

# All buildings in city (ignore building field)
curl -X POST http://monitor-report-api-alb-1071100458.us-east-1.elb.amazonaws.com/api/reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "database_name": "UF2",
    "mainKey": 1,
    "form_data": {
      "service": "robot-management",
      "location": {
        "country": "us",
        "state": "fl",
        "city": "gainesville"
      },
      "contentCategories": ["charging-performance", "cleaning-performance", "resource-utilization", "financial-performance"],
      "reportName": "UF All Buildings Report",
      "outputFormat": "html",
      "timeRange": "custom",
      "customStartDate": "2025-09-01",
      "customEndDate": "2025-09-12",
      "detailLevel": "detailed"
    }
  }'

# Multiple robots by name
curl -X POST http://monitor-report-api-alb-1071100458.us-east-1.elb.amazonaws.com/api/reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "database_name": "UF2",
    "mainKey": 1,
    "form_data": {
      "service": "robot-management",
      "robot": {
        "name": ["Building_205_Dental_Science", "Building_43_Marston_Library"]
      },
      "contentCategories": ["charging-performance", "cleaning-performance", "resource-utilization", "financial-performance"],
      "reportName": "UF Robot Names Report",
      "outputFormat": "html",
      "timeRange": "custom",
      "customStartDate": "2025-09-01",
      "customEndDate": "2025-09-12",
      "detailLevel": "detailed"
    }
  }'

# Single robot by serial number with PDF output
curl -X POST http://monitor-report-api-alb-1071100458.us-east-1.elb.amazonaws.com/api/reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "database_name": "UF2",
    "mainKey": 1,
    "form_data": {
      "service": "robot-management",
      "robot": {
        "serialNumber": ["811135422060216"]
      },
      "contentCategories": ["charging-performance", "cleaning-performance", "resource-utilization", "financial-performance"],
      "reportName": "UF Single Robot PDF Report",
      "outputFormat": "pdf",
      "timeRange": "last-7-days",
      "detailLevel": "detailed"
    }
  }'

# Last 30 days with predefined time range
curl -X POST http://monitor-report-api-alb-1071100458.us-east-1.elb.amazonaws.com/api/reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "database_name": "UF2",
    "mainKey": 1,
    "form_data": {
      "service": "robot-management",
      "location": {
        "country": "us",
        "state": "fl",
        "city": "gainesville"
      },
      "contentCategories": ["charging-performance", "cleaning-performance", "resource-utilization", "financial-performance"],
      "reportName": "UF Last 30 Days Report",
      "outputFormat": "html",
      "timeRange": "last-30-days",
      "detailLevel": "detailed"
    }
  }'

# Email delivery (when email service is configured)
curl -X POST http://monitor-report-api-alb-1071100458.us-east-1.elb.amazonaws.com/api/reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "database_name": "UF2",
      "mainKey": 1,
    "form_data": {
      "service": "robot-management",
      "location": {
        "country": "us",
        "state": "fl",
        "city": "gainesville"
      },
      "contentCategories": ["charging-performance", "cleaning-performance", "resource-utilization", "financial-performance"],
      "reportName": "UF Email Report",
      "outputFormat": "html",
      "timeRange": "custom",
      "customStartDate": "2025-09-01",
      "customEndDate": "2025-09-12",
      "detailLevel": "detailed",
      "delivery": "email",
      "emailRecipients": ["user@example.com"]
    }
  }'

# Check status (use request_id from above response)
curl http://monitor-report-api-alb-1071100458.us-east-1.elb.amazonaws.com/api/reports/status/{request_id}

# Get report history
curl http://monitor-report-api-alb-1071100458.us-east-1.elb.amazonaws.com/api/reports/history/UF2

# Health check
curl http://monitor-report-api-alb-1071100458.us-east-1.elb.amazonaws.com/api/reports/health
```

### Configuration Testing

```bash
# Verify all config files exist
make verify-config

# Test S3 bucket access
make check-bucket

# Check ALB and service status
make status

# Test database connectivity (if configured)
python -c "from pudu.configs.database_config_loader import DynamicDatabaseConfig; print('DB Config OK')"
```

## Troubleshooting

### Common Issues

1. **S3 Access Denied**
   ```bash
   make check-bucket  # Test bucket access
   aws sts get-caller-identity  # Check AWS credentials
   ```
   - Verify AWS credentials are configured
   - Check IAM permissions for S3 bucket
   - Ensure correct region configuration

2. **Database Connection Failed**
   ```bash
   make verify-config  # Check database config
   ```
   - Verify RDS endpoint and credentials
   - Check VPC security groups
   - Validate database exists
   - Ensure ECS task role has RDS permissions

3. **ALB Health Checks Failing**
   ```bash
   make status  # Check comprehensive status
   ```
   - Verify ECS service is running
   - Check security group allows ALB → ECS traffic
   - Confirm `/api/reports/health` endpoint works

4. **Docker Build Fails**
   ```bash
   make clean-docker  # Clean docker cache
   make build-local   # Rebuild
   ```

5. **Report Generation Timeout**
   - Check database query performance
   - Verify adequate compute resources
   - Review data volume for date range
   - Check ECS task logs in CloudWatch

### Debug Commands

```bash
# Check all configuration
make verify-config

# Test bucket access
make check-bucket

# Check ALB status
make status

# View environment variables
cat .env
cat app.env
cat alb-config.env

# Test imports
python -c "from pudu.reporting.core.report_config import ReportConfig; print('Imports OK')"

# Clean and restart
make clean-config
make deploy-us-east-1-alb
```

### ALB-Specific Troubleshooting

```bash
# Check ALB status
make status

# Test ALB endpoint directly
curl http://your-alb-dns-name/api/reports/health

# Check ECS service logs
aws logs tail /ecs/monitor-report-api --follow --region us-east-1

# Verify ALB target health
aws elbv2 describe-target-health --target-group-arn your-target-group-arn --region us-east-1
```

### Monitoring

#### Health Checks
```bash
# API health via ALB
curl http://monitor-report-api-alb-1071100458.us-east-1.elb.amazonaws.com/api/reports/health

# ALB and ECS status
make status

# Container health (if running locally)
docker ps
```

#### Logs
```bash
# ECS logs (CloudWatch)
aws logs tail /ecs/monitor-report-api --follow --region us-east-1

# Local container logs
docker logs <container_id>

# Follow logs
docker logs -f <container_id>
```

#### Performance Monitoring
Monitor these metrics:
- Report generation time (`/api/reports/status/{id}`)
- S3 upload success rate
- API response times via ALB
- ALB target health status
- Error rates by endpoint

## Security

### AWS Permissions Required

The API requires these AWS permissions:

**S3 Permissions:**
- `s3:PutObject` - Upload reports
- `s3:GetObject` - Download reports
- `s3:DeleteObject` - Delete reports
- `s3:ListBucket` - List customer reports

**RDS Permissions:**
- `rds:DescribeDBInstances` - RDS connections
- `secretsmanager:GetSecretValue` - Database credentials

**ECR Permissions:**
- `ecr:GetAuthorizationToken`
- `ecr:BatchCheckLayerAvailability`
- `ecr:BatchGetImage`

### ALB Security

- ALB security group allows HTTP traffic from internet
- ECS security group allows traffic only from ALB
- ECS tasks run in private subnets with public IP for S3/RDS access
- IAM roles provide least-privilege access

### Best Practices

- Use IAM roles instead of access keys in production
- Enable S3 bucket encryption
- Configure VPC security groups appropriately
- Implement proper logging and monitoring
- Use secrets manager for database credentials
- ALB provides SSL termination capability (configure HTTPS)

## Maintenance

### Cleaning Up

```bash
# Clean configuration files
make clean-config

# Clean failed deployments
make clean-failed-deployment

# Clean Docker images
make clean-docker

# Full cleanup
make clean-config clean-docker
```

### Updates

For code changes with ALB setup:

```bash
# Quick update (2-3 minutes)
make quick-deploy

# Check status
make status
```

For infrastructure changes:

```bash
# Update dependencies
pip install -r requirements.txt

# Full redeploy
make clean-config
make deploy-us-east-1-alb
```

## Support

For issues or questions:

1. Check this troubleshooting section
2. Run `make status` to check ALB and service health
3. Review logs with `aws logs tail /ecs/monitor-report-api --follow`
4. Verify configuration with `make verify-config`
5. Test bucket access with `make check-bucket`
6. Check AWS credentials with `aws sts get-caller-identity`
7. For ALB issues, check target group health in AWS Console