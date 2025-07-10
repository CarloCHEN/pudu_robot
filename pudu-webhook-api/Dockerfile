FROM python:3.9-slim

WORKDIR /usr/src/app

# Copy requirements first for better Docker layer caching
COPY pudu-webhook-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY pudu-webhook-api/callback_handler.py .
COPY pudu-webhook-api/config.py .
COPY pudu-webhook-api/main.py .
COPY pudu-webhook-api/models.py .
COPY pudu-webhook-api/processors.py .

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /usr/src/app
USER appuser

# Set default environment variables (can be overridden)
ENV HOST=0.0.0.0
ENV PORT=8000
ENV DEBUG=false

# Expose the port from environment variable
EXPOSE $PORT

# Health check using environment variable for port
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://localhost:{os.getenv(\"PORT\", \"8000\")}/api/pudu/webhook/health')" || exit 1

# Run the Flask application
CMD ["python", "main.py"]