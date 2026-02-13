# terraform/outputs.tf

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "alb_url" {
  description = "Full URL of the Application Load Balancer"
  value       = var.domain_name != "" ? "https://${var.domain_name}" : "http://${aws_lb.main.dns_name}"
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.app.name
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.app.name
}

output "webhook_endpoints" {
  description = "Available webhook endpoints"
  value = {
    pudu_webhook = var.domain_name != "" ? "https://${var.domain_name}/api/pudu/webhook" : "http://${aws_lb.main.dns_name}/api/pudu/webhook"
    gas_webhook  = var.domain_name != "" ? "https://${var.domain_name}/api/gas/webhook" : "http://${aws_lb.main.dns_name}/api/gas/webhook"
    health_check = var.domain_name != "" ? "https://${var.domain_name}/api/webhook/health" : "http://${aws_lb.main.dns_name}/api/webhook/health"
  }
}

output "route53_nameservers" {
  description = "Route53 nameservers - update your domain registrar to use these for webhook-east2.com"
  value       = var.create_hosted_zone ? aws_route53_zone.app[0].name_servers : []
}

output "certificate_validation_records" {
  description = "DNS records needed for certificate validation (only when creating new cert)"
  value       = local.create_cert ? [for dvo in aws_acm_certificate.app[0].domain_validation_options : {
    name  = dvo.resource_record_name
    type  = dvo.resource_record_type
    value = dvo.resource_record_value
  }] : []
}

output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = "${var.aws_account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/${var.ecr_repository_name}"
}

output "region" {
  description = "AWS region deployed to"
  value       = var.aws_region
}