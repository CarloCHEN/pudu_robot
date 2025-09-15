import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
import uuid

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from pudu.reporting.core.report_generator import ReportGenerator
from pudu.reporting.core.report_config import ReportConfig
from pudu.reporting.services.report_delivery_service import ReportDeliveryService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Robot Management Async Report API",
    description="Async API for generating robot management reports",
    version="1.0.0"
)

# Global services (initialized on startup)
report_generator: Optional[ReportGenerator] = None
delivery_service: Optional[ReportDeliveryService] = None

# Request models
class ReportGenerationRequest(BaseModel):
    customer_id: str = Field(..., description="Customer identifier")
    form_data: Dict[str, Any] = Field(..., description="Report configuration form data")

    class Config:
        schema_extra = {
            "example": {
                "customer_id": "customer-123",
                "form_data": {
                    "service": "robot-management",
                    "contentCategories": ["robot-status", "cleaning-tasks", "performance"],
                    "timeRange": "last-30-days",
                    "detailLevel": "detailed",
                    "delivery": "in-app",
                    "schedule": "immediate",
                    "location": {
                        "country": "US",
                        "state": "Ohio",
                        "city": "",
                        "building": ""
                    },
                    "robot": {
                        "name": "",
                        "serialNumber": ""
                    }
                }
            }
        }

# Response models
class ReportGenerationResponse(BaseModel):
    success: bool
    request_id: str
    message: str
    status: str = "processing"

class ReportStatusResponse(BaseModel):
    success: bool
    request_id: str
    status: str  # processing, completed, failed
    report_url: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

# In-memory storage for request status (in production, use Redis or database)
request_status_store: Dict[str, Dict[str, Any]] = {}

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global report_generator, delivery_service

    try:
        # Get AWS region from environment
        aws_region = os.getenv('AWS_REGION', 'us-east-2')
        config_paths = [
            'database_config.yaml',
            '../src/pudu/configs/database_config.yaml',
            'src/pudu/configs/database_config.yaml',
            'pudu/configs/database_config.yaml',
            '/opt/database_config.yaml'
        ]

        config_path = None
        for path in config_paths:
            if os.path.exists(path):
                config_path = path
                break
        if not config_path:
            raise FileNotFoundError("Configuration file not found")

        logger.info(f"Starting API in region: {aws_region}")

        # Initialize services
        report_generator = ReportGenerator(config_path=config_path)
        delivery_service = ReportDeliveryService(region=aws_region)

        logger.info("Services initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global report_generator, delivery_service

    try:
        if report_generator:
            report_generator.close()
        # No explicit cleanup needed for delivery_service
        logger.info("Services cleaned up successfully")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

async def generate_report_async(request_id: str, customer_id: str, form_data: Dict[str, Any]):
    """Async function to generate report in background"""
    logger.info(f"Starting report generation for request {request_id}")

    try:
        # Update status
        request_status_store[request_id]["status"] = "processing"
        request_status_store[request_id]["updated_at"] = datetime.now().isoformat()

        # Create report configuration
        report_config = ReportConfig(form_data, customer_id)

        # Validate configuration
        validation_errors = report_config.validate()
        if validation_errors:
            error_msg = f"Validation failed: {', '.join(validation_errors)}"
            request_status_store[request_id].update({
                "status": "failed",
                "error": error_msg,
                "updated_at": datetime.now().isoformat()
            })
            return

        # Generate report (this is still sync, but runs in background)
        logger.info(f"Generating report for customer {customer_id}")
        generation_result = report_generator.generate_report(report_config)

        if not generation_result['success']:
            request_status_store[request_id].update({
                "status": "failed",
                "error": generation_result['error'],
                "updated_at": datetime.now().isoformat()
            })
            return

        # Deliver report (async)
        logger.info(f"Delivering report for request {request_id}")
        delivery_result = await delivery_service.deliver_report(
            generation_result['report_html'],
            generation_result['metadata'],
            report_config
        )

        if delivery_result['success']:
            request_status_store[request_id].update({
                "status": "completed",
                "report_url": delivery_result['storage_url'],
                "s3_key": delivery_result.get('s3_key'),
                "metadata": generation_result['metadata'],
                "delivery_result": delivery_result,
                "updated_at": datetime.now().isoformat()
            })
            logger.info(f"Report generation completed for request {request_id}")
        else:
            request_status_store[request_id].update({
                "status": "failed",
                "error": f"Delivery failed: {delivery_result.get('error', 'Unknown error')}",
                "updated_at": datetime.now().isoformat()
            })

    except Exception as e:
        logger.error(f"Error generating report for request {request_id}: {e}")
        request_status_store[request_id].update({
            "status": "failed",
            "error": str(e),
            "updated_at": datetime.now().isoformat()
        })

@app.post("/api/reports/generate", response_model=ReportGenerationResponse)
async def generate_report(request: ReportGenerationRequest, background_tasks: BackgroundTasks):
    """Generate a report asynchronously"""
    try:
        # Generate unique request ID
        request_id = str(uuid.uuid4())

        # Initialize request status
        request_status_store[request_id] = {
            "customer_id": request.customer_id,
            "status": "queued",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "report_url": None,
            "error": None
        }

        # Add background task for report generation
        background_tasks.add_task(
            generate_report_async,
            request_id,
            request.customer_id,
            request.form_data
        )

        logger.info(f"Queued report generation for customer {request.customer_id}, request {request_id}")

        return ReportGenerationResponse(
            success=True,
            request_id=request_id,
            message="Report generation started",
            status="queued"
        )

    except Exception as e:
        logger.error(f"Error queueing report generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reports/status/{request_id}", response_model=ReportStatusResponse)
async def get_report_status(request_id: str):
    """Get status of a report generation request"""
    try:
        if request_id not in request_status_store:
            raise HTTPException(status_code=404, detail="Request not found")

        status_info = request_status_store[request_id]

        return ReportStatusResponse(
            success=True,
            request_id=request_id,
            status=status_info["status"],
            report_url=status_info.get("report_url"),
            error=status_info.get("error"),
            metadata=status_info.get("metadata")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reports/health")
async def health_check():
    """Health check endpoint"""
    return {
        "success": True,
        "service": "Robot Management Async Report API",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "aws_region": os.getenv('AWS_REGION', 'us-east-2')
    }

@app.get("/api/reports/history/{customer_id}")
async def get_report_history(customer_id: str, limit: int = 50):
    """Get report history for a customer"""
    try:
        if not delivery_service:
            raise HTTPException(status_code=500, detail="Service not initialized")

        reports = await delivery_service.get_report_history(customer_id, limit)

        return {
            "success": True,
            "customer_id": customer_id,
            "reports": reports,
            "count": len(reports)
        }

    except Exception as e:
        logger.error(f"Error getting report history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/reports/delete")
async def delete_report(customer_id: str, report_key: str):
    """Delete a stored report"""
    try:
        if not delivery_service:
            raise HTTPException(status_code=500, detail="Service not initialized")

        result = await delivery_service.delete_report(customer_id, report_key)

        if result['success']:
            return result
        else:
            raise HTTPException(status_code=400, detail=result['error'])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )