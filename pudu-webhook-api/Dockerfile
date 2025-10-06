FROM public.ecr.aws/docker/library/python:3.9-slim

# Accept brand as build argument (optional, for future use)
ARG BRAND=pudu
ENV BRAND=${BRAND}

WORKDIR /usr/src/app

# Copy requirements first for better Docker layer caching
COPY pudu-webhook-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY pudu-webhook-api/callback_handler.py .
COPY pudu-webhook-api/config.py .
COPY pudu-webhook-api/main.py .
COPY pudu-webhook-api/models.py .
COPY pudu-webhook-api/database_writer.py .

# Copy core files
COPY pudu-webhook-api/core/ ./core/

# Copy notification files
COPY pudu-webhook-api/notifications/ ./notifications/
# Copy configs
COPY pudu-webhook-api/configs/ ./configs/
# Copy rds
COPY pudu-webhook-api/rds/ ./rds/
# Copy services
COPY pudu-webhook-api/services/ ./services/
# Copy test files for mock services
COPY pudu-webhook-api/test/ ./test/

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /usr/src/app
USER appuser

# Set default environment variables (can be overridden)
ENV HOST=0.0.0.0
ENV PORT=8000
ENV DEBUG=false

# Expose the port
EXPOSE $PORT

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://localhost:{os.getenv(\"PORT\", \"8000\")}/api/webhook/health')" || exit 1

# Use test main when in test mode, otherwise use production main
CMD ["sh", "-c", "if [ \"$TEST_MODE\" = \"true\" ]; then python test/test_main_cicd.py; else python main.py; fi"]