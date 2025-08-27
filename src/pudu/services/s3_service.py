# src/pudu/services/s3_service.py
import boto3
import io
import logging
from datetime import datetime
from typing import Optional, Dict
from PIL import Image
import numpy as np
from botocore.exceptions import ClientError
import pandas as pd

logger = logging.getLogger(__name__)

class S3TransformService:
    """
    Service for uploading transformed images to S3 and generating public URLs
    """

    def __init__(self, region: str = 'us-east-2'):
        """
        Initialize S3 service

        Args:
            region: AWS region for S3 operations (default: us-east-2)
        """
        self.region = region
        self.s3_client = boto3.client('s3', region_name=region)

        # S3 bucket mapping for each database
        # This will be loaded from configuration
        self.bucket_mapping = {
            'university_of_florida': 'pudu-robot-transforms-university-of-florida-123456-us-east-2'
            # Add more databases and their buckets here
        }

    def update_bucket_mapping(self, database_to_bucket_mapping: Dict[str, str]):
        """
        Update the bucket mapping from configuration

        Args:
            database_to_bucket_mapping: Dict mapping database names to bucket names
        """
        self.bucket_mapping.update(database_to_bucket_mapping)
        logger.info(f"Updated S3 bucket mapping for {len(self.bucket_mapping)} databases")

    def get_bucket_for_database(self, database_name: str) -> Optional[str]:
        """
        Get S3 bucket name for a specific database

        Args:
            database_name: Name of the database

        Returns:
            Bucket name if found, None otherwise
        """
        return self.bucket_mapping.get(database_name)

    def upload_transformed_image(self,
                                image_array: np.ndarray,
                                map_name: str,
                                task_id: str,
                                robot_sn: str,
                                database_name: str,
                                original_map_url: str = None) -> Optional[str]:
        """
        Upload transformed image to S3 and return public URL

        Args:
            image_array: Numpy array of the transformed image (RGB format)
            map_name: Name of the map being transformed
            task_id: Task ID for unique identification
            robot_sn: Robot serial number
            database_name: Database name to determine bucket
            original_map_url: Original map URL to create deterministic naming

        Returns:
            Public HTTPS URL if upload successful, None if failed
        """
        try:
            # Get bucket for this database
            bucket_name = self.get_bucket_for_database(database_name)
            if not bucket_name:
                logger.error(f"No S3 bucket configured for database: {database_name} for image upload")
                return None

            # Generate deterministic S3 key (path) for the image
            s3_key = self._generate_deterministic_s3_key(map_name, task_id, robot_sn, original_map_url)

            # Check if image already exists and is the same
            if self._should_skip_upload(bucket_name, s3_key, image_array):
                # Return existing URL without uploading
                public_url = f"https://{bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
                logger.info(f"♻️ Using existing transformed image: {public_url}")
                return public_url

            # Convert numpy array to PNG bytes
            image_bytes = self._numpy_to_png_bytes(image_array)
            if not image_bytes:
                logger.error("Failed to convert image array to PNG bytes")
                return None

            # Upload to S3 (this will overwrite if exists)
            success = self._upload_to_s3(bucket_name, s3_key, image_bytes)
            if not success:
                return None

            # Generate public URL with proper URL encoding
            public_url = f"https://{bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"

            logger.info(f"✅ Uploaded transformed image: {public_url}")
            return public_url

        except Exception as e:
            logger.error(f"❌ Error uploading transformed image: {e}")
            return None

    def _generate_deterministic_s3_key(self, map_name: str, task_id: str, robot_sn: str, original_map_url: str = None) -> str:
        """
        Generate deterministic S3 key (path) for the transformed image based on content

        This ensures that the same transformation will always produce the same S3 key,
        allowing for deduplication and overwriting of identical content.

        Format: transformed-maps/{clean_map_name}/{content_hash}.png

        Args:
            map_name: Name of the map
            task_id: Task ID
            robot_sn: Robot serial number
            original_map_url: Original map URL to include in hash

        Returns:
            S3 key string with URL-safe characters
        """
        import hashlib
        import urllib.parse

        # Clean map name for use in S3 key - remove problematic characters
        clean_map_name = map_name.replace(' ', '_').replace('/', '_').replace('#', '_').replace('%', '_')

        # Create content hash from key identifying information
        # This ensures same map + same original URL = same S3 key
        hash_input = f"{map_name}:{original_map_url}" if original_map_url else map_name
        content_hash = hashlib.md5(hash_input.encode()).hexdigest()[:12]  # Use first 12 chars

        # Generate filename with content hash
        filename = f"{content_hash}.png"

        # Return full S3 key with URL-safe path
        return f"transformed-maps/{clean_map_name}/{filename}"

    def _generate_s3_key(self, map_name: str, task_id: str, robot_sn: str) -> str:
        """
        Generate timestamped S3 key (path) for the transformed image (legacy method)

        Format: transformed-maps/{map_name}/{timestamp}_{task_id}_{robot_sn}.png

        Args:
            map_name: Name of the map
            task_id: Task ID
            robot_sn: Robot serial number

        Returns:
            S3 key string
        """
        # Clean map name for use in S3 key
        clean_map_name = map_name.replace(' ', '_').replace('/', '_')

        # Generate timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Generate unique filename
        filename = f"{timestamp}_{task_id}_{robot_sn}.png"

        # Return full S3 key
        return f"transformed-maps/{clean_map_name}/{filename}"

    def _should_skip_upload(self, bucket_name: str, s3_key: str, image_array: np.ndarray) -> bool:
        """
        Check if we should skip upload because the same image already exists

        Args:
            bucket_name: S3 bucket name
            s3_key: S3 key (path)
            image_array: Current image array

        Returns:
            True if upload should be skipped, False otherwise
        """
        try:
            # Check if object exists
            response = self.s3_client.head_object(Bucket=bucket_name, Key=s3_key)

            # Object exists, optionally we could check if content is the same
            # For now, we assume if the key exists, it's the same content
            # (since we use deterministic naming based on content)
            logger.debug(f"Object already exists: s3://{bucket_name}/{s3_key}")
            return True

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey' or error_code == '404':
                # Object doesn't exist, proceed with upload
                return False
            else:
                # Other error, proceed with upload to be safe
                logger.debug(f"Error checking object existence: {e}")
                return False
        except Exception as e:
            # Any other error, proceed with upload
            logger.debug(f"Unexpected error checking object: {e}")
            return False

    def _numpy_to_png_bytes(self, image_array: np.ndarray) -> Optional[bytes]:
        """
        Convert numpy array to PNG bytes

        Args:
            image_array: Numpy array in RGB format

        Returns:
            PNG bytes if successful, None if failed
        """
        try:
            # Ensure array is in correct format
            if image_array.dtype != np.uint8:
                image_array = image_array.astype(np.uint8)

            # Convert to PIL Image
            if len(image_array.shape) == 3 and image_array.shape[2] == 3:
                # RGB image
                image = Image.fromarray(image_array, 'RGB')
            else:
                logger.error(f"Unsupported image shape: {image_array.shape}")
                return None

            # Convert to PNG bytes
            with io.BytesIO() as output:
                image.save(output, format='PNG', optimize=True)
                return output.getvalue()

        except Exception as e:
            logger.error(f"Error converting numpy array to PNG: {e}")
            return None

    def _upload_to_s3(self, bucket_name: str, s3_key: str, image_bytes: bytes) -> bool:
        """
        Upload image bytes to S3

        Args:
            bucket_name: S3 bucket name
            s3_key: S3 key (path)
            image_bytes: Image data as bytes

        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=image_bytes,
                ContentType='image/png',
                CacheControl='max-age=86400'  # Cache for 24 hours
            )

            logger.debug(f"✅ Uploaded to S3: s3://{bucket_name}/{s3_key}")
            return True

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                logger.error(f"❌ S3 bucket does not exist: {bucket_name}")
            elif error_code == 'AccessDenied':
                logger.error(f"❌ Access denied to S3 bucket: {bucket_name}")
            else:
                logger.error(f"❌ S3 upload error: {e}")
            return False

        except Exception as e:
            logger.error(f"❌ Unexpected error uploading to S3: {e}")
            return False

    def test_bucket_access(self, database_name: str) -> bool:
        """
        Test if we can access the S3 bucket for a database

        Args:
            database_name: Database name to test

        Returns:
            True if bucket is accessible, False otherwise
        """
        bucket_name = self.get_bucket_for_database(database_name)
        if not bucket_name:
            logger.error(f"No bucket configured for database: {database_name}")
            return False

        try:
            # Try to list objects in the bucket (with limit 1)
            self.s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
            logger.info(f"✅ S3 bucket access confirmed: {bucket_name}")
            return True

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                logger.error(f"❌ S3 bucket does not exist: {bucket_name}")
            elif error_code == 'AccessDenied':
                logger.error(f"❌ Access denied to S3 bucket: {bucket_name}")
            else:
                logger.error(f"❌ S3 bucket access error: {e}")
            return False

        except Exception as e:
            logger.error(f"❌ Unexpected error testing S3 bucket: {e}")
            return False

    def upload_work_location_data(self, archive_data: pd.DataFrame, robot_sn: str, database_name: str) -> bool:
        """
        Upload robot work location data to S3 for archival

        S3 structure:
        robot-work-location-archive/
        ├── database=university_of_florida/
        │   └── year=2025/month=01/day=15/
        │       └── robot_sn=811064412050012/
        │           └── batch_20250115_1400.parquet

        Args:
            archive_data (pd.DataFrame): Work location data to archive
            robot_sn (str): Robot serial number
            database_name (str): Database name to determine S3 bucket

        Returns:
            bool: True if upload successful, False otherwise
        """
        try:
            # Get bucket name for this database
            bucket_name = self.bucket_mapping.get(database_name)
            if not bucket_name:
                logger.warning(f"No S3 bucket configured for database: {database_name} for work location data upload")
                return False

            # Create S3 key with date partitioning
            current_time = datetime.now()
            date_str = current_time.strftime('%Y-%m-%d')
            timestamp_str = current_time.strftime('%Y%m%d_%H%M%S')

            s3_key = f"robot-work-location-archive/database={database_name}/year={current_time.year}/month={current_time.month:02d}/day={current_time.day:02d}/robot_sn={robot_sn}/batch_{timestamp_str}.parquet"

            # Convert DataFrame to parquet bytes
            parquet_buffer = io.BytesIO()
            archive_data.to_parquet(parquet_buffer, index=False, engine='pyarrow')
            parquet_bytes = parquet_buffer.getvalue()

            # Upload to S3
            self.s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=parquet_bytes,
                ContentType='application/octet-stream',
                Metadata={
                    'robot_sn': robot_sn,
                    'database_name': database_name,
                    'record_count': str(len(archive_data)),
                    'archive_date': date_str,
                    'content_type': 'work_location_data'
                }
            )

            logger.info(f"📦 Uploaded {len(archive_data)} work location records to S3: s3://{bucket_name}/{s3_key}")
            return True

        except Exception as e:
            logger.error(f"Error uploading work location data to S3: {e}")
            return False

# Factory function for easy integration
def create_s3_service(region: str = 'us-east-1',
                     bucket_mapping: Optional[Dict[str, str]] = None) -> S3TransformService:
    """
    Create S3 service with optional bucket mapping

    Args:
        region: AWS region
        bucket_mapping: Optional mapping of database names to bucket names

    Returns:
        Configured S3TransformService instance
    """
    service = S3TransformService(region)

    if bucket_mapping:
        service.update_bucket_mapping(bucket_mapping)

    return service