#!/usr/bin/env python3
"""
Enhanced S3 Bucket Setup Script for Transform Service

This script creates S3 buckets for each transform-supported database/project
with auto-region detection and support for both us-east-1 and us-east-2.

Usage:
    python setup_s3_buckets.py [--region us-east-2] [--auto-region]
    python setup_s3_buckets.py --auto-region  # Auto-detect from config
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

class EnhancedS3BucketSetup:
    """Enhanced S3 setup with auto-region detection and multi-region support"""

    def __init__(self, region=None, auto_detect_region=False):
        self.bucket_prefix = "pudu-robot-transforms"

        # Auto-detect region from config if requested
        if auto_detect_region:
            self.region = self._detect_region_from_config()
            logger.info(f"🔍 Auto-detected region from config: {self.region}")
        else:
            self.region = region or 'us-east-2'

        # Create S3 client with detected/specified region
        self.s3_client = boto3.client('s3', region_name=self.region)

        # Test AWS connectivity first
        self._test_aws_connectivity()

    def _detect_region_from_config(self) -> str:
        """Auto-detect region from database_config.yaml or AWS credentials"""
        # First try to get from config file
        config_paths = [
            'src/pudu/configs/database_config.yaml',
            'database_config.yaml',
            '../src/pudu/configs/database_config.yaml',
            'pudu/configs/database_config.yaml',
            '../configs/database_config.yaml'
        ]

        for config_path in config_paths:
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as file:
                        config = yaml.safe_load(file)
                        detected_region = config.get('region', None)
                        if detected_region:
                            logger.info(f"📋 Found region in config at {config_path}: {detected_region}")
                            return detected_region
                except Exception as e:
                    logger.debug(f"Error reading {config_path}: {e}")
                    continue

        # Fallback: try to detect from AWS session
        try:
            session = boto3.Session()
            detected_region = session.region_name
            if detected_region:
                logger.info(f"🔍 Detected region from AWS session: {detected_region}")
                return detected_region
        except Exception as e:
            logger.debug(f"Could not detect region from AWS session: {e}")

        logger.warning("⚠️ Could not auto-detect region, defaulting to us-east-2")
        return 'us-east-2'

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

    def load_config(self, config_path: str = None) -> Dict:
        """Load database configuration with auto-discovery"""
        if config_path and os.path.exists(config_path):
            config_paths = [config_path]
        else:
            # Auto-discover config file
            config_paths = [
                'src/pudu/configs/database_config.yaml',
                'database_config.yaml',
                '../src/pudu/configs/database_config.yaml',
                'pudu/configs/database_config.yaml',
                '../configs/database_config.yaml'
            ]

        for path in config_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as file:
                        config = yaml.safe_load(file)
                        logger.info(f"📋 Loaded config from: {path}")
                        return config
                except yaml.YAMLError as e:
                    logger.error(f"Error parsing YAML configuration: {e}")
                    raise ValueError(f"Error parsing YAML configuration: {e}")

        raise FileNotFoundError("Configuration file not found in any expected location")

    def get_bucket_name(self, database_name: str) -> str:
        """
        Generate unique bucket name for a database

        Format: pudu-robot-transforms-{database_name}-{timestamp}-{region}
        Example: pudu-robot-transforms-foxx-irvine-office-123456-us-east-1
        """
        # Replace underscores with hyphens and ensure lowercase
        clean_db_name = database_name.lower().replace('_', '-')

        # Add timestamp for uniqueness
        timestamp = str(int(time.time()))[-6:]  # Last 6 digits

        return f"{self.bucket_prefix}-{clean_db_name}-{timestamp}-{self.region}"

    def create_bucket(self, bucket_name: str) -> bool:
        """Create S3 bucket with proper configuration for any region"""
        try:
            logger.info(f"Creating bucket: {bucket_name} in region: {self.region}")

            # Create bucket with region-specific configuration
            if self.region == 'us-east-1':
                # For us-east-1, do NOT include CreateBucketConfiguration
                self.s3_client.create_bucket(Bucket=bucket_name)
            else:
                # For all other regions, include CreateBucketConfiguration
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

    def setup_buckets_for_config(self, config_path: str = None, dry_run: bool = False) -> Dict[str, str]:
        """
        Setup S3 buckets for transform-supported databases with hardcoded region mappings

        Returns:
            Dict mapping database_name to bucket_name
        """
        # Hardcoded transform supported databases by region - no config file needed
        region_to_databases = {
            'us-east-1': ['foxx_irvine_office'],
            'us-east-2': ['university_of_florida']
        }

        supported_databases = region_to_databases.get(self.region, [])

        if not supported_databases:
            logger.warning(f"No transform_supported_databases defined for region {self.region}")
            logger.info(f"Supported regions: {list(region_to_databases.keys())}")
            return {}

        bucket_mapping = {}

        logger.info(f"Setting up S3 buckets for {len(supported_databases)} databases in {self.region}...")
        logger.info(f"Transform databases for {self.region}: {supported_databases}")

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

    def update_config_with_s3_settings(self, bucket_mapping: Dict[str, str], config_path: str = None):
        """Update or append s3_config in YAML while preserving formatting"""
        if not bucket_mapping:
            logger.warning("No bucket mapping to update config with")
            return

        # Find config file
        if config_path and os.path.exists(config_path):
            target_config = config_path
        else:
            config_paths = [
                'src/pudu/configs/database_config.yaml',
                'database_config.yaml'
            ]
            target_config = None
            for path in config_paths:
                if os.path.exists(path):
                    target_config = path
                    break

            if not target_config:
                logger.warning("Could not find config file, will create S3 config snippet file")
                self._create_s3_config_snippet(bucket_mapping)
                return

        try:
            # Read the file content
            with open(target_config, 'r') as file:
                content = file.read()

            # Create new s3_config content
            s3_config_content = f"""s3_config:
            region: "{self.region}"
            buckets:"""

            for database_name, bucket_name in bucket_mapping.items():
                s3_config_content += f'\n    {database_name}: "{bucket_name}"'

            if 's3_config:' in content:
                # s3_config exists - replace it using sed-like logic
                logger.info("Found existing s3_config, updating in place...")

                # Use regex to replace the entire s3_config section
                import re

                # Pattern to match s3_config section (including nested content)
                # This matches from 's3_config:' until the next top-level key or end of file
                pattern = r'^s3_config:.*?(?=^\w|\Z)'

                new_content = re.sub(
                    pattern,
                    s3_config_content,
                    content,
                    flags=re.MULTILINE | re.DOTALL
                )

                # Write back to file
                with open(target_config, 'w') as file:
                    file.write(new_content)

                logger.info(f"✅ Updated existing s3_config in {target_config} (preserving format)")

            else:
                # s3_config doesn't exist - append it
                logger.info("s3_config not found, appending to end of file...")

                with open(target_config, 'a') as file:
                    file.write(f"\n{s3_config_content}\n")

                logger.info(f"✅ Appended s3_config to {target_config}")

        except Exception as e:
            logger.error(f"❌ Error updating config file: {e}")
            self._create_s3_config_snippet(bucket_mapping)

    def _create_s3_config_snippet(self, bucket_mapping: Dict[str, str]):
        """Create a separate S3 config snippet file"""
        try:
            s3_config_path = f's3_config_{self.region}.yaml'
            s3_config_content = f"""# S3 Configuration for {self.region}
            # Add this to your main database_config.yaml file

            s3_config:
              region: "{self.region}"
              buckets:
            """
            for database_name, bucket_name in bucket_mapping.items():
                s3_config_content += f'    {database_name}: "{bucket_name}"\n'

            with open(s3_config_path, 'w') as file:
                file.write(s3_config_content)
            logger.info(f"✅ Created S3 config snippet file: {s3_config_path}")
            logger.info("💡 Please manually add the S3 config to your main database_config.yaml file")
        except Exception as fallback_error:
            logger.error(f"❌ S3 config snippet creation failed: {fallback_error}")

    def generate_config_snippet(self, bucket_mapping: Dict[str, str]) -> str:
        """Generate configuration snippet for the application"""
        config_snippet = f"""
        # S3 Configuration for {self.region}
        s3_config:
          region: "{self.region}"
          buckets:
        """

        for database_name, bucket_name in bucket_mapping.items():
            config_snippet += f'    {database_name}: "{bucket_name}"\n'

        config_snippet += f"""
        # Example URLs:
        # https://{list(bucket_mapping.values())[0] if bucket_mapping else 'bucket-name'}.s3.{self.region}.amazonaws.com/transformed-maps/map_name/content_hash.png
        """

        return config_snippet

def main():
    parser = argparse.ArgumentParser(description='Setup S3 buckets for transform service')
    parser.add_argument('--region', help='AWS region for buckets (if not specified, will auto-detect)')
    parser.add_argument('--auto-region', action='store_true', help='Auto-detect region from database config or AWS session')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be created without actually creating')

    args = parser.parse_args()

    try:
        # Initialize S3 setup with auto-detection if requested
        s3_setup = EnhancedS3BucketSetup(
            region=args.region,
            auto_detect_region=args.auto_region or (args.region is None)
        )

        logger.info(f"🔧 Using hardcoded transform database mappings for {s3_setup.region}")
        logger.info(f"   us-east-1 → foxx_irvine_office")
        logger.info(f"   us-east-2 → university_of_florida")

        # Setup buckets (no longer needs config file)
        bucket_mapping = s3_setup.setup_buckets_for_config(dry_run=args.dry_run)

        if bucket_mapping:
            logger.info("=" * 60)
            logger.info(f"📋 S3 BUCKET SETUP SUMMARY ({s3_setup.region})")
            logger.info("=" * 60)

            for database_name, bucket_name in bucket_mapping.items():
                logger.info(f"🗄️  Database: {database_name}")
                logger.info(f"   Bucket: {bucket_name}")
                logger.info(f"   URL: https://{bucket_name}.s3.{s3_setup.region}.amazonaws.com/")
                logger.info("")

            if not args.dry_run:
                # Update the config file if it exists
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

                s3_setup.update_config_with_s3_settings(bucket_mapping, config_path)

            # Generate config snippet for reference
            config_snippet = s3_setup.generate_config_snippet(bucket_mapping)
            logger.info("📝 S3 Configuration:")
            logger.info(config_snippet)

        else:
            logger.warning("No buckets were created")

        logger.info("🎯 Supported regions and their transform databases:")
        logger.info("   us-east-1: foxx_irvine_office")
        logger.info("   us-east-2: university_of_florida")

    except Exception as e:
        logger.error(f"💥 Error in S3 setup: {e}")
        return 1

    return 0

if __name__ == '__main__':
    exit(main())