# Include .env file if it exists, otherwise use defaults
-include .env

.EXPORT_ALL_VARIABLES:
# Get brand from .env or default to pudu
BRAND ?= pudu
APP_NAME=foxx_monitor_$(BRAND)_webhook_api

TAG=latest
TF_VAR_app_name=${APP_NAME}
REGISTRY_NAME=${APP_NAME}
TF_VAR_image=${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REGISTRY_NAME}:${TAG}
TF_VAR_region=${AWS_REGION}

print-vars:
	@if [ ! -f ".env" ]; then \
		echo "❌ .env file missing. Run 'make setup-<region>-<brand>' first"; \
		exit 1; \
	fi
	@echo "🔍 Current Configuration:"
	@export $(grep -v '^#' .env | xargs) && \
	echo "BRAND=$$BRAND" && \
	echo "APP_NAME=${APP_NAME}" && \
	echo "TAG=${TAG}" && \
	echo "AWS_REGION=$$AWS_REGION" && \
	echo "AWS_ACCOUNT_ID=$$AWS_ACCOUNT_ID" && \
	echo "REGISTRY_NAME=${APP_NAME}" && \
	echo "TF_VAR_image=$$AWS_ACCOUNT_ID.dkr.ecr.$$AWS_REGION.amazonaws.com/${APP_NAME}:${TAG}"

# Setup commands for different regions and brands
setup-us-east-1-pudu: clean-config
	@echo "🚀 Setting up Pudu Webhook API for us-east-1..."
	./setup-environment.sh us-east-1 pudu

setup-us-east-1-gas: clean-config
	@echo "🚀 Setting up Gas Webhook API for us-east-1..."
	./setup-environment.sh us-east-1 gas

setup-us-east-2-pudu: clean-config
	@echo "🚀 Setting up Pudu Webhook API for us-east-2..."
	./setup-environment.sh us-east-2 pudu

setup-us-east-2-gas: clean-config
	@echo "🚀 Setting up Gas Webhook API for us-east-2..."
	./setup-environment.sh us-east-2 gas

# Legacy commands (default to pudu for backward compatibility)
setup-us-east-1: setup-us-east-1-pudu
setup-us-east-2: setup-us-east-2-pudu

verify-config:
	@echo "🔍 Verifying current configuration..."
	@if [ -f ".env" ]; then \
		echo "✅ .env exists"; \
		echo "Brand: $(shell grep '^BRAND=' .env | cut -d'=' -f2)"; \
		echo "AWS Region: $(shell grep '^AWS_REGION=' .env | cut -d'=' -f2)"; \
		echo "Notification Host: $(shell grep NOTIFICATION_API_HOST .env)"; \
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
		echo "RDS Host: $(shell grep 'host:' rds/credentials.yaml)"; \
	else \
		echo "❌ credentials.yaml missing - run setup first"; \
	fi

deploy-container:
	@if [ ! -f ".env" ]; then \
		echo "❌ .env file missing. Run 'make setup-<region>-<brand>' first"; \
		exit 1; \
	fi
	@echo "🔍 Loading environment variables..."
	@export $(grep -v '^#' .env | xargs) && \
	BRAND_VAR=$$(grep '^BRAND=' .env | cut -d'=' -f2) && \
	echo "🚀 Deploying $$BRAND_VAR Webhook API to $$AWS_REGION..." && \
	if [ ! -f ".env" ] || [ ! -f "notifications/.env" ] || [ ! -f "rds/credentials.yaml" ]; then \
		echo "❌ Configuration files missing. Run setup first"; \
		exit 1; \
	fi && \
	sh deploy.sh

# Deploy commands for specific region-brand combinations
deploy-us-east-1-pudu: setup-us-east-1-pudu deploy-container
deploy-us-east-1-gas: setup-us-east-1-gas deploy-container
deploy-us-east-2-pudu: setup-us-east-2-pudu deploy-container
deploy-us-east-2-gas: setup-us-east-2-gas deploy-container

# Legacy commands (default to pudu)
deploy-us-east-1: deploy-us-east-1-pudu
deploy-us-east-2: deploy-us-east-2-pudu

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
	@export $(grep -v '^#' .env | xargs) && \
	BRAND_VAR=$$(grep '^BRAND=' .env | cut -d'=' -f2 || echo "pudu") && \
	echo "Building for brand: $$BRAND_VAR" && \
	docker build --platform=linux/amd64 --build-arg BRAND=$$BRAND_VAR -t ${APP_NAME}:${TAG} -f Dockerfile ..

run-local: build-local
	@echo "🚀 Running Webhook API container locally..."
	@if [ ! -f ".env" ]; then \
		echo "❌ .env missing. Run setup first"; \
		exit 1; \
	fi
	@docker run -p 8000:8000 --env-file .env ${APP_NAME}:${TAG}

test-api:
	@echo "🧪 Testing Webhook API endpoints..."
	@if [ ! -f ".env" ]; then \
		echo "❌ .env missing. Cannot determine brand."; \
		exit 1; \
	fi
	@BRAND_VAR=$$(grep '^BRAND=' .env | cut -d'=' -f2 || echo "pudu") && \
	echo "Testing $$BRAND_VAR endpoints:" && \
	echo "General health check:" && \
	curl -s http://localhost:8000/api/webhook/health | python -m json.tool && \
	echo "" && \
	echo "$$BRAND_VAR-specific health check:" && \
	curl -s http://localhost:8000/api/$$BRAND_VAR/webhook/health | python -m json.tool || \
	echo "❌ API not running. Start with 'make test-local' first."

clean-config:
	@echo "🧹 Cleaning generated configuration files..."
	@rm -f .env
	@rm -f notifications/.env
	@rm -f rds/credentials.yaml
	@echo "✅ Configuration files cleaned"

clean-docker:
	@echo "🧹 Cleaning Docker images..."
	@docker rmi ${APP_NAME}:${TAG} 2>/dev/null || true
	@docker system prune -f

install-deps:
	@echo "📦 Installing Python dependencies..."
	@pip install -r requirements.txt

help:
	@echo "🚀 Multi-Brand Robot Webhook API - Deployment"
	@echo "=============================================="
	@echo ""
	@echo "🛠️  Setup Commands (Region + Brand):"
	@echo "  setup-us-east-1-pudu    Setup Pudu for us-east-1"
	@echo "  setup-us-east-1-gas     Setup Gas for us-east-1"
	@echo "  setup-us-east-2-pudu    Setup Pudu for us-east-2"
	@echo "  setup-us-east-2-gas     Setup Gas for us-east-2"
	@echo ""
	@echo "🚀 Deployment Commands:"
	@echo "  deploy-us-east-1-pudu   Deploy Pudu to us-east-1"
	@echo "  deploy-us-east-1-gas    Deploy Gas to us-east-1"
	@echo "  deploy-us-east-2-pudu   Deploy Pudu to us-east-2"
	@echo "  deploy-us-east-2-gas    Deploy Gas to us-east-2"
	@echo "  deploy-container        Deploy with current config"
	@echo ""
	@echo "🏗️  Local Development:"
	@echo "  build-local             Build Docker image locally"
	@echo "  test-local              Run API with Python locally"
	@echo "  run-local               Run API in Docker locally"
	@echo "  install-deps            Install Python dependencies"
	@echo ""
	@echo "🔍 Utility Commands:"
	@echo "  print-vars              Show current configuration"
	@echo "  verify-config           Verify configuration files"
	@echo "  test-api                Test API endpoints"
	@echo "  clean-config            Remove generated configs"
	@echo "  clean-docker            Remove Docker images"
	@echo ""
	@echo "📝 Example Usage:"
	@echo "  make deploy-us-east-2-gas    # Deploy Gas to us-east-2"
	@echo "  make deploy-us-east-1-pudu   # Deploy Pudu to us-east-1"
	@echo "  make test-local              # Test locally"
	@echo ""
	@echo "📋 API Endpoints:"
	@echo "  POST /api/pudu/webhook - Pudu callbacks"
	@echo "  POST /api/gas/webhook  - Gas callbacks"
	@echo "  GET  /api/webhook/health - General health"
	@echo "  GET  /api/<brand>/webhook/health - Brand health"