# Multi-Brand Robot Webhook API

A flexible webhook API system that processes callbacks from multiple robot brands (Pudu, Gas, and future brands) with unified database storage and notification support.

## 🏗️ Architecture Overview

The system uses a **config-driven architecture** that separates brand-specific logic from core functionality:

```
┌─────────────────┐
│  Brand Webhook  │ (Pudu, Gas, etc.)
└────────┬────────┘
         │
    ┌────▼─────┐
    │ Endpoint │ (/api/pudu/webhook, /api/gas/webhook)
    └────┬─────┘
         │
    ┌────▼──────────┐
    │ Verification  │ (Header-based or Body-based)
    └────┬──────────┘
         │
    ┌────▼──────────┐
    │ Type Mapping  │ (Brand callback type → Abstract type)
    └────┬──────────┘
         │
    ┌────▼──────────┐
    │ Field Mapping │ (Brand fields → Unified schema)
    └────┬──────────┘
         │
    ┌────▼──────────┐
    │   Database    │ (Unified storage)
    └───────────────┘
```

## 📁 Codebase Structure

```
robot-webhook-api/
├── core/                          # Brand-agnostic core logic
│   ├── brand_config.py            # Loads brand configs, handles field mapping
│   └── services/
│       └── verification_service.py # Request verification (header/body)
│
├── brands/                        # Brand-specific extensions (optional)
│   ├── pudu/                      # Pudu-specific processors (if needed)
│   └── gas/                       # Gas-specific processors (if needed)
│
├── configs/                       # Configuration files
│   ├── database_config.yaml       # Database routing (which DBs to write to)
│   ├── database_config.py         # Database resolver logic
│   ├── pudu/
│   │   └── config.yaml            # Pudu: type mappings, field mappings, verification
│   └── gas/
│       └── config.yaml            # Gas: type mappings, field mappings, verification
│
├── notifications/                 # Notification system (unchanged)
├── rds/                          # Database utilities (unchanged)
├── services/                     # Shared services (transform, resolvers)
│
├── callback_handler.py           # Main handler: verification → mapping → DB write
├── database_writer.py            # Writes to database with change detection
├── processors.py                 # Base processors for status/error/pose/power
├── models.py                     # Data models (CallbackResponse, etc.)
├── main.py                       # Flask app with brand endpoints
└── config.py                     # Environment configuration
```

## 🔑 Key Concepts

### 1. **Abstract Types**
Brand-specific callback types map to abstract types:
- `status_event` - Robot status updates
- `error_event` - Errors/warnings/incidents
- `pose_event` - Position/location updates
- `power_event` - Battery/power updates
- `report_event` - Task reports (Gas-specific, placeholder)

### 2. **Field Mapping**
Each brand's fields map to a unified database schema:
```yaml
# Pudu uses:
sn → robot_sn
error_level → event_level

# Gas uses:
payload.serialNumber → robot_sn
payload.content.incidentLevel → event_level (with H2→error conversion)
```

### 3. **Verification**
- **Pudu**: Header-based (`CallbackCode` header)
- **Gas**: Body-based (`appId` field)

## 🚀 Adding a New Brand

### Step 1: Create Brand Config

Create `configs/newbrand/config.yaml`:

```yaml
---
brand: newbrand

# Verification method
verification:
  method: header  # or 'body'
  key: X-API-Key  # Header name or body field name

# Map brand callback types to abstract types
type_mappings:
  robot_online: status_event
  robot_alert: error_event
  location_update: pose_event
  battery_report: power_event

# Ignore certain callback types
ignored_types:
  - delivery_update
  - order_status

# Field mappings for each abstract type
field_mappings:
  error_event:
    source_to_db:
      robot_id: robot_sn              # Direct mapping
      alert.id: event_id              # Nested field (dot notation)
      alert.severity: event_level
      alert.message: event_detail
      timestamp_ms: task_time
    conversions:
      event_level:
        type: lowercase
        mapping:                       # Value mapping
          CRITICAL: fatal
          HIGH: error
          MEDIUM: warning
      task_time:
        type: timestamp_ms_to_s        # Convert milliseconds to seconds
    drop_fields:                       # Fields to exclude from DB
      - internal_id
      - metadata

  # Repeat for status_event, pose_event, power_event...

# Coordinate transformation support
transform_enabled: false
```

### Step 2: Add Environment Variable

In `.env`:
```bash
NEWBRAND_CALLBACK_CODE=your-secret-verification-code
```

### Step 3: Register Endpoint

In `main.py`, add:
```python
@app.route("/api/newbrand/webhook", methods=["POST"])
def newbrand_webhook():
    """NewBrand robot webhook endpoint"""
    return create_webhook_endpoint("newbrand")()
```

### Step 4: Test

```bash
# Test the new endpoint
curl -X POST http://localhost:8000/api/newbrand/webhook \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-verification-code" \
  -d '{
    "robot_online": true,
    "robot_id": "NB-001",
    "timestamp_ms": 1715740800000
  }'

# Check health
curl http://localhost:8000/api/newbrand/webhook/health
```

### Step 5: Optional - Brand-Specific Processors

If you need custom processing logic, create `brands/newbrand/processors.py`:

```python
from processors import BaseProcessor

class NewBrandErrorProcessor(BaseProcessor):
    """Custom error processing for NewBrand"""

    def process(self, data):
        # Custom logic here
        return super().process(data)
```

Then register in `callback_handler.py`.

## 🔧 Configuration Reference

### Supported Conversions
- `type: lowercase` - Convert to lowercase
- `type: uppercase` - Convert to uppercase
- `type: int` - Convert to integer
- `type: float` - Convert to float
- `type: timestamp_ms_to_s` - Convert milliseconds to seconds
- `mapping: {A: B}` - Map value A to value B

### Nested Field Access
Use dot notation for nested fields:
```yaml
payload.content.incidentId: event_id
robot.status.level: event_level
```

## 🌐 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/pudu/webhook` | POST | Pudu robot callbacks |
| `/api/gas/webhook` | POST | Gas robot callbacks |
| `/api/webhook/health` | GET | Overall system health |
| `/api/<brand>/webhook/health` | GET | Brand-specific health |

## 🧪 Testing

```bash
# Run tests
python -m pytest test/

# Test specific brand
curl -X POST http://localhost:8000/api/pudu/webhook \
  -H "CallbackCode: $PUDU_CALLBACK_CODE" \
  -d @test/test_data/robot_status_data.json
```

## 📝 Environment Variables

```bash
# Server
HOST=0.0.0.0
PORT=8000

# Brand verification
PUDU_CALLBACK_CODE=secret-pudu-code
GAS_CALLBACK_CODE=secret-gas-code

# Database
DATABASE_URL=mysql://...

# Notifications
ALERT_EMAIL=alerts@company.com
```

## 🎯 Design Principles

1. **Config over Code** - Maximize configuration, minimize brand-specific code
2. **Abstract Types** - Internal processing uses generic types
3. **Fail Gracefully** - Missing fields → NULL, not errors
4. **Single Source of Truth** - One unified database schema
5. **Extensibility** - Adding brands should be mostly configuration

## 📚 Further Reading

- `configs/database_config.yaml` - Database routing rules
- `core/brand_config.py` - Field mapping implementation
- `callback_handler.py` - Request processing flow
- `database_writer.py` - Database writing with change detection
