#!/usr/bin/env python3
"""
Fixed S3 Bucket Setup Script for Transform Service

This script creates S3 buckets for each transform-supported database/project
with proper naming conventions and public access policies.

Usage:
    python fixed_s3_setup.py --config database_config.yaml [--region us-east-2]
"""

import boto3
import json
import argparse
import yaml
import logging
import time
import os
from botocore.exceptions import ClientError
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FixedS3BucketSetup:
    """Fixed setup S3 buckets for transform service with proper naming and policies"""

    def __init__(self, region='us-east-2'):
        self.region = region
        # Create S3 client with explicit configuration
        self.s3_client = boto3.client('s3', region_name=region)
        self.bucket_prefix = "pudu-robot-transforms"

        # Test AWS connectivity first
        self._test_aws_connectivity()

    def _test_aws_connectivity(self):
        """Test AWS connectivity and credentials"""
        try:
            # Test credentials
            sts_client = boto3.client('sts', region_name=self.region)
            identity = sts_client.get_caller_identity()
            logger.info(f"✅ AWS credentials valid for account: {identity.get('Account', 'Unknown')}")
            logger.info(f"✅ Using region: {self.region}")

            # Test S3 access
            self.s3_client.list_buckets()
            logger.info(f"✅ S3 access confirmed")

        except Exception as e:
            logger.error(f"❌ AWS connectivity test failed: {e}")
            raise

    def load_config(self, config_path: str) -> Dict:
        """Load database configuration"""
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            logger.error(f"Configuration file {config_path} not found")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration: {e}")
            raise

    def get_bucket_name(self, database_name: str) -> str:
        """
        Generate unique bucket name for a database

        Format: pudu-robot-transforms-{database_name}-{timestamp}-{region}
        Example: pudu-robot-transforms-university-of-florida-123456-us-east-2
        """
        # Replace underscores with hyphens and ensure lowercase
        clean_db_name = database_name.lower().replace('_', '-')

        # Add timestamp for uniqueness
        timestamp = str(int(time.time()))[-6:]  # Last 6 digits

        return f"{self.bucket_prefix}-{clean_db_name}-{timestamp}-{self.region}"

    def create_bucket(self, bucket_name: str) -> bool:
        """Create S3 bucket with proper configuration for us-east-2"""
        try:
            logger.info(f"Creating bucket: {bucket_name} in region: {self.region}")

            # For us-east-2, we MUST include CreateBucketConfiguration
            self.s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={
                    'LocationConstraint': self.region
                }
            )

            logger.info(f"✅ Created bucket: {bucket_name}")

            # Configure public access settings
            self._configure_bucket_public_access(bucket_name)

            # Set bucket policy for public read access to specific paths
            self._set_bucket_policy(bucket_name)

            # Configure CORS for web access
            self._configure_cors(bucket_name)

            return True

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'BucketAlreadyOwnedByYou':
                logger.info(f"ℹ️ Bucket {bucket_name} already exists and is owned by you")
                return True
            elif error_code == 'BucketAlreadyExists':
                logger.error(f"❌ Bucket {bucket_name} already exists but is owned by someone else")
                # Try with a different timestamp
                new_bucket_name = self.get_bucket_name(bucket_name.split('-')[3])  # Extract database name
                logger.info(f"🔄 Trying alternative name: {new_bucket_name}")
                return self.create_bucket(new_bucket_name)
            else:
                logger.error(f"❌ Error creating bucket {bucket_name}: {e}")
                return False

    def _configure_bucket_public_access(self, bucket_name: str):
        """Configure bucket for selective public access"""
        try:
            # Allow public access for specific paths only
            self.s3_client.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': False,
                    'IgnorePublicAcls': False,
                    'BlockPublicPolicy': False,
                    'RestrictPublicBuckets': False
                }
            )
            logger.info(f"✅ Configured public access for bucket: {bucket_name}")

        except ClientError as e:
            logger.error(f"❌ Error configuring public access for {bucket_name}: {e}")

    def _set_bucket_policy(self, bucket_name: str):
        """Set bucket policy to allow public read access to transformed images"""
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/transformed-maps/*"
                }
            ]
        }

        try:
            self.s3_client.put_bucket_policy(
                Bucket=bucket_name,
                Policy=json.dumps(policy)
            )
            logger.info(f"✅ Set bucket policy for public access: {bucket_name}")

        except ClientError as e:
            logger.error(f"❌ Error setting bucket policy for {bucket_name}: {e}")

    def _configure_cors(self, bucket_name: str):
        """Configure CORS for web access"""
        cors_configuration = {
            'CORSRules': [
                {
                    'AllowedHeaders': ['*'],
                    'AllowedMethods': ['GET'],
                    'AllowedOrigins': ['*'],
                    'MaxAgeSeconds': 3600
                }
            ]
        }

        try:
            self.s3_client.put_bucket_cors(
                Bucket=bucket_name,
                CORSConfiguration=cors_configuration
            )
            logger.info(f"✅ Configured CORS for bucket: {bucket_name}")

        except ClientError as e:
            logger.error(f"❌ Error setting CORS for {bucket_name}: {e}")

    def setup_buckets_for_config(self, config_path: str, dry_run: bool = False) -> Dict[str, str]:
        """
        Setup S3 buckets for all transform-supported databases

        Returns:
            Dict mapping database_name to bucket_name
        """
        config = self.load_config(config_path)
        supported_databases = config.get('transform_supported_databases', [])

        if not supported_databases:
            logger.warning("No transform_supported_databases found in config")
            return {}

        bucket_mapping = {}

        logger.info(f"Setting up S3 buckets for {len(supported_databases)} databases...")

        for database_name in supported_databases:
            bucket_name = self.get_bucket_name(database_name)

            if dry_run:
                logger.info(f"🔍 DRY RUN: Would create bucket {bucket_name} for database {database_name}")
                bucket_mapping[database_name] = bucket_name
                continue

            logger.info(f"Creating bucket for database: {database_name}")
            success = self.create_bucket(bucket_name)

            if success:
                bucket_mapping[database_name] = bucket_name
            else:
                logger.error(f"Failed to create bucket for {database_name}")

        return bucket_mapping

    def generate_config_snippet(self, bucket_mapping: Dict[str, str]) -> str:
        """Generate configuration snippet for the application"""
        config_snippet = f"""
        # Add this to the database_config.yaml file
        s3_config:
          region: "{self.region}"
          buckets:
        """

        for database_name, bucket_name in bucket_mapping.items():
            config_snippet += f'    {database_name}: "{bucket_name}"\n'

        config_snippet += f"""
        # S3 path structure:
        # {{bucket_name}}/transformed-maps/{{map_name}}/{{timestamp}}_{{task_id}}_{{robot_sn}}.png
        #
        # Example URLs:
        # https://{list(bucket_mapping.values())[0] if bucket_mapping else 'bucket-name'}.s3.{self.region}.amazonaws.com/transformed-maps/library_floor_1/20250820_143022_task123_robot456.png
        """

        return config_snippet

def main():
    parser = argparse.ArgumentParser(description='Setup S3 buckets for transform service')
    parser.add_argument('--region', default='us-east-2', help='AWS region for buckets (default: us-east-2)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be created without actually creating')

    args = parser.parse_args()

    # Check if config file exists
    config_paths = [
        'database_config.yaml',
        '../src/pudu/configs/database_config.yaml',
        'src/pudu/configs/database_config.yaml',
        'pudu/configs/database_config.yaml',
        '../configs/database_config.yaml'
    ]

    config_path = None
    for path in config_paths:
        if os.path.exists(path):
            config_path = path
            break
    if not config_path:
        raise FileNotFoundError("Configuration file not found")

    try:
        # Initialize S3 setup
        s3_setup = FixedS3BucketSetup(region=args.region)

        # Setup buckets
        bucket_mapping = s3_setup.setup_buckets_for_config(config_path, args.dry_run)

        if bucket_mapping:
            logger.info("=" * 60)
            logger.info("📋 S3 BUCKET SETUP SUMMARY")
            logger.info("=" * 60)

            for database_name, bucket_name in bucket_mapping.items():
                logger.info(f"🗄️  Database: {database_name}")
                logger.info(f"   Bucket: {bucket_name}")
                logger.info(f"   URL: https://{bucket_name}.s3.{args.region}.amazonaws.com/")
                logger.info("")

            # Generate config snippet
            config_snippet = s3_setup.generate_config_snippet(bucket_mapping)
            logger.info("📝 Configuration snippet for your application:")
            logger.info(config_snippet)

            # Save config to file
            with open('s3_bucket_config.yaml', 'w') as f:
                f.write(config_snippet)
            logger.info("💾 Saved configuration to s3_bucket_config.yaml")

        else:
            logger.warning("No buckets were created")

    except Exception as e:
        logger.error(f"💥 Error in S3 setup: {e}")
        return 1

    return 0

if __name__ == '__main__':
    exit(main())