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
	echo "AWS_REGION=$$AWS_REGION" && \
	echo "AWS_ACCOUNT_ID=$$AWS_ACCOUNT_ID" && \
	echo "TF_VAR_app_name=${APP_NAME}" && \
	echo "REGISTRY_NAME=${APP_NAME}" && \
	echo "TF_VAR_image=$$AWS_ACCOUNT_ID.dkr.ecr.$$AWS_REGION.amazonaws.com/${APP_NAME}:${TAG}" && \
	echo "TF_VAR_region=$$AWS_REGION"

setup-us-east-1: clean-config
	@echo "🚀 Setting up Webhook API for us-east-1..."
	./setup-environment.sh us-east-1

setup-us-east-2: clean-config
	@echo "🚀 Setting up Webhook API for us-east-2..."
	./setup-environment.sh us-east-2

verify-config:
	@echo "🔍 Verifying current configuration..."
	@echo "Current AWS Region: ${AWS_REGION}"
	@if [ -f ".env" ]; then \
		echo "✅ .env exists"; \
		echo "Notification Host: $(shell grep NOTIFICATION_API_HOST .env)"; \
	else \
		echo "❌ .env missing - run setup first"; \
	fi
	@if [ -f "notifications/.env" ]; then \
		echo "✅ notifications/.env exists"; \
		echo "Notifications Host: $(shell grep NOTIFICATION_API_HOST notifications/.env)"; \
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
		echo "❌ .env file missing. Run 'make setup-us-east-1' or 'make setup-us-east-2' first"; \
		exit 1; \
	fi
	@echo "🔍 Loading environment variables..."
	@export $(grep -v '^#' .env | xargs) && \
	echo "🚀 Deploying Webhook API container to $$AWS_REGION..." && \
	if [ ! -f ".env" ] || [ ! -f "notifications/.env" ] || [ ! -f "rds/credentials.yaml" ]; then \
		echo "❌ Configuration files missing. Run setup first"; \
		exit 1; \
	fi && \
	sh deploy.sh

deploy-us-east-1: setup-us-east-1 deploy-container

deploy-us-east-2: setup-us-east-2 deploy-container

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
	docker build --platform=linux/amd64 -t ${APP_NAME}:${TAG} -f Dockerfile ..

run-local: build-local
	@echo "🚀 Running Webhook API container locally..."
	@if [ ! -f ".env" ]; then \
		echo "❌ .env missing. Run setup first"; \
		exit 1; \
	fi
	@docker run -p 8000:8000 --env-file .env ${APP_NAME}:${TAG}

test-api:
	@echo "🧪 Testing Webhook API endpoints..."
	@echo "Health check:"
	@curl -s http://localhost:8000/api/pudu/webhook/health | python -m json.tool || \
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
	@echo "🏗️  Local Development:"
	@echo "  build-local        Build Docker image locally"
	@echo "  test-local         Run API with Python locally"
	@echo "  run-local          Run API in Docker container locally"
	@echo "  install-deps       Install Python dependencies"
	@echo ""
	@echo "🔍 Utility Commands:"
	@echo "  print-vars         Show current configuration variables"
	@echo "  verify-config      Verify current configuration files"
	@echo "  test-api           Test API endpoints (requires running API)"
	@echo "  clean-config       Remove generated configuration files"
	@echo "  clean-docker       Remove Docker images and cleanup"
	@echo ""
	@echo "📝 Example Usage:"
	@echo "  make deploy-us-east-1   # Clean + Deploy to us-east-1"
	@echo "  make test-local         # Test locally with Python"
	@echo "  make run-local          # Test locally with Docker"
	@echo ""
	@echo "📋 API Endpoints (when running):"
	@echo "  POST /api/pudu/webhook          - Process robot callbacks"
	@echo "  GET  /api/pudu/webhook/health   - Health check"
	@echo ""
	@echo "ℹ️  Note: All setup commands automatically clean first"