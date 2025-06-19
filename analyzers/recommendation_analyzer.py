from typing import Dict, List, Any
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from models.work_order import WorkOrder, WorkOrderSource
from models.employee import Employee, EmploymentStatus
from models.location import Location
from models.alert import Alert, AlertStatus, AlertSeverity
from models.recommendation import TaskRecommendation, RecommendationSource, RecommendationPriority

class RecommendationAnalyzer:
    """Pure analysis engine for work order recommendations"""

    def __init__(self, database_connection):
        self.db = database_connection
        self.employees = self._load_active_employees()
        self.locations = self._load_locations()
        self.templates = self._load_task_templates()

    def analyze_historical_patterns(self, location_id: str, work_order_type: str,
                                  lookback_days: int = 30) -> Dict[str, Any]:
        """Analyze historical completion patterns for similar work orders"""

        # Query historical work orders
        historical_orders = self._query_historical_work_orders(
            location_id, work_order_type, lookback_days
        )

        if len(historical_orders) < 3:  # Insufficient data
            return {
                "sufficient_data": False,
                "pattern_strength": 0.0,
                "recommendation_confidence": 0.0
            }

        # Analyze completion patterns
        completion_intervals = []
        quality_scores = []
        efficiency_scores = []
        assignee_frequency = Counter()

        for i in range(1, len(historical_orders)):
            interval = (historical_orders[i]['actual_end_time'] -
                       historical_orders[i-1]['actual_end_time']).days
            completion_intervals.append(interval)

            if historical_orders[i]['quality_score']:
                quality_scores.append(historical_orders[i]['quality_score'])
            if historical_orders[i]['efficiency_score']:
                efficiency_scores.append(historical_orders[i]['efficiency_score'])

            assignee_frequency[historical_orders[i]['assignee']] += 1

        # Calculate pattern metrics
        if completion_intervals:
            avg_interval = sum(completion_intervals) / len(completion_intervals)
            interval_variance = sum((x - avg_interval) ** 2 for x in completion_intervals) / len(completion_intervals)
            pattern_strength = 1.0 / (1.0 + interval_variance / avg_interval) if avg_interval > 0 else 0.0
        else:
            avg_interval = 0
            pattern_strength = 0.0

        # Predict next occurrence
        last_completion = max(order['actual_end_time'] for order in historical_orders)
        predicted_next = last_completion + timedelta(days=avg_interval)

        return {
            "sufficient_data": True,
            "pattern_strength": pattern_strength,
            "avg_completion_interval_days": avg_interval,
            "predicted_next_date": predicted_next,
            "avg_quality_score": sum(quality_scores) / len(quality_scores) if quality_scores else None,
            "avg_efficiency_score": sum(efficiency_scores) / len(efficiency_scores) if efficiency_scores else None,
            "most_common_assignee": assignee_frequency.most_common(1)[0][0] if assignee_frequency else None,
            "assignee_distribution": dict(assignee_frequency),
            "recommendation_confidence": min(0.95, pattern_strength * 0.8 + len(historical_orders) * 0.05)
        }

    def analyze_alert_triggers(self, location_id: str, alert_severity_threshold: str = "severe") -> Dict[str, Any]:
        """Analyze alert patterns that should trigger work orders"""

        # Get current active alerts
        active_alerts = self._query_active_alerts(location_id)

        # Get historical alert-to-work-order correlations
        alert_correlations = self._query_alert_work_order_correlations(location_id)

        # Analyze alert escalation patterns
        escalation_patterns = self._analyze_alert_escalation(location_id)

        trigger_score = 0.0
        trigger_reasons = []

        # Check for immediate triggers
        critical_alerts = [a for a in active_alerts if a['severity'] in ['critical', 'very_severe']]
        severe_alerts = [a for a in active_alerts if a['severity'] == 'severe']

        if critical_alerts:
            trigger_score += 0.9
            trigger_reasons.append(f"{len(critical_alerts)} critical alerts require immediate attention")

        if len(severe_alerts) >= 2:
            trigger_score += 0.7
            trigger_reasons.append(f"{len(severe_alerts)} severe alerts indicate deteriorating conditions")

        # Check for escalation patterns
        if escalation_patterns['escalation_probability'] > 0.7:
            trigger_score += 0.6
            trigger_reasons.append("Alert pattern indicates likely escalation to critical")

        # Check for duration-based triggers
        long_duration_alerts = [a for a in active_alerts if a['duration_hours'] > 24]
        if long_duration_alerts:
            trigger_score += 0.5
            trigger_reasons.append(f"{len(long_duration_alerts)} alerts persisting >24h")

        return {
            "trigger_score": min(1.0, trigger_score),
            "should_trigger": trigger_score >= 0.6,
            "active_alerts_count": len(active_alerts),
            "critical_alerts": len(critical_alerts),
            "severe_alerts": len(severe_alerts),
            "trigger_reasons": trigger_reasons,
            "escalation_probability": escalation_patterns['escalation_probability'],
            "recommended_priority": self._calculate_alert_priority(active_alerts),
            "estimated_response_time": self._estimate_response_time(active_alerts)
        }

    def analyze_metric_performance(self, location_id: str, work_order_type: str,
                                 variance_threshold: float = 0.2) -> Dict[str, Any]:
        """Analyze performance metrics to identify degradation patterns"""

        # Get recent metric data
        recent_metrics = self._query_recent_metrics(location_id, 30)  # Last 30 days

        # Get baseline metrics from completed work orders
        baseline_metrics = self._query_baseline_metrics(location_id, work_order_type)

        performance_indicators = {}
        degradation_score = 0.0
        recommendations = []

        for metric_type, recent_values in recent_metrics.items():
            if metric_type in baseline_metrics:
                baseline_avg = baseline_metrics[metric_type]['average']
                recent_avg = sum(recent_values) / len(recent_values)

                # Calculate degradation
                if baseline_avg > 0:
                    variance = abs(recent_avg - baseline_avg) / baseline_avg

                    performance_indicators[metric_type] = {
                        'baseline_average': baseline_avg,
                        'recent_average': recent_avg,
                        'variance_percentage': variance * 100,
                        'degradation_detected': variance > variance_threshold,
                        'trend': 'improving' if recent_avg > baseline_avg else 'degrading'
                    }

                    if variance > variance_threshold:
                        degradation_score += variance
                        recommendations.append(
                            f"{metric_type} showing {variance*100:.1f}% variance from baseline"
                        )

        # Determine if intervention needed
        intervention_needed = degradation_score > 0.4  # Configurable threshold

        return {
            "degradation_score": min(1.0, degradation_score),
            "intervention_needed": intervention_needed,
            "performance_indicators": performance_indicators,
            "recommendations": recommendations,
            "confidence": min(0.9, len(performance_indicators) * 0.2),
            "predicted_improvement": self._predict_metric_improvement(performance_indicators)
        }

    def analyze_employee_availability(self, recommended_time: datetime,
                                    preferred_assignees: List[str]) -> Dict[str, Any]:
        """Analyze employee availability and capacity for recommendations"""

        availability_analysis = {}

        for assignee_name in preferred_assignees:
            employee = self.employees.get(assignee_name)
            if not employee:
                continue

            # Get current workload
            current_workload = self._query_employee_workload(
                employee.employee_id, recommended_time.date()
            )

            # Calculate availability
            scheduled_hours = sum(wo['duration_minutes'] for wo in current_workload) / 60.0
            capacity_hours = 8.0  # Standard day
            availability_percentage = max(0, (capacity_hours - scheduled_hours) / capacity_hours * 100)

            # Check for conflicts
            conflicts = self._check_time_conflicts(employee.employee_id, recommended_time)

            availability_analysis[assignee_name] = {
                'employee_id': employee.employee_id,
                'scheduled_hours': scheduled_hours,
                'availability_percentage': availability_percentage,
                'has_conflicts': len(conflicts) > 0,
                'hourly_rate': employee.hourly_rate,
                'efficiency_rating': employee.efficiency_rating,
                'skill_match_score': self._calculate_skill_match(employee, required_skills=[]),
                'preferred_zones': employee.preferred_zones,
                'recommendation_score': self._calculate_assignee_score(employee, availability_percentage)
            }

        return availability_analysis

    def generate_performance_insights(self, recommendations: List[TaskRecommendation]) -> List[Dict[str, Any]]:
        """Generate insights about recommendation patterns and performance"""

        insights = []

        # Analyze recommendation frequency by location
        location_frequency = Counter(rec.recommended_location for rec in recommendations)
        if location_frequency:
            high_frequency_locations = [loc for loc, count in location_frequency.most_common(3)]
            insights.append({
                'type': 'location_frequency',
                'insight': f"Locations requiring frequent attention: {', '.join(high_frequency_locations)}",
                'recommendation': 'Consider preventive maintenance schedules for high-frequency locations',
                'data': dict(location_frequency.most_common(5))
            })

        # Analyze source distribution
        source_distribution = Counter(rec.source.value for rec in recommendations)
        alert_driven_percentage = (source_distribution.get('alert_triggered', 0) / len(recommendations)) * 100

        if alert_driven_percentage > 60:
            insights.append({
                'type': 'reactive_pattern',
                'insight': f"{alert_driven_percentage:.1f}% of recommendations are reactive (alert-driven)",
                'recommendation': 'Increase preventive maintenance to reduce reactive work',
                'data': dict(source_distribution)
            })

        # Analyze confidence patterns
        confidence_scores = [rec.confidence_score for rec in recommendations]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0

        insights.append({
            'type': 'confidence_analysis',
            'insight': f"Average recommendation confidence: {avg_confidence:.2f}",
            'recommendation': 'High confidence indicates strong data patterns' if avg_confidence > 0.8
                            else 'Consider collecting more historical data to improve confidence',
            'data': {
                'average_confidence': avg_confidence,
                'high_confidence_count': sum(1 for score in confidence_scores if score > 0.8),
                'low_confidence_count': sum(1 for score in confidence_scores if score < 0.6)
            }
        })

        return insights

    def calculate_business_impact(self, recommendation: TaskRecommendation) -> Dict[str, Any]:
        """Calculate business impact of accepting or rejecting recommendation"""

        # Get location data
        location = self._find_location_by_name(recommendation.recommended_location)

        # Calculate impact based on source
        if recommendation.source == RecommendationSource.ALERT_TRIGGERED:
            impact = self._calculate_alert_impact(recommendation)
        elif recommendation.source == RecommendationSource.PATTERN_BASED:
            impact = self._calculate_pattern_impact(recommendation)
        elif recommendation.source == RecommendationSource.METRIC_DRIVEN:
            impact = self._calculate_metric_impact(recommendation)
        else:
            impact = self._calculate_default_impact(recommendation)

        # Add location-specific factors
        if location:
            impact['location_priority_multiplier'] = location.cleaning_priority_score / 5.0
            impact['facility_importance'] = 'critical' if location.cleaning_priority_score >= 9.0 else 'standard'

        return impact

    # Helper methods for data querying (these would interact with your database)
    def _query_historical_work_orders(self, location_id: str, work_order_type: str, lookback_days: int):
        """Query historical work orders from database"""
        # Implementation depends on your database structure
        # This would query Table 1 (WORK_ORDERS) and Table 2 (completion data)
        if hasattr(self, 'db') and self.db:
            query = """
            SELECT wo.*, comp.quality_score, comp.efficiency_score,
                   comp.actual_start_time, comp.actual_end_time
            FROM work_orders wo
            LEFT JOIN completion_data comp ON wo.work_order_id = comp.work_order_id
            WHERE wo.location LIKE %s
            AND wo.work_order_type = %s
            AND wo.actual_end_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
            AND wo.status = 'completed'
            ORDER BY wo.actual_end_time DESC
            """
            return self.db.execute_query(query, [f"%{location_id}%", work_order_type, lookback_days])
        else:
            # Mock data for testing
            from datetime import datetime, timedelta
            return [
                {
                    'work_order_id': 1001,
                    'assignee': 'John Doe',
                    'actual_end_time': datetime.now() - timedelta(days=7),
                    'quality_score': 8.5,
                    'efficiency_score': 9.0
                },
                {
                    'work_order_id': 1002,
                    'assignee': 'John Doe',
                    'actual_end_time': datetime.now() - timedelta(days=14),
                    'quality_score': 8.8,
                    'efficiency_score': 8.7
                }
            ]

    def _query_active_alerts(self, location_id: str):
        """Query active alerts from database"""
        # This would query Table 8 (alerts)
        if hasattr(self, 'db') and self.db:
            query = """
            SELECT alert_id, location_id, data_type, severity, value, threshold,
                   duration_minutes, timestamp, description
            FROM alerts
            WHERE location_id = %s
            AND status = 'active'
            ORDER BY severity DESC, timestamp DESC
            """
            return self.db.execute_query(query, [location_id])
        else:
            # Mock data for testing
            return [
                {
                    'alert_id': 'A001',
                    'location_id': location_id,
                    'data_type': 'air_quality',
                    'severity': 'severe',
                    'duration_hours': 6.5,
                    'value': 85,
                    'threshold': 70
                }
            ]

    def _query_recent_metrics(self, location_id: str, days: int):
        """Query recent metric values"""
        # This would query your metrics table
        if hasattr(self, 'db') and self.db:
            query = """
            SELECT data_type, value, timestamp
            FROM metrics
            WHERE location_id = %s
            AND timestamp >= DATE_SUB(NOW(), INTERVAL %s DAY)
            ORDER BY data_type, timestamp
            """
            results = self.db.execute_query(query, [location_id, days])

            # Group by data_type
            metrics_by_type = {}
            for row in results:
                data_type = row['data_type']
                if data_type not in metrics_by_type:
                    metrics_by_type[data_type] = []
                metrics_by_type[data_type].append(row['value'])
            return metrics_by_type
        else:
            # Mock data for testing
            return {
                'air_quality': [75, 78, 82, 85, 88],
                'temperature': [72, 73, 74, 76, 78],
                'humidity': [45, 47, 50, 52, 55]
            }

    def _load_active_employees(self):
        """Load active employees from database"""
        # Implementation would load from your employee table
        if hasattr(self, 'db') and self.db:
            query = """
            SELECT employee_id, first_name, last_name, hourly_rate,
                   efficiency_rating, skill_level, employment_status
            FROM employees
            WHERE employment_status = 'active'
            """
            results = self.db.execute_query(query, [])
            # Convert to Employee objects
            employees = {}
            for row in results:
                # You'd need to also load skills for each employee
                emp = Employee(
                    employee_id=row['employee_id'],
                    first_name=row['first_name'],
                    last_name=row['last_name'],
                    hourly_rate=row['hourly_rate'],
                    efficiency_rating=row['efficiency_rating'],
                    # ... other fields
                )
                employees[emp.full_name] = emp
            return employees
        else:
            # Mock data for testing
            from models.employee import Employee, EmployeeSkill, SkillLevel
            employees = {}

            # Create mock employees
            john = Employee(
                employee_id="EMP001",
                first_name="John",
                last_name="Doe",
                hourly_rate=25.0,
                efficiency_rating=8.5,
                skills=[
                    EmployeeSkill("general_cleaning", "cleaning", SkillLevel.SENIOR, 3.0),
                    EmployeeSkill("emergency_response", "safety", SkillLevel.JUNIOR, 1.0)
                ]
            )
            employees[john.full_name] = john

            return employees

    def _load_locations(self):
        """Load locations from database"""
        if hasattr(self, 'db') and self.db:
            query = """
            SELECT location_id, location_name, zone_type, building, floor,
                   cleaning_priority_score, coordinates
            FROM locations
            WHERE active = 1
            """
            results = self.db.execute_query(query, [])
            # Convert to Location objects
            locations = {}
            for row in results:
                loc = Location(
                    location_id=row['location_id'],
                    location_name=row['location_name'],
                    zone_id=row['location_id'],  # Assuming same
                    building=row['building'],
                    floor=row['floor'],
                    zone_type=row['zone_type'],
                    cleaning_priority_score=row['cleaning_priority_score'],
                    coordinates=row['coordinates'] or {"x": 0, "y": 0}
                )
                locations[loc.location_id] = loc
            return locations
        else:
            # Mock data for testing
            from models.location import Location, ZoneType
            locations = {}

            loc1 = Location(
                location_id="HQ-F1-RR",
                location_name="HQ Floor 1 Restroom",
                zone_id="HQ-F1",
                building="HQ",
                floor=1,
                zone_type=ZoneType.RESTROOM,
                cleaning_priority_score=9.2,
                coordinates={"x": 10, "y": 20}
            )
            locations[loc1.location_id] = loc1

            return locations

    def _load_task_templates(self):
        """Load task templates from database"""
        if hasattr(self, 'db') and self.db:
            query = """
            SELECT template_id, template_name, work_order_type,
                   default_duration_minutes, required_skills
            FROM task_templates
            WHERE active = 1
            """
            results = self.db.execute_query(query, [])
            templates = {}
            for row in results:
                template = TaskTemplate(
                    template_id=row['template_id'],
                    template_name=row['template_name'],
                    work_order_type=row['work_order_type'],
                    default_duration_minutes=row['default_duration_minutes'],
                    required_skills=row['required_skills'].split(',') if row['required_skills'] else []
                )
                templates[template.template_id] = template
            return templates
        else:
            # Mock data for testing
            from models.task_template import TaskTemplate
            templates = {}

            template1 = TaskTemplate(
                template_id=1001,
                template_name="Standard Restroom Cleaning",
                work_order_type="cleaning",
                default_duration_minutes=90,
                required_skills=["restroom_cleaning", "sanitization"],
                optimal_assignees=["John Doe"],
                location_types=["restroom"]
            )
            templates[1001] = template1

            return templates

    def _query_alert_work_order_correlations(self, location_id: str):
        """Query historical correlations between alerts and work orders"""
        # Mock implementation
        return {
            'correlation_strength': 0.85,
            'avg_response_time_hours': 4.2,
            'success_rate': 0.92
        }

    def _analyze_alert_escalation(self, location_id: str):
        """Analyze alert escalation patterns"""
        # Mock implementation
        return {
            'escalation_probability': 0.73,
            'avg_escalation_time_hours': 12.5,
            'prevention_success_rate': 0.88
        }

    def _query_baseline_metrics(self, location_id: str, work_order_type: str):
        """Query baseline metrics from completed work orders"""
        # Mock implementation
        return {
            'air_quality': {'average': 75.5, 'std_dev': 5.2},
            'temperature': {'average': 72.0, 'std_dev': 2.1},
            'humidity': {'average': 48.0, 'std_dev': 4.8}
        }

    def _predict_metric_improvement(self, performance_indicators: Dict):
        """Predict improvement in metrics after intervention"""
        improvements = {}
        for metric, data in performance_indicators.items():
            if data.get('degradation_detected'):
                variance = data['variance_percentage']
                # Estimate improvement based on variance
                expected_improvement = min(variance * 0.7, 25)  # Cap at 25%
                improvements[metric] = f"{expected_improvement:.1f}% improvement expected"
        return improvements

    def _calculate_alert_priority(self, active_alerts: List[Dict]) -> str:
        """Calculate recommended priority based on alerts"""
        if not active_alerts:
            return "Medium"

        critical_count = sum(1 for alert in active_alerts if alert['severity'] == 'critical')
        severe_count = sum(1 for alert in active_alerts if alert['severity'] in ['severe', 'very_severe'])

        if critical_count > 0:
            return "Urgent"
        elif severe_count >= 2:
            return "High"
        elif severe_count >= 1:
            return "Medium"
        else:
            return "Low"

    def _estimate_response_time(self, active_alerts: List[Dict]) -> str:
        """Estimate required response time based on alert severity"""
        if not active_alerts:
            return "24 hours"

        max_severity = max(alert['severity'] for alert in active_alerts)

        response_times = {
            'critical': "30 minutes",
            'very_severe': "2 hours",
            'severe': "4 hours",
            'warning': "24 hours"
        }

        return response_times.get(max_severity, "24 hours")

    def _query_employee_workload(self, employee_id: str, date):
        """Query employee's current workload"""
        # Mock implementation
        return [
            {
                'work_order_id': 2001,
                'duration_minutes': 120,
                'start_time': '09:00',
                'end_time': '11:00'
            }
        ]

    def _check_time_conflicts(self, employee_id: str, recommended_time):
        """Check for time conflicts for employee"""
        # Mock implementation - return empty list (no conflicts)
        return []

    def _find_location_by_name(self, location_name: str):
        """Find location by name"""
        for location in self.locations.values():
            if location.location_name == location_name:
                return location
        return None

    def _calculate_pattern_impact(self, recommendation):
        """Calculate business impact for pattern-based recommendations"""
        return {
            'type': 'efficiency_improvement',
            'estimated_savings': 150.0,
            'risk_reduction': 'medium',
            'service_level_impact': 'positive'
        }

    def _calculate_alert_impact(self, recommendation):
        """Calculate business impact for alert-triggered recommendations"""
        return {
            'type': 'risk_mitigation',
            'estimated_savings': 500.0,
            'risk_reduction': 'high',
            'service_level_impact': 'critical'
        }

    def _calculate_metric_impact(self, recommendation):
        """Calculate business impact for metric-driven recommendations"""
        return {
            'type': 'performance_restoration',
            'estimated_savings': 300.0,
            'risk_reduction': 'medium',
            'service_level_impact': 'positive'
        }

    def _calculate_default_impact(self, recommendation):
        """Calculate default business impact"""
        return {
            'type': 'maintenance',
            'estimated_savings': 100.0,
            'risk_reduction': 'low',
            'service_level_impact': 'neutral'
        }
    def _calculate_skill_match(self, employee: Employee, required_skills: List[str]) -> float:
        """Calculate how well employee skills match requirements"""
        if not required_skills:
            return 1.0

        employee_skills = set(skill.skill_name for skill in employee.skills)
        matched_skills = len(set(required_skills).intersection(employee_skills))
        return matched_skills / len(required_skills)

    def _calculate_assignee_score(self, employee: Employee, availability_percentage: float) -> float:
        """Calculate overall score for assignee recommendation"""
        base_score = (employee.efficiency_rating / 10.0) * 0.4
        availability_score = (availability_percentage / 100.0) * 0.3
        cost_score = (1.0 - min(employee.hourly_rate / 50.0, 1.0)) * 0.3  # Lower cost = higher score

        return base_score + availability_score + cost_score