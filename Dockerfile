# Use AWS Lambda Python runtime as base
FROM public.ecr.aws/lambda/python:3.9

# Install system dependencies for OpenCV and image processing
RUN yum update -y && \
    yum install -y \
    libX11 \
    libXext \
    libXrender \
    libSM \
    libICE \
    libGL \
    libglib2.0-0 \
    && yum clean all

# Copy requirements and install Python dependencies
COPY requirements_container.txt ${LAMBDA_TASK_ROOT}/requirements.txt
RUN pip install -r requirements.txt

# Copy source code
COPY src/pudu/ ${LAMBDA_TASK_ROOT}/pudu/
COPY lambda/robot_lambda_function.py ${LAMBDA_TASK_ROOT}/lambda_function.py
COPY src/pudu/configs/database_config.yaml ${LAMBDA_TASK_ROOT}/
COPY src/pudu/notifications/icons.yaml ${LAMBDA_TASK_ROOT}/

# Copy credential files
COPY credentials.yaml ${LAMBDA_TASK_ROOT}/
RUN mkdir -p ${LAMBDA_TASK_ROOT}/pudu/rds/
COPY src/pudu/rds/credentials.yaml ${LAMBDA_TASK_ROOT}/pudu/rds/

# Set the CMD to your handler
CMD ["lambda_function.lambda_handler"]
