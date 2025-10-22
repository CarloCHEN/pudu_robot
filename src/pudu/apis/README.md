# Multi-Customer API Usage

## Quick Setup

1. **Create credentials file:**
```bash
cp src/pudu/apis/configs/credentials.example.yaml src/pudu/apis/configs/credentials.yaml
```

2. **Edit credentials.yaml** - add your customers and credentials

3. **Set environment variable:**
```bash
# .env file
ROBOT_API_CUSTOMERS=customer_a,customer_b,customer_c
```

## Usage Patterns

### Pattern 1: Single Customer (Direct API calls)
```python
from pudu.apis import foxx_api

# Set customer once
foxx_api.set_customer('customer_a')

# Make API calls
schedule = foxx_api.get_schedule_table(
    start_time='2024-01-01 00:00:00',
    end_time='2024-01-31 23:59:59',
    robot_type='pudu'
)
```

### Pattern 2: Multiple Customers (main.py - Automatic)

The `main.py` pipeline automatically:
1. Reads customers from `ROBOT_API_CUSTOMERS` environment variable
2. Determines robot types for each customer from credentials
3. Fetches data for all customers in parallel
4. Combines and processes data
```python
# In main.py - happens automatically
app = App(config_path='database_config.yaml')
app.run(start_time='2024-01-01 00:00:00', end_time='2024-01-31 23:59:59')
```

### Pattern 3: Per-Request Customer Override
```python
from pudu.apis import foxx_api

# Query different customers without switching global state
data_a = foxx_api.get_schedule_table(
    start_time='2024-01-01 00:00:00',
    end_time='2024-01-31 23:59:59',
    robot_type='pudu',
    customer_name='customer_a'
)

data_b = foxx_api.get_schedule_table(
    start_time='2024-01-01 00:00:00',
    end_time='2024-01-31 23:59:59',
    robot_type='gas',
    customer_name='customer_b'
)
```

## Configuration Files

### credentials.yaml Structure
```yaml
customers:
  customer_a:
    pudu:
      enabled: true
      api_app_key: "key_here"
      api_app_secret: "secret_here"
    gas:
      enabled: false

  customer_b:
    pudu:
      enabled: false
    gas:
      enabled: true
      client_id: "id_here"
      client_secret: "secret_here"
      open_access_key: "key_here"
      base_url: "https://openapi.gs-robot.com"
```

### Environment Variables
```bash
# List of customers to process (comma-separated)
ROBOT_API_CUSTOMERS=customer_a,customer_b

# Optional: Custom credentials path
ROBOT_API_CREDENTIALS_PATH=/path/to/credentials.yaml
```

## Troubleshooting

**No customers found:**
```bash
# Check credentials file exists
ls src/pudu/apis/configs/credentials.yaml

# List available customers
python -c "from src.pudu.apis import foxx_api; print(foxx_api.list_customers())"
```

**Wrong credentials:**
```python
# Check current customer
from src.pudu.apis import foxx_api
print(foxx_api.get_current_customer())

# Check enabled APIs
from src.pudu.apis.core.api_factory import APIFactory
print(APIFactory.get_enabled_apis())
```

**Environment variable not working:**
```bash
# Verify environment variable
echo $ROBOT_API_CUSTOMERS

# Or check in Python
python -c "import os; print(os.getenv('ROBOT_API_CUSTOMERS'))"
```

# Multi-Customer Setup Checklist

## 1. Configuration Files
- [ ] Copy `credentials.example.yaml` to `credentials.yaml`
- [ ] Fill in credentials for each customer
- [ ] Set `enabled: true/false` for each robot type per customer
- [ ] Add to `.gitignore`: `credentials.yaml`

## 2. Environment Setup
- [ ] Create `.env` file (or set environment variables)
- [ ] Set `ROBOT_API_CUSTOMERS=customer1,customer2,...`
- [ ] Optionally set `ROBOT_API_CREDENTIALS_PATH` if using custom location

## 3. Testing
- [ ] Run `python test_multi_customer.py` to verify setup
- [ ] Check all customers are detected
- [ ] Verify robot types are correct for each customer
- [ ] Test API instance creation

## 4. Integration
- [ ] Update `main.py` with new multi-customer methods
- [ ] Remove old `_fetch_all_api_data_parallel` method
- [ ] Test full pipeline with `app.run()`

## 5. Verification
- [ ] Check logs show all customers being processed
- [ ] Verify data is fetched for correct robot types per customer
- [ ] Confirm parallel execution is working (check execution time)