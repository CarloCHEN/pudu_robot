# How to use this Repo
## Warning
- Always make sure to destroy your API Service. Forgetting to do so could incur a large AWS fee
- Never commit your AWS Account ID to git. Save it in an `.env` file and ensure `.env` is added to your `.gitiginore`

## Setup, Deploy, and Destroy

### Setup Env Variables
Add an `.env` file containing your AWS account ID and region. Example file:
```
AWS_ACCOUNT_ID=1234567890
AWS_REGION=ap-southeast-1
```

Create a `backend.tf` file and add it to both `/infra/setup/backend.tf` and `/infra/app/backend.tf`. Example files:
```
terraform {
  backend "s3" {
    region = "<AWS_REGION>"
    bucket = "<BUCKET_NAME>"
    key    = "<APP_NAME>/terraform.tfstate"
  }
}
```
```
terraform {
  backend "s3" {
    region = "<AWS_REGION>"
    bucket = "<BUCKET_NAME>"
    key    = "<APP_NAME>/terraform.tfstate"
  }
}
```
Alternatively you can skip this step to store your Terraform state locally.

<br>

### Setup, Deploy, and Destroy Infrastructure/App
Build and deploy your container
    ```
    make deploy-container
    ```

### Local API Tests
1. To test the API, move the `app.py` file to `src` directory
2. Run `uvicorn api:app --reload --host 127.0.0.1 --port 8000`

3. Use the following API call
curl -X POST "http://127.0.0.1:8000/robots/" \
  -H "Content-Type: application/json" \
  -d '{
    "start_time": "2024-09-10 00:00:00",
    "end_time": "2024-09-19 23:59:59",
    "location_id": null,
    "robot_sn": null,
    "timezone_offset": -8
  }'

  curl -X POST "http://127.0.0.1:8000/schedule/" \
  -H "Content-Type: application/json" \
  -d '{
    "start_time": "2024-09-10 00:00:00",
    "end_time": "2024-09-19 23:59:59",
    "location_id": null,
    "robot_sn": null,
    "timezone_offset": -8
  }'

  curl -X POST "http://127.0.0.1:8000/charging/" \
  -H "Content-Type: application/json" \
  -d '{
    "start_time": "2024-09-10 00:00:00",
    "end_time": "2024-09-19 23:59:59",
    "location_id": null,
    "robot_sn": null,
    "timezone_offset": -8
  }'

  curl -X POST "http://127.0.0.1:8000/task-overview/" \
  -H "Content-Type: application/json" \
  -d '{
    "start_time": "2024-09-10 00:00:00",
    "end_time": "2024-09-19 23:59:59",
    "location_id": null,
    "robot_sn": null,
    "timezone_offset": -8,
    "groupby": "hour"
  }'