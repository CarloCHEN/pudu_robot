# Include .env file if it exists, otherwise use defaults
-include .env

.EXPORT_ALL_VARIABLES:
APP_NAME=foxx_monitor_pudu_webhook_api

TAG=latest
TF_VAR_app_name=${APP_NAME}
REGISTRY_NAME=${APP_NAME}
TF_VAR_image=${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REGISTRY_NAME}:${TAG}
TF_VAR_region=${AWS_REGION}

print-vars:
	@if [ ! -f ".env" ]; then \
		echo "❌ .env file missing. Run 'make setup-us-east-1' or 'make setup-us-east-2' first"; \
		exit 1; \
	fi
	@echo "🔍 Current Configuration:"
	@export $(grep -v '^#' .env | xargs) && \
	echo "APP_NAME=${APP_NAME}" && \
	echo "TAG=${TAG}" && \
	echo "AWS_REGION=$AWS_REGION" && \
	echo "AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID" && \
	echo "TF_VAR_app_name=${APP_NAME}" && \
	echo "REGISTRY_NAME=${APP_NAME}" && \
	echo "TF_VAR_image=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/${APP_NAME}:${TAG}" && \
	echo "TF_VAR_region=$AWS_REGION"

setup-us-east-1: clean-config
	@echo "🚀 Setting up for us-east-1..."
	./setup-environment.sh us-east-1

setup-us-east-2: clean-config
	@echo "🚀 Setting up for us-east-2..."
	./setup-environment.sh us-east-2

verify-config:
	@echo "🔍 Verifying current configuration..."
	@echo "Current AWS Region: ${AWS_REGION}"
	@if [ -f "pudu-webhook-api/.env" ]; then \
		echo "✅ pudu-webhook-api/.env exists"; \
		echo "Notification Host: $(grep NOTIFICATION_API_HOST pudu-webhook-api/.env)"; \
	else \
		echo "❌ pudu-webhook-api/.env missing - run setup first"; \
	fi
	@if [ -f "pudu-webhook-api/notifications/.env" ]; then \
		echo "✅ pudu-webhook-api/notifications/.env exists"; \
		echo "Notifications Host: $(grep NOTIFICATION_API_HOST pudu-webhook-api/notifications/.env)"; \
	else \
		echo "❌ pudu-webhook-api/notifications/.env missing - run setup first"; \
	fi
	@if [ -f "pudu-webhook-api/rds/credentials.yaml" ]; then \
		echo "✅ credentials.yaml exists"; \
		echo "RDS Host: $(grep 'host:' pudu-webhook-api/rds/credentials.yaml)"; \
	else \
		echo "❌ credentials.yaml missing - run setup first"; \
	fi

deploy-container:
	@if [ ! -f ".env" ]; then \
		echo "❌ .env file missing. Run 'make setup-us-east-1' or 'make setup-us-east-2' first"; \
		exit 1; \
	fi
	@echo "🔍 Loading environment variables..."
	@export $(grep -v '^#' .env | xargs) && \
	echo "🚀 Deploying container to $AWS_REGION..." && \
	if [ ! -f "pudu-webhook-api/.env" ] || [ ! -f "pudu-webhook-api/notifications/.env" ] || [ ! -f "pudu-webhook-api/rds/credentials.yaml" ]; then \
		echo "❌ Configuration files missing. Run setup first"; \
		exit 1; \
	fi && \
	sh deploy.sh

deploy-us-east-1: setup-us-east-1 deploy-container

deploy-us-east-2: setup-us-east-2 deploy-container

clean-config:
	@echo "🧹 Cleaning generated configuration files..."
	@rm -f .env
	@rm -f pudu-webhook-api/.env
	@rm -f pudu-webhook-api/notifications/.env
	@rm -f pudu-webhook-api/rds/credentials.yaml
	@echo "✅ Configuration files cleaned"

help:
	@echo "🚀 Pudu Webhook API - Multi-Region Deployment"
	@echo "=============================================="
	@echo ""
	@echo "🛠️  Setup Commands:"
	@echo "  setup-us-east-1    Clean and setup configuration for us-east-1"
	@echo "  setup-us-east-2    Clean and setup configuration for us-east-2"
	@echo ""
	@echo "🚀 Deployment Commands:"
	@echo "  deploy-us-east-1   Clean, setup and deploy to us-east-1"
	@echo "  deploy-us-east-2   Clean, setup and deploy to us-east-2"
	@echo "  deploy-container   Deploy with current configuration"
	@echo ""
	@echo "🔍 Utility Commands:"
	@echo "  print-vars         Show current configuration variables"
	@echo "  verify-config      Verify current configuration files"
	@echo "  clean-config       Remove generated configuration files"
	@echo ""
	@echo "📝 Example Usage:"
	@echo "  make deploy-us-east-1   # Clean + Deploy to us-east-1"
	@echo "  make deploy-us-east-2   # Clean + Deploy to us-east-2"
	@echo ""
	@echo "ℹ️  Note: All setup commands automatically clean first"