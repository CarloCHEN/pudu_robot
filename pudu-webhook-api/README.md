# Pudu Robot Webhook API

A Flask-based webhook receiver for Pudu cleaning robot callbacks, designed for deployment on AWS ECS with ECR. Now includes real-time database integration for storing robot data.

## Table of Contents

- [Overview](#overview)
- [Supported Callback Types](#supported-callback-types)
- [Database Integration](#database-integration)
- [Project Structure](#project-structure)
- [Setup and Configuration](#setup-and-configuration)
- [Local Development](#local-development)
- [Deployment to AWS ECS](#deployment-to-aws-ecs)
- [Health Check Testing](#health-check-testing)
- [API Endpoints](#api-endpoints)
- [Troubleshooting](#troubleshooting)

## Overview

This webhook API receives and processes real-time notifications from Pudu cleaning robots. It handles robot status updates, error warnings, position updates, and power/battery information, automatically storing the data in RDS MySQL databases for real-time monitoring and analytics.

### Key Features

- **Secure webhook authentication** using callback codes in headers
- **Modular processor architecture** for different callback types
- **Real-time database integration** with AWS RDS MySQL
- **Automatic data storage** for robot status, pose, power, and events
- **Comprehensive logging** and error handling
- **Health check endpoint** for monitoring
- **Production-ready** with ECS deployment
- **Environment-based configuration**
- **Graceful degradation** if database is unavailable

## Supported Callback Types

The API handles four types of callbacks from Pudu robots and automatically stores them in the database:

### 1. Robot Status (`robotStatus`)

Handles robot operational status changes and updates the `mnt_robots_management` table.

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
  "callback_type": "robotStatus",
  "data": {
    "sn": "811064412050012",
    "run_status": "ONLINE",
    "timestamp": 1640995800
  }
}
```

**Database Storage:** Updates `mnt_robots_management` table with robot status and timestamp.

### 2. Robot Error Warning (`robotErrorWarning`)

Processes error notifications and warnings from robots, storing them in the `mnt_robot_events` table.

**Severity Levels:**
- `critical` - Immediate attention required
- `high` - High priority error
- `medium` - Standard error (default)
- `warning` - Warning level
- `info` - Informational

**Example Callback:**
```json
{
  "callback_type": "robotErrorWarning",
  "data": {
    "sn": "811064412050012",
    "error_level": "WARNING",
    "error_type": "LostLocalization",
    "error_detail": "OdomSlip",
    "error_id": "vir_1726794796",
    "timestamp": 1640995800
  }
}
```

**Database Storage:** Inserts new records into `mnt_robot_events` table with event details.

### 3. Robot Pose (`notifyRobotPose`)

Tracks robot position and orientation for navigation monitoring, updating the `mnt_robots_management` table.

**Position Data:**
- `x`, `y` - Coordinates in meters
- `yaw` - Rotation angle in degrees
- `sn` - Robot serial number
- `mac` - Robot MAC address

**Example Callback:**
```json
{
  "callback_type": "notifyRobotPose",
  "data": {
    "sn": "811064412050012",
    "mac": "B0:0C:9D:59:16:E8",
    "x": 15.5,
    "y": 8.2,
    "yaw": 90.5,
    "timestamp": 1640995800
  }
}
```

**Database Storage:** Updates robot position fields in `mnt_robots_management` table.

### 4. Robot Power (`notifyRobotPower`)

Monitors battery and power consumption data, updating the `mnt_robots_management` table.

**Power Metrics:**
- `power` - Battery percentage (0-100)
- `charge_state` - Charging status (charging, discharging, etc.)
- `sn` - Robot serial number
- `mac` - Robot MAC address

**Example Callback:**
```json
{
  "callback_type": "notifyRobotPower",
  "data": {
    "sn": "811064412050012",
    "mac": "B0:0C:9D:59:16:E8",
    "power": 75,
    "charge_state": "discharging",
    "timestamp": 1640995800
  }
}
```

**Database Storage:** Updates battery level and charging state in `mnt_robots_management` table.

## Database Integration

### Database Tables

The webhook automatically writes to two main tables:

#### 1. `mnt_robots_management`
- **Purpose:** Stores current robot status, position, and power data
- **Primary Key:** `robot_sn`
- **Updated by:** `robotStatus`, `notifyRobotPose`, `notifyRobotPower` callbacks
- **Behavior:** Updates existing records (upsert operation)

#### 2. `mnt_robot_events`
- **Purpose:** Stores robot error events and warnings
- **Primary Key:** `robot_sn`, `event_id`
- **Updated by:** `robotErrorWarning` callbacks
- **Behavior:** Inserts new event records

### Database Configuration

Database connections are configured through:
- `credentials.yaml` - RDS connection details and AWS Secrets Manager configuration
- `database_config.yaml` - Table mappings and primary key definitions

### Data Flow

1. **Webhook receives callback** → Validates and processes data
2. **Data transformation** → Converts callback data to database format
3. **Database write** → Updates/inserts data using MySQL upsert operations
4. **Error handling** → Logs failures but continues processing other callbacks
5. **Connection management** → Maintains persistent connections with automatic reconnection

## Project Structure

```
pudu-webhook-api/
├── callback_handler.py      # Main callback dispatcher with DB integration
├── config.py               # Configuration management
├── database_config.py      # Database configuration manager
├── database_writer.py      # Database operations handler
├── rds_utils.py           # RDS connection utilities
├── Dockerfile             # Container configuration
├── main.py               # Flask application entry point
├── models.py             # Data models and enums
├── processors.py         # Individual callback processors
├── credentials.yaml      # Database connection configuration
├── database_config.yaml  # Table mapping configuration
├── README.md            # This file
└── requirements.txt     # Python dependencies (updated)
```

### Key Components

- **`main.py`** - Flask app with webhook endpoint, health check, and database initialization
- **`callback_handler.py`** - Routes callbacks to processors and handles database writes
- **`database_writer.py`** - Manages database connections and write operations
- **`database_config.py`** - Loads and manages database configuration
- **`rds_utils.py`** - RDS connection utilities and SQL operations
- **`processors.py`** - Individual processors for each callback type
- **`models.py`** - Data models for type safety and validation
- **`config.py`** - Environment-based configuration

## Setup and Configuration

### Prerequisites

- Python 3.9+
- Docker
- AWS CLI configured
- AWS account with ECS, ECR, and RDS access
- MySQL RDS instance with required tables

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

### Database Configuration

1. **Update `credentials.yaml`** with your RDS details:
```yaml
database:
  host: "your-rds-endpoint.region.rds.amazonaws.com"
  secret_name: "your-secret-name"
  region_name: "your-region"
```

2. **Configure `database_config.yaml`** for your database setup:
```yaml
databases:
  - "your-database-name"

tables:
  robot_status:
    - database: "your-database-name"
      table_name: "mnt_robots_management"
      primary_keys: ["robot_sn"]

  robot_events:
    - database: "your-database-name"
      table_name: "mnt_robot_events"
      primary_keys: ["robot_sn", "event_id"]
```

### Required Database Schema

Ensure your RDS instance has the following tables:

```sql
-- Robot management table
CREATE TABLE mnt_robots_management (
    robot_sn VARCHAR(50) PRIMARY KEY,
    status VARCHAR(50),
    battery_level INT,
    water_level INT,
    sewage_level INT,
    x DECIMAL(10,6),
    y DECIMAL(10,6),
    z DECIMAL(10,6),
    yaw DECIMAL(10,6),
    charge_state VARCHAR(50),
    last_updated INT
);

-- Robot events table
CREATE TABLE mnt_robot_events (
    robot_sn VARCHAR(50),
    event_id VARCHAR(100),
    event_level VARCHAR(20),
    event_type VARCHAR(100),
    event_detail TEXT,
    task_time INT,
    upload_time INT,
    PRIMARY KEY (robot_sn, event_id)
);
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

### 3. Configure Database Connection

Update `credentials.yaml` and `database_config.yaml` with your local or development database settings.

### 4. Run Locally

```bash
python main.py
```

The application will start and attempt to connect to the database. If the database is unavailable, it will log warnings but continue to process callbacks.

### 5. Test Locally

```bash
# Health check
curl http://localhost:8000/api/pudu/webhook/health

# Test webhook with robot status
curl -X POST http://localhost:8000/api/pudu/webhook \
  -H "Content-Type: application/json" \
  -H "CallbackCode: local_test_code" \
  -d '{
    "callback_type": "robotStatus",
    "data": {
      "sn": "test_robot_123",
      "run_status": "ONLINE",
      "timestamp": 1640995800
    }
  }'

# Test webhook with robot error
curl -X POST http://localhost:8000/api/pudu/webhook \
  -H "Content-Type: application/json" \
  -H "CallbackCode: local_test_code" \
  -d '{
    "callback_type": "robotErrorWarning",
    "data": {
      "sn": "test_robot_123",
      "error_level": "WARNING",
      "error_type": "LostLocalization",
      "error_detail": "OdomSlip",
      "error_id": "test_error_001",
      "timestamp": 1640995800
    }
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
1. Build the Docker image from `pudu-webhook-api/Dockerfile` (now includes database files)
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

5. **IAM Permissions:**
   Ensure the ECS task role has permissions for:
   - **Secrets Manager**: `secretsmanager:GetSecretValue`
   - **RDS**: Network access to your RDS instance

6. **Logging Configuration:**
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
   - **VPC**: Same VPC as your RDS instance
   - **Subnets**: Select public subnets with RDS access
   - **Security group**: Create new or use existing
   - **Auto-assign public IP**: `ENABLED`

4. **Security Group Rules:**
   Ensure the security group allows:
   ```
   Inbound:
   Type: Custom TCP
   Port: 8000
   Source: 0.0.0.0/0 (or specific IP ranges)

   Outbound:
   Type: MYSQL/Aurora
   Port: 3306
   Destination: RDS security group
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
#   "timestamp": "2025-07-10",
#   "service": "pudu-callback-api"
# }
```

### Test the Webhook Endpoint

```bash
# Test with sample robot status callback
curl -X POST http://$PUBLIC_IP:8000/api/pudu/webhook \
  -H "Content-Type: application/json" \
  -H "CallbackCode: your_actual_callback_code" \
  -d '{
    "callback_type": "robotStatus",
    "data": {
      "sn": "811064412050012",
      "run_status": "ONLINE",
      "timestamp": 1640995800
    }
  }'

# Test with sample robot error callback
curl -X POST http://$PUBLIC_IP:8000/api/pudu/webhook \
  -H "Content-Type: application/json" \
  -H "CallbackCode: your_actual_callback_code" \
  -d '{
    "callback_type": "robotErrorWarning",
    "data": {
      "sn": "811064412050012",
      "error_level": "WARNING",
      "error_type": "LostLocalization",
      "error_detail": "OdomSlip",
      "error_id": "vir_1726794796",
      "timestamp": 1640995800
    }
  }'

# Expected success response:
# {
#   "status": "success",
#   "message": "Robot status processed: online",
#   "timestamp": 1640995800,
#   "data": {
#     "robot_sn": "811064412050012",
#     "status": "online"
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
- **Purpose**: Receive Pudu robot callbacks and store in database
- **Database**: Automatically writes to configured RDS tables

## Pudu Integration

### Webhook Registration

When applying to Pudu for webhook access, provide:

```
Webhook URL: http://YOUR_PUBLIC_IP:8000/api/pudu/webhook
Health Check URL: http://YOUR_PUBLIC_IP:8000/api/pudu/webhook/health
Contact: your-email@company.com
Use Case: Real-time monitoring of cleaning robot fleet with database storage
```

### Expected Callback Format

All Pudu callbacks will include the `CallbackCode` header:

```http
POST /api/pudu/webhook HTTP/1.1
Host: YOUR_PUBLIC_IP:8000
Content-Type: application/json
CallbackCode: your_callback_code_from_pudu

{
  "callback_type": "robotStatus",
  "data": {
    "sn": "811064412050012",
    "run_status": "ONLINE",
    "timestamp": 1640995800
  }
}
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

#### 2. Database Connection Issues
```bash
# Check logs for database connection errors
aws logs filter-log-events \
  --log-group-name /ecs/pudu-webhook \
  --filter-pattern "database"

# Common database issues:
# - Security group not allowing MySQL traffic
# - Incorrect credentials in Secrets Manager
# - RDS instance not accessible from ECS subnet
# - Wrong database name in configuration
```

#### 3. Callback Processing but No Database Updates
- Check ECS task role permissions for Secrets Manager
- Verify RDS security group allows connections from ECS
- Review database configuration files
- Check application logs for SQL errors

#### 4. Connection Refused
- Verify security group allows port 8000
- Ensure task has public IP assigned
- Check if container is binding to 0.0.0.0

#### 5. Invalid Callback Code
- Verify `PUDU_CALLBACK_CODE` environment variable is set
- Check ECS task definition environment variables
- Ensure Pudu is sending correct header

#### 6. Container Won't Start
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

### Database Troubleshooting

#### Check Database Connection
```bash
# Test database connectivity from ECS task
aws ecs execute-command \
  --cluster pudu-webhook-cluster \
  --task YOUR_TASK_ARN \
  --container pudu-webhook \
  --interactive \
  --command "python -c \"from database_writer import DatabaseWriter; dw = DatabaseWriter(); print('Database connected successfully')\""
```

#### Monitor Database Operations
```bash
# Filter logs for database operations
aws logs filter-log-events \
  --log-group-name /ecs/pudu-webhook \
  --filter-pattern "Updated robot\|Inserted robot\|Failed to write"

# Monitor specific robot updates
aws logs filter-log-events \
  --log-group-name /ecs/pudu-webhook \
  --filter-pattern "robot_sn_here"
```

### Log Analysis

View real-time logs:

```bash
# Follow logs in real-time
aws logs tail /ecs/pudu-webhook --follow

# Search for specific robot events
aws logs filter-log-events \
  --log-group-name /ecs/pudu-webhook \
  --filter-pattern "robot_sn"

# Search for database errors
aws logs filter-log-events \
  --log-group-name /ecs/pudu-webhook \
  --filter-pattern "ERROR.*database"
```

## Security Considerations

### Production Recommendations

1. **Use HTTPS**: Deploy behind an Application Load Balancer with SSL
2. **Restrict Access**: Limit security group rules to Pudu's IP ranges
3. **Environment Isolation**: Use separate clusters for staging/production
4. **Secret Management**: Store `PUDU_CALLBACK_CODE` in AWS Parameter Store
5. **Database Security**: Use RDS encryption and restrict access
6. **Monitoring**: Set up CloudWatch alarms for health check failures and database errors
7. **Network Security**: Place RDS in private subnets

### Database Security

1. **Encryption**: Enable RDS encryption at rest and in transit
2. **Access Control**: Use IAM database authentication when possible
3. **Network Isolation**: Place RDS in private subnets
4. **Secrets Rotation**: Regularly rotate database credentials
5. **Monitoring**: Enable RDS Performance Insights and CloudWatch monitoring

### AWS Parameter Store Integration

For enhanced security, store secrets in Parameter Store:

```bash
# Store callback code securely
aws ssm put-parameter \
  --name "/pudu/callback-code" \
  --value "your_actual_callback_code" \
  --type "SecureString"

# Store database credentials
aws ssm put-parameter \
  --name "/pudu/database/host" \
  --value "your-rds-endpoint" \
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

## Monitoring and Observability

### CloudWatch Metrics

Set up CloudWatch alarms for:
- **ECS task health**: Monitor task status and container exits
- **HTTP errors**: Track 4xx and 5xx responses
- **Database connections**: Monitor connection failures
- **Callback processing**: Track callback success/failure rates

### Database Monitoring

Monitor database operations:
- **Connection pool usage**: Track active database connections
- **Query performance**: Monitor slow queries and errors
- **Table sizes**: Track growth of robot data tables
- **Replication lag**: If using read replicas
