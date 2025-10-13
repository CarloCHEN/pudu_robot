# Multi-Brand Robot Webhook API

Unified webhook API that handles callbacks from Pudu and Gas robots with automatic brand detection.

## Features

- ✅ **Auto-detects brand** from incoming data structure
- ✅ **Single endpoint** handles both Pudu and Gas robots
- ✅ **Multi-region support** (us-east-1, us-east-2)
- ✅ **Fixed ALB URL** - doesn't change on redeployments
- ✅ **Dynamic database routing** with change detection
- ✅ **Graceful handling** of missing callback codes

## Quick Start

### 1. Deploy to us-east-1
```bash
cd pudu-webhook-api
make deploy-us-east-1
```

### 2. Deploy to us-east-2
```bash
cd pudu-webhook-api
make deploy-us-east-2
```

### 3. Save the ALB URL
After deployment completes, save the ALB URL from the output:
```
Load Balancer: http://foxx-monitor-webhook-api-alb-us-east-1-xxxxx.elb.amazonaws.com
```

## API Endpoints

### Primary Endpoint (Recommended)
```
POST http://<alb-url>/api/webhook
```
Automatically detects if request is from Pudu or Gas robot.

### Legacy Endpoints (Backward Compatibility)
```
POST http://<alb-url>/api/pudu/webhook
POST http://<alb-url>/api/gas/webhook
```

### Health Check
```
GET http://<alb-url>/api/webhook/health
```

## Architecture

```
Internet → ALB (Fixed URL) → ECS Fargate Task → RDS
                                ↓
                          CloudWatch Logs
```

## Environment Variables

Configured per region in `terraform/<region>.tfvars`:

| Variable | us-east-1 | us-east-2 |
|----------|-----------|-----------|
| `pudu_callback_code` | ✅ Configured | ✅ Configured |
| `gas_callback_code` | ✅ Configured | ⚠️ Empty (allowed) |
| `notification_api_host` | Region-specific | Region-specific |

## Updating Environment Variables

1. Edit the appropriate file:
   ```bash
   vim terraform/us-east-1.tfvars  # or us-east-2.tfvars
   ```

2. Update the values:
   ```hcl
   gas_callback_code = "new-callback-code-here"
   ```

3. Redeploy:
   ```bash
   make deploy
   ```

## Brand Detection Logic

The API automatically detects the brand using:

**Gas Detection:**
- Has `messageTypeId` + `appId` fields
- Has `payload.serialNumber` structure

**Pudu Detection:**
- Has `callback_type` field
- Has `sn` field

**Fallback:** Defaults to Pudu if uncertain

## Common Commands

```bash
# View current configuration
make print-vars

# Test locally (without deploying)
make test-local

# View deployment information
make show-deployment

# View logs (after deployment)
aws logs tail /ecs/foxx-monitor-webhook-api-us-east-1 --follow

# Destroy infrastructure (be careful!)
make terraform-destroy
```

## Directory Structure

```
pudu-webhook-api/
├── terraform/              # Infrastructure as Code
│   ├── main.tf            # ECS + ALB configuration
│   ├── variables.tf       # Variable definitions
│   ├── outputs.tf         # Deployment outputs
│   ├── us-east-1.tfvars   # us-east-1 config
│   └── us-east-2.tfvars   # us-east-2 config
├── configs/               # Brand configurations
│   ├── pudu/config.yaml
│   └── gas/config.yaml
├── deploy.sh              # Full deployment script
├── setup-environment.sh   # Environment setup
├── Makefile              # Convenience commands
└── main.py               # Flask application
```

## Troubleshooting

### Deployment fails
```bash
# Check AWS credentials
aws sts get-caller-identity

# Verify Terraform files exist
make verify-config

# Check logs
aws logs tail /ecs/foxx-monitor-webhook-api-<region> --follow
```

### Callback verification fails
- Check callback codes in `terraform/<region>.tfvars`
- Empty callback codes are allowed (verification skipped)
- Check logs for verification details

### Can't access ALB URL
- Security groups allow port 80/443
- Check ECS service is running
- Wait 2-3 minutes for health checks

## Cost Estimate

**Per Region:**
- ECS Fargate (512 CPU, 1GB RAM): ~$15/month
- ALB: ~$16/month
- CloudWatch Logs: ~$1/month
- **Total: ~$32/month per region**

## Support

Check health status:
```bash
curl http://<alb-url>/api/webhook/health | jq
```

## Common Issues

For error:
```bash
╷
│ Error: Failed to load plugin schemas
│
│ Error while loading schemas for plugin components: Failed to obtain provider schema: Could not load the schema for provider registry.terraform.io/hashicorp/aws: failed to instantiate provider
│ "registry.terraform.io/hashicorp/aws" to obtain schema: timeout while waiting for plugin to start..
╵
❌ Terraform plan failed!
```

```bash
cd terraform
rm -rf .terraform .terraform.lock.hcl
GODEBUG=netdns=go terraform init
cd ..
make deploy
```