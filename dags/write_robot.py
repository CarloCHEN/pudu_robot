from airflow import DAG
from airflow.operators.python import PythonOperator  # Updated import
from datetime import datetime, timedelta
import sys
import logging
import os

# Configure logging for better visibility in Airflow
logger = logging.getLogger(__name__)

def start_app():
    """
    Main task function that runs the robot data pipeline
    Maintains original time calculation logic but adds proper logging
    """
    try:
        # Import here to avoid import issues at DAG parsing time
        from pudu.app.main import App

        # Calculate time values when the function actually executes
        now = datetime.now()
        start_time = now.replace(hour=0, minute=0, second=0).strftime('%Y-%m-%d %H:%M:%S')
        end_time = now.replace(hour=23, minute=59, second=59).strftime('%Y-%m-%d %H:%M:%S')

        # Log start information (visible in Airflow UI)
        logger.info("🚀 Starting Pudu robot data pipeline")
        logger.info(f"📅 Start date: {start_time}")
        logger.info(f"📅 End date: {end_time}")

        # Initialize app with configuration
        logger.info("🔧 Initializing application with database configuration...")
        app = App("/usr/local/airflow/dags/pudu/configs/database_config.yaml")

        # Log configuration summary
        config_summary = app.get_config_summary()
        logger.info(f"📊 Configuration loaded: {config_summary['total_tables']} tables across {len(config_summary['databases'])} databases")

        # Run the pipeline
        logger.info("▶️ Starting data pipeline execution...")
        success = app.run(start_time=start_time, end_time=end_time)

        # Final status logging
        if success:
            logger.info("✅ Pudu robot data pipeline completed successfully")
            return "SUCCESS"
        else:
            logger.error("❌ Pudu robot data pipeline completed with failures")
            raise RuntimeError("Pipeline completed but no data was successfully inserted")

    except ImportError as e:
        logger.error(f"💥 Import error - check Python path and dependencies: {e}")
        raise
    except FileNotFoundError as e:
        logger.error(f"💥 Configuration file error: {e}")
        raise
    except Exception as e:
        logger.error(f"💥 Pipeline execution failed: {e}", exc_info=True)
        # Re-raise the exception so Airflow marks the task as failed
        raise

# Default arguments for the DAG
default_args = {
    'owner': 'Jiaxu Chen',
    'depends_on_past': False,
    'email_on_failure': False,  # Set to True and add email if needed
    'email_on_retry': False,
    'retries': 0,  # Retry once on failure
    'retry_delay': timedelta(minutes=5),  # Wait 5 minutes before retry
    'start_date': datetime(2024, 10, 29),
}

# Define the DAG
with DAG(
    dag_id='pudu_robot_data_to_db_dag',
    description='DAG to write Pudu robot data to database with enhanced logging and error handling',
    schedule_interval='0 */1 * * *',  # Run every 1 hour
    start_date=datetime(2024, 10, 29),
    catchup=False,
    max_active_runs=1,  # Prevent overlapping runs
    default_args=default_args,
    tags=['pudu', 'robot', 'data_pipeline', 'hourly'],  # Tags for easy filtering in UI
) as dag:

    # Main robot data pipeline task
    robot_data_task = PythonOperator(
        task_id="pudu_robot_task",
        python_callable=start_app,
        # Removed provide_context parameter - not needed in modern Airflow
    )

    robot_data_task