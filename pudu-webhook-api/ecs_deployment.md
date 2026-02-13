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
Load Balancer: https://webhook-east2.yourdomain.com   # with HTTPS configured
# or
Load Balancer: http://foxx-monitor-webhook-api-alb-xxxxx.elb.amazonaws.com   # HTTP only
```

### 4. Enable HTTPS (Required for production)
Endpoints: `https://webhook-east1.com/api/webhook` (us-east-1), `https://webhook-east2.com/api/webhook` (us-east-2)

**us-east-1:** Uses existing zone in `terraform/us-east-1.tfvars`.

**us-east-2:** Two-phase deploy (required because webhook-east2.com must point to Route53 first):

**Phase 1 – Deploy and get nameservers:**
```hcl
# terraform/us-east-2.tfvars
domain_name               = "webhook-east2.com"
create_hosted_zone        = true
skip_cert_validation_wait = true   # Don't wait for cert (DNS not set yet)
```
Run `make deploy-us-east-2`. Deploy succeeds with HTTP only. **Save the Route53 nameservers** from the output.

**Phase 2 – Point domain to Route53:**
1. In your domain registrar (where you bought webhook-east2.com), set the domain’s nameservers to the Route53 nameservers from Phase 1.
2. Wait 5–30 minutes for DNS propagation.
3. Set `skip_cert_validation_wait = false` in `terraform/us-east-2.tfvars`.
4. Run `make deploy-us-east-2` again. Cert validates and HTTPS is enabled.

## API Endpoints

### Primary Endpoint (Recommended)
```
POST https://<your-domain>/api/webhook   # or http:// when HTTPS not configured
```
Automatically detects if request is from Pudu or Gas robot.

### Legacy Endpoints (Backward Compatibility)
```
POST https://<your-domain>/api/pudu/webhook
POST https://<your-domain>/api/gas/webhook
```

### Health Check
```
GET https://<your-domain>/api/webhook/health
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

## HTTPS Setup Details

| Variable | Purpose |
|----------|---------|
| `domain_name` | Domain for your API (e.g., `webhook-east2.yourdomain.com`) |
| `route53_zone_id` | Route53 hosted zone ID for DNS validation + A record |
| `certificate_arn` | Optional: use existing ACM cert instead of creating one |

**Get your Route53 zone ID:**
```bash
aws route53 list-hosted-zones --query 'HostedZones[*].[Name,Id]' --output table
```

## Troubleshooting

### ACM cert validation timeout (1h15m)
**Cause:** webhook-east2.com is not pointing to Route53 nameservers at your domain registrar.

**Fix:**
1. Set `skip_cert_validation_wait = true` in `terraform/us-east-2.tfvars`.
2. Run `make deploy-us-east-2` – deploy will succeed with HTTP only.
3. Update your registrar to use the Route53 nameservers from the output.
4. After DNS propagates (5–30 min), set `skip_cert_validation_wait = false` and redeploy.

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

```bash
cd terraform

# Back up current state (it's your us-east-1 state)
cp terraform.tfstate terraform-us-east-1.tfstate
cp terraform.tfstate.backup terraform-us-east-1.tfstate.backup

# Remove the state so us-east-2 starts fresh
rm terraform.tfstate terraform.tfstate.backup

# Now deploy us-east-2
cd ..
make deploy-us-east-2
```