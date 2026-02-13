# Include .env file if it exists, otherwise use defaults
-include .env

.EXPORT_ALL_VARIABLES:

TAG=latest
REGISTRY_NAME=robot-webhook

print-vars:
	@if [ ! -f ".env" ]; then \
		echo "❌ .env file missing. Run 'make setup-<region>' first"; \
		exit 1; \
	fi
	@echo "🔍 Current Configuration:"
	@export $(grep -v '^#' .env | xargs) && \
	echo "AWS_REGION=$$AWS_REGION" && \
	echo "AWS_ACCOUNT_ID=$$AWS_ACCOUNT_ID" && \
	echo "REGISTRY_NAME=${REGISTRY_NAME}" && \
	echo "TAG=${TAG}" && \
	echo "NOTIFICATION_API_HOST=$$NOTIFICATION_API_HOST" && \
	echo "PUDU_CALLBACK_CODE=$$PUDU_CALLBACK_CODE" && \
	echo "GAS_CALLBACK_CODE=$$GAS_CALLBACK_CODE"

# Setup commands for different regions
setup-us-east-1: clean-config
	@echo "🚀 Setting up Webhook API for us-east-1..."
	./setup-environment.sh us-east-1

setup-us-east-2: clean-config
	@echo "🚀 Setting up Webhook API for us-east-2..."
	./setup-environment.sh us-east-2

verify-config:
	@echo "🔍 Verifying current configuration..."
	@if [ -f ".env" ]; then \
		echo "✅ .env exists"; \
		echo "AWS Region: $(shell grep '^AWS_REGION=' .env | cut -d'=' -f2)"; \
		echo "Notification Host: $(shell grep NOTIFICATION_API_HOST .env | cut -d'=' -f2)"; \
	else \
		echo "❌ .env missing - run setup first"; \
	fi
	@if [ -f "notifications/.env" ]; then \
		echo "✅ notifications/.env exists"; \
	else \
		echo "❌ notifications/.env missing - run setup first"; \
	fi
	@if [ -f "rds/credentials.yaml" ]; then \
		echo "✅ credentials.yaml exists"; \
		echo "RDS Host: $(shell grep 'host:' rds/credentials.yaml | cut -d':' -f2-)"; \
	else \
		echo "❌ credentials.yaml missing - run setup first"; \
	fi
	@if [ -d "terraform" ] && [ -f "terraform/main.tf" ]; then \
		echo "✅ Terraform configuration exists"; \
	else \
		echo "❌ Terraform configuration missing"; \
	fi

# Main deployment command
deploy: verify-config
	@if [ ! -f ".env" ]; then \
		echo "❌ .env file missing. Run 'make setup-<region>' first"; \
		exit 1; \
	fi
	@export $(grep -v '^#' .env | xargs) && \
	echo "🚀 Deploying Webhook API to $$AWS_REGION..." && \
	sh deploy.sh

# Convenience commands for specific regions
deploy-us-east-1: setup-us-east-1 deploy

deploy-us-east-2: setup-us-east-2 deploy

# Local testing without Terraform
test-local:
	@if [ ! -f ".env" ]; then \
		echo "❌ .env missing. Run setup first"; \
		exit 1; \
	fi
	@echo "🧪 Starting Webhook API locally..."
	@export $(grep -v '^#' .env | xargs) && \
	python main.py

build-local:
	@echo "🏗️ Building Webhook API image locally..."
	@if [ ! -f ".env" ]; then \
		echo "❌ .env file missing. Run setup first"; \
		exit 1; \
	fi
	@docker build --platform=linux/amd64 -t ${REGISTRY_NAME}:${TAG} -f Dockerfile ..

run-local: build-local
	@echo "🚀 Running Webhook API container locally..."
	@if [ ! -f ".env" ]; then \
		echo "❌ .env missing. Run setup first"; \
		exit 1; \
	fi
	@docker run -p 8000:8000 --env-file .env ${REGISTRY_NAME}:${TAG}

test-api:
	@echo "🧪 Testing Webhook API endpoints..."
	@echo "General health check:" && \
	curl -s http://localhost:8000/api/webhook/health | python -m json.tool && \
	echo "" && \
	echo "Pudu health check:" && \
	curl -s http://localhost:8000/api/pudu/webhook/health | python -m json.tool && \
	echo "" && \
	echo "Gas health check:" && \
	curl -s http://localhost:8000/api/gas/webhook/health | python -m json.tool || \
	echo "❌ API not running. Start with 'make test-local' first."

# Terraform-specific commands
terraform-init:
	@echo "🔧 Initializing Terraform..."
	@cd terraform && terraform init

terraform-plan:
	@if [ ! -f ".env" ]; then \
		echo "❌ .env missing. Run setup first"; \
		exit 1; \
	fi
	@export $(grep -v '^#' .env | xargs) && \
	cd terraform && terraform plan -var-file="$$AWS_REGION.tfvars" -state="terraform-$$AWS_REGION.tfstate"

terraform-apply:
	@if [ ! -f ".env" ]; then \
		echo "❌ .env missing. Run setup first"; \
		exit 1; \
	fi
	@export $(grep -v '^#' .env | xargs) && \
	cd terraform && terraform apply -var-file="$$AWS_REGION.tfvars" -state="terraform-$$AWS_REGION.tfstate"

terraform-destroy:
	@if [ ! -f ".env" ]; then \
		echo "❌ .env missing. Run setup first"; \
		exit 1; \
	fi
	@echo "⚠️  WARNING: This will destroy all infrastructure!" && \
	read -p "Are you sure? (yes/no): " confirm && \
	if [ "$$confirm" = "yes" ]; then \
		export $(grep -v '^#' .env | xargs) && \
		cd terraform && terraform destroy -var-file="$$AWS_REGION.tfvars"; \
	else \
		echo "Cancelled."; \
	fi

terraform-output:
	@cd terraform && terraform output

clean-config:
	@echo "🧹 Cleaning generated configuration files..."
	@rm -f .env
	@rm -f notifications/.env
	@rm -f rds/credentials.yaml
	@echo "✅ Configuration files cleaned"

clean-docker:
	@echo "🧹 Cleaning Docker images..."
	@docker rmi ${REGISTRY_NAME}:${TAG} 2>/dev/null || true
	@docker system prune -f

clean-terraform:
	@echo "🧹 Cleaning Terraform files..."
	@cd terraform && rm -rf .terraform .terraform.lock.hcl terraform.tfstate terraform.tfstate.backup tfplan
	@echo "✅ Terraform cleaned"

install-deps:
	@echo "📦 Installing Python dependencies..."
	@pip install -r requirements.txt

# Show deployment info
show-deployment:
	@if [ -f "deployment-output.json" ]; then \
		echo "🌐 Current Deployment Information:"; \
		cat deployment-output.json | python -m json.tool; \
	else \
		echo "❌ No deployment information found. Deploy first."; \
	fi

help:
	@echo "🚀 Multi-Brand Robot Webhook API - Deployment"
	@echo "=============================================="
	@echo ""
	@echo "🛠️  Setup Commands:"
	@echo "  setup-us-east-1         Setup for us-east-1"
	@echo "  setup-us-east-2         Setup for us-east-2"
	@echo ""
	@echo "🚀 Deployment Commands:"
	@echo "  deploy                  Deploy with current config"
	@echo "  deploy-us-east-1        Setup + deploy to us-east-1"
	@echo "  deploy-us-east-2        Setup + deploy to us-east-2"
	@echo ""
	@echo "🏗️  Local Development:"
	@echo "  build-local             Build Docker image locally"
	@echo "  test-local              Run API with Python locally"
	@echo "  run-local               Run API in Docker locally"
	@echo "  test-api                Test API endpoints locally"
	@echo "  install-deps            Install Python dependencies"
	@echo ""
	@echo "☁️  Terraform Commands:"
	@echo "  terraform-init          Initialize Terraform"
	@echo "  terraform-plan          Preview infrastructure changes"
	@echo "  terraform-apply         Apply infrastructure changes"
	@echo "  terraform-destroy       Destroy all infrastructure"
	@echo "  terraform-output        Show deployment outputs"
	@echo ""
	@echo "🔍 Utility Commands:"
	@echo "  print-vars              Show current configuration"
	@echo "  verify-config           Verify configuration files"
	@echo "  show-deployment         Show current deployment info"
	@echo "  clean-config            Remove generated configs"
	@echo "  clean-docker            Remove Docker images"
	@echo "  clean-terraform         Clean Terraform state/cache"
	@echo ""
	@echo "📝 Example Usage:"
	@echo "  make deploy-us-east-2   # Full deployment to us-east-2"
	@echo "  make deploy-us-east-1   # Full deployment to us-east-1"
	@echo "  make test-local         # Test locally"
	@echo ""
	@echo "📋 Unified API Endpoints (handles both brands):"
	@echo "  POST /api/pudu/webhook  - Pudu callbacks"
	@echo "  POST /api/gas/webhook   - Gas callbacks"
	@echo "  GET  /api/webhook/health - General health"
	@echo ""
	@echo "🔄 To update environment variables:"
	@echo "  1. Edit terraform/<region>.tfvars"
	@echo "  2. Run: make deploy"