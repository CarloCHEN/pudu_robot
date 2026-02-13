# terraform/us-east-2.tfvars

aws_region     = "us-east-2"
aws_account_id = "908027373537"

# ECR Repository
ecr_repository_name = "robot-webhook"
image_tag          = "latest"

# ECS Task Configuration
task_cpu       = "512"
task_memory    = "1024"
desired_count  = 1

# Region-specific notification API host
notification_api_host = "alb-notice-1223048054.us-east-2.elb.amazonaws.com"

# Brand-specific callback codes for us-east-2
pudu_callback_code = "1vQ6MfUxqyoGMRQ9nK8C4pSkg1Qsa3Vpq"
gas_callback_code  = ""  # Not available for us-east-2 yet - empty string will be used

# HTTPS Configuration - subdomain of webhook-east1.com (uses existing zone)
domain_name              = "east2.webhook-east1.com"
route53_zone_id          = "Z10056663J1NAES793Y4U"  # Same zone as webhook-east1.com
create_hosted_zone       = false
domain_record_name       = "east2"  # Creates east2.webhook-east1.com in the zone
skip_cert_validation_wait = false    # Zone exists, cert validates immediately

# Optional: Use existing ACM cert instead of creating one
# certificate_arn = "arn:aws:acm:us-east-2:908027373537:certificate/xxxx"