# Pudu Webhook API Testing Framework

A comprehensive testing framework for the Pudu Robot Webhook API that validates all components using mock services and real data scenarios.

## 📁 Test Structure

```
test/
├── __init__.py                    # Package initialization
├── conftest.py                    # pytest configuration
├── README.md                      # This file
├── run_tests.py                   # Main test runner
│
├── test_data/                     # Test data files
│   ├── robot_status_data.json     # Robot status test cases
│   ├── robot_error_data.json      # Robot error test cases
│   ├── robot_pose_data.json       # Robot pose test cases
│   └── robot_power_data.json      # Robot power test cases
│
├── mocks/                         # Mock services
│   ├── __init__.py
│   ├── mock_database.py           # Mock database with schema validation
│   └── mock_notification.py       # Mock notification service
│
├── utils/                         # Test utilities
│   ├── __init__.py
│   ├── test_helpers.py            # Test utility functions
│   └── webhook_client.py          # HTTP client for webhook testing
│
├── unit/                          # Unit tests
│   ├── __init__.py
│   ├── test_processors.py         # Test callback processors
│   ├── test_database_writer.py    # Test database operations
│   └── test_notification_sender.py # Test notification logic
│
└── integration/                   # Integration tests
    ├── __init__.py
    ├── test_webhook_endpoint.py   # End-to-end webhook tests
    └── test_complete_flow.py      # Complete data flow tests
```

## 🚀 Quick Start

### 1. Run All Tests (Recommended)

```bash
# Run complete test suite (excluding endpoint tests)
python test/run_tests.py

# Run all tests including webhook endpoint tests (requires running server)
python test/run_tests.py --include-endpoint
```

### 2. Run Specific Test Categories

```bash
# Run only unit tests
python test/run_tests.py --unit-only

# Run only integration tests
python test/run_tests.py --integration-only

# Run with verbose output
python test/run_tests.py --verbose --log-level DEBUG
```

### 3. Run Individual Test Files

```bash
# Test processors
python test/unit/test_processors.py

# Test database operations
python test/unit/test_database_writer.py

# Test notifications
python test/unit/test_notification_sender.py

# Test complete flow
python test/integration/test_complete_flow.py

# Test webhook endpoint (requires running server)
python test/integration/test_webhook_endpoint.py
```

## 📊 Test Categories

### Unit Tests

#### 1. Processor Tests (`test_processors.py`)
- **RobotStatusProcessor**: Tests all robot status changes (online, offline, working, etc.)
- **RobotErrorProcessor**: Tests error handling for different severity levels
- **RobotPoseProcessor**: Tests position tracking and coordinate validation
- **RobotPowerProcessor**: Tests battery monitoring and power state changes

#### 2. Database Writer Tests (`test_database_writer.py`)
- **Schema Validation**: Ensures data matches expected database schemas
- **Field Mapping**: Validates that callback data maps correctly to database fields
- **Primary Key Validation**: Confirms primary keys match configuration
- **Data Filtering**: Tests None value filtering and data sanitization
- **Configuration Consistency**: Validates config files match expected schemas

#### 3. Notification Sender Tests (`test_notification_sender.py`)
- **Content Generation**: Tests notification title and content creation
- **Severity Mapping**: Validates error levels map to correct notification severities
- **Icon Integration**: Tests notification formatting with appropriate icons
- **Battery Thresholds**: Validates battery level notification triggers
- **Service Connectivity**: Tests mock notification service communication

### Integration Tests

#### 1. Webhook Endpoint Tests (`test_webhook_endpoint.py`)
**⚠️ Requires running webhook server on localhost:8000**

- **Health Check**: Validates webhook service availability
- **Callback Processing**: Tests all callback types end-to-end
- **Invalid Request Handling**: Tests security and error handling
- **Batch Processing**: Tests multiple concurrent callbacks
- **Performance Testing**: Validates throughput and response times

#### 2. Complete Flow Tests (`test_complete_flow.py`)
- **End-to-End Pipeline**: Tests complete data flow from callback to database/notification
- **Data Consistency**: Validates data integrity across all components
- **Error Resilience**: Tests system behavior with invalid/corrupted data
- **Mixed Callback Processing**: Tests handling multiple callback types
- **Performance Flow**: Tests system performance under load

## 📋 Test Data

### Robot Status Test Cases
- **Valid Status Changes**: online, offline, working, idle, charging, error, maintenance
- **Edge Cases**: unknown status, empty values, case sensitivity
- **Invalid Cases**: missing required fields

### Robot Error Test Cases (4. **Test with new cases**: `python run_tests.py --unit-only`

### Custom Test Scenarios

Create custom test cases by modifying the JSON files:

```json
{
  "name": "custom_test_case",
  "callback_type": "robotStatus",
  "data": {
    "sn": "CUSTOM_ROBOT_001",
    "run_status": "CUSTOM_STATUS",
    "timestamp": 1640995800
  },
  "expected_status": "custom",
  "expected_severity": "event"
}
```

## 🎯 Success Criteria

### Unit Test Success Criteria
- **Processors**: 100% of valid test cases should pass
- **Database Writer**: All schema validations should pass
- **Notification Sender**: All format validations should pass

### Integration Test Success Criteria
- **Complete Flow**: 90%+ success rate for end-to-end processing
- **Webhook Endpoint**: 85%+ success rate for HTTP requests
- **Error Resilience**: All error scenarios handled gracefully

### Performance Criteria
- **Throughput**: ≥5 callbacks per second
- **Response Time**: <200ms per callback
- **Memory Usage**: Stable during batch processing

## 🔒 Security Testing

The framework includes security validation:

- **Authentication**: Callback code validation
- **Input Sanitization**: Invalid data handling
- **Error Information**: Secure error messages
- **Rate Limiting**: Batch processing limits

## 🌐 Curl Command Generation

Generate curl commands for manual testing:

```python
from test.utils.webhook_client import WebhookClient

client = WebhookClient()
callback_data = {"callback_type": "robotStatus", "data": {"sn": "TEST_001", "run_status": "ONLINE"}}
curl_command = client.generate_curl_command(callback_data)
print(curl_command)
```

## 📖 Example Usage

### Basic Test Run
```bash
python test/run_tests.py
```

### Full Validation (with running server)
```bash
# Terminal 1: Start webhook server
cd pudu-webhook-api
python test/test_main.py

# Terminal 2: Run all tests
python test/run_tests.py --include-endpoint --verbose
```

### Quick Unit Test
```bash
python test/unit/test_processors.py
```

### Manual Webhook Test
```bash
curl -X POST "http://localhost:8000/api/pudu/webhook" \
  -H "Content-Type: application/json" \
  -H "CallbackCode: 1vQ6MfUxqyoGMRQ9nK8C4pSkg1Qsa3Vpq" \
  -d '{
    "callback_type": "robotStatus",
    "data": {
      "sn": "MANUAL_TEST_001",
      "run_status": "ONLINE",
      "timestamp": 1640995800
    }
  }'
```

## 🎉 Expected Output

### Successful Test Run
```
================================================================================
🚀 PUDU WEBHOOK API TEST SUITE
================================================================================
📋 Test Categories:
  • Unit Tests: Processors, Database Writer, Notification Sender
  • Integration Tests: Complete Flow
================================================================================

🧪 RUNNING UNIT TESTS
================================================================================
✅ test_processors.py - PASSED
✅ test_database_writer.py - PASSED
✅ test_notification_sender.py - PASSED

🔗 RUNNING INTEGRATION TESTS
================================================================================
✅ test_complete_flow.py - PASSED

📊 FINAL TEST SUITE SUMMARY
================================================================================
⏱️  Total execution time: 45.67 seconds
📈 Test categories: 4
✅ Passed: 4
❌ Failed: 0
📊 Success rate: 100.0%

🎉 ALL TESTS PASSED! The webhook API is ready for deployment.
```

## 📚 Additional Resources

- **Main Documentation**: `../README.md`
- **API Configuration**: `../config.py`
- **Database Schema**: `../database_config.yaml`
- **Notification Setup**: `../notifications/`

## 🤝 Contributing

When adding new tests:

1. **Follow naming conventions**: `test_feature_scenario`
2. **Add comprehensive docstrings**: Explain what each test validates
3. **Include edge cases**: Test boundary conditions and error scenarios
4. **Update test data**: Add new JSON test cases as needed
5. **Document expectations**: Clearly state what constitutes success/failure

## 🏁 Conclusion

This testing framework provides comprehensive validation of the Pudu Webhook API, ensuring:

- ✅ **Functional Correctness**: All components work as expected
- ✅ **Data Integrity**: Information flows correctly through the pipeline
- ✅ **Error Resilience**: System handles failures gracefully
- ✅ **Performance**: System meets throughput requirements
- ✅ **Security**: Proper authentication and input validation
- ✅ **Configuration**: All config files are valid and consistent

Run the tests regularly during development and before deployment to ensure system reliability! types × 4 severity levels = 16 scenarios)
- **Navigation Errors**: LostLocalization with FATAL/ERROR/WARNING/INFO levels
- **Hardware Errors**: MotorFault with all severity levels
- **Sensor Errors**: SensorFailure with all severity levels
- **Cleaning Errors**: CleaningSystemFault with all severity levels

### Robot Pose Test Cases
- **Normal Positions**: typical office coordinates and orientations
- **Boundary Positions**: extreme coordinates and rotation values
- **Precision Positions**: high-precision decimal coordinates
- **Edge Cases**: missing fields, null values, string coordinates

### Robot Power Test Cases
- **Normal Power Levels**: 100%, 85%, 50%, 75% battery scenarios
- **Low Battery Alerts**: Critical (3%), Low (8%), Warning (15%) levels
- **Charging Scenarios**: charging states and completion notifications
- **Edge Cases**: 0%, >100%, negative values, invalid data types

## 🧪 Mock Services

### Mock Database (`mock_database.py`)
- **Schema Validation**: Validates data against expected table schemas
- **Field Verification**: Ensures all fields exist in target tables
- **Primary Key Checking**: Validates primary keys match configuration
- **Data Capture**: Stores all write operations for test validation
- **Configuration Validation**: Checks config files against schemas

**Validated Tables:**
- `mnt_robots_management`: Robot status, position, and power data
- `mnt_robot_events`: Robot error events and warnings

### Mock Notification Service (`mock_notification.py`)
- **HTTP Request Simulation**: Captures all notification requests
- **Format Validation**: Validates notification payload structure
- **Connectivity Testing**: Simulates service availability checks
- **Data Aggregation**: Collects notifications for test verification
- **Performance Metrics**: Tracks notification sending performance

## 🔧 Configuration Validation

The testing framework validates that your configuration files are correct:

### Database Configuration (`database_config.yaml`)
- Validates table names match expected schemas
- Confirms primary keys are correctly defined
- Checks database names are properly configured

### Credentials Configuration (`credentials.yaml`)
- Tests database connection parameters (mock validation)
- Validates AWS Secrets Manager configuration format

## 📈 Test Reports

### Console Output
- ✅ **PASS/FAIL** indicators for each test
- 📊 **Summary statistics** for each test category
- 🔍 **Detailed error messages** for failed tests
- ⏱️ **Performance metrics** for timing-sensitive tests

### Test Categories Reporting
- **Unit Tests**: Individual component validation
- **Integration Tests**: End-to-end system validation
- **Mock Service Summaries**: Data written and notifications sent
- **Performance Metrics**: Throughput and response times

## 🛠️ Development Workflow

### 1. Before Deployment
```bash
# Run complete test suite
python run_tests.py --verbose

# Ensure all tests pass
# Review any warnings or recommendations
```

### 2. Testing Changes
```bash
# Test specific component after changes
python unit/test_processors.py          # After processor changes
python unit/test_database_writer.py     # After database changes
python unit/test_notification_sender.py # After notification changes
```

### 3. Pre-Production Validation
```bash
# Start webhook server in test mode
cd ..
python test/test_main.py

# Run endpoint tests in another terminal
python test/run_tests.py --include-endpoint
```

## 🚨 Troubleshooting

### Common Issues

#### "Module not found" errors
```bash
# Ensure you're running from the test directory
python test/run_tests.py
```

#### Mock database validation failures
- Check that `database_config.yaml` exists and is valid
- Ensure table schemas in mock match your actual database
- Verify primary key definitions are correct

#### Notification test failures
- Confirm notification payload structure matches expected format
- Check severity and status value mappings
- Verify icon configuration if using custom icons

#### Endpoint test failures
- Ensure webhook server is running: `python test_main.py`
- Check server is accessible on localhost:8000
- Verify callback code in server matches test configuration
- Ensure mock services are properly configured in server

### Debug Mode
```bash
# Run with maximum verbosity
python test/run_tests.py --verbose --log-level DEBUG

# This will show:
# - Detailed request/response data
# - Mock service operations
# - Database write operations
# - Notification sending details
```

## 📝 Test Data Generation

### Adding New Test Cases

1. **Edit JSON files** in `test_data/` directory
2. **Follow existing structure** for consistency
3. **Include edge cases** and error scenarios