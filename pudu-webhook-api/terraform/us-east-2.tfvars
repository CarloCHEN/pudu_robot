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

# HTTPS Configuration (optional)
domain_name      = ""            # Change to your domain
route53_zone_id  = ""           # Your Route53 zone ID