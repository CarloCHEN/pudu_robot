# disable pycache
import sys
sys.dont_write_bytecode = True

from pudu.reporting import *
import os

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
        'timeRange': 'custom',
        "location": {
            "country": "us",
            "state": "fl",
            "city": "gainesville"
        },
        'outputFormat': 'pdf',
        'reportName': 'UF Report',
        'customStartDate': '2025-08-01',
        'customEndDate': '2025-09-01',
        'detailLevel': 'in-depth',
        'delivery': 'in-app',
        'schedule': 'immediate'
    }

    config = ReportConfig(test_form_data, 'test-customer-123')

    # Generate comprehensive report
    generator = ReportGenerator(config, config_path=config_path, output_dir="reports")

    try:
        # Test HTML generation
        print(f"=== Testing {test_form_data['outputFormat']} Generation ===")
        html_result = generator.generate_and_save_report(save_file=True)
        if html_result['success']:
            print(f"{test_form_data['outputFormat']} report saved to: {html_result.get('saved_file_path')}")
        else:
            print(f"{test_form_data['outputFormat']} generation error: {html_result['error']}")

    except Exception as e:
        print(f"Error during testing: {e}")
    finally:
        generator.close()