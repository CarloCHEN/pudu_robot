# Pudu Robot Webhook API

A Flask-based webhook receiver for Pudu cleaning robot callbacks, designed for deployment on AWS ECS with ECR.

## Table of Contents

- [Overview](#overview)
- [Supported Callback Types](#supported-callback-types)
- [Project Structure](#project-structure)
- [Setup and Configuration](#setup-and-configuration)
- [Local Development](#local-development)
- [Deployment to AWS ECS](#deployment-to-aws-ecs)
- [Health Check Testing](#health-check-testing)
- [API Endpoints](#api-endpoints)
- [Troubleshooting](#troubleshooting)

## Overview

This webhook API receives and processes real-time notifications from Pudu cleaning robots. It handles robot status updates, error warnings, position updates, and power/battery information.

### Key Features

- **Secure webhook authentication** using callback codes in headers
- **Modular processor architecture** for different callback types
- **Comprehensive logging** and error handling
- **Health check endpoint** for monitoring
- **Production-ready** with ECS deployment
- **Environment-based configuration**

## Supported Callback Types

The API handles four types of callbacks from Pudu robots:

### 1. Robot Status (`robotStatus`)

Handles robot operational status changes.

**Supported Status Values:**
- `online` - Robot is connected and ready
- `offline` - Robot is disconnected
- `working` - Robot is actively cleaning
- `idle` - Robot is connected but not working
- `charging` - Robot is charging
- `error` - Robot is in error state
- `maintenance` - Robot requires maintenance

**Example Callback:**
```json
{
  "type": "robotStatus",
  "robot_id": "CC1_001",
  "status": "working",
  "battery_level": 75,
  "location": "Floor 2, Zone A",
  "timestamp": "2025-07-01T10:30:00Z"
}
```

### 2. Robot Error Warning (`robotErrorWarning`)

Processes error notifications and warnings from robots.

**Severity Levels:**
- `critical` - Immediate attention required
- `high` - High priority error
- `medium` - Standard error (default)

**Example Callback:**
```json
{
  "type": "robotErrorWarning",
  "robot_id": "CC1_001",
  "error_code": "SENSOR_BLOCKED",
  "error_message": "Front sensor is blocked by obstacle",
  "severity": "medium",
  "timestamp": "2025-07-01T10:35:00Z"
}
```

### 3. Robot Pose (`notifyRobotPose`)

Tracks robot position and orientation for navigation monitoring.

**Position Data:**
- `x`, `y`, `z` - Coordinates in meters
- `yaw` - Rotation angle in degrees
- `floor_id` - Floor identifier
- `map_id` - Map reference

**Example Callback:**
```json
{
  "type": "notifyRobotPose",
  "robot_id": "CC1_001",
  "x": 15.5,
  "y": 8.2,
  "z": 0.0,
  "yaw": 90.5,
  "floor_id": "floor_2",
  "map_id": "building_map_001",
  "timestamp": "2025-07-01T10:32:00Z"
}
```

### 4. Robot Power (`notifyRobotPower`)

Monitors battery and power consumption data.

**Power Metrics:**
- `battery_level` - Battery percentage (0-100)
- `is_charging` - Charging status
- `voltage` - Battery voltage
- `current` - Battery current
- `power_consumption` - Power usage in watts
- `estimated_runtime` - Remaining runtime in minutes

**Example Callback:**
```json
{
  "type": "notifyRobotPower",
  "robot_id": "CC1_001",
  "battery_level": 25,
  "is_charging": false,
  "voltage": 24.1,
  "current": 2.5,
  "power_consumption": 60.25,
  "estimated_runtime": 45,
  "timestamp": "2025-07-01T10:40:00Z"
}
```

## Project Structure

```
pudu-webhook-api/
├── callback_handler.py    # Main callback dispatcher
├── config.py             # Configuration management
├── Dockerfile           # Container configuration
├── main.py             # Flask application entry point
├── models.py           # Data models and enums
├── processors.py       # Individual callback processors
├── README.md          # This file
└── requirements.txt   # Python dependencies
```

### Key Components

- **`main.py`** - Flask app with webhook endpoint and health check
- **`callback_handler.py`** - Routes callbacks to appropriate processors
- **`processors.py`** - Individual processors for each callback type
- **`models.py`** - Data models for type safety and validation
- **`config.py`** - Environment-based configuration

## Setup and Configuration

### Prerequisites

- Python 3.9+
- Docker
- AWS CLI configured
- AWS account with ECS and ECR access

### Environment Variables

The application requires the following environment variables:

```bash
# Required
PUDU_CALLBACK_CODE=your_callback_code_from_pudu

# Optional (with defaults)
HOST=0.0.0.0
PORT=8000
DEBUG=false
LOG_LEVEL=INFO
LOG_FILE=pudu_callbacks.log
```

## Local Development

### 1. Install Dependencies

```bash
cd pudu-webhook-api
pip install -r requirements.txt
```

### 2. Create Local Environment File

```bash
# Create .env file
cat > .env << EOF
PUDU_CALLBACK_CODE=local_test_code
HOST=0.0.0.0
PORT=8000
DEBUG=true
LOG_LEVEL=DEBUG
EOF
```

### 3. Run Locally

```bash
python main.py
```

### 4. Test Locally

```bash
# Health check
curl http://localhost:8000/api/pudu/webhook/health

# Test webhook
curl -X POST http://localhost:8000/api/pudu/webhook \
  -H "Content-Type: application/json" \
  -H "CallbackCode: local_test_code" \
  -d '{
    "type": "robotStatus",
    "robot_id": "test_robot",
    "status": "online"
  }'
```

## Deployment to AWS ECS

### Step 1: Configure Root Directory Environment

In the **root directory** (not in `pudu-webhook-api`), create a `.env` file with AWS configuration:

```bash
# In root directory (same level as Makefile)
cat > .env << EOF
AWS_ACCOUNT_ID=123456789012
AWS_REGION=us-east-1
EOF
```

### Step 2: Deploy Container to ECR

From the root directory, run:

```bash
make deploy-container
```

This command will:
1. Build the Docker image from `pudu-webhook-api/Dockerfile`
2. Tag the image for ECR
3. Push to your ECR repository
4. Output the image URI for ECS deployment

### Step 3: Create ECS Task Definition

1. **Navigate to ECS Console** → **Task Definitions** → **Create new task definition**

2. **Configure Task Definition:**
   - **Family name**: `pudu-webhook`
   - **Launch type**: `Fargate`
   - **Operating system**: `Linux/X86_64`
   - **CPU**: `0.25 vCPU`
   - **Memory**: `0.5 GB`

3. **Container Configuration:**
   - **Container name**: `pudu-webhook`
   - **Image URI**: Use the URI from ECR push output
   - **Port mappings**: `8000` (TCP)

4. **Environment Variables:**
   Add the following environment variables:
   ```
   HOST = 0.0.0.0
   PORT = 8000
   DEBUG = false
   LOG_LEVEL = INFO
   PUDU_CALLBACK_CODE = your_actual_callback_code_from_pudu
   ```

5. **Logging Configuration:**
   - **Log driver**: `awslogs`
   - **Log group**: `/ecs/pudu-webhook`
   - **Region**: Your AWS region
   - **Stream prefix**: `ecs`

### Step 4: Create ECS Cluster

1. **Navigate to ECS Console** → **Clusters** → **Create cluster**
2. **Cluster name**: `pudu-webhook-cluster`
3. **Infrastructure**: `AWS Fargate (serverless)`
4. **Create cluster**

### Step 5: Create and Run Task

1. **Go to your cluster** → **Tasks** → **Run new task**

2. **Task Configuration:**
   - **Launch type**: `Fargate`
   - **Platform version**: `LATEST`
   - **Task definition**: `pudu-webhook:1` (or latest revision)

3. **Network Configuration:**
   - **VPC**: Default VPC
   - **Subnets**: Select public subnets
   - **Security group**: Create new or use existing
   - **Auto-assign public IP**: `ENABLED`

4. **Security Group Rules:**
   Ensure the security group allows:
   ```
   Type: Custom TCP
   Port: 8000
   Source: 0.0.0.0/0 (or specific IP ranges)
   ```

### Step 6: Get Public IP Address

1. **Wait for task status** to become `RUNNING`
2. **Click on the task** → **Configuration** tab
3. **Copy the Public IP** from the network section

## Health Check Testing

### External Health Check from Your Laptop

Once your ECS task is running and you have the public IP address:

```bash
# Replace with your actual public IP
PUBLIC_IP="13.220.117.7"

# Test health check endpoint
curl http://$PUBLIC_IP:8000/api/pudu/webhook/health

# Expected response:
# {
#   "status": "healthy",
#   "timestamp": "2025-07-01T10:30:00.123456",
#   "service": "pudu-callback-api"
# }
```

### Test the Webhook Endpoint

```bash
# Test with sample callback (replace with your actual callback code)
curl -X POST http://$PUBLIC_IP:8000/api/pudu/webhook \
  -H "Content-Type: application/json" \
  -H "CallbackCode: your_actual_callback_code" \
  -d '{
    "type": "robotStatus",
    "robot_id": "test_robot",
    "status": "online",
    "battery_level": 85
  }'

# Expected success response:
# {
#   "status": "success",
#   "message": "Robot status processed: online",
#   "timestamp": "2025-07-01T10:30:00.123456",
#   "data": {
#     "robot_id": "test_robot",
#     "status": "online",
#     "battery_level": 85
#   }
# }
```

### Continuous Health Monitoring

```bash
# Monitor health check every 30 seconds
watch -n 30 "curl -s http://$PUBLIC_IP:8000/api/pudu/webhook/health | jq ."

# Check if service is responding
while true; do
  if curl -f -s http://$PUBLIC_IP:8000/api/pudu/webhook/health > /dev/null; then
    echo "$(date): Service is healthy"
  else
    echo "$(date): Service is down!"
  fi
  sleep 60
done
```

## API Endpoints

### Health Check
- **URL**: `GET /api/pudu/webhook/health`
- **Purpose**: Service health monitoring
- **Response**: JSON with status and timestamp

### Webhook Endpoint
- **URL**: `POST /api/pudu/webhook`
- **Headers**: `CallbackCode: your_callback_code`
- **Content-Type**: `application/json`
- **Purpose**: Receive Pudu robot callbacks

## Pudu Integration

### Webhook Registration

When applying to Pudu for webhook access, provide:

```
Webhook URL: http://YOUR_PUBLIC_IP:8000/api/pudu/webhook
Health Check URL: http://YOUR_PUBLIC_IP:8000/api/pudu/webhook/health
Contact: your-email@company.com
Use Case: Real-time monitoring of cleaning robot fleet
```

### Expected Callback Format

All Pudu callbacks will include the `CallbackCode` header:

```http
POST /api/pudu/webhook HTTP/1.1
Host: YOUR_PUBLIC_IP:8000
Content-Type: application/json
CallbackCode: your_callback_code_from_pudu

{callback_json_data}
```

## Troubleshooting

### Common Issues

#### 1. Health Check Fails
```bash
# Check if container is running
aws ecs describe-tasks --cluster pudu-webhook-cluster --tasks YOUR_TASK_ARN

# Check container logs
aws logs get-log-events \
  --log-group-name /ecs/pudu-webhook \
  --log-stream-name ecs/pudu-webhook/YOUR_TASK_ID
```

#### 2. Connection Refused
- Verify security group allows port 8000
- Ensure task has public IP assigned
- Check if container is binding to 0.0.0.0

#### 3. Invalid Callback Code
- Verify `PUDU_CALLBACK_CODE` environment variable is set
- Check ECS task definition environment variables
- Ensure Pudu is sending correct header

#### 4. Container Won't Start
```bash
# Check task stopped reason
aws ecs describe-tasks --cluster pudu-webhook-cluster --tasks YOUR_TASK_ARN \
  --query 'tasks[0].stoppedReason'

# Check container logs for startup errors
aws logs get-log-events \
  --log-group-name /ecs/pudu-webhook \
  --log-stream-name ecs/pudu-webhook/YOUR_TASK_ID \
  --start-time $(date -d '10 minutes ago' +%s)000
```

### Debug Mode

For debugging, update the ECS task definition to enable debug mode:

```json
{
  "name": "DEBUG",
  "value": "true"
}
```

This will provide more verbose logging and error details.

### Log Analysis

View real-time logs:

```bash
# Follow logs in real-time
aws logs tail /ecs/pudu-webhook --follow

# Search for specific robot events
aws logs filter-log-events \
  --log-group-name /ecs/pudu-webhook \
  --filter-pattern "robot_id"
```

## Security Considerations

### Production Recommendations

1. **Use HTTPS**: Deploy behind an Application Load Balancer with SSL
2. **Restrict Access**: Limit security group rules to Pudu's IP ranges
3. **Environment Isolation**: Use separate clusters for staging/production
4. **Secret Management**: Store `PUDU_CALLBACK_CODE` in AWS Parameter Store
5. **Monitoring**: Set up CloudWatch alarms for health check failures

### AWS Parameter Store Integration

For enhanced security, store secrets in Parameter Store:

```bash
# Store callback code securely
aws ssm put-parameter \
  --name "/pudu/callback-code" \
  --value "your_actual_callback_code" \
  --type "SecureString"
```

Then update task definition to use secrets:

```json
{
  "secrets": [
    {
      "name": "PUDU_CALLBACK_CODE",
      "valueFrom": "/pudu/callback-code"
    }
  ]
}
```

## Support

For issues related to:
- **Webhook integration**: Contact Pudu technical support
- **AWS deployment**: Check AWS ECS documentation
- **Application bugs**: Review container logs and GitHub issues

---

**Last Updated**: July 2025
**Version**: 1.0.0