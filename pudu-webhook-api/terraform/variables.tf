# terraform/variables.tf

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
}

variable "aws_account_id" {
  description = "AWS account ID"
  type        = string
}

variable "ecr_repository_name" {
  description = "Name of the ECR repository"
  type        = string
  default     = "robot-webhook"
}

variable "image_tag" {
  description = "Docker image tag to deploy"
  type        = string
  default     = "latest"
}

variable "task_cpu" {
  description = "Fargate task CPU units (256, 512, 1024, 2048, 4096)"
  type        = string
  default     = "512"
}

variable "task_memory" {
  description = "Fargate task memory in MB (512, 1024, 2048, etc.)"
  type        = string
  default     = "1024"
}

variable "desired_count" {
  description = "Desired number of ECS tasks to run"
  type        = number
  default     = 1
}

# Region-specific notification API host
variable "notification_api_host" {
  description = "Notification API host (region-specific)"
  type        = string
}

# Brand-specific callback codes
variable "pudu_callback_code" {
  description = "Pudu callback code for verification (region-specific)"
  type        = string
  default     = ""
}

variable "gas_callback_code" {
  description = "Gas callback code for verification (region-specific)"
  type        = string
  default     = ""
}

variable "domain_name" {
  description = "Domain name for HTTPS certificate (e.g., webhook.yourdomain.com)"
  type        = string
  default     = ""
}

variable "route53_zone_id" {
  description = "Route53 hosted zone ID (leave empty if create_hosted_zone=true)"
  type        = string
  default     = ""
}

variable "domain_record_name" {
  description = "Route53 record name in the zone (empty for apex, e.g. 'east2' for east2.webhook-east1.com)"
  type        = string
  default     = ""
}

variable "create_hosted_zone" {
  description = "Create Route53 hosted zone for domain_name (use when domain has no zone yet, e.g. webhook-east2.com)"
  type        = bool
  default     = false
}

variable "skip_cert_validation_wait" {
  description = "Skip waiting for ACM cert validation (use for first deploy - get nameservers, update registrar, then set to false)"
  type        = bool
  default     = false
}

variable "certificate_arn" {
  description = "Optional: ARN of existing ACM certificate for HTTPS. If set, skips cert creation. Must be in same region."
  type        = string
  default     = ""
}