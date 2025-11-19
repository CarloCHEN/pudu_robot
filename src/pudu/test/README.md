# Pudu Robot Data Pipeline - Test Suite

A comprehensive testing framework for the Pudu robot data pipeline that validates data processing, change detection, notifications, and complete integration flows.

## 📁 Test Structure

```
test/
├── unit/                           # Unit tests for individual components
│   ├── test_change_detection.py    # Change detection algorithm tests
│   ├── test_data_processing.py     # Data transformation and processing tests
│   ├── test_data_validation.py     # Data validation and sanitization tests
│   └── test_notifications.py       # Notification logic and content tests
│
├── integration/                    # Integration tests for complete flows
│   └── test_pipeline.py           # End-to-end pipeline testing with real data
│
├── test_data/                      # JSON test data files
│   ├── comprehensive_test_data.json   # Combined test scenarios
│   ├── location_data.json             # Location/building test data
│   ├── robot_charging_data.json       # Robot charging session data
│   ├── robot_event_data.json          # Robot error/warning events
│   ├── robot_status_data.json         # Robot status and battery data
│   └── robot_task_data.json           # Robot task and cleaning data
│
├── mocks/                          # Mock services for testing
│   ├── mock_apis.py               # Mock API responses
│   ├── mock_notifications.py     # Mock notification service
│   └── mock_rds.py               # Mock database operations
│
├── utils/                          # Test utilities and helpers
│   └── test_helpers.py           # Data loading and validation utilities
│
├── run_tests.py                   # Main test runner
├── test_database_config.yaml     # Test database configuration
└── conftest.py                   # Pytest configuration
```

## 🚀 Quick Start

### Prerequisites
- Navigate to the test directory: `cd src/pudu/test`
- Ensure Python path is correctly set (automatically handled by test files)

### Run All Tests
```bash
# Run complete test suite (unit + integration)
python run_tests.py
```

### Run Specific Test Categories

#### Unit Tests Only
```bash
# Run all unit tests
python run_tests.py --unit-only

# Or run individual unit test files
python unit/test_change_detection.py
python unit/test_data_processing.py
python unit/test_data_validation.py
python unit/test_notifications.py
```

#### Integration Tests Only
```bash
# Run all integration tests
python run_tests.py --integration-only

# Or run integration test file directly
python integration/test_pipeline.py
```

### Run Specific Test File
```bash
# Run a specific test file through the runner
python run_tests.py --test-file unit/test_change_detection.py
python run_tests.py --test-file integration/test_pipeline.py
```

## 🧪 What Each Test Validates

### Unit Tests

#### `test_change_detection.py`
- ✅ Decimal value normalization (battery levels, areas, efficiency)
- ✅ Value equivalence checking (case-insensitive strings, numeric precision)
- ✅ New record detection vs. updates
- ✅ Change field identification
- ✅ Real-world data comparison scenarios

#### `test_data_processing.py`
- ✅ DataFrame column formatting (spaces → underscores, lowercase)
- ✅ Column removal functionality
- ✅ Data type preservation during processing
- ✅ Empty DataFrame handling
- ✅ Database preparation workflows

#### `test_data_validation.py`
- ✅ Field precision handling for monetary/measurement values
- ✅ Robot data structure validation
- ✅ Edge case data handling (nulls, empty strings, invalid types)
- ✅ Schema compliance checking

#### `test_notifications.py`
- ✅ Battery level → severity mapping (fatal/error/warning thresholds)
- ✅ Task status → notification content generation
- ✅ Notification skipping logic (high battery, charging updates)
- ✅ Message content validation with real robot data

### Integration Tests

#### `test_pipeline.py`
- ✅ **Complete data flows**: JSON → DataFrame → Database → Notifications
- ✅ **Robot status pipeline**: Battery changes, online/offline notifications
- ✅ **Task completion pipeline**: Status updates, progress tracking
- ✅ **Charging session pipeline**: Power level monitoring, notification skipping
- ✅ **Event processing pipeline**: Error/warning severity mapping
- ✅ **Location data pipeline**: Building data processing
- ✅ **Mixed data scenarios**: Multiple data types processed together

## 📊 Test Data

All tests use realistic data from JSON files in `test_data/`:

- **Robot Status**: Online/offline robots, various battery levels, edge cases
- **Robot Tasks**: Completed/in-progress tasks, different cleaning modes
- **Charging Sessions**: Various power gains, charging durations
- **Robot Events**: Errors, warnings, fatal events with different severities
- **Locations**: Valid buildings and edge cases
- **Comprehensive**: Combined scenarios and test configurations

## 🎯 Example Output

### Successful Test Run
```
================================================================================
🚀 PUDU ROBOT DATA PIPELINE TEST SUITE
================================================================================
📂 Test directory: /path/to/src/pudu/test
📁 Source path: /path/to/src
================================================================================

🧪 RUNNING REAL UNIT TESTS
============================================================
✅ unit/test_data_processing.py - PASSED
✅ unit/test_change_detection.py - PASSED
✅ unit/test_notifications.py - PASSED
✅ unit/test_data_validation.py - PASSED

🔗 RUNNING INTEGRATION TESTS
============================================================
✅ integration/test_pipeline.py - PASSED

================================================================================
📊 FINAL TEST SUMMARY
================================================================================
⏱️  Total execution time: 12.34 seconds
✅ Passed: 5
❌ Failed: 0
📊 Success rate: 100.0%

🎉 ALL TESTS PASSED!
✅ The Pudu pipeline is ready for deployment
================================================================================
```

### Individual Test Output
```bash
$ python unit/test_change_detection.py

============================================================
🧪 TESTING REAL CHANGE DETECTION LOGIC
============================================================
✅ test_decimal_normalization_real_scenarios - PASSED
✅ test_values_equivalence_edge_cases - PASSED
✅ test_record_normalization_with_mixed_data - PASSED
✅ test_change_detection_with_real_scenario - PASSED

📊 Real Change Detection Tests: 4 passed, 0 failed
```

## 🔧 Command Options

The test runner supports several options:

```bash
# Basic usage
python run_tests.py                    # Run all tests
python run_tests.py --unit-only        # Unit tests only
python run_tests.py --integration-only # Integration tests only
python run_tests.py --verbose          # Detailed output

# Run specific test file
python run_tests.py --test-file unit/test_change_detection.py
```

## 📝 Test Development Guidelines

### Adding New Tests
1. **Unit Tests**: Add to appropriate file in `unit/` directory
2. **Integration Tests**: Add to `integration/test_pipeline.py`
3. **Test Data**: Add realistic scenarios to JSON files in `test_data/`

### Test Naming Convention
- Test files: `test_*.py`
- Test functions: `test_*_scenario_description()`
- Test classes: `TestComponentName`

### What Makes a Good Test
- ✅ Tests real business logic, not mocks
- ✅ Uses realistic data from JSON files
- ✅ Validates actual requirements
- ✅ Can catch real bugs
- ✅ Has clear, descriptive names

## 🚨 Troubleshooting

### Common Issues

#### Import Errors
If you see `ModuleNotFoundError: No module named 'pudu'`:
- Ensure you're running from the `src/pudu/test/` directory
- The test files automatically add the correct Python path

#### Test Data Issues
If tests can't find JSON data files:
- Verify you're in the correct directory: `src/pudu/test/`
- Check that `test_data/*.json` files exist and are valid JSON

#### Mock Service Errors
If mock services fail:
- Tests use in-memory mocks, no external dependencies required
- Check that mock files in `mocks/` directory are present

### Getting Help
- Check test output for specific error messages
- Run individual test files to isolate issues
- Use `--verbose` flag for detailed output

## ✅ Success Criteria

The test suite validates that:
- **Data Processing**: Correctly transforms API data for database storage
- **Change Detection**: Accurately identifies what data has changed
- **Notifications**: Sends appropriate alerts based on business rules
- **Integration**: Complete pipelines work end-to-end with real data
- **Error Handling**: System gracefully handles edge cases and invalid data

Running these tests regularly ensures the Pudu robot data pipeline maintains high quality and reliability! 🎯