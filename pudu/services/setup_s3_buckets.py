#!/usr/bin/env python3
"""
Simple S3 Bucket Setup Script - Actually Works

This script creates S3 buckets for project databases, checking for existing buckets first.
"""

import boto3
import yaml
import logging
import time
import os
import sys
from typing import List, Dict, Set

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from pudu.services.robot_database_resolver import RobotDatabaseResolver

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config():
    """Load database config"""
    config_paths = [
        'src/pudu/configs/database_config.yaml',
        'database_config.yaml',
        '../configs/database_config.yaml'
    ]

    for path in config_paths:
        if os.path.exists(path):
            with open(path, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(f"Loaded config from: {path}")
                return config

    raise FileNotFoundError("Could not find database_config.yaml")

def get_existing_transform_buckets(s3_client, region):
    """Get existing pudu transform buckets and extract database names"""
    try:
        response = s3_client.list_buckets()
        existing_db_buckets = {}

        for bucket in response['Buckets']:
            bucket_name = bucket['Name']

            # Check if it's a pudu transform bucket in our region
            if (bucket_name.startswith('pudu-robot-transforms-') and
                bucket_name.endswith(f'-{region}')):

                logger.info(f"Found existing bucket: {bucket_name}")

                # Extract database name: everything between 'pudu-robot-transforms-' and the last timestamp-region part
                # Example: pudu-robot-transforms-university-of-florida-889717-us-east-2
                prefix = 'pudu-robot-transforms-'
                suffix = f'-{region}'

                # Remove prefix and suffix
                middle = bucket_name[len(prefix):]
                middle = middle[:middle.rfind(suffix)]

                # Remove timestamp (last 6 digits if present)
                parts = middle.split('-')
                if parts and parts[-1].isdigit() and len(parts[-1]) == 6:
                    parts = parts[:-1]

                db_name = '-'.join(parts)
                existing_db_buckets[db_name] = bucket_name
                logger.info(f"  -> Database: {db_name}")

        return existing_db_buckets

    except Exception as e:
        logger.error(f"Error listing buckets: {e}")
        return {}

def normalize_db_name(db_name):
    """Convert database name to bucket-friendly format"""
    return db_name.lower().replace('_', '-')

def create_bucket_with_confirmation(s3_client, bucket_name, region, database_name):
    """Create S3 bucket with user confirmation"""
    print(f"\n{'='*60}")
    print(f"READY TO CREATE BUCKET")
    print(f"{'='*60}")
    print(f"Database: {database_name}")
    print(f"Bucket name: {bucket_name}")
    print(f"Region: {region}")
    print(f"ARN: arn:aws:s3:::{bucket_name}")
    print(f"URL: https://{bucket_name}.s3.{region}.amazonaws.com/")
    print(f"{'='*60}")

    while True:
        response = input("Do you want to create this bucket? (y/n/skip): ").strip().lower()

        if response == 'y' or response == 'yes':
            try:
                if region == 'us-east-1':
                    s3_client.create_bucket(Bucket=bucket_name)
                else:
                    s3_client.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': region}
                    )

                # Set basic public access policy
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": "s3:GetObject",
                        "Resource": f"arn:aws:s3:::{bucket_name}/transformed-maps/*"
                    }]
                }

                s3_client.put_bucket_policy(Bucket=bucket_name, Policy=str(policy).replace("'", '"'))
                logger.info(f"✅ Successfully created bucket: {bucket_name}")
                return True

            except Exception as e:
                logger.error(f"❌ Error creating bucket {bucket_name}: {e}")
                return False

        elif response == 'n' or response == 'no':
            logger.info(f"⏭️ Skipped creating bucket for {database_name}")
            return False

        elif response == 'skip':
            logger.info(f"⏭️ Skipped creating bucket for {database_name}")
            return False

        else:
            print("Please enter 'y' for yes, 'n' for no, or 'skip' to skip this bucket")

def create_bucket(s3_client, bucket_name, region):
    """Create S3 bucket"""
    try:
        if region == 'us-east-1':
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )

        # Set basic public access policy
        policy = {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket_name}/transformed-maps/*"
            }]
        }

        s3_client.put_bucket_policy(Bucket=bucket_name, Policy=str(policy).replace("'", '"'))
        logger.info(f"Created bucket: {bucket_name}")
        return True

    except Exception as e:
        logger.error(f"Error creating bucket {bucket_name}: {e}")
        return False

def main():
    # Load config
    config = load_config()
    region = config.get('region', 'us-east-2')
    main_db = config.get('main_database', 'ry-vue')

    # Setup AWS
    s3_client = boto3.client('s3', region_name=region)

    # Get project databases
    resolver = RobotDatabaseResolver(main_db)
    project_databases = resolver.get_all_project_databases()
    logger.info(f"Found {len(project_databases)} project databases: {project_databases}")

    # Get existing buckets
    existing_buckets = get_existing_transform_buckets(s3_client, region)
    logger.info(f"Existing buckets: {existing_buckets}")

    # Create buckets for databases that don't have them
    created_buckets = {}
    skipped_buckets = []

    print(f"\n🔍 ANALYSIS COMPLETE")
    print(f"📊 Found {len(project_databases)} project databases")
    print(f"🏪 Found {len(existing_buckets)} existing buckets")

    databases_needing_buckets = []
    for db in project_databases:
        normalized_db = normalize_db_name(db)
        if normalized_db not in existing_buckets:
            databases_needing_buckets.append((db, normalized_db))

    if not databases_needing_buckets:
        print("✅ All databases already have buckets!")
        print("\nEXISTING BUCKETS:")
        for db in project_databases:
            normalized_db = normalize_db_name(db)
            if normalized_db in existing_buckets:
                print(f"  {db} -> {existing_buckets[normalized_db]}")
    else:
        print(f"\n🏗️ Need to create buckets for {len(databases_needing_buckets)} databases:")
        for db, normalized_db in databases_needing_buckets:
            print(f"  {db} -> {normalized_db}")

        print(f"\nEXISTING BUCKETS (will be skipped):")
        for db in project_databases:
            normalized_db = normalize_db_name(db)
            if normalized_db in existing_buckets:
                print(f"  ✓ {db} -> {existing_buckets[normalized_db]}")
                created_buckets[normalized_db] = existing_buckets[normalized_db]

    # Ask for confirmation before creating each new bucket
    for db, normalized_db in databases_needing_buckets:
        timestamp = str(int(time.time()))[-6:]
        bucket_name = f"pudu-robot-transforms-{normalized_db}-{timestamp}-{region}"

        if create_bucket_with_confirmation(s3_client, bucket_name, region, db):
            created_buckets[normalized_db] = bucket_name
        else:
            skipped_buckets.append(db)

    # Print summary
    print("\n" + "="*60)
    print(f"S3 BUCKET SETUP SUMMARY")
    print("="*60)
    print(f"Region: {region}")
    print(f"Total databases: {len(project_databases)}")
    print(f"Existing buckets: {len([k for k, v in created_buckets.items() if k in existing_buckets])}")
    print(f"Newly created: {len([k for k, v in created_buckets.items() if k not in existing_buckets])}")
    if skipped_buckets:
        print(f"Skipped: {len(skipped_buckets)}")
    print()

    if created_buckets:
        print("ALL BUCKETS:")
        for db_name, bucket_name in created_buckets.items():
            arn = f"arn:aws:s3:::{bucket_name}"
            url = f"https://{bucket_name}.s3.{region}.amazonaws.com/"
            status = "EXISTING" if db_name in existing_buckets else "NEWLY CREATED"
            print(f"Database: {db_name} [{status}]")
            print(f"  Bucket: {bucket_name}")
            print(f"  ARN: {arn}")
            print(f"  URL: {url}")
            print()

    if skipped_buckets:
        print("SKIPPED DATABASES:")
        for db in skipped_buckets:
            print(f"  {db}")

    resolver.close()

if __name__ == '__main__':
    main()