# Testing Guide - Multi-Robot API System

## What Changed?

The adapters now contain **full data processing logic** and implement the **5 critical DataFrame-returning methods**:
- `get_schedule_table()`
- `get_charging_table()`
- `get_events_table()`
- `get_robot_status_table()`
- `get_ongoing_tasks_table()`

## Testing Methods

### Method 1: Test via foxx_api.py (Recommended)
This is the **simplest** way - just like before, but now cleaner:

```python
from pudu.apis.foxx_api import (
    get_schedule_table,
    get_charging_table,
    get_events_table,
    get_robot_status_table,
    get_ongoing_tasks_table,
    get_robot_status
)

# Test basic robot status (returns dict)
pudu_status = get_robot_status("811135422060216", robot_type="pudu")
print(f"Pudu in task: {pudu_status['is_in_task']}")

gas_status = get_robot_status("GS438-6030-74Q-Q100", robot_type="gas")
print(f"Gas in task: {gas_status['is_in_task']}")

# Test the 5 critical functions (return DataFrames)
start_time = "2025-10-01 00:00:00"
end_time = "2025-10-01 23:59:59"

# Pudu schedule
pudu_schedule = get_schedule_table(start_time, end_time, robot_type="pudu")
print(f"Pudu tasks: {len(pudu_schedule)}")
print(pudu_schedule.head())

# Gas schedule
gas_schedule = get_schedule_table(start_time, end_time, robot_type="gas")
print(f"Gas tasks: {len(gas_schedule)}")
print(gas_schedule.head())

# Test robot status table
pudu_robots = get_robot_status_table(robot_type="pudu")
gas_robots = get_robot_status_table(robot_type="gas")

# Test ongoing tasks
pudu_ongoing = get_ongoing_tasks_table(robot_type="pudu")
gas_ongoing = get_ongoing_tasks_table(robot_type="gas")

# Test charging records
pudu_charging = get_charging_table(start_time, end_time, robot_type="pudu")
gas_charging = get_charging_table(start_time, end_time, robot_type="gas")

# Test events
pudu_events = get_events_table(start_time, end_time, robot_type="pudu")
gas_events = get_events_table(start_time, end_time, robot_type="gas")
```

### Method 2: Test via API Factory (Direct adapter access)
Use this to test **adapter-specific methods** or **basic API calls**:

```python
from pudu.apis.core.api_factory import APIFactory

# Create factory
api_factory = APIFactory()

# Get adapter instances
pudu_adapter = api_factory.create_api("pudu")
gas_adapter = api_factory.create_api("gas")

# Test basic API methods (return dicts/lists - NOT DataFrames)
pudu_details = pudu_adapter.get_robot_details("811135422060216")
print(f"Pudu battery: {pudu_details.get('battery')}%")

gas_details = gas_adapter.get_robot_details("GS438-6030-74Q-Q100")
print(f"Gas battery: {gas_details.get('battery')}%")

# Test the 5 critical methods (return DataFrames)
start_time = "2024-09-01 00:00:00"
end_time = "2024-09-30 23:59:59"

pudu_schedule = pudu_adapter.get_schedule_table(start_time, end_time)
gas_schedule = gas_adapter.get_schedule_table(start_time, end_time)

print(f"Pudu schedule columns: {pudu_schedule.columns.tolist()}")
print(f"Gas schedule columns: {gas_schedule.columns.tolist()}")
# Should be identical!

# Test adapter-specific methods
pudu_stores = pudu_adapter.get_list_stores()
gas_stores = gas_adapter.get_list_stores()
```

### Method 3: Test Gas-Specific Features
Gas adapter has unique methods not available in Pudu:

```python
from pudu.apis.core.api_factory import APIFactory

gas_adapter = APIFactory().create_api("gas")

# Gas-specific features
robots_list = ["GS438-6030-74Q-Q100", "GS442-6130-82R-6000"]
batch_status = gas_adapter.batch_get_robot_statuses(robots_list)

# Generate task report PNG
report_png = gas_adapter.generate_robot_task_report_png(
    "GS438-6030-74Q-Q100",
    "task_report_id_here"
)

# Get map download URI
map_uri = gas_adapter.get_map_download_uri(
    "GS438-6030-74Q-Q100",
    "map_id_here"
)
```

## Key Differences from Before

### Before:
- `get_robot_details()` returned dict ✅ (still does)
- `get_schedule_table()` was only in `foxx_api.py` ❌

### Now:
- `get_robot_details()` returns dict ✅ (in adapter)
- **`get_schedule_table()` exists in BOTH:**
  - `adapter.get_schedule_table()` - returns DataFrame
  - `foxx_api.get_schedule_table(robot_type="pudu")` - routes to adapter

## Complete Test Script

```python
# test_multi_robot.py
from pudu.apis.foxx_api import (
    get_schedule_table,
    get_charging_table,
    get_events_table,
    get_robot_status_table,
    get_ongoing_tasks_table
)

def test_all_functions():
    start_time = "2024-09-01 00:00:00"
    end_time = "2024-09-30 23:59:59"

    print("=" * 60)
    print("Testing Pudu Robot")
    print("=" * 60)

    # Test all 5 functions for Pudu
    pudu_schedule = get_schedule_table(start_time, end_time, robot_type="pudu")
    pudu_charging = get_charging_table(start_time, end_time, robot_type="pudu")
    pudu_events = get_events_table(start_time, end_time, robot_type="pudu")
    pudu_status = get_robot_status_table(robot_type="pudu")
    pudu_ongoing = get_ongoing_tasks_table(robot_type="pudu")

    print(f"Schedule: {len(pudu_schedule)} rows")
    print(f"Charging: {len(pudu_charging)} rows")
    print(f"Events: {len(pudu_events)} rows")
    print(f"Robot Status: {len(pudu_status)} rows")
    print(f"Ongoing Tasks: {len(pudu_ongoing)} rows")

    print("\n" + "=" * 60)
    print("Testing Gas Robot")
    print("=" * 60)

    # Test all 5 functions for Gas
    gas_schedule = get_schedule_table(start_time, end_time, robot_type="gas")
    gas_charging = get_charging_table(start_time, end_time, robot_type="gas")
    gas_events = get_events_table(start_time, end_time, robot_type="gas")
    gas_status = get_robot_status_table(robot_type="gas")
    gas_ongoing = get_ongoing_tasks_table(robot_type="gas")

    print(f"Schedule: {len(gas_schedule)} rows")
    print(f"Charging: {len(gas_charging)} rows")
    print(f"Events: {len(gas_events)} rows")
    print(f"Robot Status: {len(gas_status)} rows")
    print(f"Ongoing Tasks: {len(gas_ongoing)} rows")

    # Verify column consistency
    print("\n" + "=" * 60)
    print("Verifying Column Consistency")
    print("=" * 60)

    if set(pudu_schedule.columns) == set(gas_schedule.columns):
        print("✓ Schedule columns match!")
    else:
        print("✗ Schedule columns differ!")
        print(f"  Pudu: {pudu_schedule.columns.tolist()}")
        print(f"  Gas: {gas_schedule.columns.tolist()}")

    if set(pudu_status.columns) == set(gas_status.columns):
        print("✓ Robot status columns match!")
    else:
        print("✗ Robot status columns differ!")

if __name__ == "__main__":
    test_all_functions()
```

## Expected Results

✅ **All 5 functions return DataFrames with identical columns** for both robot types
✅ **Pudu returns data** (if you have Pudu robots with data in the time range)
✅ **Gas returns data** for schedule/status (charging/events return empty - Gas API doesn't have these)
✅ **No errors** - everything runs smoothly

## Troubleshooting

### "API pudu 不可用" or "API gas 不可用"
- Check that adapter files are in `src/pudu/apis/adapters/`
- Check that `api_registry.py` was updated
- Run: `python -c "from pudu.apis.core.api_factory import APIFactory; print(APIFactory().get_available_apis())"`

### "'NoneType' object has no attribute 'get_schedule_table'"
- The adapter wasn't created properly
- Check OAuth token for Gas API
- Check that adapter has the method implemented

### Columns don't match between Pudu and Gas
- Check the adapter implementations
- Both should return the exact same column names