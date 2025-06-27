import json
import time
import threading
import logging
import pandas as pd
import os
from kafka import KafkaConsumer, KafkaProducer
from datetime import datetime, timedelta
from collections import defaultdict, deque
import sys
from pathlib import Path
import sys
sys.path.append('src')
sys.path.append('/home/ec2-user/iaq_score/src')
from iaq.rds.rdsTable import RDSTable
from iaq.model import AirQualityCalculator

# Set AWS region before importing Kafka
# OR run aws configure set region us-east-1
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
os.environ['AWS_REGION'] = 'us-east-1'

class MultiSensorKafkaProcessor:
    def __init__(self, bootstrap_servers, database_name, credentials_file="credentials.yaml"):
        self.setup_logging()

        # Database configuration using your RDSTable
        self.database_name = database_name
        self.credentials_file = credentials_file

        # Setup RDSTable for sensor info
        self.sensor_info_table = RDSTable(
            connection_config=self.credentials_file,
            database_name=self.database_name,
            table_name="pro_sensor_info",
            fields=['sensor_id', 'sensor_type', 'project_id', 'building_id', 'floor', 'zone'],
            primary_keys=['sensor_id']
        )

        # Initialize IAQ calculator
        self.iaq_calculator = AirQualityCalculator()

        # Kafka configuration
        self.kafka_config = {
            'bootstrap_servers': bootstrap_servers,
            'security_protocol': 'SASL_SSL',
            'sasl_mechanism': 'AWS_MSK_IAM',
        }

        self.consumer_config = {
            **self.kafka_config,
            'auto_offset_reset': 'latest',
            'enable_auto_commit': True,
        }

        # Multiple consumers for different sensor types
        self.consumers = {}
        self.consumer_threads = {}

        # Producer for optional output
        try:
            self.producer = KafkaProducer(
                value_serializer=lambda x: json.dumps(x, default=str).encode('utf-8'),
                **self.kafka_config
            )
        except Exception as e:
            self.logger.warning(f"Failed to create producer: {e}")
            self.producer = None

        # Location and sensor mapping from RDS
        self.location_sensors = {}  # location_key -> sensor info
        self.sensor_locations = {}  # sensor_id -> location info
        self.sensor_types = set()   # Available sensor types

        # In-memory state for windowing by location
        self.location_windows = defaultdict(lambda: deque(maxlen=1000))
        self.window_size = timedelta(minutes=5)

        # Control flags
        self.running = True

        # Statistics tracking
        self.stats = {
            'messages_processed': 0,
            'last_message_time': None,
            'locations_with_data': set()
        }

        # Initialize
        self.load_sensor_mappings()
        self.setup_consumers()

        # Background thread for periodic processing
        self.window_thread = threading.Thread(target=self.process_windows_periodically, daemon=True)

        print(f"🚀 IAQ Processor initialized - monitoring {len(self.location_sensors)} locations with {len(self.sensor_types)} sensor types")

    def setup_logging(self):
        # Suppress noisy loggers
        logging.getLogger('kafka').setLevel(logging.ERROR)
        logging.getLogger('botocore').setLevel(logging.ERROR)

        logging.basicConfig(
            level=logging.WARNING,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def load_sensor_mappings(self):
        """Load sensor location mappings from RDS"""
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

            # Process sensor mappings
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
                        'sensors': {},
                        'space_type': self.determine_space_type(sensor['zone'])
                    }

                if sensor_type not in self.location_sensors[location_key]['sensors']:
                    self.location_sensors[location_key]['sensors'][sensor_type] = []

                self.location_sensors[location_key]['sensors'][sensor_type].append(sensor_id)
                self.sensor_types.add(sensor_type)

        except Exception as e:
            self.logger.error(f"Error loading sensor mappings: {e}")
            raise

    def determine_space_type(self, zone_name):
        """Determine space type from zone name for IAQ scoring"""
        return "Conference/Meeting Rooms"
        # zone_lower = zone_name.lower()

        # # Map zone names to space types
        # if any(keyword in zone_lower for keyword in ['office', 'cubicle', 'desk', 'work']):
        #     return "Office/Cubicle"
        # elif any(keyword in zone_lower for keyword in ['conference', 'meeting', 'boardroom']):
        #     return "Conference/Meeting Rooms"
        # elif any(keyword in zone_lower for keyword in ['restroom', 'bathroom', 'toilet']):
        #     return "Restrooms"
        # elif any(keyword in zone_lower for keyword in ['corridor', 'hallway', 'common']):
        #     return "Corridors/Common Areas"
        # elif any(keyword in zone_lower for keyword in ['circulation', 'walkway']):
        #     return "Office Circulation/Walkways"
        # elif any(keyword in zone_lower for keyword in ['cafeteria', 'dining', 'kitchen', 'cafe']):
        #     return "Cafeteria/Dining Area"
        # else:
        #     return "Other Areas"

    def setup_consumers(self):
        """Setup Kafka consumers for supported sensor types"""
        supported_types = ['am319', 'em500co2']

        for sensor_type in self.sensor_types:
            if sensor_type not in supported_types:
                continue

            try:
                consumer = KafkaConsumer(
                    sensor_type,
                    group_id=f'iaq-processor-{sensor_type}',
                    value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                    **self.consumer_config
                )

                self.consumers[sensor_type] = consumer
                thread = threading.Thread(
                    target=self.consume_sensor_type,
                    args=(sensor_type, consumer),
                    name=f"Consumer-{sensor_type}",
                    daemon=True
                )
                self.consumer_threads[sensor_type] = thread

            except Exception as e:
                self.logger.error(f"Error setting up consumer for {sensor_type}: {e}")

    def consume_sensor_type(self, sensor_type, consumer):
        """Consumer thread for a specific sensor type"""
        try:
            for message in consumer:
                if not self.running:
                    print(f"⚠️ Stopping {sensor_type} consumer")
                    break
                try:
                    sensor_reading = message.value
                    print(f"🔍 Processing {sensor_type} message: {sensor_reading}")
                    sensor_id = sensor_reading.get('devEUI') or sensor_reading.get('sensor_id')

                    if not sensor_id:
                        continue

                    # Update statistics
                    self.stats['messages_processed'] += 1
                    self.stats['last_message_time'] = datetime.now()

                    if sensor_id in self.sensor_locations:
                        enriched = self.enrich_with_location(sensor_reading, sensor_type, sensor_id)
                        if enriched:
                            self.add_to_window(enriched)
                            self.stats['locations_with_data'].add(enriched['location_key'])

                except Exception as e:
                    self.logger.error(f"Error processing {sensor_type} message: {e}")

        except Exception as e:
            self.logger.error(f"Error in {sensor_type} consumer thread: {e}")

    def enrich_with_location(self, sensor_reading, sensor_type, sensor_id):
        """Enrich sensor data with location information"""
        try:
            location_info = self.sensor_locations[sensor_id]
            enriched = sensor_reading.copy()
            enriched.update({
                'sensor_id': sensor_id,
                'location_key': location_info['location_key'],
                'project_id': location_info['project_id'],
                'building_id': location_info['building_id'],
                'floor': location_info['floor'],
                'zone': location_info['zone'],
                'sensor_type': sensor_type,
                'processing_time': datetime.now()
            })
            return enriched
        except Exception as e:
            self.logger.error(f"Error enriching sensor data: {e}")
            return None

    def add_to_window(self, enriched_reading):
        """Add reading to location-based time window"""
        location_key = enriched_reading['location_key']
        self.location_windows[location_key].append(enriched_reading)

        # Clean old readings
        cutoff_time = datetime.now() - self.window_size - timedelta(minutes=1)
        while (self.location_windows[location_key] and
               self.location_windows[location_key][0]['processing_time'] < cutoff_time):
            self.location_windows[location_key].popleft()

    def get_location_aggregate(self, location_key):
        """Aggregate readings for a location in current window"""
        readings = list(self.location_windows[location_key])
        if not readings:
            return None

        cutoff_time = datetime.now() - self.window_size
        recent_readings = [r for r in readings if r['processing_time'] >= cutoff_time]
        if not recent_readings:
            return None

        # Group by sensor type and aggregate parameters
        readings_by_sensor_type = defaultdict(list)
        for reading in recent_readings:
            readings_by_sensor_type[reading['sensor_type']].append(reading)

        all_parameters = {}
        for sensor_type, type_readings in readings_by_sensor_type.items():
            parameter_sums = defaultdict(list)

            for reading in type_readings:
                # Extract parameters from reading
                if 'parameters' in reading:
                    for param, value in reading['parameters'].items():
                        if isinstance(value, (int, float)):
                            parameter_sums[param].append(value)
                else:
                    # Direct parameters in reading
                    exclude_fields = {'sensor_id', 'location_key', 'project_id', 'building_id',
                                    'floor', 'zone', 'sensor_type', 'processing_time', 'timestamp', 'devEUI'}
                    for param, value in reading.items():
                        if param not in exclude_fields and isinstance(value, (int, float)):
                            parameter_sums[param].append(value)

            # Calculate averages
            sensor_type_params = {
                param: sum(values) / len(values)
                for param, values in parameter_sums.items() if values
            }
            all_parameters.update(sensor_type_params)

        if not all_parameters:
            return None

        first_reading = recent_readings[0]
        return {
            'location_key': location_key,
            'project_id': first_reading['project_id'],
            'building_id': first_reading['building_id'],
            'floor': first_reading['floor'],
            'zone': first_reading['zone'],
            'parameters': all_parameters,
            'total_readings': len(recent_readings),
            'total_sensors': len(set(r['sensor_id'] for r in recent_readings)),
            'window_start': min(r['processing_time'] for r in recent_readings),
            'window_end': max(r['processing_time'] for r in recent_readings)
        }

    def calculate_iaq_scores(self):
        """Calculate IAQ scores for all locations with data"""
        location_scores = {}

        for location_key in self.stats['locations_with_data']:
            try:
                location_aggregate = self.get_location_aggregate(location_key)
                if not location_aggregate:
                    continue

                location_info = self.location_sensors[location_key]
                space_type = location_info['space_type']
                parameters = location_aggregate['parameters']

                # Map parameters to IAQ calculator format
                mapped_params = self.map_parameters_for_iaq(parameters)

                if mapped_params:
                    # Add zone to calculator temporarily for scoring
                    zone_name = f"{location_info['zone']}"
                    try:
                        self.iaq_calculator.add_zone(zone_name, space_type, mapped_params)
                        score = self.iaq_calculator.calculate_zone_score(
                            next(zone for zone in self.iaq_calculator.zones if zone.name == zone_name)
                        )

                        location_scores[location_key] = {
                            'score': score,
                            'status': self.get_score_status(score),
                            'space_type': space_type,
                            'parameters': mapped_params,
                            'readings_info': {
                                'total_readings': location_aggregate['total_readings'],
                                'total_sensors': location_aggregate['total_sensors'],
                                'window_start': location_aggregate['window_start'],
                                'window_end': location_aggregate['window_end']
                            }
                        }

                        # Remove zone from calculator to avoid accumulation
                        self.iaq_calculator.zones = [z for z in self.iaq_calculator.zones if z.name != zone_name]

                    except Exception as e:
                        self.logger.error(f"Error calculating score for {location_key}: {e}")

            except Exception as e:
                self.logger.error(f"Error processing location {location_key}: {e}")

        return location_scores

    def map_parameters_for_iaq(self, parameters):
        """Map sensor parameters to IAQ calculator expected format"""
        # Common parameter mappings between sensor data and IAQ calculator
        param_mapping = {
            'pm25': 'PM2.5',
            'pm2_5': 'PM2.5',
            'pm10': 'PM10',
            'co2': 'CO2',
            'tvoc': 'tVOC',
            'temperature': 'Temperature',
            'temp': 'Temperature',
            'humidity': 'Humidity',
            'rh': 'Humidity',
            'formaldehyde': 'HCHO',
            'hcho': 'HCHO',
            'ozone': 'O3',
            'o3': 'O3',
            'nh3': 'NH3',
            'ammonia': 'NH3',
            'h2s': 'H2S'
        }

        mapped = {}
        for sensor_param, value in parameters.items():
            # Convert parameter name to lowercase for matching
            param_lower = sensor_param.lower().replace('_', '').replace('-', '')

            # Direct match or mapped match
            if param_lower in param_mapping:
                iaq_param = param_mapping[param_lower]
                mapped[iaq_param] = value
            elif sensor_param in ['PM2.5', 'PM10', 'CO2', 'Temperature', 'Humidity', 'tVOC', 'HCHO', 'O3', 'NH3', 'H2S']:
                mapped[sensor_param] = value

        return mapped

    def get_score_status(self, score):
        """Get status string from score"""
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

    def process_windows_periodically(self):
        """Background thread to process windows and calculate/print scores"""
        while self.running:
            try:
                self.process_and_display_results()
                time.sleep(60)  # Process every minute
            except Exception as e:
                self.logger.error(f"Error in window processing: {e}")
                time.sleep(10)

    def process_and_display_results(self):
        """Process all windows and display IAQ scoring results"""
        # Calculate scores for all locations
        location_scores = self.calculate_iaq_scores()

        if not location_scores:
            # Only show brief status if no data
            current_time = datetime.now().strftime('%H:%M:%S')
            total_messages = self.stats['messages_processed']
            print(f"\r[{current_time}] Monitoring... ({total_messages} messages processed)", end='', flush=True)
            return

        # Clear the monitoring line and show full results
        print("\r" + " " * 80 + "\r", end='')  # Clear line

        print(f"\n{'='*80}")
        print(f"🏢 IAQ MONITORING REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")

        # Sort locations by score (worst first for attention)
        sorted_locations = sorted(location_scores.items(), key=lambda x: x[1]['score'])

        # Overall statistics
        scores = [data['score'] for data in location_scores.values()]
        avg_score = sum(scores) / len(scores)
        total_messages = self.stats['messages_processed']

        print(f"📊 SUMMARY:")
        print(f"   • Locations monitored: {len(location_scores)}")
        print(f"   • Average building score: {avg_score:.1f} ({self.get_score_status(avg_score)})")
        print(f"   • Messages processed: {total_messages}")
        print(f"   • Last data: {self.stats['last_message_time'].strftime('%H:%M:%S') if self.stats['last_message_time'] else 'None'}")

        print(f"\n🎯 LOCATION SCORES:")
        print(f"{'Location':<35} {'Score':<8} {'Status':<12} {'Sensors':<8} {'Key Issues'}")
        print("-" * 80)

        for location_key, score_data in sorted_locations:
            location_info = self.location_sensors[location_key]
            zone_name = location_info['zone'][:30]  # Truncate long names
            score = score_data['score']
            status = score_data['status']
            sensor_count = score_data['readings_info']['total_sensors']

            # Identify key issues (parameters that might be causing low scores)
            issues = []
            params = score_data['parameters']

            # Check for common issues
            if 'CO2' in params and params['CO2'] > 1000:
                issues.append("High CO2")
            if 'PM2.5' in params and params['PM2.5'] > 15:
                issues.append("High PM2.5")
            if 'tVOC' in params and params['tVOC'] > 500:
                issues.append("High tVOC")
            if 'Temperature' in params and (params['Temperature'] < 18 or params['Temperature'] > 26):
                issues.append("Temp issue")

            issues_str = ", ".join(issues[:2]) if issues else "None"  # Limit to 2 issues

            # Color coding with emojis for status
            status_emoji = {"Excellent": "🟢", "Good": "🟡", "Moderate": "🟠", "Poor": "🔴", "Very Poor": "⚫"}
            emoji = status_emoji.get(status, "⚪")

            print(f"{emoji} {zone_name:<32} {score:6.1f}   {status:<12} {sensor_count:<8} {issues_str}")

        # Show raw sensor data and detailed analysis
        if sorted_locations:
            self.display_raw_sensor_data(sorted_locations)

            # Show detailed parameters for worst location
            worst_location_key, worst_data = sorted_locations[0]
            if worst_data['score'] < 80:  # Only show details if there's an issue
                print(f"\n⚠️  DETAILED ANALYSIS - {self.location_sensors[worst_location_key]['zone']}:")
                print(f"   Space Type: {worst_data['space_type']}")
                print(f"   Score: {worst_data['score']:.1f} ({worst_data['status']})")
                print(f"   IAQ Score Calculation Parameters:")

                for param, value in sorted(worst_data['parameters'].items()):
                    # Add units and thresholds for context
                    unit_map = {
                        'PM2.5': 'μg/m³', 'PM10': 'μg/m³', 'CO2': 'ppm',
                        'Temperature': '°C', 'Humidity': '%RH', 'tVOC': 'μg/m³',
                        'HCHO': 'mg/m³', 'O3': 'ppm', 'NH3': 'ppm', 'H2S': 'ppm'
                    }
                    unit = unit_map.get(param, '')

                    # Get individual parameter score
                    try:
                        param_score = self.iaq_calculator.calculate_parameter_score(
                            worst_data['space_type'], param, value
                        )
                        print(f"      {param:<12}: {value:8.1f} {unit:<6} → Score: {param_score:5.1f}")
                    except:
                        print(f"      {param:<12}: {value:8.1f} {unit}")

        print(f"{'='*80}\n")

    def display_raw_sensor_data(self, sorted_locations):
        """Display raw sensor data for score calculation transparency"""
        print(f"\n📋 RAW SENSOR DATA (Last 5 minutes):")
        print("-" * 80)

        for location_key, score_data in sorted_locations[:3]:  # Show top 3 locations
            location_info = self.location_sensors[location_key]
            zone_name = location_info['zone']

            print(f"\n🔍 {zone_name}:")

            # Get raw readings from window
            location_aggregate = self.get_location_aggregate(location_key)
            if not location_aggregate:
                continue

            # Show reading summary
            readings_info = score_data['readings_info']
            print(f"   📊 Data Summary:")
            print(f"      • Total readings: {readings_info['total_readings']}")
            print(f"      • Total sensors: {readings_info['total_sensors']}")
            print(f"      • Time window: {readings_info['window_start'].strftime('%H:%M:%S')} → {readings_info['window_end'].strftime('%H:%M:%S')}")

            # Show raw parameters extracted from sensors
            print(f"   📈 Raw Sensor Parameters:")
            raw_readings = list(self.location_windows[location_key])
            if raw_readings:
                # Get recent readings
                cutoff_time = datetime.now() - self.window_size
                recent_readings = [r for r in raw_readings if r['processing_time'] >= cutoff_time]

                # Group by sensor type
                readings_by_sensor_type = defaultdict(list)
                for reading in recent_readings:
                    readings_by_sensor_type[reading['sensor_type']].append(reading)

                for sensor_type, type_readings in readings_by_sensor_type.items():
                    print(f"      🔹 {sensor_type} sensors ({len(type_readings)} readings):")

                    # Show sample raw reading
                    if type_readings:
                        sample_reading = type_readings[-1]  # Most recent
                        sensor_id = sample_reading['sensor_id']
                        timestamp = sample_reading['processing_time'].strftime('%H:%M:%S')

                        print(f"         Latest from {sensor_id} at {timestamp}:")

                        # Extract and display parameters
                        if 'parameters' in sample_reading:
                            for param, value in sample_reading['parameters'].items():
                                if isinstance(value, (int, float)):
                                    print(f"           {param}: {value}")
                        else:
                            # Direct parameters
                            exclude_fields = {'sensor_id', 'location_key', 'project_id', 'building_id',
                                            'floor', 'zone', 'sensor_type', 'processing_time', 'timestamp', 'devEUI'}
                            for param, value in sample_reading.items():
                                if param not in exclude_fields and isinstance(value, (int, float)):
                                    print(f"           {param}: {value}")

            # Show aggregated values used for scoring
            print(f"   🎯 Aggregated Values for IAQ Scoring:")
            for param, value in sorted(score_data['parameters'].items()):
                unit_map = {
                    'PM2.5': 'μg/m³', 'PM10': 'μg/m³', 'CO2': 'ppm',
                    'Temperature': '°C', 'Humidity': '%RH', 'tVOC': 'μg/m³'
                }
                unit = unit_map.get(param, '')
                print(f"      {param}: {value:.3f} {unit}")

        print(f"\n{'='*40}")
        print(f"📝 Note: Scores are calculated using aggregated values")
        print(f"   from all sensor readings in the time window.")
        print(f"{'='*40}")

    def start_consumers(self):
        """Start all consumer threads"""
        for sensor_type, thread in self.consumer_threads.items():
            thread.start()

    def run(self):
        """Main processing loop"""
        print("🔄 Starting IAQ monitoring system...")

        # Start consumer threads
        self.start_consumers()

        # Start window processing thread
        self.window_thread.start()

        try:
            print("✅ System running - monitoring sensor data and calculating IAQ scores...")
            print("Press Ctrl+C to stop\n")

            while self.running:
                time.sleep(1)

        except KeyboardInterrupt:
            print("\n🛑 Shutdown requested...")
        finally:
            self.shutdown()

    def shutdown(self):
        """Clean shutdown"""
        self.running = False

        # Close consumers
        for sensor_type, consumer in self.consumers.items():
            try:
                consumer.close()
            except Exception:
                pass

        # Close producer
        if self.producer:
            try:
                self.producer.close()
            except Exception:
                pass

        print("✅ Shutdown complete")


if __name__ == "__main__":
    bootstrap_servers = [
        'b-2.msktest.6xni82.c13.kafka.us-east-1.amazonaws.com:9098',
        'b-1.msktest.6xni82.c13.kafka.us-east-1.amazonaws.com:9098'
    ]

    DATABASE_NAME = "ry-vue"
    CREDENTIALS_FILE = "credentials.yaml"

    processor = MultiSensorKafkaProcessor(
        bootstrap_servers=bootstrap_servers,
        database_name=DATABASE_NAME,
        credentials_file=CREDENTIALS_FILE
    )
    processor.run()