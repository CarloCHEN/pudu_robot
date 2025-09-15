# Include .env file if it exists, otherwise use defaults
-include .env

.EXPORT_ALL_VARIABLES:
APP_NAME=foxx_monitor_report_api

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
	echo "S3_REPORTS_BUCKET=$$S3_REPORTS_BUCKET" && \
	echo "TF_VAR_app_name=${APP_NAME}" && \
	echo "REGISTRY_NAME=${APP_NAME}" && \
	echo "TF_VAR_image=$$AWS_ACCOUNT_ID.dkr.ecr.$$AWS_REGION.amazonaws.com/${APP_NAME}:${TAG}" && \
	echo "TF_VAR_region=$$AWS_REGION"

setup-us-east-1: clean-config
	@echo "🚀 Setting up Report API for us-east-1..."
	./setup-environment.sh us-east-1

setup-us-east-2: clean-config
	@echo "🚀 Setting up Report API for us-east-2..."
	./setup-environment.sh us-east-2

verify-config:
	@echo "🔍 Verifying current configuration..."
	@echo "Current AWS Region: ${AWS_REGION}"
	@if [ -f "app.env" ]; then \
		echo "✅ app.env exists"; \
		echo "S3 Bucket: $(shell grep S3_REPORTS_BUCKET app.env)"; \
		echo "AWS Region: $(shell grep AWS_REGION app.env)"; \
	else \
		echo "❌ app.env missing - run setup first"; \
	fi
	@if [ -f "../src/pudu/configs/database_config.yaml" ]; then \
		echo "✅ database_config.yaml exists in src/pudu/configs/"; \
	else \
		echo "❌ database_config.yaml missing in src/pudu/configs/"; \
	fi

deploy-container:
	@if [ ! -f ".env" ]; then \
		echo "❌ .env file missing. Run 'make setup-us-east-1' or 'make setup-us-east-2' first"; \
		exit 1; \
	fi
	@echo "🔍 Loading environment variables..."
	@export $(grep -v '^#' .env | xargs) && \
	echo "🚀 Deploying Report API container to $$AWS_REGION..." && \
	if [ ! -f "app.env" ]; then \
		echo "❌ Configuration files missing. Run setup first"; \
		exit 1; \
	fi && \
	if [ ! -f "../src/pudu/configs/database_config.yaml" ]; then \
		echo "❌ database_config.yaml missing in src/pudu/configs/"; \
		exit 1; \
	fi && \
	sh deploy.sh

deploy-us-east-1: setup-us-east-1 deploy-container

deploy-us-east-2: setup-us-east-2 deploy-container

test-local:
	@if [ ! -f "app.env" ]; then \
		echo "❌ app.env missing. Run setup first"; \
		exit 1; \
	fi
	@echo "🧪 Starting Report API locally..."
	@export $(grep -v '^#' app.env | xargs) && \
	python main.py

build-local:
	@echo "🏗️ Building Report API image locally..."
	@if [ ! -f ".env" ]; then \
		echo "❌ .env file missing. Run setup first"; \
		exit 1; \
	fi
	@export $(grep -v '^#' .env | xargs) && \
	docker build --platform=linux/amd64 -t ${APP_NAME}:${TAG} -f Dockerfile ..

run-local: build-local
	@echo "🚀 Running Report API container locally..."
	@if [ ! -f "app.env" ]; then \
		echo "❌ app.env missing. Run setup first"; \
		exit 1; \
	fi
	@docker run -p 8000:8000 --env-file app.env ${APP_NAME}:${TAG}

check-bucket:
	@echo "🪣 Checking S3 bucket access..."
	@if [ ! -f ".env" ]; then \
		echo "❌ .env file missing. Run setup first"; \
		exit 1; \
	fi
	@export $(grep -v '^#' .env | xargs) && \
	echo "Testing access to bucket: $$S3_REPORTS_BUCKET in region: $$AWS_REGION" && \
	aws s3 ls s3://$$S3_REPORTS_BUCKET --region $$AWS_REGION || \
	echo "❌ Cannot access bucket. Check AWS credentials and bucket permissions."

clean-config:
	@echo "🧹 Cleaning generated configuration files..."
	@rm -f .env
	@rm -f app.env
	@echo "✅ Configuration files cleaned"

clean-docker:
	@echo "🧹 Cleaning Docker images..."
	@docker rmi ${APP_NAME}:${TAG} 2>/dev/null || true
	@docker system prune -f

install-deps:
	@echo "📦 Installing Python dependencies..."
	@pip install -r requirements.txt

test-api:
	@echo "🧪 Testing API endpoints..."
	@if [ ! -f "app.env" ]; then \
		echo "❌ app.env missing. Run setup first"; \
		exit 1; \
	fi
	@echo "Starting API test..."
	@python -c "import requests; print('Health check:', requests.get('http://localhost:8000/api/reports/health').json())" || \
	echo "❌ API not running. Start with 'make test-local' first."

help:
	@echo "🚀 Report API - Multi-Region Deployment"
	@echo "======================================"
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
	@echo "  check-bucket       Test S3 bucket access"
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
	@echo "  POST /api/reports/generate          - Generate report"
	@echo "  GET  /api/reports/status/{id}       - Check generation status"
	@echo "  GET  /api/reports/health            - Health check"
	@echo "  GET  /api/reports/history/{customer} - Get report history"
	@echo ""
	@echo "ℹ️  Note: Uses existing database_config.yaml from src/pudu/configs/"