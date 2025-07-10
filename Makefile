include .env

.EXPORT_ALL_VARIABLES:
APP_NAME=foxx_monitor_pudu_webhook_api

TAG=latest
TF_VAR_app_name=${APP_NAME}
REGISTRY_NAME=${APP_NAME}
TF_VAR_image=${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REGISTRY_NAME}:${TAG}
TF_VAR_region=${AWS_REGION}


print-vars:
	@echo "APP_NAME=${APP_NAME}"
	@echo "TAG=${TAG}"
	@echo "TF_VAR_app_name=${TF_VAR_app_name}"
	@echo "REGISTRY_NAME=${REGISTRY_NAME}"
	@echo "TF_VAR_image=${TF_VAR_image}"
	@echo "TF_VAR_region=${TF_VAR_region}"

deploy-container:
	sh deploy.sh