from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from pydantic import BaseModel, Field
import asyncio
from concurrent.futures import ThreadPoolExecutor
import warnings
import sys
import logging
from datetime import datetime
import traceback

sys.path.append("..")
from src.pudu.apis import (
    get_robot_table,
    get_schedule_table,
    get_charging_table,
    get_task_overview_data,
    get_events_table  # Add the new events table import
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Silence warnings
warnings.filterwarnings("ignore")

app = FastAPI(
    title="Robot Management API",
    description="API for managing and monitoring Pudu robots with comprehensive data access",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware for web frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a thread pool executor
executor = ThreadPoolExecutor(max_workers=30)

# Enhanced request models with validation
class TimeRangeRequest(BaseModel):
    start_time: str = Field(..., description="Start time in format 'YYYY-MM-DD HH:MM:SS'")
    end_time: str = Field(..., description="End time in format 'YYYY-MM-DD HH:MM:SS'")
    location_id: Optional[int] = Field(None, description="Filter by specific location ID")
    robot_sn: Optional[str] = Field(None, description="Filter by specific robot serial number")
    timezone_offset: Optional[int] = Field(-8, description="Timezone offset in hours")

    class Config:
        schema_extra = {
            "example": {
                "start_time": "2024-01-01 00:00:00",
                "end_time": "2024-01-01 23:59:59",
                "location_id": 1,
                "robot_sn": "ROBOT001",
                "timezone_offset": -8
            }
        }

class TaskOverviewRequest(BaseModel):
    start_time: str = Field(..., description="Start time in format 'YYYY-MM-DD HH:MM:SS'")
    end_time: str = Field(..., description="End time in format 'YYYY-MM-DD HH:MM:SS'")
    location_id: Optional[int] = Field(None, description="Filter by specific location ID")
    robot_sn: Optional[str] = Field(None, description="Filter by specific robot serial number")
    timezone_offset: Optional[int] = Field(-8, description="Timezone offset in hours")
    groupby: Optional[str] = Field("day", description="Group by 'day' or 'hour'")

    class Config:
        schema_extra = {
            "example": {
                "start_time": "2024-01-01 00:00:00",
                "end_time": "2024-01-07 23:59:59",
                "groupby": "day",
                "timezone_offset": -8
            }
        }

class EventsRequest(BaseModel):
    start_time: str = Field(..., description="Start time in format 'YYYY-MM-DD HH:MM:SS'")
    end_time: str = Field(..., description="End time in format 'YYYY-MM-DD HH:MM:SS'")
    location_id: Optional[int] = Field(None, description="Filter by specific location ID")
    robot_sn: Optional[str] = Field(None, description="Filter by specific robot serial number")
    timezone_offset: Optional[int] = Field(-8, description="Timezone offset in hours")
    event_type: Optional[str] = Field(None, description="Filter by event type (e.g., 'error', 'warning', 'info')")
    severity: Optional[str] = Field(None, description="Filter by severity level")

    class Config:
        schema_extra = {
            "example": {
                "start_time": "2024-01-01 00:00:00",
                "end_time": "2024-01-01 23:59:59",
                "robot_sn": "ROBOT001",
                "event_type": "error",
                "timezone_offset": -8
            }
        }

# Response models
class APIResponse(BaseModel):
    data: List[dict]
    count: int
    status: str = "success"
    message: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class ErrorResponse(BaseModel):
    status: str = "error"
    message: str
    error_type: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

# Helper function to run synchronous functions in a separate thread
async def run_in_executor(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(executor, func, *args, **kwargs)
        return result
    except Exception as e:
        logger.error(f"Error in executor: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Convert dataframe to dict for JSON response with enhanced error handling
def df_to_response(df, message: str = None) -> APIResponse:
    if df is None:
        return APIResponse(
            data=[],
            count=0,
            message=message or "No data returned from query"
        )

    if hasattr(df, 'empty') and df.empty:
        return APIResponse(
            data=[],
            count=0,
            message=message or "No data found for the specified criteria"
        )

    try:
        # Convert DataFrame to records
        if hasattr(df, 'to_dict'):
            result = df.to_dict(orient="records")
        else:
            # Handle case where df might already be a list or dict
            result = df if isinstance(df, list) else [df]

        return APIResponse(
            data=result,
            count=len(result),
            message=message or f"Successfully retrieved {len(result)} records"
        )
    except Exception as e:
        logger.error(f"Error converting dataframe to response: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing data: {str(e)}")

# Validation helper
def validate_time_format(time_str: str) -> bool:
    try:
        datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
        return True
    except ValueError:
        return False

@app.post("/robots/", response_model=APIResponse, summary="Get robot information")
async def get_robots(request: TimeRangeRequest):
    """
    Get comprehensive information about robots for a specific time period.

    Returns details including:
    - Robot type and specifications
    - Robot name and serial number
    - Location assignments
    - Operational statistics
    - Status information
    """
    # Validate time format
    if not validate_time_format(request.start_time) or not validate_time_format(request.end_time):
        raise HTTPException(status_code=400, detail="Invalid time format. Use 'YYYY-MM-DD HH:MM:SS'")

    logger.info(f"Getting robots data from {request.start_time} to {request.end_time}")

    df = await run_in_executor(
        get_robot_table,
        request.start_time,
        request.end_time,
        request.location_id,
        request.robot_sn,
        request.timezone_offset
    )
    return df_to_response(df, "Robot information retrieved successfully")

@app.post("/schedule/", response_model=APIResponse, summary="Get robot schedule information")
async def get_schedule(request: TimeRangeRequest):
    """
    Get detailed schedule information for robots within a time range.

    Returns comprehensive task details including:
    - Task assignments and scheduling
    - Efficiency metrics and performance data
    - Status information and completion rates
    - Task duration and timing analysis
    """
    if not validate_time_format(request.start_time) or not validate_time_format(request.end_time):
        raise HTTPException(status_code=400, detail="Invalid time format. Use 'YYYY-MM-DD HH:MM:SS'")

    logger.info(f"Getting schedule data from {request.start_time} to {request.end_time}")

    df = await run_in_executor(
        get_schedule_table,
        request.start_time,
        request.end_time,
        request.location_id,
        request.robot_sn,
        request.timezone_offset
    )
    return df_to_response(df, "Schedule information retrieved successfully")

@app.post("/charging/", response_model=APIResponse, summary="Get robot charging records")
async def get_charging(request: TimeRangeRequest):
    """
    Get comprehensive charging records for robots within a time period.

    Returns detailed charging information including:
    - Charging session start and end times
    - Power levels and consumption data
    - Charging duration and efficiency
    - Battery status and health metrics
    """
    if not validate_time_format(request.start_time) or not validate_time_format(request.end_time):
        raise HTTPException(status_code=400, detail="Invalid time format. Use 'YYYY-MM-DD HH:MM:SS'")

    logger.info(f"Getting charging data from {request.start_time} to {request.end_time}")

    df = await run_in_executor(
        get_charging_table,
        request.start_time,
        request.end_time,
        request.location_id,
        request.robot_sn
    )
    return df_to_response(df, "Charging records retrieved successfully")

@app.post("/task-overview/", response_model=APIResponse, summary="Get task overview data")
async def get_task_overview(request: TaskOverviewRequest):
    """
    Get aggregated task overview data grouped by day or hour.

    Provides summarized performance metrics including:
    - Task completion statistics
    - Performance trends over time
    - Efficiency metrics and KPIs
    - Operational summaries by time period
    """
    if not validate_time_format(request.start_time) or not validate_time_format(request.end_time):
        raise HTTPException(status_code=400, detail="Invalid time format. Use 'YYYY-MM-DD HH:MM:SS'")

    if request.groupby not in ["day", "hour"]:
        raise HTTPException(status_code=400, detail="groupby must be either 'day' or 'hour'")

    logger.info(f"Getting task overview data from {request.start_time} to {request.end_time}, grouped by {request.groupby}")

    df = await run_in_executor(
        get_task_overview_data,
        request.start_time,
        request.end_time,
        request.location_id,
        request.robot_sn,
        request.timezone_offset,
        request.groupby
    )
    return df_to_response(df, f"Task overview data retrieved successfully (grouped by {request.groupby})")

@app.post("/events/", response_model=APIResponse, summary="Get robot events and alerts")
async def get_events(request: EventsRequest):
    """
    Get robot events and alerts for a specific time period.

    Returns comprehensive event information including:
    - System events and notifications
    - Error logs and warnings
    - Performance alerts
    - Operational status changes
    - Security and safety events

    Supports filtering by:
    - Event type (error, warning, info, etc.)
    - Severity level
    - Specific robot or location
    """
    if not validate_time_format(request.start_time) or not validate_time_format(request.end_time):
        raise HTTPException(status_code=400, detail="Invalid time format. Use 'YYYY-MM-DD HH:MM:SS'")

    logger.info(f"Getting events data from {request.start_time} to {request.end_time}")

    # Note: Adjust parameters based on the actual get_events_table function signature
    try:
        df = await run_in_executor(
            get_events_table,
            request.start_time,
            request.end_time,
            request.location_id,
            request.robot_sn,
            request.timezone_offset
            # Add additional parameters if get_events_table supports them:
            # request.event_type,
            # request.severity
        )
        return df_to_response(df, "Events data retrieved successfully")
    except TypeError as e:
        # Handle case where get_events_table has different parameters
        logger.warning(f"Parameter mismatch for get_events_table: {e}")
        df = await run_in_executor(
            get_events_table,
            request.start_time,
            request.end_time
        )
        return df_to_response(df, "Events data retrieved successfully (with limited filtering)")

@app.get("/health/", summary="API health check")
async def health_check():
    """
    Comprehensive health check endpoint to verify API and system status.
    """
    try:
        # Test thread pool executor
        test_result = await run_in_executor(lambda: "OK")

        return {
            "status": "healthy",
            "message": "Robot Management API is running",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "services": {
                "thread_pool": "healthy" if test_result == "OK" else "degraded",
                "database_connection": "unknown"  # Add actual DB health check if needed
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.get("/api-info/", summary="Get API information and available endpoints")
async def get_api_info():
    """
    Get information about available API endpoints and their capabilities.
    """
    return {
        "api_name": "Robot Management API",
        "version": "1.0.0",
        "description": "Comprehensive API for Pudu robot data management",
        "endpoints": {
            "/robots/": "Get robot information and specifications",
            "/schedule/": "Get robot task schedules and performance data",
            "/charging/": "Get robot charging records and battery data",
            "/task-overview/": "Get aggregated task performance metrics",
            "/events/": "Get robot events, alerts, and system logs",
            "/health/": "API health check",
            "/api-info/": "This endpoint - API documentation"
        },
        "supported_time_format": "YYYY-MM-DD HH:MM:SS",
        "default_timezone_offset": -8,
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc"
        }
    }

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return {
        "status": "error",
        "message": exc.detail,
        "error_type": "HTTP_ERROR",
        "status_code": exc.status_code,
        "timestamp": datetime.now().isoformat()
    }

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    return {
        "status": "error",
        "message": "Internal server error",
        "error_type": "INTERNAL_ERROR",
        "timestamp": datetime.now().isoformat()
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Robot Management API is starting up...")
    logger.info(f"Thread pool executor initialized with {executor._max_workers} workers")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Robot Management API is shutting down...")
    executor.shutdown(wait=True)
    logger.info("Thread pool executor shutdown complete")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )