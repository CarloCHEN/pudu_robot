# Robot Management Reporting System

A comprehensive reporting framework for the Robot Management System that provides scheduled and on-demand report generation with multi-tenant support.

## Architecture Overview

```
├── core/
│   ├── report_generator.py    # Main report generation logic
│   ├── report_scheduler.py    # EventBridge scheduling management
│   └── report_config.py       # Report configuration handling
├── templates/
│   └── robot_performance_template.py  # HTML report template
├── services/
│   └── report_delivery_service.py     # Email/S3 delivery service
├── lambda/
│   └── report_generator_lambda.py     # Lambda function for report processing
├── api/
│   └── reporting_api.py               # REST API endpoints
└── database/
    └── schema.sql                     # Database schema
```

## Key Features

- **Multi-tenant Architecture**: Single Lambda processes all customers via EventBridge rules
- **Flexible Scheduling**: Daily, weekly, monthly, or immediate report generation
- **Multiple Delivery Methods**: In-app storage and email delivery
- **Configurable Detail Levels**: Summary, detailed, or comprehensive reports
- **Content Categories**: Robot status, cleaning tasks, charging, performance, cost analysis
- **Reuses Existing Infrastructure**: Leverages current database and API architecture

## Components

### 1. Report Configuration (`report_config.py`)
Parses HTML form data into structured configuration:
- Service and content category selection
- Hardware filtering (location, specific robots)
- Time range and custom date ranges
- Detail level and delivery preferences
- Schedule frequency and email recipients

### 2. Report Generator (`report_generator.py`)
Core report generation logic:
- Reuses existing `App` infrastructure for data fetching
- Dynamic robot resolution based on project configuration
- Parallel API data fetching for performance
- Modular content generation based on selected categories

### 3. Report Scheduler (`report_scheduler.py`)
Manages scheduled reports:
- Creates/updates EventBridge rules per customer
- Stores schedule configuration in database
- Handles rule cleanup and updates
- Calculates next run times

### 4. Report Templates (`robot_performance_template.py`)
HTML template generation:
- Responsive design with Chart.js integration
- Variable content injection based on configuration
- Interactive charts for data visualization
- Support for different detail levels

### 5. Delivery Service (`report_delivery_service.py`)
Report delivery and storage:
- S3 storage for all reports (backup/history)
- SES email delivery with HTML formatting
- Report history and access management
- Customer-specific storage organization

### 6. Lambda Function (`report_generator_lambda.py`)
Serverless report processing:
- Triggered by EventBridge rules or direct API calls
- Processes customer-specific report requests
- Handles errors and cleanup
- Returns detailed execution results

### 7. REST API (`reporting_api.py`)
Flask-based API endpoints:
- `POST /api/reports/generate` - Immediate report generation
- `POST /api/reports/schedule` - Create/update scheduled reports
- `GET /api/reports/schedules/<database_name>` - Get customer schedules
- `DELETE /api/reports/schedules/<schedule_id>` - Cancel schedule
- `GET /api/reports/history/<database_name>` - Get report history

## Database Schema

### Main Tables
- `mnt_report_schedules` - Scheduled report configurations
- `mnt_report_execution_history` - Report generation history
- `mnt_report_deliveries` - Delivery tracking
- `mnt_customer_report_preferences` - Customer preferences
- `mnt_report_access_logs` - Access audit logs

### Views
- `vw_active_report_schedules` - Active schedule summary
- `vw_customer_report_summary` - Customer report statistics
- `vw_recent_report_activity` - Recent activity overview

## Usage Examples

### Generate Immediate Report
```python
from pudu.reporting.core.report_generator import ReportGenerator
from pudu.reporting.core.report_config import ReportConfig

# Form data from HTML interface
form_data = {
    'service': 'robot-management',
    'contentCategories': ['robot-status', 'cleaning-tasks'],
    'timeRange': 'last-30-days',
    'detailLevel': 'detailed',
    'delivery': 'email',
    'schedule': 'immediate',
    'emailRecipients': ['user@example.com']
}

config = ReportConfig(form_data, 'customer-123')
generator = ReportGenerator()
result = generator.generate_report(config)
```

### Create Scheduled Report
```python
from pudu.reporting.core.report_scheduler import ReportScheduler

scheduler = ReportScheduler()
schedule_result = scheduler.create_or_update_schedule('customer-123', config)
```

### API Usage
```bash
# Generate immediate report
curl -X POST http://api.example.com/api/reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "database_name": "customer-123",
    "form_data": {
      "service": "robot-management",
      "contentCategories": ["robot-status"],
      "timeRange": "last-7-days",
      "detailLevel": "summary",
      "delivery": "in-app",
      "schedule": "immediate"
    }
  }'

# Create weekly scheduled report
curl -X POST http://api.example.com/api/reports/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "database_name": "customer-123",
    "form_data": {
      "service": "robot-management",
      "contentCategories": ["robot-status", "cleaning-tasks"],
      "timeRange": "last-30-days",
      "detailLevel": "detailed",
      "delivery": "email",
      "schedule": "weekly",
      "emailRecipients": ["manager@company.com"]
    }
  }'
```

## Configuration

### Database Configuration
Uses existing `database_config.yaml` for database connections and robot resolution.

### Environment Variables
```bash
# AWS Configuration
AWS_REGION=us-east-2
REPORTS_S3_BUCKET=robot-reports-us-east-2

# Email Configuration
SES_FROM_EMAIL=reports@robotmanagement.com

# Lambda Configuration
REPORT_GENERATOR_LAMBDA_ARN=arn:aws:lambda:us-east-2:account:function:report-generator
```

## Deployment

### Prerequisites
1. Existing robot management infrastructure
2. AWS EventBridge, Lambda, S3, and SES configured
3. Database schema deployed
4. Lambda function deployed with appropriate IAM permissions

### Lambda Permissions Required
- EventBridge: Create/update/delete rules and targets
- S3: Read/write access to reports bucket
- SES: Send email permissions
- RDS: Database access via existing credentials
- Logs: CloudWatch logging

### API Deployment
```bash
# Run Flask API locally
python -m pudu.reporting.api.reporting_api --port 5000

# Deploy with WSGI server
gunicorn "pudu.reporting.api.reporting_api:create_app()" --bind 0.0.0.0:5000
```

## Monitoring and Troubleshooting

### Key Metrics
- Report generation success rate
- Average execution time
- Delivery success rate
- Schedule adherence
- Customer adoption rates

### Common Issues
1. **Report generation failures**: Check robot database mappings and API connectivity
2. **Schedule not triggering**: Verify EventBridge rule configuration and Lambda permissions
3. **Email delivery issues**: Check SES configuration and recipient verification
4. **Performance issues**: Monitor database connection pooling and API response times

### Logging
All components use structured logging with correlation IDs for tracking requests across services.

## Extending the System

### Adding New Report Types
1. Create new template class extending base template functionality
2. Add report type to configuration enums
3. Update generator logic for new data sources
4. Add template selection to Lambda function

### Adding New Delivery Methods
1. Extend `DeliveryMethod` enum in `report_config.py`
2. Implement delivery logic in `report_delivery_service.py`
3. Update Lambda function to handle new method
4. Add API endpoints if needed

### Custom Content Categories
1. Add category to form data parsing
2. Implement data fetching logic in generator
3. Add template section rendering
4. Update database schema if new tables needed

This reporting system provides a scalable, multi-tenant solution that leverages your existing infrastructure while adding powerful scheduled reporting capabilities.