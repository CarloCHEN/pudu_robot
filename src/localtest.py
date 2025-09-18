# disable pycache
import sys
sys.dont_write_bytecode = True

from pudu.apis.foxx_api import *
from pudu.apis.pudu_api import *
from pudu.app.main import App
from pudu.rds import RDSTable
from pudu.rds.utils import *
from pudu.notifications.change_detector import *
from pudu.reporting import *


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

# Example usage and testing function
if __name__ == "__main__":
    # Example configuration for testing comprehensive reports
    test_form_data = {
        'service': 'robot-management',
        'contentCategories': ['charging-performance', 'cleaning-performance', 'resource-utilization', 'financial-performance'],
        "location": {
            "country": "us",
            "state": "fl",
            "city": "gainesville"
        },
        'mainKey': '123',
        'outputFormat': 'pdf', # html, pdf
        'reportName': 'UF Report', # user provided report name
        'timeRange': 'custom', # last-30-days, last-7-days, last-3-days, custom
        'customStartDate': '2025-08-20',
        'customEndDate': '2025-09-09',
        'detailLevel': 'detailed', # overview, detailed, in-depth
        'delivery': 'in-app', # in-app ONLY
        'schedule': 'immediate' # immediate ONLY
    }

    config = ReportConfig(test_form_data, 'test-customer-123')

    # Generate comprehensive report
    generator = ReportGenerator(config_path=config_path, output_dir="reports")

    try:
        # Test HTML generation
        print(f"=== Testing {test_form_data['outputFormat']} Generation ===")
        html_result = generator.generate_and_save_report(config, save_file=True)
        if html_result['success']:
            print(f"{test_form_data['outputFormat']} report saved to: {html_result.get('saved_file_path')}")
        else:
            print(f"{test_form_data['outputFormat']} generation error: {html_result['error']}")

    except Exception as e:
        print(f"Error during testing: {e}")
    finally:
        generator.close()