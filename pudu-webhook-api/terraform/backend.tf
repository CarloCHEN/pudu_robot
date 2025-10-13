# terraform/backend.tf

# S3 backend for state storage (recommended for production)
# Uncomment and configure if you want to use S3 backend
# Otherwise, Terraform will use local state file

# terraform {
#   backend "s3" {
#     bucket         = "your-terraform-state-bucket"
#     key            = "webhook-api/${var.aws_region}/terraform.tfstate"
#     region         = "us-east-1"
#     encrypt        = true
#     dynamodb_table = "terraform-state-lock"
#   }
# }

# For now, using local backend (default)
# State will be stored in terraform.tfstate file locally