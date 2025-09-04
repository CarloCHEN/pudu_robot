# src/pudu/reporting/api/reporting_api.py
from flask import Flask, request, jsonify
import logging
from datetime import datetime
import json
from typing import Dict, Any

# Import reporting components
from ..core.report_generator import ReportGenerator
from ..core.report_scheduler import ReportScheduler
from ..core.report_config import ReportConfig, ScheduleFrequency
from ..services.report_delivery_service import ReportDeliveryService

logger = logging.getLogger(__name__)

class ReportingAPI:
    """REST API for report management operations"""

    def __init__(self, config_path: str = "database_config.yaml"):
        self.app = Flask(__name__)
        self.config_path = config_path

        # Initialize services
        self.report_generator = ReportGenerator(config_path)
        self.report_scheduler = ReportScheduler()
        self.delivery_service = ReportDeliveryService()

        # Set up routes
        self._setup_routes()

        logger.info("Initialized ReportingAPI")

    def _setup_routes(self):
        """Set up Flask routes"""

        @self.app.route('/api/reports/generate', methods=['POST'])
        def generate_immediate_report():
            """Generate an immediate report"""
            try:
                data = request.get_json()
                customer_id = data.get('customer_id')
                form_data = data.get('form_data', {})

                if not customer_id:
                    return jsonify({
                        'success': False,
                        'error': 'customer_id is required'
                    }), 400

                # Force immediate generation
                form_data['schedule'] = 'immediate'

                # Create report configuration
                report_config = ReportConfig(form_data, customer_id)

                # Validate configuration
                validation_errors = report_config.validate()
                if validation_errors:
                    return jsonify({
                        'success': False,
                        'error': f"Validation failed: {', '.join(validation_errors)}"
                    }), 400

                # Generate report
                logger.info(f"Generating immediate report for customer {customer_id}")
                generation_result = self.report_generator.generate_report(report_config)

                if not generation_result['success']:
                    return jsonify({
                        'success': False,
                        'error': generation_result['error']
                    }), 500

                # Deliver report
                delivery_result = self.delivery_service.deliver_report(
                    generation_result['report_html'],
                    generation_result['metadata'],
                    report_config
                )

                return jsonify({
                    'success': True,
                    'message': 'Report generated successfully',
                    'generation_metadata': generation_result['metadata'],
                    'delivery_result': delivery_result
                })

            except Exception as e:
                logger.error(f"Error generating immediate report: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @self.app.route('/api/reports/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return jsonify({
                'success': True,
                'service': 'Robot Management Reporting API',
                'timestamp': datetime.now().isoformat(),
                'version': '1.0.0'
            })

        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({
                'success': False,
                'error': 'Endpoint not found'
            }), 404

        @self.app.errorhandler(500)
        def internal_error(error):
            return jsonify({
                'success': False,
                'error': 'Internal server error'
            }), 500

        @self.app.route('/api/reports/schedule', methods=['POST'])
        def create_scheduled_report():
            """Create or update a scheduled report"""
            try:
                data = request.get_json()
                customer_id = data.get('customer_id')
                form_data = data.get('form_data', {})

                if not customer_id:
                    return jsonify({
                        'success': False,
                        'error': 'customer_id is required'
                    }), 400

                # Create report configuration
                report_config = ReportConfig(form_data, customer_id)

                # Validate configuration
                validation_errors = report_config.validate()
                if validation_errors:
                    return jsonify({
                        'success': False,
                        'error': f"Validation failed: {', '.join(validation_errors)}"
                    }), 400

                # Check if it's actually a scheduled report
                if report_config.schedule == ScheduleFrequency.IMMEDIATE:
                    return jsonify({
                        'success': False,
                        'error': 'Use /generate endpoint for immediate reports'
                    }), 400

                # Create or update schedule
                logger.info(f"Creating scheduled report for customer {customer_id}")
                schedule_result = self.report_scheduler.create_or_update_schedule(customer_id, report_config)

                if schedule_result['success']:
                    return jsonify({
                        'success': True,
                        'message': schedule_result['message'],
                        'schedule_id': schedule_result['schedule_id'],
                        'next_run_time': schedule_result.get('next_run_time')
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': schedule_result['error']
                    }), 500

            except Exception as e:
                logger.error(f"Error creating scheduled report: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @self.app.route('/api/reports/schedules/<customer_id>', methods=['GET'])
        def get_customer_schedules(customer_id):
            """Get all schedules for a customer"""
            try:
                schedules = self.report_scheduler.get_customer_schedules(customer_id)
                return jsonify({
                    'success': True,
                    'schedules': schedules
                })

            except Exception as e:
                logger.error(f"Error getting customer schedules: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @self.app.route('/api/reports/schedules/<schedule_id>', methods=['DELETE'])
        def delete_schedule(schedule_id):
            """Delete a scheduled report"""
            try:
                customer_id = request.args.get('customer_id')
                if not customer_id:
                    return jsonify({
                        'success': False,
                        'error': 'customer_id parameter is required'
                    }), 400

                result = self.report_scheduler.delete_schedule(customer_id, schedule_id)

                if result['success']:
                    return jsonify(result)
                else:
                    return jsonify(result), 500

            except Exception as e:
                logger.error(f"Error deleting schedule: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @self.app.route('/api/reports/history/<customer_id>', methods=['GET'])
        def get_report_history(customer_id):
            """Get report history for a customer"""
            try:
                limit = request.args.get('limit', 50, type=int)
                reports = self.delivery_service.get_report_history(customer_id, limit)

                return jsonify({
                    'success': True,
                    'reports': reports,
                    'count': len(reports)
                })

            except Exception as e:
                logger.error(f"Error getting report history: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @self.app.route('/api/reports/delete', methods=['DELETE'])
        def delete_report():
            """Delete a stored report"""
            try:
                data = request.get_json()
                customer_id = data.get('customer_id')
                report_key = data.get('report_key')

                if not customer_id or not report_key:
                    return jsonify({
                        'success': False,
                        'error': 'customer_id and report_key are required'
                    }), 400

                result = self.delivery_service.delete_report(customer_id, report_key)

                if result['success']:
                    return jsonify(result)
                else:
                    return jsonify(result), 500

            except Exception as e:
                logger.error(f"Error deleting report: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @self.app.route('/api/reports/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return jsonify({
                'success': True,
                'service': 'Robot Management Reporting API',
                'timestamp': datetime.now().isoformat(),
                'version': '1.0.0'
            })

        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({
                'success': False,
                'error': 'Endpoint not found'
            }), 404

        @self.app.errorhandler(500)
        def internal_error(error):
            return jsonify({
                'success': False,
                'error': 'Internal server error'
            }), 500

    def run(self, host='0.0.0.0', port=5000, debug=False):
        """Run the Flask application"""
        logger.info(f"Starting ReportingAPI server on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)

    def get_app(self):
        """Get the Flask app instance for WSGI deployment"""
        return self.app

    def close(self):
        """Clean up resources"""
        try:
            self.report_generator.close()
            self.report_scheduler.close()
            logger.info("ReportingAPI resources cleaned up")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")

# Factory function for easy deployment
def create_app(config_path: str = "database_config.yaml"):
    """Create and configure Flask app"""
    api = ReportingAPI(config_path)
    return api.get_app()

# For running the API server directly
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Robot Management Reporting API')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--config', default='database_config.yaml', help='Database config path')

    args = parser.parse_args()

    # Initialize and run API
    api = ReportingAPI(args.config)

    try:
        api.run(host=args.host, port=args.port, debug=args.debug)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        api.close()