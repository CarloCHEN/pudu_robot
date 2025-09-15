# Use Python 3.9 slim image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY report_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only what we need - specific directories and files
COPY src/pudu/reporting ./pudu/reporting
COPY src/pudu/configs ./pudu/configs
COPY src/pudu/rds ./pudu/rds
COPY src/pudu/apis ./pudu/apis

COPY src/pudu/services/robot_database_resolver.py ./pudu/services/robot_database_resolver.py
COPY src/pudu/__init__.py ./pudu/__init__.py
COPY report_api/main.py .

# Create services __init__.py with only what we need
RUN mkdir -p ./pudu/services && \
    echo '""" Robot Package """' > ./pudu/services/__init__.py && \
    echo '' >> ./pudu/services/__init__.py && \
    echo 'from .robot_database_resolver import *' >> ./pudu/services/__init__.py && \
    echo '' >> ./pudu/services/__init__.py && \
    echo '__all__ = [' >> ./pudu/services/__init__.py && \
    echo '    "RobotDatabaseResolver"' >> ./pudu/services/__init__.py && \
    echo ']' >> ./pudu/services/__init__.py


# Set Python path to include current directory
ENV PYTHONPATH="/app"

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/reports/health || exit 1

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["python", "main.py"]