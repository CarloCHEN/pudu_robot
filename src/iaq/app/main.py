#!/usr/bin/env python3
"""
Modular IAQ Processing System
=============================

A well-structured system for processing IoT sensor data from Kafka and calculating
Indoor Air Quality (IAQ) scores using environmental monitors.

Structure:
1. Configuration & Setup
2. Database & Sensor Management
3. Kafka Connection Management
4. Raw Sensor Data Ingestion
5. Data Processing & Aggregation
6. IAQ Score Calculation
7. Results Display & Output
8. Main Application Controller
"""

import json
import time
import threading
import logging
import pandas as pd
import os
from kafka import KafkaConsumer, KafkaProducer
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Optional, Any
import sys

# Add paths for custom modules
sys.path.append('src')
sys.path.append('/home/ec2-user/iaq_score/src')

from iaq.rds.rdsTable import RDSTable
from iaq.model import AirQualityCalculator
from iaq.data import EnvironmentalMonitor

# Set AWS region for MSK authentication
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
os.environ['AWS_REGION'] = 'us-east-1'


# =============================================================================
# 1. CONFIGURATION & SETUP
# =============================================================================

class IAQConfig:
    """Configuration management for the IAQ processing system."""

    def __init__(self):
        self.kafka_bootstrap_servers = [
            'b-2.msktest.6xni82.c13.kafka.us-east-1.amazonaws.com:9098',
            'b-1.msktest.6xni82.c13.kafka.us-east-1.amazonaws.com:9098'
        ]

        self.database_name = "ry-vue"
        self.credentials_file = "credentials.yaml"

        # Supported sensor types and their Kafka topics
        self.supported_sensor_types = ['am319', 'em500co2']

        # Processing configuration
        self.window_size_minutes = 5
        self.processing_interval_seconds = 60
        self.max_readings_per_location = 1000

        # Kafka configuration
        self.kafka_config = {
            'bootstrap_servers': self.kafka_bootstrap_servers,
            'security_protocol': 'SASL_SSL',
            'sasl_mechanism': 'AWS_MSK_IAM',
        }

        self.consumer_config = {
            **self.kafka_config,
            'auto_offset_reset': 'latest',
            'enable_auto_commit': True,
        }

    @staticmethod
    def setup_logging():
        """Configure logging for the application."""
        # Suppress noisy loggers
        logging.getLogger('kafka').setLevel(logging.ERROR)
        logging.getLogger('botocore').setLevel(logging.ERROR)

        logging.basicConfig(
            level=logging.WARNING,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)


# =============================================================================
# 2. DATABASE & SENSOR MANAGEMENT
# =============================================================================

class SensorManager:
    """Manages sensor metadata and location mappings from the database."""

    def __init__(self, config: IAQConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.sensor_info_table = None

        # Sensor mapping data structures
        self.sensor_locations = {}  # sensor_id -> location info
        self.location_sensors = {}  # location_key -> sensor info
        self.sensor_types = set()   # Available sensor types

        self._initialize_database()
        self._load_sensor_mappings()

    def _initialize_database(self):
        """Initialize database connection."""
        try:
            self.sensor_info_table = RDSTable(
                connection_config=self.config.credentials_file,
                database_name=self.config.database_name,
                table_name="pro_sensor_info",
                fields=['sensor_id', 'sensor_type', 'project_id', 'building_id', 'floor', 'zone'],
                primary_keys=['sensor_id']
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise

    def _load_sensor_mappings(self):
        """Load sensor to location mappings from RDS."""
        try:
            query = """
                SELECT sensor_id, sensor_type, project_id, building_id, floor, zone
                FROM pro_sensor_info
                WHERE sensor_id IS NOT NULL AND sensor_type IS NOT NULL AND zone IS NOT NULL
                ORDER BY project_id, building_id, floor, zone, sensor_type
            """

            sensors_df = self.sensor_info_table.query_data_as_df(query)
            if sensors_df.empty:
                self.logger.warning("No sensor data found in database")
                return

            self._process_sensor_mappings(sensors_df)

        except Exception as e:
            self.logger.error(f"Error loading sensor mappings: {e}")
            raise

    def _process_sensor_mappings(self, sensors_df: pd.DataFrame):
        """Process sensor mappings from DataFrame."""
        for _, sensor in sensors_df.iterrows():
            sensor_id = sensor['sensor_id']
            sensor_type = sensor['sensor_type']
            location_key = f"{sensor['project_id']}_{sensor['building_id']}_{sensor['floor']}_{sensor['zone']}"

            # Store sensor location mapping
            self.sensor_locations[sensor_id] = {
                'location_key': location_key,
                'project_id': sensor['project_id'],
                'building_id': sensor['building_id'],
                'floor': sensor['floor'],
                'zone': sensor['zone'],
                'sensor_type': sensor_type
            }

            # Group sensors by location
            if location_key not in self.location_sensors:
                self.location_sensors[location_key] = {
                    'project_id': sensor['project_id'],
                    'building_id': sensor['building_id'],
                    'floor': sensor['floor'],
                    'zone': sensor['zone'],
                    'sensors': defaultdict(list),
                    'space_type': self._determine_space_type(sensor['zone'])
                }

            self.location_sensors[location_key]['sensors'][sensor_type].append(sensor_id)
            self.sensor_types.add(sensor_type)

    def _determine_space_type(self, zone_name: str) -> str:
        """Determine space type from zone name for IAQ scoring."""
        zone_lower = zone_name.lower()
        return "Conference/Meeting Rooms"

        if any(keyword in zone_lower for keyword in ['office', 'cubicle', 'desk', 'work']):
            return "office"
        elif any(keyword in zone_lower for keyword in ['conference', 'meeting', 'boardroom']):
            return "conference"
        elif any(keyword in zone_lower for keyword in ['restroom', 'bathroom', 'toilet']):
            return "restroom"
        elif any(keyword in zone_lower for keyword in ['corridor', 'hallway', 'circulation']):
            return "circulation"
        elif any(keyword in zone_lower for keyword in ['cafeteria', 'dining', 'kitchen', 'cafe']):
            return "cafeteria"
        else:
            return "office"  # Default

    def get_sensor_location_info(self, sensor_id: str) -> Optional[Dict]:
        """Get location information for a sensor."""
        return self.sensor_locations.get(sensor_id)

    def get_location_info(self, location_key: str) -> Optional[Dict]:
        """Get information for a location."""
        return self.location_sensors.get(location_key)

    def get_supported_sensor_types(self) -> List[str]:
        """Get list of sensor types that are both in DB and supported."""
        return [st for st in self.config.supported_sensor_types if st in self.sensor_types]

    def close(self):
        """Close database connections."""
        if self.sensor_info_table:
            self.sensor_info_table.close()


# =============================================================================
# 3. KAFKA CONNECTION MANAGEMENT
# =============================================================================

class KafkaManager:
    """Manages Kafka producers and consumers."""

    def __init__(self, config: IAQConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.consumers = {}
        self.producer = None

        self._initialize_producer()

    def _initialize_producer(self):
        """Initialize Kafka producer."""
        try:
            self.producer = KafkaProducer(
                value_serializer=lambda x: json.dumps(x, default=str).encode('utf-8'),
                **self.config.kafka_config
            )
        except Exception as e:
            self.logger.warning(f"Failed to create producer: {e}")
            self.producer = None

    def create_consumer(self, sensor_type: str) -> Optional[KafkaConsumer]:
        """Create a Kafka consumer for a specific sensor type."""
        try:
            consumer = KafkaConsumer(
                sensor_type,
                group_id=f'iaq-processor-{sensor_type}',
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                **self.config.consumer_config
            )
            self.consumers[sensor_type] = consumer
            return consumer
        except Exception as e:
            self.logger.error(f"Error creating consumer for {sensor_type}: {e}")
            return None

    def publish_result(self, topic: str, data: Dict):
        """Publish results to a Kafka topic.
        It creates a data feedback loop where the calculated IAQ scores become available as data in the MSK cluster,
        just like the original sensor data.
        """
        if self.producer:
            try:
                self.producer.send(topic, data)
            except Exception as e:
                self.logger.error(f"Error publishing to {topic}: {e}")

    def close(self):
        """Close all Kafka connections."""
        for consumer in self.consumers.values():
            try:
                consumer.close()
            except Exception:
                pass

        if self.producer:
            try:
                self.producer.flush()
                self.producer.close()
            except Exception:
                pass


# =============================================================================
# 4. RAW SENSOR DATA INGESTION
# =============================================================================

class SensorDataIngestion:
    """Handles raw sensor data ingestion from Kafka."""

    def __init__(self, config: IAQConfig, sensor_manager: SensorManager,
                 kafka_manager: KafkaManager, logger: logging.Logger):
        self.config = config
        self.sensor_manager = sensor_manager
        self.kafka_manager = kafka_manager
        self.logger = logger

        # Consumer threads
        self.consumer_threads = {}
        self.running = True

        # Statistics
        self.stats = {
            'messages_processed': 0,
            'last_message_time': None,
            'locations_with_data': set()
        }

        # Callback for processed messages
        self.message_callback = None

    def set_message_callback(self, callback):
        """Set callback function for processed messages."""
        self.message_callback = callback

    def start_ingestion(self):
        """Start ingestion for all supported sensor types."""
        supported_types = self.sensor_manager.get_supported_sensor_types()

        for sensor_type in supported_types:
            consumer = self.kafka_manager.create_consumer(sensor_type)
            if consumer:
                thread = threading.Thread(
                    target=self._consume_sensor_type,
                    args=(sensor_type, consumer),
                    name=f"Consumer-{sensor_type}",
                    daemon=True
                )
                self.consumer_threads[sensor_type] = thread
                thread.start() # start the thread to consume the data from the kafka topic

    def _consume_sensor_type(self, sensor_type: str, consumer: KafkaConsumer):
        """Consumer thread for a specific sensor type."""
        try:
            for message in consumer:
                if not self.running:
                    break
                try:
                    self._process_raw_message(sensor_type, message.value)
                except Exception as e:
                    self.logger.error(f"Error processing {sensor_type} message: {e}")

        except Exception as e:
            self.logger.error(f"Error in {sensor_type} consumer thread: {e}")

    def _process_raw_message(self, sensor_type: str, sensor_reading: Dict):
        """Process a single raw sensor message."""
        # Extract sensor ID
        sensor_id = sensor_reading.get('devEUI') or sensor_reading.get('sensor_id')
        if not sensor_id:
            return

        # Update statistics
        self.stats['messages_processed'] += 1
        self.stats['last_message_time'] = datetime.now()

        # Get location info
        location_info = self.sensor_manager.get_sensor_location_info(sensor_id)
        if not location_info:
            return

        # Enrich message with location data
        enriched_message = self._enrich_message(sensor_reading, sensor_type, location_info)

        # Track locations with data
        self.stats['locations_with_data'].add(location_info['location_key'])

        # Call back to data processor
        if self.message_callback:
            self.message_callback(enriched_message)

    def _enrich_message(self, sensor_reading: Dict, sensor_type: str, location_info: Dict) -> Dict:
        """Enrich sensor data with location and metadata."""
        enriched = sensor_reading.copy()
        enriched.update({
            'sensor_type': sensor_type,
            'processing_time': datetime.now(),
            **location_info
        })
        return enriched

    def stop_ingestion(self):
        """Stop all ingestion threads."""
        self.running = False
        for thread in self.consumer_threads.values():
            thread.join(timeout=5) # Wait for processing thread to finish (max 5 seconds)


# =============================================================================
# 5. DATA PROCESSING & AGGREGATION
# =============================================================================

class DataProcessor:
    """Processes and aggregates sensor data using EnvironmentalMonitor."""

    def __init__(self, config: IAQConfig, sensor_manager: SensorManager, logger: logging.Logger):
        self.config = config
        self.sensor_manager = sensor_manager
        self.logger = logger

        # Environmental monitors for each location
        self.environmental_monitors = {}  # location_key -> EnvironmentalMonitor

        # Initialize monitors for all locations
        self._initialize_monitors()

    def _initialize_monitors(self):
        """Initialize EnvironmentalMonitor for each location."""
        for location_key, location_info in self.sensor_manager.location_sensors.items():
            monitor = EnvironmentalMonitor(
                monitor_id=location_key,
                location=location_info['zone'],
                space_type=location_info['space_type']
            )
            self.environmental_monitors[location_key] = monitor

        self.logger.warning(f"Initialized {len(self.environmental_monitors)} environmental monitors")

    def process_enriched_message(self, enriched_message: Dict):
        """Process an enriched sensor message."""
        location_key = enriched_message['location_key']
        monitor = self.environmental_monitors.get(location_key)

        if not monitor:
            return

        # Extract timestamp
        timestamp = self._extract_timestamp(enriched_message)

        # Map sensor parameters to standard format
        standard_params = self._map_sensor_parameters(enriched_message)

        if standard_params:
            # Add reading to environmental monitor
            monitor.add_reading(timestamp, standard_params)

    def _extract_timestamp(self, enriched_message: Dict) -> datetime:
        """Extract timestamp from enriched message."""
        timestamp_fields = ['timestamp', 'ts', 'time', 'datetime', 'processing_time']

        for field in timestamp_fields:
            if field in enriched_message:
                ts_value = enriched_message[field]
                if isinstance(ts_value, datetime):
                    return ts_value
                elif isinstance(ts_value, str):
                    try:
                        return pd.to_datetime(ts_value)
                    except:
                        continue
                elif isinstance(ts_value, (int, float)):
                    try:
                        if ts_value > 1e12:  # Milliseconds
                            return datetime.fromtimestamp(ts_value / 1000)
                        else:  # Seconds
                            return datetime.fromtimestamp(ts_value)
                    except:
                        continue

        return datetime.now()

    def _map_sensor_parameters(self, enriched_message: Dict) -> Dict[str, float]:
        """Map sensor parameters to standard IAQ parameter names."""
        param_mapping = {
            'pm25': 'PM2.5', 'pm2_5': 'PM2.5', 'pm2.5': 'PM2.5',
            'pm10': 'PM10',
            'co2': 'CO2',
            'tvoc': 'tVOC', 'voc': 'tVOC',
            'temperature': 'Temperature', 'temp': 'Temperature',
            'humidity': 'Humidity', 'rh': 'Humidity',
            'formaldehyde': 'HCHO', 'hcho': 'HCHO',
            'ozone': 'O3', 'o3': 'O3',
            'nh3': 'NH3', 'ammonia': 'NH3',
            'h2s': 'H2S'
        }

        standard_params = {}
        exclude_fields = {
            'sensor_id', 'location_key', 'project_id', 'building_id',
            'floor', 'zone', 'sensor_type', 'processing_time', 'timestamp',
            'devEUI', 'time', 'ts', 'datetime'
        }

        for key, value in enriched_message.items():
            if key in exclude_fields or not isinstance(value, (int, float)):
                continue

            key_lower = key.lower().replace('_', '').replace('-', '')

            if key_lower in param_mapping:
                standard_name = param_mapping[key_lower]
                standard_params[standard_name] = float(value)
            elif key in ['PM2.5', 'PM10', 'CO2', 'Temperature', 'Humidity', 'tVOC', 'HCHO', 'O3', 'NH3', 'H2S']:
                standard_params[key] = float(value)

        return standard_params

    def get_location_current_data(self, location_key: str) -> Optional[Dict]:
        """Get current aggregated data for a location."""
        monitor = self.environmental_monitors.get(location_key)
        if not monitor or monitor.data is None:
            return None

        # Filter data to only include readings within the time window
        cutoff_time = datetime.now() - timedelta(minutes=self.config.window_size_minutes)
        recent_data = monitor.data[monitor.data['time'] >= cutoff_time]

        if recent_data.empty:
            return None

        # Calculate mean values for each parameter within the window
        parameters = {}
        for param in monitor.get_available_parameters():
            if param in recent_data.columns:
                param_values = recent_data[param].dropna()
                if not param_values.empty:
                    parameters[param] = float(param_values.mean())

        if not parameters:
            return None

        return {
            'location_key': location_key,
            'parameters': parameters,
            'timestamp': recent_data['time'].max(),
            'available_parameters': monitor.get_available_parameters(),
            'missing_parameters': monitor.get_missing_parameters(),
            'window_size_minutes': self.config.window_size_minutes,
            'readings_count': len(recent_data),
            'time_range': {
                'start': recent_data['time'].min(),
                'end': recent_data['time'].max()
            }
        }

    def get_all_locations_data(self) -> Dict[str, Dict]:
        """Get current data for all locations with recent readings."""
        location_data = {}

        for location_key in self.environmental_monitors.keys():
            data = self.get_location_current_data(location_key)
            if data:
                location_data[location_key] = data

        return location_data


# =============================================================================
# 6. IAQ SCORE CALCULATION
# =============================================================================

class IAQCalculator:
    """Handles IAQ score calculations using the AirQualityCalculator."""

    def __init__(self, sensor_manager: SensorManager, logger: logging.Logger):
        self.sensor_manager = sensor_manager
        self.logger = logger
        self.iaq_calculator = AirQualityCalculator()

    def calculate_location_score(self, location_key: str, location_data: Dict) -> Optional[Dict]:
        """Calculate IAQ score for a single location."""
        try:
            location_info = self.sensor_manager.get_location_info(location_key)
            if not location_info:
                return None

            space_type = location_info['space_type']
            parameters = location_data['parameters']

            iaq_space_type = self._map_space_type(space_type)

            zone_name = f"{location_info['zone']}"

            self.iaq_calculator.add_zone(zone_name, iaq_space_type, parameters)

            zone = next((z for z in self.iaq_calculator.zones if z.name == zone_name), None)
            if zone:
                score = self.iaq_calculator.calculate_zone_score(zone)

                self.iaq_calculator.zones = [z for z in self.iaq_calculator.zones if z.name != zone_name]

                return {
                    'location_key': location_key,
                    'score': score,
                    'status': self._get_score_status(score),
                    'space_type': space_type,
                    'iaq_space_type': iaq_space_type,
                    'parameters': parameters,
                    'timestamp': location_data['timestamp'],
                    'available_parameters': location_data['available_parameters'],
                    'missing_parameters': location_data['missing_parameters']
                }

        except Exception as e:
            self.logger.error(f"Error calculating score for {location_key}: {e}")

        return None

    def _map_space_type(self, space_type: str) -> str:
        """Map internal space type to IAQ calculator space type."""
        mapping = {
            'office': 'Office/Cubicle',
            'conference': 'Conference/Meeting Rooms',
            'restroom': 'Restrooms',
            'circulation': 'Corridors/Common Areas',
            'cafeteria': 'Cafeteria/Dining Area'
        }
        return mapping.get(space_type, 'Conference/Meeting Rooms')

    def _get_score_status(self, score: float) -> str:
        """Get status string from score."""
        if score >= 90:
            return "Excellent"
        elif score >= 80:
            return "Good"
        elif score >= 60:
            return "Moderate"
        elif score >= 40:
            return "Poor"
        else:
            return "Very Poor"

    def calculate_all_scores(self, locations_data: Dict) -> Dict[str, Dict]:
        """Calculate IAQ scores for all locations."""
        scores = {}

        for location_key, location_data in locations_data.items():
            score_result = self.calculate_location_score(location_key, location_data)
            if score_result:
                scores[location_key] = score_result

        return scores


# =============================================================================
# 7. RESULTS DISPLAY & OUTPUT
# =============================================================================

class ResultsDisplay:
    """Handles display and output of IAQ results."""

    def __init__(self, sensor_manager: SensorManager, kafka_manager: KafkaManager,
                 logger: logging.Logger):
        self.sensor_manager = sensor_manager
        self.kafka_manager = kafka_manager
        self.logger = logger

    def display_monitoring_status(self, stats: Dict):
        """Display brief monitoring status."""
        current_time = datetime.now().strftime('%H:%M:%S')
        total_messages = stats['messages_processed']
        print(f"\r[{current_time}] Monitoring... ({total_messages} messages processed)", end='', flush=True)

    def display_full_report(self, scores: Dict, stats: Dict):
        """Display comprehensive IAQ report."""
        if not scores:
            self.display_monitoring_status(stats)
            return

        print("\r" + " " * 80 + "\r", end='')

        print(f"\n{'='*80}")
        print(f"🏢 IAQ MONITORING REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")

        self._display_summary(scores, stats)
        self._display_location_scores(scores)
        self._display_detailed_analysis(scores)

        print(f"{'='*80}\n")

    def _display_summary(self, scores: Dict, stats: Dict):
        """Display summary statistics."""
        score_values = [data['score'] for data in scores.values()]
        avg_score = sum(score_values) / len(score_values) if score_values else 0

        print(f"📊 SUMMARY:")
        print(f"   • Locations monitored: {len(scores)}")
        print(f"   • Average building score: {avg_score:.1f} ({self._get_score_status(avg_score)})")
        print(f"   • Messages processed: {stats['messages_processed']}")
        last_time = stats['last_message_time']
        print(f"   • Last data: {last_time.strftime('%H:%M:%S') if last_time else 'None'}")

    def _display_location_scores(self, scores: Dict):
        """Display location scores table."""
        print(f"\n🎯 LOCATION SCORES:")
        print(f"{'Location':<35} {'Score':<8} {'Status':<12} {'Parameters':<12} {'Key Issues'}")
        print("-" * 80)

        sorted_scores = sorted(scores.items(), key=lambda x: x[1]['score'])

        for location_key, score_data in sorted_scores:
            location_info = self.sensor_manager.get_location_info(location_key)
            zone_name = location_info['zone'][:30]
            score = score_data['score']
            status = score_data['status']
            param_count = len(score_data['available_parameters'])

            issues = self._identify_issues(score_data['parameters'])
            issues_str = ", ".join(issues[:2]) if issues else "None"

            status_emoji = {
                "Excellent": "🟢", "Good": "🟡", "Moderate": "🟠",
                "Poor": "🔴", "Very Poor": "⚫"
            }
            emoji = status_emoji.get(status, "⚪")

            print(f"{emoji} {zone_name:<32} {score:6.1f}   {status:<12} {param_count:<12} {issues_str}")

    def _display_detailed_analysis(self, scores: Dict):
        """Display detailed analysis for problematic locations."""
        poor_locations = [(k, v) for k, v in scores.items() if v['score'] < 80]

        if not poor_locations:
            return

        worst_location_key, worst_data = min(poor_locations, key=lambda x: x[1]['score'])
        location_info = self.sensor_manager.get_location_info(worst_location_key)

        print(f"\n⚠️  DETAILED ANALYSIS - {location_info['zone']}:")
        print(f"   Space Type: {worst_data['space_type']} → {worst_data['iaq_space_type']}")
        print(f"   Score: {worst_data['score']:.1f} ({worst_data['status']})")
        print(f"   Available Parameters: {', '.join(worst_data['available_parameters'])}")

        if worst_data['missing_parameters']:
            print(f"   Missing Parameters: {', '.join(worst_data['missing_parameters'])}")

        # Show window information if available
        if 'window_size_minutes' in worst_data:
            print(f"   Time Window: {worst_data['window_size_minutes']} minutes")
            print(f"   Readings in Window: {worst_data.get('readings_count', 'N/A')}")
            if 'time_range' in worst_data:
                time_range = worst_data['time_range']
                start_time = time_range['start'].strftime('%H:%M:%S')
                end_time = time_range['end'].strftime('%H:%M:%S')
                print(f"   Data Range: {start_time} → {end_time}")

        print(f"   Current Readings:")
        for param, value in sorted(worst_data['parameters'].items()):
            unit_map = {
                'PM2.5': 'μg/m³', 'PM10': 'μg/m³', 'CO2': 'ppm',
                'Temperature': '°C', 'Humidity': '%RH', 'tVOC': 'μg/m³',
                'HCHO': 'mg/m³', 'O3': 'ppm', 'NH3': 'ppm', 'H2S': 'ppm'
            }
            unit = unit_map.get(param, '')
            print(f"      {param:<12}: {value:8.1f} {unit}")

    def _identify_issues(self, parameters: Dict) -> List[str]:
        """Identify potential issues from parameters."""
        issues = []

        if 'CO2' in parameters and parameters['CO2'] > 1000:
            issues.append("High CO2")
        if 'PM2.5' in parameters and parameters['PM2.5'] > 15:
            issues.append("High PM2.5")
        if 'tVOC' in parameters and parameters['tVOC'] > 500:
            issues.append("High tVOC")
        if 'Temperature' in parameters:
            temp = parameters['Temperature']
            if temp < 18 or temp > 26:
                issues.append("Temp issue")
        if 'Humidity' in parameters:
            humidity = parameters['Humidity']
            if humidity < 30 or humidity > 70:
                issues.append("Humidity issue")

        return issues

    def _get_score_status(self, score: float) -> str:
        """Get status string from score."""
        if score >= 90:
            return "Excellent"
        elif score >= 80:
            return "Good"
        elif score >= 60:
            return "Moderate"
        elif score >= 40:
            return "Poor"
        else:
            return "Very Poor"

    def publish_results(self, scores: Dict):
        """Publish IAQ scores to Kafka topic."""
        for location_key, score_data in scores.items():
            location_info = self.sensor_manager.get_location_info(location_key)

            result = {
                **score_data,
                'project_id': location_info['project_id'],
                'building_id': location_info['building_id'],
                'floor': location_info['floor'],
                'zone': location_info['zone'],
                'publish_timestamp': datetime.now().isoformat()
            }

            self.kafka_manager.publish_result('iaq_scores', result)


# =============================================================================
# 8. MAIN APPLICATION CONTROLLER
# =============================================================================

class IAQProcessor:
    """Main application controller that orchestrates all components."""

    def __init__(self, config: IAQConfig = None):
        self.config = config or IAQConfig()
        self.logger = self.config.setup_logging()

        # Initialize components
        self.sensor_manager = None
        self.kafka_manager = None
        self.data_ingestion = None
        self.data_processor = None
        self.iaq_calculator = None
        self.results_display = None

        # Control flags
        self.running = True

        # Background processing thread
        self.processing_thread = None

        self._initialize_components()

    def _initialize_components(self):
        """Initialize all system components."""
        try:
            # 1. Initialize sensor management
            self.sensor_manager = SensorManager(self.config, self.logger)

            # 2. Initialize Kafka management
            self.kafka_manager = KafkaManager(self.config, self.logger)

            # 3. Initialize data processing
            self.data_processor = DataProcessor(self.config, self.sensor_manager, self.logger)

            # 4. Initialize IAQ calculation
            self.iaq_calculator = IAQCalculator(self.sensor_manager, self.logger)

            # 5. Initialize results display
            self.results_display = ResultsDisplay(
                self.sensor_manager, self.kafka_manager, self.logger
            )

            # 6. Initialize data ingestion (must be last)
            self.data_ingestion = SensorDataIngestion(
                self.config, self.sensor_manager, self.kafka_manager, self.logger
            )

            # Set up callback for processed messages
            self.data_ingestion.set_message_callback(
                self.data_processor.process_enriched_message
            )

            # Initialize background processing
            self.processing_thread = threading.Thread(
                target=self._background_processing_loop,
                daemon=True,
                name="ProcessingThread"
            )

            print(f"🚀 IAQ Processor initialized")
            print(f"   • Locations: {len(self.sensor_manager.location_sensors)}")
            print(f"   • Sensor types: {len(self.sensor_manager.sensor_types)}")
            print(f"   • Supported types: {self.sensor_manager.get_supported_sensor_types()}")

        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            raise

    def _background_processing_loop(self):
        """Background thread for periodic IAQ calculation and display."""
        while self.running:
            try:
                self._process_and_display_results()
                time.sleep(self.config.processing_interval_seconds)
            except Exception as e:
                self.logger.error(f"Error in background processing: {e}")
                time.sleep(10)

    def _process_and_display_results(self):
        """Process current data and display results."""
        # Get current data from all locations
        locations_data = self.data_processor.get_all_locations_data()

        if not locations_data:
            # Show monitoring status if no data
            self.results_display.display_monitoring_status(
                self.data_ingestion.stats
            )
            return

        # Calculate IAQ scores
        scores = self.iaq_calculator.calculate_all_scores(locations_data)

        if scores:
            # Display full report
            self.results_display.display_full_report(
                scores, self.data_ingestion.stats
            )

            # Publish results to Kafka
            self.results_display.publish_results(scores)
        else:
            # Show monitoring status
            self.results_display.display_monitoring_status(
                self.data_ingestion.stats
            )

    def start(self):
        """Start the IAQ processing system."""
        print("🔄 Starting IAQ monitoring system...")

        try:
            # Start data ingestion
            self.data_ingestion.start_ingestion()

            # Start background processing
            self.processing_thread.start()

            print("✅ System running - monitoring sensor data and calculating IAQ scores...")
            print("Press Ctrl+C to stop\n")

            # Main loop
            while self.running:
                time.sleep(1)

        except KeyboardInterrupt:
            print("\n🛑 Shutdown requested...")
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}")
        finally:
            self.shutdown()

    def shutdown(self):
        """Gracefully shutdown the system."""
        print("🔄 Shutting down IAQ Processor...")

        self.running = False

        # Stop data ingestion
        if self.data_ingestion:
            self.data_ingestion.stop_ingestion()

        # Close Kafka connections
        if self.kafka_manager:
            self.kafka_manager.close()

        # Close database connections
        if self.sensor_manager:
            self.sensor_manager.close()

        # Wait for processing thread
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5)

        print("✅ Shutdown complete")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point for the application."""
    try:
        # Create and run the IAQ processor
        processor = IAQProcessor()
        processor.start()

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())