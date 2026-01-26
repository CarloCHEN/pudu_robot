# Robot Service Training Guide

> This document is for training new employees, providing a comprehensive introduction to the pudu_robot project structure and Robot Service architecture.

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Project Structure](#project-structure)
3. [Robot Service Architecture](#robot-service-architecture)
4. [Core Modules Deep Dive](#core-modules-deep-dive)
5. [Data Flow](#data-flow)
6. [Deployment & Operations](#deployment--operations)
7. [Development Guide](#development-guide)

---

## 1. Project Overview

### 1.1 Project Positioning

`pudu_robot` is a **multi-brand robot management platform** that provides the following core capabilities:

- 🤖 **Multi-brand Support**: Currently supports Pudu and Gas robots, with architecture designed for rapid expansion to new brands
- 📊 **Real-time Data Collection**: Receives real-time robot status via API polling and Webhook reception
- 💾 **Data Storage & Management**: Unified data model supporting multi-customer, multi-database routing
- 📈 **Data Analysis & Reporting**: Automatically generates robot performance reports and operational analytics
- 🔔 **Intelligent Notifications**: Real-time notification system based on data changes
- 🗺️ **Map & Coordinate Transformation**: Robot map management and coordinate system conversion

### 1.2 Technology Stack

- **Language**: Python 3.9+
- **Framework**: Flask (Webhook API), FastAPI (Report API)
- **Database**: MySQL (RDS), supports multi-database routing
- **Cloud Services**: AWS (ECS, ECR, RDS, S3, Lambda, EventBridge)
- **Data Processing**: Pandas, NumPy
- **Containerization**: Docker
- **Orchestration**: Airflow (DAGs)

---

## 2. Project Structure

### 2.1 Overall Directory Structure

```
pudu_robot/
├── src/pudu/                          # Core business logic
│   ├── apis/                          # API interface layer
│   │   ├── core/                      # Core API framework
│   │   ├── adapters/                  # API adapters
│   │   ├── raw/                       # Raw API implementations
│   │   └── foxx_api.py                # Unified business API
│   │
│   ├── app/                           # Main application
│   │   └── main.py                    # Core data processing logic
│   │
│   ├── services/                      # Business service layer
│   │   ├── task_management_service.py # Task management service
│   │   ├── transform_service.py        # Coordinate transformation service
│   │   ├── robot_database_resolver.py # Database routing service
│   │   └── s3_service.py              # S3 storage service
│   │
│   ├── reporting/                     # Report generation system
│   │   ├── core/                      # Report core logic
│   │   ├── templates/                 # Report templates
│   │   ├── services/                  # Report services
│   │   └── calculators/               # Metrics calculators
│   │
│   ├── notifications/                  # Notification system
│   │   ├── notification_service.py    # Notification service
│   │   ├── change_detector.py         # Change detection
│   │   └── notification_sender.py    # Notification sender
│   │
│   ├── rds/                            # Database operations
│   │   └── rdsTable.py                # Database table operation wrapper
│   │
│   └── configs/                        # Configuration management
│       └── database_config.yaml       # Database configuration
│
├── pudu-webhook-api/                  # Webhook receiving service
│   ├── main.py                        # Flask application entry point
│   ├── callback_handler.py            # Callback handler
│   ├── database_writer.py             # Database writer
│   ├── services/                      # Webhook services
│   └── configs/                       # Webhook configuration
│
├── report_api/                         # Report generation API
│   ├── main.py                        # FastAPI application
│   └── requirements.txt
│
├── lambda/                             # Lambda functions
│   ├── robot_lambda_function.py       # Robot data processing
│   └── report_generator_lambda.py    # Report generation
│
├── robot-kpi-calculator/               # KPI calculator
│   └── src/
│       ├── kpi/                       # KPI calculation logic
│       └── models/                    # Data models
│
└── dags/                               # Airflow DAGs
    └── write_robot.py                 # Scheduled tasks
```

### 2.2 Module Responsibility Matrix

| Module | Responsibility | Key Files |
|--------|---------------|-----------|
| **apis** | Multi-brand API unified interface | `foxx_api.py`, `core/api_factory.py` |
| **app** | Core data processing pipeline | `main.py` |
| **services** | Business logic services | `task_management_service.py`, `transform_service.py` |
| **reporting** | Report generation system | `core/report_generator.py` |
| **notifications** | Notification system | `notification_service.py` |
| **rds** | Database operations | `rdsTable.py` |
| **webhook-api** | Webhook receiving | `main.py`, `callback_handler.py` |

---

## 3. Robot Service Architecture

### 3.1 Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Webhook API  │  │  Report API  │  │  Lambda      │     │
│  │  (Flask)      │  │  (FastAPI)   │  │  Functions   │     │
│  └──────┬────────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │             │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
┌─────────▼──────────────────▼──────────────────▼─────────────┐
│                    SERVICE LAYER                            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Task        │  │  Transform   │  │  Notification│     │
│  │  Management  │  │  Service     │  │  Service     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Robot DB    │  │  Report      │  │  S3 Service  │     │
│  │  Resolver    │  │  Generator   │  │              │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                               │
└─────────┬───────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────────┐
│                    API LAYER                                 │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  API Factory │  │  Pudu        │  │  Gas         │     │
│  │              │  │  Adapter     │  │  Adapter     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐                       │
│  │  Pudu API    │  │  Gas API     │                       │
│  │  (Raw)       │  │  (Raw)       │                       │
│  └──────────────┘  └──────────────┘                       │
│                                                               │
└─────────┬───────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────────┐
│                    DATA LAYER                                │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  RDS MySQL   │  │  S3 Storage  │  │  External    │     │
│  │  (Multi-DB)  │  │  (Maps/      │  │  APIs        │     │
│  │              │  │  Reports)    │  │  (Pudu/Gas)  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Core Design Patterns

#### 3.2.1 Factory + Adapter Pattern (API Layer)

**Purpose**: Unify multi-brand API interfaces with low-coupling extensibility

**Implementation**:
- `APIFactory`: Creates and manages API adapter instances
- `RobotAPIInterface`: Defines unified interface specification
- `PuduAdapter` / `GasAdapter`: Brand-specific adapters

**Advantages**:
- ✅ Adding new brands only requires adding an adapter, no business code changes needed
- ✅ Unified interface facilitates business logic reuse
- ✅ Supports runtime dynamic API selection

#### 3.2.2 Service Layer Pattern (Service Layer)

**Purpose**: Separate business logic from application layer, improving testability and maintainability

**Core Services**:
- `TaskManagementService`: Task lifecycle management
- `TransformService`: Coordinate system and map transformation
- `RobotDatabaseResolver`: Intelligent database routing
- `NotificationService`: Notification sending and management

#### 3.2.3 Multi-Database Routing (Data Layer)

**Purpose**: Support flexible deployment for multi-customer, multi-database scenarios

**Implementation**:
- Automatic routing to correct database based on `robot_sn`
- Database-level configuration isolation support
- Dynamic database connection management

---

## 4. Core Modules Deep Dive

### 4.1 API Module (`src/pudu/apis/`)

#### 4.1.1 Architecture Design

```
apis/
├── core/                    # Core framework
│   ├── api_interface.py     # Interface definition
│   ├── api_factory.py       # Factory pattern
│   ├── api_registry.py      # Auto-discovery
│   └── config_manager.py    # Configuration management
│
├── adapters/                # Adapter layer
│   ├── pudu_adapter.py     # Pudu adapter
│   └── gas_adapter.py      # Gas adapter
│
├── raw/                     # Raw API implementations
│   ├── pudu_api.py         # Pudu raw API
│   └── gas_api.py          # Gas raw API
│
└── foxx_api.py              # Unified business API
```

#### 4.1.2 Usage Examples

```python
# Method 1: Through foxx_api unified interface (Recommended)
from pudu.apis.foxx_api import get_robot_status

# Get Pudu robot status
status = get_robot_status("PUDU-001", robot_type="pudu")

# Get Gas robot status
status = get_robot_status("GAS-001", robot_type="gas")

# Method 2: Direct use of API Factory
from pudu.apis.core.api_factory import APIFactory

factory = APIFactory()
pudu_api = factory.create_api("pudu")
gas_api = factory.create_api("gas")
```

#### 4.1.3 Key Interfaces

| Interface Method | Description | Supported Brands |
|-----------------|-------------|------------------|
| `get_robot_details(sn)` | Get robot detailed information | Pudu, Gas |
| `get_list_stores()` | Get store list | Pudu, Gas |
| `get_list_robots(shop_id)` | Get robot list | Pudu, Gas |
| `get_task_list()` | Get task list | Pudu |
| `get_cleaning_reports()` | Get cleaning reports | Gas |

### 4.2 Main Application Module (`src/pudu/app/main.py`)

#### 4.2.1 Core Functions

The `App` class is the core engine for data processing, responsible for:

1. **Data Collection**: Fetching robot data from multiple API sources
2. **Data Processing**: Transforming, validating, and enriching data
3. **Data Storage**: Batch writing to database
4. **Change Detection**: Identifying data changes and triggering notifications
5. **Parallel Processing**: Parallel processing across multiple databases and robots

#### 4.2.2 Workflow

```python
# Initialize App
app = App(config_path="database_config.yaml")

# Process all robot data
app.process_all_robots()

# Or process specific customers
app.process_customers(["UF2", "USF"])
```

#### 4.2.3 Data Processing Pipeline

```
1. Get robot list (grouped by database)
   ↓
2. Parallel API calls (multi-threaded)
   ↓
3. Data transformation and validation
   ↓
4. Change detection
   ↓
5. Batch database writes
   ↓
6. Send notifications (if changes detected)
```

### 4.3 Service Module (`src/pudu/services/`)

#### 4.3.1 TaskManagementService

**Responsibility**: Manage task lifecycle (ongoing → completed)

**Core Functions**:
- `manage_ongoing_tasks_complete()`: Complete task management
- `_upsert_ongoing_tasks()`: Update or insert ongoing tasks
- `_cleanup_ongoing_tasks_for_robots()`: Clean up completed tasks

**Use Cases**:
- Real-time task monitoring
- Task completion detection
- Task status synchronization

#### 4.3.2 TransformService

**Responsibility**: Coordinate system and map transformation

**Core Functions**:
- `transform_robot_coordinates_batch()`: Batch coordinate transformation
- `transform_task_maps_batch()`: Task map transformation
- S3 map upload and URL generation

**Use Cases**:
- Robot position visualization
- Map overlay display
- Coordinate system unification

#### 4.3.3 RobotDatabaseResolver

**Responsibility**: Intelligent database routing

**Core Functions**:
- Find corresponding database based on `robot_sn`
- Group robots by database
- Support multi-customer, multi-database configuration

**Configuration Example**:
```yaml
databases:
  UF2:
    robots:
      - "PUDU-001"
      - "GAS-001"
  USF:
    robots:
      - "PUDU-002"
```

### 4.4 Webhook Module (`pudu-webhook-api/`)

#### 4.4.1 Architecture Features

- **Multi-brand Support**: Unified interface with brand-specific configuration
- **Configuration-Driven**: Field mapping via YAML configuration, no code changes needed
- **Real-time Processing**: Immediate database write after receiving webhook
- **Security Verification**: Brand-specific verification mechanisms

#### 4.4.2 Supported Webhook Types

**Pudu Webhooks**:
- `robotStatus` → Robot status updates
- `robotErrorWarning` → Error/warning events
- `notifyRobotPose` → Position updates
- `notifyRobotPower` → Battery updates

**Gas Webhooks**:
- `messageTypeId: 1` → Events/errors
- `messageTypeId: 2` → Task reports

#### 4.4.3 Data Flow

```
Webhook Request
    ↓
Brand Identification & Verification
    ↓
Field Mapping & Transformation
    ↓
Unified Data Model
    ↓
Database Write
    ↓
Change Detection & Notification
```

### 4.5 Reporting Module (`src/pudu/reporting/`)

#### 4.5.1 Report Types

- **Robot Performance Report**: Cleaning efficiency, task completion rate
- **Charging Performance Report**: Charging frequency, battery health
- **Resource Utilization Report**: Robot usage rate, task distribution
- **Financial Performance Report**: ROI, cost analysis

#### 4.5.2 Report Generation Flow

```
1. Receive Report Request (API/Lambda)
   ↓
2. Parse Configuration (ReportConfig)
   ↓
3. Fetch Data (via App class)
   ↓
4. Calculate Metrics (Calculators)
   ↓
5. Generate Template (HTML/PDF)
   ↓
6. Upload to S3
   ↓
7. Send Notification (Email/In-app)
```

#### 4.5.3 Report Configuration

```python
form_data = {
    'service': 'robot-management',
    'contentCategories': ['charging-performance', 'cleaning-performance'],
    'timeRange': 'last-30-days',
    'detailLevel': 'detailed',
    'outputFormat': 'html',
    'delivery': 'email',
    'schedule': 'weekly'
}
```

---

## 5. Data Flow

### 5.1 Complete Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA SOURCES                              │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Pudu API    │  │  Gas API     │  │  Webhooks    │     │
│  │  (Polling)    │  │  (Polling)   │  │  (Real-time) │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                 │                 │             │
└─────────┼─────────────────┼─────────────────┼─────────────┘
          │                 │                 │
          │                 │                 │
┌─────────▼─────────────────▼─────────────────▼─────────────┐
│                    DATA INGESTION                           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  • API Polling (Scheduled)                                   │
│  • Webhook Receiving (Real-time)                             │
│  • Data Validation                                           │
│  • Brand-specific Processing                                  │
│                                                               │
└─────────┬───────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────────┐
│                    DATA PROCESSING                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  • Coordinate Transformation                                 │
│  • Map Conversion                                            │
│  • Change Detection                                          │
│  • Data Enrichment                                           │
│                                                               │
└─────────┬───────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────────┐
│                    DATA STORAGE                              │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  MySQL RDS  │  │  S3 Storage  │  │  Reports     │     │
│  │  (Structured│  │  (Maps/      │  │  (Generated) │     │
│  │   Data)     │  │   Files)     │  │              │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                               │
└─────────┬───────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────────┐
│                    DATA OUTPUT                               │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  • Real-time Dashboard                                       │
│  • Scheduled Reports                                         │
│  • Notifications (Email/SMS)                                 │
│  • API Endpoints                                             │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Database Table Structure

#### Core Tables

| Table Name | Description | Key Fields |
|------------|-------------|------------|
| `mnt_robots_management` | Robot real-time status | `robot_sn`, `status`, `position`, `battery` |
| `mnt_robots_task` | Task records | `task_id`, `robot_sn`, `status`, `start_time` |
| `mnt_robot_events` | Event records | `robot_sn`, `event_level`, `event_type`, `task_time` |
| `mnt_robots_charging` | Charging records | `robot_sn`, `charge_time`, `power_percent` |
| `mnt_robots_work_location` | Work location | `robot_sn`, `location_id`, `x`, `y` |

### 5.3 Data Synchronization Strategy

#### Scheduled Sync (Airflow DAG)

- **Frequency**: Every 30-60 seconds
- **Method**: API polling
- **Scope**: All configured robots

#### Real-time Sync (Webhook)

- **Trigger**: When robot events occur
- **Latency**: <1 second
- **Scope**: Robots with configured webhooks

---

## 6. Deployment & Operations

### 6.1 Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AWS CLOUD                                 │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  ECS         │  │  Lambda     │  │  RDS         │     │
│  │  (Webhook)   │  │  (Reports)  │  │  (MySQL)     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  S3          │  │  EventBridge │  │  ALB         │     │
│  │  (Storage)   │  │  (Schedule)  │  │  (Load       │     │
│  │              │  │              │  │   Balancer)  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Deployment Steps

#### 6.2.1 Webhook API Deployment

```bash
# 1. Build Docker image
cd pudu-webhook-api
docker build -t robot-webhook-api .

# 2. Push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-2.amazonaws.com
docker tag robot-webhook-api:latest <account>.dkr.ecr.us-east-2.amazonaws.com/foxx_monitor_pudu_webhook_api:latest
docker push <account>.dkr.ecr.us-east-2.amazonaws.com/foxx_monitor_pudu_webhook_api:latest

# 3. Deploy to ECS
./deploy.sh
```

#### 6.2.2 Report API Deployment

```bash
cd report_api
./deploy-with-alb.sh
```

#### 6.2.3 Lambda Deployment

```bash
cd lambda
./deploy_lambda.sh
```

### 6.3 Monitoring & Logging

#### 6.3.1 Key Metrics

- **API Call Success Rate**: Target >99%
- **Database Write Latency**: Target <100ms
- **Webhook Processing Latency**: Target <1s
- **Report Generation Time**: Target <30s

#### 6.3.2 Log Locations

- **ECS Logs**: CloudWatch Logs `/ecs/robot-webhook`
- **Lambda Logs**: CloudWatch Logs `/aws/lambda/robot-lambda`
- **Application Logs**: Local files or CloudWatch

### 6.4 Troubleshooting

#### Common Issues

1. **API Call Failures**
   - Check API credential configuration
   - Verify network connectivity
   - Check API rate limiting

2. **Database Write Failures**
   - Check database connection
   - Verify table structure
   - Check database capacity

3. **Webhook Reception Failures**
   - Check verification code configuration
   - Verify field mapping
   - Check log details

---

## 7. Development Guide

### 7.1 Adding New Robot Brand

#### Step 1: Create Raw API Implementation

```python
# src/pudu/apis/raw/newbrand_api.py
class NewBrandAPI:
    def get_robot_status(self, sn):
        # Implement brand-specific API calls
        pass
```

#### Step 2: Create Adapter

```python
# src/pudu/apis/adapters/newbrand_adapter.py
from pudu.apis.core.api_interface import RobotAPIInterface

class NewBrandAdapter(RobotAPIInterface):
    def __init__(self):
        self.api = NewBrandAPI()
    
    def get_robot_details(self, sn):
        # Adapt to unified interface
        return self.api.get_robot_status(sn)
```

#### Step 3: Register Adapter

```yaml
# src/pudu/apis/configs/api_config.yaml
apis:
  newbrand:
    enabled: true
    adapter: newbrand_adapter.NewBrandAdapter
```

### 7.2 Adding New Data Processing Service

```python
# src/pudu/services/new_service.py
class NewService:
    def __init__(self, config):
        self.config = config
    
    def process_data(self, data):
        # Implement processing logic
        return processed_data
```

### 7.3 Testing Guide

#### Unit Tests

```python
# test/unit/test_new_service.py
def test_new_service():
    service = NewService(config)
    result = service.process_data(test_data)
    assert result is not None
```

#### Integration Tests

```python
# test/integration/test_pipeline.py
def test_full_pipeline():
    app = App(config_path="test_config.yaml")
    app.process_all_robots()
    # Verify data in database
```

### 7.4 Code Standards

- **Naming**: Use snake_case
- **Type Hints**: Add type annotations to all functions
- **Docstrings**: Add docstrings to all public functions
- **Logging**: Use logging module, avoid print statements
- **Error Handling**: Use try-except, log error messages

---

## 8. Quick Start

### 8.1 Local Development Environment Setup

```bash
# 1. Clone repository
git clone <repository>
cd pudu_robot

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure database
cp src/pudu/configs/database_config.yaml.example \
   src/pudu/configs/database_config.yaml
# Edit configuration file

# 5. Run tests
python -m pytest test/
```

### 8.2 Usage Examples

```python
# Example 1: Get robot status
from pudu.apis.foxx_api import get_robot_status

status = get_robot_status("PUDU-001", robot_type="pudu")
print(status)

# Example 2: Process all robot data
from pudu.app.main import App

app = App()
app.process_all_robots()

# Example 3: Generate report
from pudu.reporting.core.report_generator import ReportGenerator
from pudu.reporting.core.report_config import ReportConfig

form_data = {
    'service': 'robot-management',
    'contentCategories': ['robot-status'],
    'timeRange': 'last-7-days',
    'detailLevel': 'summary'
}
config = ReportConfig(form_data, 'UF2')
generator = ReportGenerator()
result = generator.generate_report(config)
```

---

## 9. FAQ

### Q1: How to add a new database?

**A**: Add new database configuration in `database_config.yaml`:

```yaml
databases:
  NEW_DB:
    host: new-db-host
    port: 3306
    user: username
    password: password
    robots:
      - "ROBOT-001"
      - "ROBOT-002"
```

### Q2: How to customize notification rules?

**A**: Modify detection logic in `notifications/change_detector.py` or add new detection rules.

### Q3: How to extend report content?

**A**: 
1. Add new calculators in `reporting/calculators/`
2. Update templates in `reporting/templates/`
3. Add new content categories in `report_config.py`

### Q4: How to handle API rate limiting?

**A**: 
- Implement request queue and retry mechanisms
- Use caching to reduce API calls
- Negotiate higher API rate limit quotas

---

## 10. References

- [API Architecture Documentation](./src/pudu/apis/README.md)
- [Reporting System Documentation](./src/pudu/reporting/README.MD)
- [Webhook API Documentation](./pudu-webhook-api/README.md)
- [Cloud Platform Architecture Documentation](./Cloud_System.md)

---

## 11. Contact & Support

- **Technical Documentation**: Check README.md files in each module
- **Issue Reporting**: Submit Issues or contact development team
- **Code Review**: Follow Git Flow workflow

---

**Document Version**: v1.0  
**Last Updated**: 2025-01-XX  
**Maintainer**: Robot Service Team
