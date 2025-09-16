# Robot Management Report API

An asynchronous FastAPI service for generating robot management reports and storing them in AWS S3.

## Overview

This API provides asynchronous report generation capabilities for robot management data, with automatic upload to region-specific S3 buckets. Multiple users can generate reports simultaneously without blocking each other.

### Features

- **Async Report Generation**: Non-blocking report generation using FastAPI background tasks
- **Multi-Region Support**: Automatic S3 bucket selection based on AWS region
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
├── deploy.sh                           # Deployment script
├── Makefile                            # Build automation
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
reports/{customer_id}/{year}/{month}/{timestamp}_robot_performance_report.html
```

## Quick Start

### 1. Setup Environment

Choose your target region and setup configuration files:

```bash
# Navigate to report_api directory
cd report_api

# For us-east-2 (production)
make setup-us-east-2

# For us-east-1 (test)
make setup-us-east-1
```

This creates:
- `.env` - Deployment variables
- `app.env` - Application environment variables
- `database_config.yaml` - Database configuration

### 2. Deploy to AWS ECS

```bash
# One-step deployment to us-east-2
make deploy-us-east-2

# One-step deployment to us-east-1
make deploy-us-east-1

# Or deploy with current configuration
make deploy-container
```

### 3. Test Locally

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

### Generate Report
```http
POST /api/reports/generate
Content-Type: application/json

{
  "customer_id": "customer-123",
  "form_data": {
    "service": "robot-management",
    "contentCategories": ["robot-status", "cleaning-tasks", "performance"],
    "timeRange": "last-30-days",
    "detailLevel": "detailed",
    "delivery": "in-app",
    "schedule": "immediate",
    "location": {
      "country": "US",
      "state": "Ohio",
      "city": "",
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
GET /api/reports/history/{customer_id}?limit=50
```

### Delete Report
```http
DELETE /api/reports/delete?customer_id=customer-123&report_key=reports/customer-123/2024/01/file.html
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

3. **Setup environment:**
   ```bash
   make setup-us-east-2  # or us-east-1
   ```

4. **Verify configuration:**
   ```bash
   make verify-config
   ```

5. **Test S3 access:**
   ```bash
   make check-bucket
   ```

6. **Run locally:**
   ```bash
   make test-local
   ```

7. **Test API endpoints:**
   ```bash
   # In another terminal
   make test-api
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

### Automated Deployment (Recommended)

The Makefile provides one-command deployment:

```bash
# Complete setup and deployment to us-east-2
make deploy-us-east-2

# Complete setup and deployment to us-east-1
make deploy-us-east-1
```

This will:
1. Clean any existing configuration
2. Setup environment for the target region
3. Build and push Docker image to ECR
4. Configure region-specific S3 buckets

### Manual Deployment Steps

1. **Setup environment:**
   ```bash
   ./setup-environment.sh us-east-2
   ```

2. **Verify configuration:**
   ```bash
   make verify-config
   ```

3. **Deploy:**
   ```bash
   ./deploy.sh
   ```

### ECS Task Configuration

When deploying to ECS, ensure these environment variables are set:

```bash
AWS_REGION=us-east-2
S3_REPORTS_BUCKET=monitor-reports-archive
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

```bash
# Test report generation
curl -X POST http://localhost:8000/api/reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "test-customer",
    "form_data": {
      "service": "robot-management",
      "location": {
        "country": "us",
        "state": "fl",
        "city": "gainesville"
      },
      "contentCategories": ["charging-performance", "cleaning-performance", "resource-utilization", "financial-performance"],
      "timeRange": "custom",
      "customStartDate": "2025-08-20",
      "customEndDate": "2025-09-09",
      "detailLevel": "detailed",
      "delivery": "in-app",
      "schedule": "immediate"
    }
  }'

# Cloud testing
curl -X POST http://54.163.54.190:8000/api/reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "UF2",
    "form_data": {
      "service": "robot-management",
      "location": {
        "country": "us",
        "state": "fl",
        "city": "gainesville",
        "building": "Building 43 Marston Science Library"
      },
      "contentCategories": ["charging-performance", "cleaning-performance", "resource-utilization", "financial-performance"],
      "mainkey": "123",
      "reportName": "UF Report",
      "outputFormat": "html",
      "timeRange": "custom",
      "customStartDate": "2025-09-01",
      "customEndDate": "2025-09-12",
      "detailLevel": "detailed"
    }
  }'
# email - pending
curl -X POST http://34.238.51.145:8000/api/reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "test-customer",
    "form_data": {
      "service": "robot-management",
      "location": {
        "country": "us",
        "state": "fl",
        "city": "gainesville"
      },
      "contentCategories": ["charging-performance", "cleaning-performance", "resource-utilization", "financial-performance"],
      "timeRange": "custom",
      "customStartDate": "2025-08-20",
      "customEndDate": "2025-09-09",
      "detailLevel": "detailed",
      "delivery": "email",
      "emailRecipients": ["jiaxuchen16@gmail.com"],
      "schedule": "immediate"
    }
  }'
# Check status (use request_id from above response)
curl http://localhost:8000/api/reports/status/{request_id}

# Get report history
curl http://localhost:8000/api/reports/history/test-customer
```

### Configuration Testing

```bash
# Verify all config files exist
make verify-config

# Test S3 bucket access
make check-bucket

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

3. **Docker Build Fails**
   ```bash
   make clean-docker  # Clean docker cache
   make build-local   # Rebuild
   ```

4. **Report Generation Timeout**
   - Check database query performance
   - Verify adequate compute resources
   - Review data volume for date range
   - Check logs: `docker logs <container_id>`

### Debug Commands

```bash
# Check all configuration
make verify-config

# Test bucket access
make check-bucket

# View environment variables
cat .env
cat app.env

# Test imports
python -c "from pudu.reporting.core.report_config import ReportConfig; print('Imports OK')"

# Clean and restart
make clean-config
make setup-us-east-2
```

### Monitoring

#### Health Checks
```bash
# API health
curl http://localhost:8000/api/reports/health

# Container health (if running in Docker)
docker ps
```

#### Logs
```bash
# Application logs
docker logs <container_id>

# Follow logs
docker logs -f <container_id>
```

#### Performance Monitoring
Monitor these metrics:
- Report generation time (`/api/reports/status/{id}`)
- S3 upload success rate
- API response times
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
- Database connection permissions via RDS secrets

**ECR Permissions:**
- `ecr:GetAuthorizationToken`
- `ecr:BatchCheckLayerAvailability`
- `ecr:BatchGetImage`

### Best Practices

- Use IAM roles instead of access keys in production
- Enable S3 bucket encryption
- Configure VPC security groups appropriately
- Implement proper logging and monitoring
- Use secrets manager for database credentials

## Maintenance

### Cleaning Up

```bash
# Clean configuration files
make clean-config

# Clean Docker images
make clean-docker

# Full cleanup
make clean-config clean-docker
```

### Updates

```bash
# Update dependencies
pip install -r requirements.txt

# Rebuild and redeploy
make clean-docker
make deploy-us-east-2
```

## Support

For issues or questions:

1. Check this troubleshooting section
2. Review logs with `docker logs <container_id>`
3. Verify configuration with `make verify-config`
4. Test bucket access with `make check-bucket`
5. Check AWS credentials with `aws sts get-caller-identity`