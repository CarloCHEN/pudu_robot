# Pudu Robot Data Pipeline - Lambda Implementation

## Overview

This project implements a **5-minute interval data pipeline** for Pudu robot data using **AWS Lambda + EventBridge**, replacing the previous hourly Airflow/MWAA schedule to provide more timely data updates.

## Architecture Decision: Why Lambda + EventBridge?

### Comparison with Other Solutions

| Solution | Cost (Monthly) | Complexity | Scalability | Maintenance | Real-time Capability |
|----------|----------------|------------|-------------|-------------|---------------------|
| **Lambda + EventBridge** ⭐ | $ (Low) | Low | Excellent | Minimal | High |
| MWAA (5-min schedule) | $$$$ (Very High) | Medium | Good | Medium | Medium |
| ECS Scheduled Tasks | $$ (Medium) | Medium | Good | Medium | Medium |
| EC2 Cron Jobs | $$ (Medium) | High | Poor | High | Low |

### Why We Chose Lambda + EventBridge

✅ **Cost Efficiency**: Pay only for execution time (~$10-20/month vs $320+/month for MWAA)
✅ **Serverless**: No infrastructure management required
✅ **Auto-scaling**: Handles traffic spikes automatically
✅ **High Availability**: Built-in fault tolerance across multiple AZs
✅ **Fast Deployment**: Deploy updates in seconds, not minutes
✅ **Monitoring**: Native CloudWatch integration
✅ **Frequency**: Perfect for 5-minute intervals without resource waste

## Pipeline Architecture

```
EventBridge Rule (every 5 minutes)
    ↓
AWS Lambda Function
    ↓
Pudu APIs → Data Processing → RDS Database
```

### Key Components

1. **EventBridge Rule**: Triggers Lambda every 5 minutes
2. **Lambda Function**: Processes robot data (Python 3.9)
3. **IAM Role**: Provides necessary permissions
4. **CloudWatch Logs**: Monitoring and debugging

## Building the Lambda Pipeline

### Prerequisites

- **AWS CLI v1.18.x** (this script is specifically designed for v1.18.x, NOT v2.x)
- Python environment with pip
- AWS credentials configured
- Project structure with `src/pudu/` directory

### Project Structure

```
pudu_robot/
├── src/pudu/                    # Core application code
│   ├── apis/                    # API integration modules
│   ├── app/main.py             # Main application logic
│   ├── configs/database_config.yaml
│   └── rds/                    # Database utilities
├── lambda/
│   ├── deploy.sh               # Deployment script (AWS CLI v1.18.x)
│   └── robot_lambda_function.py # Lambda handler
└── credentials.yaml            # Database credentials
```

### Deployment Process

The deployment script (`lambda/deploy.sh`) performs these steps:

1. **Package Creation**: Copies source code and configs
2. **Dependency Installation**: Installs Lambda-compatible packages
3. **Binary Compatibility**: Uses `manylinux` wheels for pandas/numpy
4. **Size Optimization**: Removes tests/docs, keeps essential binaries
5. **AWS Resources**: Creates IAM role, Lambda function, EventBridge rule
6. **Permissions**: Sets up Lambda invocation permissions
7. **Scheduling**: Configures 5-minute trigger

### Critical Package Installation

The script solves pandas/numpy compatibility issues using:

```bash
# Platform-specific wheels for Lambda's Amazon Linux 2
pip install \
    --platform manylinux2014_x86_64 \
    --target . \
    --implementation cp \
    --python-version 3.9 \
    --only-binary=:all= \
    pandas==1.5.3 numpy==1.24.3
```

## Deployment Instructions

### Step 1: Verify AWS CLI Version

```bash
aws --version
# Should show: aws-cli/1.18.x (NOT 2.x)
```

⚠️ **Important**: This script is designed for AWS CLI v1.18.x. For v2.x, modifications are needed.

### Optional: Set up AWS region

```bash
# From project root directory
chmod +x lambda/*.sh
./lambda/setup_lambda.sh us-east-1
```

### Step 2: Deploy the Pipeline

```bash
# From project root directory
chmod +x lambda/*.sh
./lambda/deploy_to_region.sh us-east-1
./lambda/deploy_lambda.sh us-east-1 (must first do ./lambda/setup_lambda.sh us-east-1 )
./lambda/deploy_work_location_lambda.sh us-east-1 (must first do ./lambda/setup_lambda.sh us-east-1 )

```

### Step 3: Verify Deployment

```bash
# Test the function
aws lambda invoke --function-name pudu-robot-pipeline test-output.json
cat test-output.json

# Check if schedule is active
aws events describe-rule --name pudu-robot-5min-schedule
```

## Testing & Monitoring

### Useful Commands

#### Lambda Function Testing
```bash
# Manual function invocation
aws lambda invoke --function-name pudu-robot-pipeline test-output.json && cat test-output.json

# Get function information
aws lambda get-function --function-name pudu-robot-pipeline

# Check function configuration
aws lambda get-function-configuration --function-name pudu-robot-pipeline
```

#### Log Monitoring
```bash
# Real-time log streaming
aws logs tail /aws/lambda/pudu-robot-pipeline --follow

# Get recent log events
aws logs describe-log-streams --log-group-name /aws/lambda/pudu-robot-pipeline

# Filter logs for errors
aws logs filter-log-events \
    --log-group-name /aws/lambda/pudu-robot-pipeline \
    --filter-pattern "ERROR"
```

#### Schedule Management
```bash
# Check EventBridge rule status
aws events describe-rule --name pudu-robot-5min-schedule

# Disable the 5-minute schedule
aws events disable-rule --name pudu-robot-5min-schedule

# Enable the 5-minute schedule
aws events enable-rule --name pudu-robot-5min-schedule

# List recent rule executions
aws events list-rules --name-prefix pudu-robot
```

#### Performance Monitoring
```bash
# Get function metrics
aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Duration \
    --dimensions Name=FunctionName,Value=pudu-robot-pipeline \
    --start-time 2025-01-01T00:00:00Z \
    --end-time 2025-01-02T00:00:00Z \
    --period 300 \
    --statistics Average,Maximum

# Check error count
aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Errors \
    --dimensions Name=FunctionName,Value=pudu-robot-pipeline \
    --start-time 2025-01-01T00:00:00Z \
    --end-time 2025-01-02T00:00:00Z \
    --period 300 \
    --statistics Sum
```

## Troubleshooting Guide

### Common Deployment Issues

#### 1. Package Size Too Large (>50MB)
```bash
# Error: RequestEntityTooLargeException
# Solution: Script automatically optimizes, but if still fails:
```
- Remove unnecessary dependencies from requirements
- Use Lambda Layers for large packages
- Consider S3 upload for packages >50MB

#### 2. IAM Permission Errors
```bash
# Error: AccessDenied when creating resources
# Solution: Ensure AWS credentials have sufficient permissions:
```
- `iam:CreateRole`, `iam:AttachRolePolicy`
- `lambda:CreateFunction`, `lambda:UpdateFunctionCode`
- `events:PutRule`, `events:PutTargets`

#### 3. Import/Module Errors
```bash
# Error: "Unable to import module 'lambda_function'"
# Debug steps:
```
1. Check package structure in deployment ZIP
2. Verify all dependencies are included
3. Test imports locally first

### Common Runtime Issues

#### 1. Pandas/Numpy Compatibility
```python
# Error: "No module named 'numpy.core._multiarray_umath'"
# Solution: Script uses platform-specific wheels, but if issues persist:
```
- Verify correct manylinux wheels are installed
- Check Lambda Python runtime version matches package version
- Consider using older pandas/numpy versions

#### 2. Database Connection Issues
```bash
# Error: Database connection timeouts
# Debug steps:
```
1. Check VPC/security group settings
2. Verify database credentials
3. Test connectivity from Lambda environment
4. Check if Lambda is in same VPC as database

#### 3. Timeout Issues
```bash
# Error: Task timed out after 900.00 seconds
# Solutions:
```
- Optimize data processing logic
- Reduce batch sizes
- Increase Lambda timeout (max 15 minutes)
- Consider breaking into smaller functions

### Debugging Techniques

#### 1. Local Testing
```bash
# Test Lambda function locally
cd lambda
python robot_lambda_function.py
```

#### 2. Enhanced Logging
```python
# Add debug logging to your code
import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

logger.debug(f"Processing {len(data)} records")
logger.info(f"Database connection status: {connection.is_connected()}")
```

#### 3. Error Tracking
```python
# Wrap critical sections with try-catch
try:
    result = process_robot_data(data)
    logger.info(f"Processed {result.count} records successfully")
except Exception as e:
    logger.error(f"Processing failed: {str(e)}", exc_info=True)
    # Send notification or take corrective action
```

## Performance Optimization

### Lambda Configuration
- **Memory**: 1024MB (adjustable based on data volume)
- **Timeout**: 900 seconds (15 minutes)
- **Runtime**: Python 3.9

### Monitoring Metrics
- **Duration**: Target <5 minutes for 5-minute intervals
- **Error Rate**: Target <1%
- **Memory Usage**: Monitor for optimization opportunities

### Cost Optimization
- Current estimated cost: $10-20/month
- Monitor CloudWatch metrics for usage patterns
- Optimize memory allocation based on actual usage

## Migration from Airflow

### Comparison with Previous Hourly Schedule

| Aspect | Airflow (Hourly) | Lambda (5-minute) |
|--------|------------------|-------------------|
| **Data Freshness** | 1 hour delay | 5 minute delay |
| **Cost** | $320+/month | $10-20/month |
| **Reliability** | Good | Excellent |
| **Maintenance** | High | Minimal |
| **Scalability** | Manual | Automatic |

### Migration Benefits
1. **12x faster data updates** (5 min vs 60 min)
2. **16x cost reduction** ($20 vs $320+/month)
3. **Zero infrastructure maintenance**
4. **Built-in monitoring and alerting**
5. **Automatic scaling and fault tolerance**

## Support and Maintenance

### Regular Maintenance Tasks
1. **Monitor CloudWatch logs** for errors
2. **Review performance metrics** monthly
3. **Update dependencies** when security patches are available
4. **Test disaster recovery** procedures quarterly

### Emergency Procedures
1. **Disable schedule**: `aws events disable-rule --name pudu-robot-5min-schedule`
2. **Check logs**: `aws logs tail /aws/lambda/pudu-robot-pipeline --follow`
3. **Manual execution**: `aws lambda invoke --function-name pudu-robot-pipeline test.json`
4. **Rollback**: Deploy previous version using deployment script

### Contact Information
- **AWS Support**: For infrastructure issues
- **Development Team**: For code-related issues
- **Database Team**: For data connectivity issues

---

## Appendix

### AWS CLI v1.18.x vs v2.x Differences

This deployment script is specifically designed for **AWS CLI v1.18.x**. Key differences with v2.x:

| Feature | v1.18.x (Supported) | v2.x (Requires Modification) |
|---------|---------------------|------------------------------|
| **ZIP File Parameter** | `--zip-file "fileb://package.zip"` | `--zip-file fileb://package.zip` |
| **Error Handling** | Specific error codes | Different error format |
| **Output Format** | Tab-separated | JSON default |

### Required IAM Permissions

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "iam:CreateRole",
                "iam:AttachRolePolicy",
                "iam:GetRole",
                "lambda:CreateFunction",
                "lambda:UpdateFunctionCode",
                "lambda:UpdateFunctionConfiguration",
                "lambda:AddPermission",
                "events:PutRule",
                "events:PutTargets",
                "sts:GetCallerIdentity"
            ],
            "Resource": "*"
        }
    ]
}
```

### Package Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| boto3 | >=1.34.0 | AWS SDK |
| pandas | 1.5.3 | Data processing |
| numpy | 1.24.3 | Numerical operations |
| pymysql | >=1.1.0 | MySQL connectivity |
| sqlalchemy | >=2.0.0 | Database ORM |
| pyyaml | >=6.0.0 | Configuration files |