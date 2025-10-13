# terraform/us-east-1.tfvars

aws_region     = "us-east-1"
aws_account_id = "908027373537"

# ECR Repository
ecr_repository_name = "robot-webhook"
image_tag          = "latest"

# ECS Task Configuration
task_cpu       = "512"
task_memory    = "1024"
desired_count  = 1

# Region-specific notification API host
notification_api_host = "alb-streamnexus-demo-775802511.us-east-1.elb.amazonaws.com"

# Brand-specific callback codes for us-east-1
pudu_callback_code = "vFpG5Ga9o8NqdymFLicLfJVfqj6JU50qQYCs"
gas_callback_code  = "378c0111-5d5d-4bdc-9cc5-e3d7bd3494d3"

# HTTPS Configuration (optional)
domain_name      = "webhook-east1.com"  # Change to your domain
route53_zone_id  = "Z10056663J1NAES793Y4U"           # Your Route53 zone ID