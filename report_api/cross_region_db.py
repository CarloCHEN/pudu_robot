# Wrapper for cross-region database access without modifying rds codebase

import os
import subprocess
import shutil
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

class CrossRegionDBManager:
    """Manages cross-region database connections by temporarily switching credentials"""
    def _get_credentials_path(self):
        """Detect correct credentials path for current environment"""
        current_dir = os.path.dirname(os.path.abspath(__file__))

        possible_paths = [
            'pudu/rds/credentials.yaml',  # Docker
            '../src/pudu/rds/credentials.yaml',  # Local from report_api
            'src/pudu/rds/credentials.yaml',  # Local from root
        ]

        for path in possible_paths:
            full_path = os.path.join(current_dir, path)
            if os.path.exists(os.path.dirname(full_path)):
                return path

        raise Exception("Cannot find pudu/rds directory")

    @contextmanager
    def region_context(self, target_region: str):
        """
        Context manager that temporarily switches to target region credentials
        Uses existing setup-environment.sh script
        """
        if not target_region:
            # Same region, no need to switch
            yield
            return

        backup_files = []
        try:
            # Backup current files
            current_dir = os.path.dirname(os.path.abspath(__file__))

            files_to_backup = [
                '.env',
                'app.env',
                '../pudu/rds/credentials.yaml',
                'credentials.yaml'
                'pudu/rds/credentials.yaml'
            ]

            for file_path in files_to_backup:
                full_path = os.path.join(current_dir, file_path)
                if os.path.exists(full_path):
                    backup_path = full_path + '.backup'
                    shutil.copy2(full_path, backup_path)
                    backup_files.append((full_path, backup_path))

            # Switch to target region using existing script
            setup_script = os.path.join(current_dir, 'setup-environment.sh')
            if os.path.exists(setup_script):
                logger.info(f"🔄 Temporarily switching to region: {target_region}")
                result = subprocess.run([
                    'bash', setup_script, target_region
                ], capture_output=True, text=True, cwd=current_dir)

                if result.returncode != 0:
                    logger.error(f"Script stderr: {result.stderr}")
                    logger.error(f"Script stdout: {result.stdout}")
                    logger.error(f"Return code: {result.returncode}")
                    raise Exception(f"Failed to switch to region {target_region}: {result.stderr}")

                # PRINT CREDENTIALS AFTER SWITCH
                credentials_path = self._get_credentials_path()
                full_path = os.path.join(current_dir, credentials_path)
                if os.path.exists(full_path):
                    logger.info(f"📄 Contents of {full_path} after region switch:")
                    try:
                        with open(full_path, 'r') as f:
                            credentials_content = f.read()
                            logger.info(f"CREDENTIALS CONTENT:\n{credentials_content}")
                    except Exception as e:
                        logger.error(f"Could not read credentials file: {e}")
                else:
                    logger.error(f"Credentials file not found at: {full_path}")

            else:
                logger.error(f"Setup script not found at: {setup_script}")
                raise Exception(f"Setup script not found at: {setup_script}")
            yield  # Execute the database operations

        finally:
            # Restore all backup files
            for original_path, backup_path in backup_files:
                if os.path.exists(backup_path):
                    shutil.move(backup_path, original_path)
                    logger.debug(f"🔙 Restored {original_path}")

def determine_region_from_request(database_name: str) -> str:
    """
    Determine target region from database name
    """
    # You can create a simple mapping file or use environment variables
    database_name_region_map = {
        "foxx_irvine_office": "us-east-1",
        "university_of_florida": "us-east-2"
    }

    if database_name in database_name_region_map:
        return database_name_region_map[database_name]

    return os.getenv('AWS_REGION', 'us-east-1')
