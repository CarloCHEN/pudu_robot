# Use AWS Lambda Python base image
FROM public.ecr.aws/lambda/python:3.9

# Install system dependencies for OpenCV (this fixes your libavcodec issue)
RUN yum update -y && \
    yum install -y mesa-libGL && \
    yum clean all

# Install Python packages
COPY ../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application code
COPY src/pudu/ ${LAMBDA_TASK_ROOT}/pudu/
COPY lambda/robot_lambda_function.py ${LAMBDA_TASK_ROOT}/lambda_function.py
COPY src/pudu/configs/database_config.yaml ${LAMBDA_TASK_ROOT}/
COPY src/pudu/notifications/icons.yaml ${LAMBDA_TASK_ROOT}/
COPY credentials.yaml ${LAMBDA_TASK_ROOT}/

# Copy RDS credentials if they exist
COPY src/pudu/rds/credentials.yaml ${LAMBDA_TASK_ROOT}/pudu/rds/ 2>/dev/null || true

# Set the CMD to your handler
CMD ["lambda_function.lambda_handler"]