# Multi-Brand Robot Webhook API

A Flask-based webhook receiver for multiple robot brands (Pudu, Gas, and future brands), designed for deployment on AWS ECS with ECR. Features real-time database integration, multi-brand support, and flexible configuration.

## Table of Contents

- [Overview](#overview)
- [Supported Brands](#supported-brands)
- [Supported Callback Types](#supported-callback-types)
- [Database Integration](#database-integration)
- [Project Structure](#project-structure)
- [Setup and Configuration](#setup-and-configuration)
- [Local Development](#local-development)
- [Deployment to AWS ECS](#deployment-to-aws-ecs)
- [Adding New Robot Brands](#adding-new-robot-brands)
- [Health Check Testing](#health-check-testing)
- [API Endpoints](#api-endpoints)
- [Troubleshooting](#troubleshooting)

## Overview

This webhook API receives and processes real-time notifications from multiple robot brands. It uses a **config-driven architecture** that allows adding new robot brands with minimal code changes - just configuration updates!

### Key Features

- **Multi-brand support** - Currently supports Pudu and Gas robots with extensible architecture
- **Config-driven field mapping** - No code changes needed for new brands
- **Secure webhook authentication** - Header-based (Pudu) and body-based (Gas) verification
- **Real-time database integration** with AWS RDS MySQL
- **Automatic data transformation** - Brand-specific data → unified database schema
- **Task report support** - Gas cleaning task reports with calculated fields
- **Notification system** - Real-time alerts for critical events
- **Production-ready** with ECS deployment
- **Multi-region deployment** - Independent deployments per brand and region

## Supported Brands

### 1. Pudu Robots
- **Verification**: Header-based (`CallbackCode` header)
- **Endpoints**: `/api/pudu/webhook`
- **Callback Types**: Status, Error/Warning, Pose, Power
- **Coordinate Transform**: Supported

### 2. Gas (Gaussium) Robots
- **Verification**: Body-based (`appId` field)
- **Endpoints**: `/api/gas/webhook`
- **Callback Types**: Incidents (errors), Task Reports (cleaning reports)
- **Features**: Nested field mapping, timestamp conversion, status code mapping
- **Coordinate Transform**: Disabled (different coordinate system)

## Supported Callback Types

### Abstract Types (Brand-Agnostic)

The system uses abstract types internally:
- `status_event` - Robot status updates
- `error_event` - Errors, warnings, incidents
- `pose_event` - Position/location updates
- `power_event` - Battery/power status
- `report_event` - Task/cleaning reports (Gas only)

### Pudu Callback Types

#### 1. Robot Status (`robotStatus` → `status_event`)

**Example:**
```json
{
  "callback_type": "robotStatus",
  "data": {
    "sn": "PUDU-001",
    "run_status": "WORKING",
    "timestamp": 1640995800
  }
}
```

#### 2. Robot Error Warning (`robotErrorWarning` → `error_event`)

**Example:**
```json
{
  "callback_type": "robotErrorWarning",
  "data": {
    "sn": "PUDU-001",
    "error_level": "ERROR",
    "error_type": "LostLocalization",
    "error_detail": "OdomSlip",
    "error_id": "evt_12345",
    "timestamp": 1640995800
  }
}
```

#### 3. Robot Pose (`notifyRobotPose` → `pose_event`)

**Example:**
```json
{
  "callback_type": "notifyRobotPose",
  "data": {
    "sn": "PUDU-001",
    "x": 15.5,
    "y": 8.2,
    "yaw": 90.5,
    "timestamp": 1640995800
  }
}
```

#### 4. Robot Power (`notifyRobotPower` → `power_event`)

**Example:**
```json
{
  "callback_type": "notifyRobotPower",
  "data": {
    "sn": "PUDU-001",
    "power": 75,
    "charge_state": "discharging",
    "timestamp": 1640995800
  }
}
```

### Gas Callback Types

#### 1. Incident Callback (`messageTypeId: 1` → `error_event`)

**Example:**
```json
{
  "appId": "24416c36-d9c7-4d74-a047-d6ca461fxxxx",
  "messageTypeId": 1,
  "payload": {
    "serialNumber": "GAS-001",
    "content": {
      "incidentId": "12345",
      "incidentCode": "1011",
      "incidentName": "Clean water full",
      "incidentLevel": "H2",
      "incidentStatus": 1
    }
  },
  "messageTimestamp": 1715740800000
}
```

**Field Mappings:**
- `payload.serialNumber` → `robot_sn`
- `payload.content.incidentId` → `event_id`
- `payload.content.incidentLevel` → `event_level` (H7→fatal, H6→error, H5→warning, etc.)
- `messageTimestamp` → `task_time` (converted from milliseconds to seconds)

#### 2. Task Report Callback (`messageTypeId: 2` → `report_event`)

**Example:**
```json
{
  "appId": "24416c36-aaaa-4d74-aaaa-d6ca461faaaa",
  "messageTypeId": 2,
  "payload": {
    "serialNumber": "GAS-001",
    "taskReport": {
      "id": "684c183c-4ad9-467b-ac7c-55835255AAAA",
      "taskId": "task-123",
      "displayName": "Floor 2 Cleaning",
      "startTime": 1714124784000,
      "endTime": 1714124890000,
      "completionPercentage": 0.95,
      "actualCleaningAreaSquareMeter": 150.5,
      "waterConsumptionLiter": 5.2,
      "startBatteryPercentage": 95.0,
      "endBatteryPercentage": 78.0,
      "taskEndStatus": 0,
      "subTasks": [...]
    }
  },
  "messageTimestamp": 1715769600000
}
```

**Special Features:**
- **Calculated fields**: `battery_usage` = endBattery - startBattery
- **Unit conversion**: `waterConsumption` converted from liters to milliliters
- **JSON storage**: `subTasks` and other brand-specific data stored as JSON
- **Status mapping**: Gas codes (0=completed, 1=in_progress, 2=abnormal, 3=failed) → common text strings

## Database Integration

### Unified Database Schema

All brands write to the same tables with a unified schema:

#### 1. `mnt_robots_management`
- Stores current robot status, position, and power
- Common fields across all brands

#### 2. `mnt_robot_events`
- Stores error events from all brands
- Unified event levels: `fatal`, `error`, `warning`, `event`, `info`

#### 3. `mnt_robots_task` (NEW)
- Stores task/cleaning reports
- Common status strings: `completed`, `in_progress`, `abnormal`, `failed`, `not_started`
- Includes `extra_data` JSON field for brand-specific data

### Field Mapping Examples

**Gas Incident Level Mapping:**
```yaml
H7 → fatal
H6 → error
H5 → warning
H2 → event
```

**Gas Task Status Mapping:**
```yaml
-1 → not_started   # Unknown
0  → completed     # Normal
1  → in_progress   # Manual
2  → abnormal      # Abnormal
3  → failed        # Startup Failed
```

## Project Structure

```
robot-webhook-api/
├── core/                           # Brand-agnostic core
│   ├── brand_config.py            # Brand config loader & field mapper
│   └── services/
│       └── verification_service.py # Request verification
│
├── brands/                         # Brand-specific extensions (optional)
│   ├── pudu/
│   └── gas/
│
├── configs/                        # Configuration
│   ├── database_config.yaml       # Database routing
│   ├── database_config.py         # Database resolver
│   ├── pudu/
│   │   └── config.yaml           # Pudu field mappings
│   └── gas/
│       └── config.yaml           # Gas field mappings
│
├── notifications/                  # Notification system
├── rds/                           # Database utilities
├── services/                      # Shared services
│
├── callback_handler.py            # Main handler (brand-aware)
├── database_writer.py             # Database operations
├── processors.py                  # Base processors
├── models.py                     # Data models
├── main.py                       # Flask app (multi-brand endpoints)
├── config.py                     # Environment config
└── README.md                     # This file
```

## Setup and Configuration

### Prerequisites

- Python 3.9+
- Docker
- AWS CLI configured
- AWS account with ECS, ECR, and RDS access
- MySQL RDS instance with required tables

### Environment Variables

```bash
# Brand configuration
BRAND=pudu  # or 'gas'

# Brand verification codes
PUDU_CALLBACK_CODE=your-pudu-secret-code
GAS_CALLBACK_CODE=your-gas-secret-code

# Server config
HOST=0.0.0.0
PORT=8000
DEBUG=false
LOG_LEVEL=INFO
LOG_FILE=robot_callbacks.log

# Database
MAIN_DATABASE=ry-vue

# Notifications
NOTIFICATION_API_HOST=your-notification-host
```

### Brand Configuration Files

Each brand has a configuration file in `configs/<brand>/config.yaml`:

**Example: `configs/gas/config.yaml`**
```yaml
brand: gas

verification:
  method: body
  key: appId

type_mappings:
  "1": error_event
  "2": report_event

field_mappings:
  error_event:
    source_to_db:
      payload.serialNumber: robot_sn
      payload.content.incidentLevel: event_level
    conversions:
      event_level:
        type: lowercase
        mapping:
          "h7": "fatal"
          "h6": "error"
    drop_fields:
      - traceId
      - messageId
```

## Local Development

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create Environment File

```bash
cat > .env << EOF
BRAND=pudu
PUDU_CALLBACK_CODE=test_code
GAS_CALLBACK_CODE=test_code
HOST=0.0.0.0
PORT=8000
DEBUG=true
EOF
```

### 3. Run Locally

```bash
python main.py
```

### 4. Test Endpoints

```bash

curl -X POST "https://webhook-east2.com/api/pudu/webhook" \
  -H "Content-Type: application/json" \
  -H "CallbackCode: 1vQ6MfUxqyoGMRQ9nK8C4pSkg1Qsa3Vpq" \
  -d '{
    "callback_type": "notifyRobotStatus",
    "data": {
      "sn": "811135422060228",
      "mac": "机器人001",
      "timestamp": 1770873793004,
      "notify_timestamp": 1770873793004,
      "battery": 85,
      "is_charging": -1,
      "move_state": "STUCK",
      "charge_stage": "IDLE",
      "remain_time": 0,
      "run_state": "BUSY",
      "charge_type": 2
    }
  }'

curl -X POST "http://robot-webhook-alb-us-east-2-889479792.us-east-2.elb.amazonaws.com/api/pudu/webhook" \
  -H "Content-Type: application/json" \
  -H "CallbackCode: 1vQ6MfUxqyoGMRQ9nK8C4pSkg1Qsa3Vpq" \
  -d '{
    "callback_type": "robotErrorNotice",
    "data": {
      "error_detail": "TestEmergencyKeyPressed",
      "error_id": "11111111as",
      "error_level": "Event",
      "error_type": "EmergencyStop",
      "extend_info": {
        "battery": 58,
        "floor": "",
        "mac": "00:D6:CB:D5:28:01",
        "map_name": "0#0#T600纯激光地图20250815",
        "map_point": "",
        "sn": "811135422060228",
        "task_id": "1222222222222",
        "task_type": "Delivery",
        "position": {
          "x": -0.004843229,
          "y": 4.99104,
          "yaw": 1.3746479
        }
      },
      "language": "",
      "sn": "811135422060228",
      "timestamp": 1770865706
    }
  }'

# Test Pudu endpoint
curl -X POST http://robot-webhook-alb-us-east-2-889479792.us-east-2.elb.amazonaws.com/api/pudu/webhook \
  -H "Content-Type: application/json" \
  -H "CallbackCode: vFpG5Ga9o8NqdymFLicLfJVfqj6JU50qQYCs" \
  -d '{
    "callback_type": "robotStatus",
    "data": {"sn": "811135422060228", "run_status": "ONLINE", "timestamp": 1640995800}
  }'


curl -X POST http://robot-webhook-alb-us-east-1-1428034945.us-east-1.elb.amazonaws.com/api/webhook \
  -H "Content-Type: application/json" \
  -H "CallbackCode: vFpG5Ga9o8NqdymFLicLfJVfqj6JU50qQYCs" \
  -d '{
    "callback_type": "robotErrorWarning",
    "data": {
      "sn": "811135422060228",
      "error_id": "ERR_001",
      "event_id": "ERR_001",
      "error_level": "warning",
      "error_type": "battery_low",
      "error_detail": "Battery level below 20%",
      "task_time": 1759980527
    }
  }'

curl -X POST http://3.237.78.106:8000/api/pudu/webhook \
  -H "Content-Type: application/json" \
  -H "CallbackCode: vFpG5Ga9o8NqdymFLicLfJVfqj6JU50qQYCs" \
  -d '{
    "callback_type": "notifyRobotPose",
    "data": {
     "x":1.234,
     "y":2.345,
     "yaw":32.34,
      "sn":"811135422060228",
      "mac":"AA:AA:AA:AA:AA:AA",
      "timestamp": 1764325632
    }
  }'

curl -X POST http://3.237.78.106:8000/api/pudu/webhook \
  -H "Content-Type: application/json" \
  -H "CallbackCode: vFpG5Ga9o8NqdymFLicLfJVfqj6JU50qQYCs" \
  -d '{
    "callback_type": "notifyRobotPower",
    "data": {
      "sn": "PUDU-001",
      "power": 85,
      "charge_state": "charging",
      "timestamp": 1640995800
    }
  }'

# Test Gas endpoint
curl https://webhook-east2.com/api/webhook/health

curl --location "https://webhook-east1.com/api/webhook" \
--header 'accept: */*' \
--header 'Content-Type: application/json' \
--data '{
  "messageTypeId": 2,
  "productId": "GS442-6130-82R-6000",
  "messageId": "GS442-6130-82R-6000:2:684c183c-4ad9-467b-ac7c-55835255AAAA",
  "traceId": "3d54fe90c9a34c20b600e3b7fa9af254",
  "messageTimestamp": 1715769600000,
  "appId": "378c0111-5d5d-4bdc-9cc5-e3d7bd3494d3",
  "payload": {
    "serialNumber": "GS442-6130-82R-6000",
    "modelTypeCode": "Scrubber S1",
    "taskReport": {
      "id": "684c183c-4ad9-467b-ac7c-55835255AAAA",
      "taskId": "233123123-d9c7-4d74-a047-d6ca461faaaa",
      "planId": "233123123-d9c7-4d74-a047-d6ca461faaaa",
      "taskInstanceId": "893cbadf-3bb1-45be-b7ef-d590d54fAAAA",
      "displayName": "ceshi2",
      "startTime": 1714124784000,
      "endTime": 1714124890000,
      "robot": "S2153",
      "robotSerialNumber": "GS442-6130-82R-6000",
      "operator": "admin",
      "completionPercentage": 0.333,
      "durationSeconds": 12,
      "plannedCleaningAreaSquareMeter": 67.425,
      "actualCleaningAreaSquareMeter": 10.548,
      "efficiencySquareMeterPerHour": 407.965,
      "plannedPolishingAreaSquareMeter": null,
      "actualPolishingAreaSquareMeter": null,
      "waterConsumptionLiter": 0.0,
      "startBatteryPercentage": 100,
      "endBatteryPercentage": 0,
      "consumablesResidualPercentage": {
        "brush": 100.0,
        "filter": 100.0,
        "suctionBlade": 100.0
      },
      "cleaningMode": "清扫",
      "taskEndStatus": 1,
      "subTasks": [
        {
          "mapId": "370192bd-fe7f-40d0-8d0a-4360415bb8cf",
          "mapName": "ceshi2",
          "actualCleaningAreaSquareMeter": 10.548,
          "taskId": "233123123-d9c7-4d74-a047-d6ca461faaaa"
        }
      ],
      "taskReportPngUri": "https://bot.release.gs-robot.com/robot-task/task/report/png/v2/en/684c183c-4ad9-467b-ac7c-55835255aaaa",
      "areaNameList": "2_area1、area2、area3、area4,3_area1、area2、area3"
    }
  }
}'


curl -X POST http://robot-webhook-alb-us-east-1-1428034945.us-east-1.elb.amazonaws.com/api/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "appId": "378c0111-5d5d-4bdc-9cc5-e3d7bd3494d3",
    "payload": {
      "serialNumber": "GS442-6130-82R-6000",
      "modelTypeCode": "Scrubber 50H",
      "content": {
        "incidentId": "74bbc189-3313-4665-8204-9fbe45dfxxxx",
        "incidentCode": "1011",
        "incidentName": "Clean water full",
        "incidentLevel": "H2",
        "incidentStatus": 1,
        "startTime": "2025-05-15T02:09:28Z",
        "endTime": "",
        "taskId": "..."
      }
    },
    "messageTypeId": 1,
    "productId": "GS442-6130-82R-6000",
    "messageId": "GS442-6130-82R-6000:1:74bbc189-3313-4665-8204-9fbe45dfxxxx",
    "traceId": "34c2e8f816414f318b7419b6a9c91d8f",
    "messageTimestamp": 1715740800000
}'

```

## Deployment to AWS ECS

### Multi-Brand, Multi-Region Deployment

Each brand can be deployed independently to different regions:

```bash
# Deploy Pudu to us-east-2
make deploy-us-east-2-pudu

# Deploy Gas to us-east-1
make deploy-us-east-1-gas

# Deploy both brands to same region
make deploy-us-east-2-pudu
make deploy-us-east-2-gas
```

### Setup Commands

```bash
# Setup for specific brand and region
./setup-environment.sh us-east-2 pudu
./setup-environment.sh us-east-1 gas

# Or use make commands
make setup-us-east-2-pudu
make setup-us-east-1-gas
```

### Registry Names

Each brand gets its own ECR registry:
- `foxx_monitor_pudu_webhook_api`
- `foxx_monitor_gas_webhook_api`

## Adding New Robot Brands

### Step 1: Create Brand Config

Create `configs/newbrand/config.yaml`:

```yaml
brand: newbrand

verification:
  method: header  # or 'body'
  key: X-API-Key

type_mappings:
  robot_online: status_event
  robot_alert: error_event

field_mappings:
  error_event:
    source_to_db:
      robot_id: robot_sn
      alert.severity: event_level
    conversions:
      event_level:
        mapping:
          CRITICAL: fatal
          HIGH: error
    drop_fields:
      - internal_id
```

### Step 2: Add Environment Variable

```bash
NEWBRAND_CALLBACK_CODE=your-secret-code
```

### Step 3: Register Endpoint

In `main.py`:
```python
@app.route("/api/newbrand/webhook", methods=["POST"])
def newbrand_webhook():
    return create_webhook_endpoint("newbrand")()
```

### Step 4: Deploy

```bash
./setup-environment.sh us-east-2 newbrand
make deploy-container
```

**That's it!** No other code changes needed.

## Health Check Testing

### Multi-Brand Health Checks

```bash
# General health check
curl http://$PUBLIC_IP:8000/api/webhook/health

# Brand-specific health checks
curl http://$PUBLIC_IP:8000/api/pudu/webhook/health
curl http://$PUBLIC_IP:8000/api/gas/webhook/health
```

### Response Example

```json
{
  "status": "healthy",
  "timestamp": "2025-10-03 12:00:00",
  "service": "robot-webhook-api",
  "configured_brand": "pudu",
  "features": {
    "multi_brand_support": "enabled",
    "dynamic_database_routing": "enabled",
    "change_detection": "enabled"
  },
  "brand_config": {
    "brand": "pudu",
    "method": "header",
    "key": "callbackcode",
    "configured": true
  },
  "supported_endpoints": [
    "/api/pudu/webhook",
    "/api/gas/webhook"
  ]
}
```

## API Endpoints

### General Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/webhook/health` | GET | Overall system health |

### Brand-Specific Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/pudu/webhook` | POST | Pudu robot callbacks |
| `/api/pudu/webhook/health` | GET | Pudu health check |
| `/api/gas/webhook` | POST | Gas robot callbacks |
| `/api/gas/webhook/health` | GET | Gas health check |

## Troubleshooting

### Common Issues

#### 1. Verification Fails

```bash
# Check brand configuration
curl http://localhost:8000/api/pudu/webhook/health

# Verify environment variable is set
echo $PUDU_CALLBACK_CODE
echo $GAS_CALLBACK_CODE
```

#### 2. Field Mapping Issues

Check logs for field mapping errors:
```bash
aws logs filter-log-events \
  --log-group-name /ecs/robot-webhook \
  --filter-pattern "field mapping\|conversion"
```

#### 3. Database Write Failures

```bash
# Check for database errors
aws logs filter-log-events \
  --log-group-name /ecs/robot-webhook \
  --filter-pattern "database\|ERROR"
```

#### 4. Wrong Brand Endpoint

Ensure you're using the correct endpoint:
- Pudu → `/api/pudu/webhook`
- Gas → `/api/gas/webhook`

### Debug Mode

Enable debug logging:
```bash
DEBUG=true
LOG_LEVEL=DEBUG
```

## Monitoring and Notifications

### Notification System

The webhook sends real-time notifications for:
- **Critical events**: Fatal errors, battery critical
- **Task completions**: Cleaning reports (Gas)
- **Status changes**: Robot online/offline
- **Warnings**: Low battery, abnormal status

### CloudWatch Monitoring

Set up alarms for:
- Brand-specific endpoint health
- Database write failures
- Field mapping errors
- Verification failures

## Security Considerations

### Multi-Brand Security

1. **Separate verification codes** for each brand
2. **Brand-specific endpoints** for isolation
3. **Independent deployments** per brand
4. **Separate ECR registries** per brand

### Best Practices

1. Store secrets in AWS Secrets Manager
2. Use HTTPS with ALB
3. Restrict security groups per brand
4. Enable RDS encryption
5. Rotate credentials regularly
6. Monitor brand-specific metrics

## License

Internal use only - [Your Company Name]

## Support

For issues or questions:
- Check logs: `aws logs tail /ecs/robot-webhook --follow`
- Review configuration: `make verify-config`
- Test locally: `make test-local`
- Contact: your-team@company.com
