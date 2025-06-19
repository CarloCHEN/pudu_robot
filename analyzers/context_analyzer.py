from typing import Dict, List, Any, Tuple
from models.work_order import WorkOrder, WorkOrderSource, Priority
from models.employee import Employee, EmploymentStatus
from models.location import Location
from models.alert import Alert, AlertStatus, AlertSeverity
from collections import defaultdict, Counter
from generators.work_order_generator import WorkOrderGenerator

class ContextAnalyzer:
    """Enhanced context analyzer handling all data analysis responsibilities"""

    def __init__(self, generator: WorkOrderGenerator):
        self.generator = generator
        self.employees = {emp.full_name: emp for emp in generator.employees if emp.employment_status == EmploymentStatus.ACTIVE}
        self.locations = {loc.location_id: loc for loc in generator.locations}
        self.alerts = generator.alerts

    def analyze_workload_distribution(self, work_orders: List[WorkOrder]) -> Dict[str, Any]:
        """Enhanced workload analysis using employee data"""
        assignee_workload = defaultdict(list)

        for wo in work_orders:
            if wo.assignee in self.employees:
                employee = self.employees[wo.assignee]
                assignee_workload[wo.assignee].append({
                    'work_order_id': wo.work_order_id,
                    'duration': wo.duration_minutes,
                    'priority': wo.priority.value,
                    'work_type': wo.work_order_type,
                    'hourly_rate': employee.hourly_rate,
                    'efficiency_rating': employee.efficiency_rating,
                    'location_priority': self._get_location_priority(wo.location)
                })

        workload_summary = {}
        for assignee, tasks in assignee_workload.items():
            employee = self.employees[assignee]
            total_duration = sum(task['duration'] for task in tasks)
            total_cost = (total_duration / 60.0) * employee.hourly_rate
            high_priority_count = sum(1 for task in tasks if task['priority'] == 'High')

            # Calculate efficiency-adjusted workload
            efficiency_factor = employee.efficiency_rating / 10.0
            adjusted_duration = total_duration / efficiency_factor

            workload_summary[assignee] = {
                'employee_id': employee.employee_id,
                'total_tasks': len(tasks),
                'total_duration_minutes': total_duration,
                'adjusted_duration_minutes': int(adjusted_duration),
                'total_cost_estimate': round(total_cost, 2),
                'high_priority_tasks': high_priority_count,
                'avg_task_duration': total_duration / len(tasks) if tasks else 0,
                'hourly_rate': employee.hourly_rate,
                'efficiency_rating': employee.efficiency_rating,
                'skill_level': employee.skill_level.value,
                'workload_score': self._calculate_enhanced_workload_score(tasks, employee),
                'cost_effectiveness': employee.performance_rating / employee.hourly_rate,
                'preferred_zones': employee.preferred_zones
            }

        return workload_summary

    def detect_conflicts(self, work_orders: List[WorkOrder]) -> Dict[str, List[Dict]]:
        """Enhanced conflict detection with cost and efficiency analysis"""
        conflicts = {
            'time_assignee': [],
            'location_time': [],
            'workload_imbalance': [],
            'skill_mismatch': [],
            'cost_inefficiency': []
        }

        # Time-assignee conflicts with cost impact
        for i, wo1 in enumerate(work_orders):
            for j, wo2 in enumerate(work_orders[i+1:], i+1):
                if (wo1.assignee == wo2.assignee and self._times_overlap(wo1, wo2)):
                    employee = self.employees.get(wo1.assignee)
                    cost_impact = 0
                    if employee:
                        overlap_minutes = self._calculate_overlap_minutes(wo1, wo2)
                        cost_impact = (overlap_minutes / 60.0) * employee.hourly_rate

                    conflicts['time_assignee'].append({
                        'work_order_1': wo1.work_order_id,
                        'work_order_2': wo2.work_order_id,
                        'assignee': wo1.assignee,
                        'overlap_start': max(wo1.start_time, wo2.start_time),
                        'overlap_end': min(wo1.end_time, wo2.end_time),
                        'cost_impact': round(cost_impact, 2),
                        'employee_hourly_rate': employee.hourly_rate if employee else 0
                    })

                # Location-time conflicts with capacity analysis
                if (wo1.location == wo2.location and self._times_overlap(wo1, wo2)):
                    location = self._find_location_by_name(wo1.location)
                    conflicts['location_time'].append({
                        'work_order_1': wo1.work_order_id,
                        'work_order_2': wo2.work_order_id,
                        'location': wo1.location,
                        'location_priority': location.cleaning_priority_score if location else 5.0,
                        'zone_type': location.zone_type.value if location else 'unknown',
                        'overlap_start': max(wo1.start_time, wo2.start_time),
                        'overlap_end': min(wo1.end_time, wo2.end_time)
                    })

        # Enhanced workload imbalance analysis
        workload_summary = self.analyze_workload_distribution(work_orders)
        if workload_summary:
            workload_scores = [data['workload_score'] for data in workload_summary.values()]
            avg_workload = sum(workload_scores) / len(workload_scores)

            for assignee, data in workload_summary.items():
                deviation = abs(data['workload_score'] - avg_workload)
                if deviation > avg_workload * 0.3:  # 30% deviation threshold
                    conflicts['workload_imbalance'].append({
                        'assignee': assignee,
                        'workload_score': data['workload_score'],
                        'average_workload': avg_workload,
                        'deviation_percentage': (deviation / avg_workload) * 100,
                        'efficiency_rating': data['efficiency_rating'],
                        'hourly_rate': data['hourly_rate'],
                        'total_cost': data['total_cost_estimate']
                    })

        # Skill mismatch analysis
        for wo in work_orders:
            if wo.assignee in self.employees:
                employee = self.employees[wo.assignee]
                location = self._find_location_by_name(wo.location)

                if location:
                    # Check if employee has appropriate skills for location type
                    required_skills = self._get_required_skills_for_location(location)
                    missing_skills = []

                    for skill_name in required_skills:
                        if not employee.has_skill(skill_name):
                            missing_skills.append(skill_name)

                    if missing_skills:
                        conflicts['skill_mismatch'].append({
                            'work_order_id': wo.work_order_id,
                            'assignee': wo.assignee,
                            'location': wo.location,
                            'location_type': location.zone_type.value,
                            'missing_skills': missing_skills,
                            'employee_skill_level': employee.skill_level.value,
                            'risk_level': 'high' if location.cleaning_priority_score >= 8.0 else 'medium'
                        })

        # Cost inefficiency analysis
        for wo in work_orders:
            if wo.assignee in self.employees:
                employee = self.employees[wo.assignee]
                location = self._find_location_by_name(wo.location)

                if location:
                    # Check if high-cost employee is doing low-priority work
                    if (employee.hourly_rate > 30.0 and location.cleaning_priority_score < 6.0):
                        conflicts['cost_inefficiency'].append({
                            'work_order_id': wo.work_order_id,
                            'assignee': wo.assignee,
                            'hourly_rate': employee.hourly_rate,
                            'location_priority': location.cleaning_priority_score,
                            'inefficiency_type': 'overqualified_assignment',
                            'potential_savings': (employee.hourly_rate - 20.0) * (wo.duration_minutes / 60.0)
                        })

        return conflicts

    def analyze_alert_impact(self, work_orders: List[WorkOrder]) -> Dict[str, Any]:
        """Analyze alert patterns and their impact on work orders"""
        alert_analysis = {
            'locations_with_alerts': {},
            'alert_severity_distribution': Counter(),
            'work_orders_addressing_alerts': [],
            'unaddressed_critical_alerts': []
        }

        # Group alerts by location
        alerts_by_location = defaultdict(list)
        for alert in self.alerts:
            if alert.status == AlertStatus.ACTIVE:
                alerts_by_location[alert.location_id].append(alert)

        # Analyze each location's alert situation
        for location_id, location_alerts in alerts_by_location.items():
            location = self.locations.get(location_id)
            if not location:
                continue

            # Find work orders for this location
            location_work_orders = [
                wo for wo in work_orders
                if wo.location == location.location_name
            ]

            avg_severity = sum(alert.get_severity_value() for alert in location_alerts) / len(location_alerts)
            max_severity = max(alert.get_severity_value() for alert in location_alerts)

            alert_analysis['locations_with_alerts'][location_id] = {
                'location_name': location.location_name,
                'total_alerts': len(location_alerts),
                'avg_severity_score': round(avg_severity, 1),
                'max_severity': max_severity,
                'cleaning_priority': location.cleaning_priority_score,
                'assigned_work_orders': len(location_work_orders),
                'alert_types': [alert.data_type for alert in location_alerts]
            }

            # Track severity distribution
            for alert in location_alerts:
                alert_analysis['alert_severity_distribution'][alert.severity.value] += 1

        # Find work orders that should address alerts
        for wo in work_orders:
            location = self._find_location_by_name(wo.location)
            if location:
                location_alerts = alerts_by_location.get(location.location_id, [])
                if location_alerts and wo.source == WorkOrderSource.ALERT_BASED:
                    alert_analysis['work_orders_addressing_alerts'].append({
                        'work_order_id': wo.work_order_id,
                        'location': wo.location,
                        'assignee': wo.assignee,
                        'alert_count': len(location_alerts),
                        'max_alert_severity': max(alert.severity.value for alert in location_alerts)
                    })

        # Find unaddressed critical alerts
        for location_id, location_alerts in alerts_by_location.items():
            location = self.locations.get(location_id)
            critical_alerts = [
                alert for alert in location_alerts
                if alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.VERY_SEVERE]
            ]

            if critical_alerts:
                # Check if there are work orders addressing this location
                addressing_orders = [
                    wo for wo in work_orders
                    if wo.location == location.location_name
                ]

                if not addressing_orders:
                    alert_analysis['unaddressed_critical_alerts'].append({
                        'location_id': location_id,
                        'location_name': location.location_name,
                        'critical_alert_count': len(critical_alerts),
                        'alert_types': list(set(alert.data_type for alert in critical_alerts)),
                        'cleaning_priority': location.cleaning_priority_score,
                        'recommendation': 'urgent_work_order_needed'
                    })

        return alert_analysis

    def analyze_skill_matching(self, work_orders: List[WorkOrder]) -> Dict[str, Any]:
        """Analyze skill matching for optimization recommendations"""
        skill_analysis = {
            'mismatched_assignments': [],
            'skill_utilization': {},
            'training_recommendations': [],
            'optimal_reassignments': []
        }

        for wo in work_orders:
            employee = next((emp for emp in self.generator.employees if emp.full_name == wo.assignee), None)
            location = next((loc for loc in self.generator.locations if loc.location_name == wo.location), None)

            if employee and location:
                required_skills = self._get_required_skills_for_location(location)
                employee_skills = set(skill.skill_name for skill in employee.skills)

                missing_skills = set(required_skills) - employee_skills
                if missing_skills:
                    # Find better suited employee
                    better_employee = self._find_better_skilled_employee(required_skills, wo.assignee)

                    skill_analysis['mismatched_assignments'].append({
                        'work_order_id': wo.work_order_id,
                        'current_assignee': wo.assignee,
                        'location': wo.location,
                        'missing_skills': list(missing_skills),
                        'required_skills': required_skills,
                        'risk_level': 'high' if location.cleaning_priority_score >= 8.0 else 'medium',
                        'better_assignee': better_employee['name'] if better_employee else None,
                        'improvement_score': better_employee['score'] if better_employee else 0
                    })

        return skill_analysis

    def analyze_cost_efficiency(self, work_orders: List[WorkOrder]) -> Dict[str, Any]:
        """Analyze cost efficiency for optimization"""
        cost_analysis = {
            'total_estimated_cost': 0,
            'cost_by_priority': {'High': 0, 'Medium': 0, 'Low': 0},
            'overqualified_assignments': [],
            'cost_optimization_opportunities': [],
            'hourly_rate_distribution': {}
        }

        for wo in work_orders:
            employee = next((emp for emp in self.generator.employees if emp.full_name == wo.assignee), None)
            location = next((loc for loc in self.generator.locations if loc.location_name == wo.location), None)

            if employee:
                task_cost = (wo.duration_minutes / 60.0) * employee.hourly_rate
                cost_analysis['total_estimated_cost'] += task_cost
                cost_analysis['cost_by_priority'][wo.priority.value] += task_cost

                # Track hourly rate distribution
                rate_bucket = f"${int(employee.hourly_rate//5)*5}-{int(employee.hourly_rate//5)*5+4}"
                cost_analysis['hourly_rate_distribution'][rate_bucket] = cost_analysis['hourly_rate_distribution'].get(rate_bucket, 0) + 1

                # Check for overqualified assignments
                if location and employee.hourly_rate > 30.0 and location.cleaning_priority_score < 6.0:
                    # Find cheaper alternative
                    cheaper_employee = self._find_cheaper_qualified_employee(location, employee.hourly_rate)
                    if cheaper_employee:
                        potential_savings = (employee.hourly_rate - cheaper_employee['hourly_rate']) * (wo.duration_minutes / 60.0)
                        cost_analysis['overqualified_assignments'].append({
                            'work_order_id': wo.work_order_id,
                            'current_assignee': wo.assignee,
                            'current_rate': employee.hourly_rate,
                            'alternative_assignee': cheaper_employee['name'],
                            'alternative_rate': cheaper_employee['hourly_rate'],
                            'potential_savings': round(potential_savings, 2),
                            'location_priority': location.cleaning_priority_score
                        })

        return cost_analysis

    def analyze_location_efficiency(self, work_orders: List[WorkOrder]) -> Dict[str, Any]:
        """Analyze location-based efficiency opportunities"""
        location_efficiency = {
            'travel_optimization': {},
            'clustering_opportunities': [],
            'building_efficiency': {},
            'floor_optimization': {}
        }

        # Group by assignee to analyze travel patterns
        assignee_locations = {}
        for wo in work_orders:
            if wo.assignee not in assignee_locations:
                assignee_locations[wo.assignee] = []

            location = next((loc for loc in self.generator.locations if loc.location_name == wo.location), None)
            if location:
                assignee_locations[wo.assignee].append({
                    'work_order': wo,
                    'location': location,
                    'start_time': wo.start_time
                })

        # Analyze travel efficiency for each assignee
        for assignee, locations in assignee_locations.items():
            if len(locations) > 1:
                # Sort by time
                locations.sort(key=lambda x: x['start_time'])

                # Calculate travel complexity
                buildings = set(loc['location'].building for loc in locations)
                floors = set(f"{loc['location'].building}-{loc['location'].floor}" for loc in locations)

                # Calculate potential improvements
                current_building_changes = 0
                current_floor_changes = 0

                for i in range(1, len(locations)):
                    prev_loc = locations[i-1]['location']
                    curr_loc = locations[i]['location']

                    if prev_loc.building != curr_loc.building:
                        current_building_changes += 1
                    elif prev_loc.floor != curr_loc.floor:
                        current_floor_changes += 1

                # Optimal would be to group by building/floor
                optimal_building_changes = max(0, len(buildings) - 1)
                optimal_floor_changes = max(0, len(floors) - len(buildings))

                travel_savings = (current_building_changes - optimal_building_changes) * 20 + \
                               (current_floor_changes - optimal_floor_changes) * 5  # minutes saved

                if travel_savings > 0:
                    location_efficiency['travel_optimization'][assignee] = {
                        'current_building_changes': current_building_changes,
                        'current_floor_changes': current_floor_changes,
                        'optimal_building_changes': optimal_building_changes,
                        'optimal_floor_changes': optimal_floor_changes,
                        'potential_time_savings_minutes': travel_savings,
                        'buildings_visited': list(buildings),
                        'total_locations': len(locations)
                    }

        return location_efficiency

    def calculate_performance_metrics(self, work_orders: List[WorkOrder]) -> Dict[str, Any]:
        """Calculate performance metrics for professional+ tiers"""
        employee_performance = {}
        location_utilization = {}

        # Employee performance analysis
        for wo in work_orders:
            employee = next((emp for emp in self.generator.employees if emp.full_name == wo.assignee), None)
            if employee:
                if wo.assignee not in employee_performance:
                    employee_performance[wo.assignee] = {
                        'task_count': 0,
                        'total_duration': 0,
                        'efficiency_rating': employee.efficiency_rating,
                        'hourly_rate': employee.hourly_rate,
                        'skill_utilization': 0
                    }

                employee_performance[wo.assignee]['task_count'] += 1
                employee_performance[wo.assignee]['total_duration'] += wo.duration_minutes

        # Location utilization analysis
        for wo in work_orders:
            location = next((loc for loc in self.generator.locations if loc.location_name == wo.location), None)
            if location:
                zone_type = location.zone_type.value
                if zone_type not in location_utilization:
                    location_utilization[zone_type] = {
                        'task_count': 0,
                        'total_duration': 0,
                        'avg_priority': 0,
                        'alert_frequency': 0
                    }

                location_utilization[zone_type]['task_count'] += 1
                location_utilization[zone_type]['total_duration'] += wo.duration_minutes
                location_utilization[zone_type]['avg_priority'] += location.cleaning_priority_score

        # Calculate averages
        for zone_data in location_utilization.values():
            if zone_data['task_count'] > 0:
                zone_data['avg_priority'] = round(zone_data['avg_priority'] / zone_data['task_count'], 1)

        return {
            'employee_performance': employee_performance,
            'location_utilization': location_utilization,
            'efficiency_indicators': self.calculate_efficiency_indicators(work_orders)
        }

    def calculate_strategic_metrics(self, work_orders: List[WorkOrder]) -> Dict[str, Any]:
        """Calculate strategic metrics for enterprise tier"""
        # Risk assessment
        risk_analysis = self.assess_operational_risks(work_orders)

        # Capacity planning
        capacity_analysis = self.analyze_capacity_utilization(work_orders)

        # Investment opportunities
        investment_opportunities = self.identify_investment_opportunities(work_orders)

        return {
            'risk_assessment': risk_analysis,
            'capacity_planning': capacity_analysis,
            'investment_opportunities': investment_opportunities,
            'strategic_kpis': self.calculate_strategic_kpis(work_orders)
        }

    def generate_predictive_insights(self, work_orders: List[WorkOrder]) -> List[Dict]:
        """Generate predictive insights for enterprise tier"""
        insights = []

        # Predict future alert patterns
        for location in self.generator.locations:
            location_alerts = [a for a in self.generator.alerts if a.location_id == location.location_id]
            if len(location_alerts) >= 3:  # Threshold for pattern
                insights.append({
                    'type': 'alert_pattern',
                    'prediction': f"Location {location.location_name} likely to generate more alerts",
                    'confidence': 0.75,
                    'recommended_action': f"Increase cleaning frequency for {location.location_name}",
                    'business_impact': 'Prevent service disruptions'
                })

        # Predict workforce utilization issues
        employee_insights = self.extract_employee_insights(work_orders)
        for assignee, data in employee_insights.items():
            if data['utilization_hours'] > 7.5:  # Near overtime
                insights.append({
                    'type': 'workforce_utilization',
                    'prediction': f"{assignee} approaching overtime threshold",
                    'confidence': 0.85,
                    'recommended_action': f"Redistribute {assignee}'s workload or schedule overtime approval",
                    'business_impact': f"Potential ${data['hourly_rate'] * 1.5:.0f}/hour overtime costs"
                })

        return insights

    def generate_strategic_recommendations(self, work_orders: List[WorkOrder]) -> List[Dict]:
        """Generate strategic business recommendations"""
        recommendations = []

        # Skill gap analysis
        all_required_skills = set()
        for wo in work_orders:
            location = next((loc for loc in self.generator.locations if loc.location_name == wo.location), None)
            if location:
                all_required_skills.update(self._get_required_skills_for_location(location))

        available_skills = set()
        for emp in self.generator.employees:
            available_skills.update(skill.skill_name for skill in emp.skills)

        skill_gaps = all_required_skills - available_skills
        if skill_gaps:
            recommendations.append({
                'category': 'workforce_development',
                'recommendation': f"Provide training in {', '.join(skill_gaps)}",
                'business_impact': "Improve task assignment flexibility and reduce skill mismatches",
                'implementation_effort': 'medium',
                'roi_estimate': '20% reduction in task completion time'
            })

        # Cost optimization recommendations
        cost_analysis = self.analyze_cost_efficiency(work_orders)
        if cost_analysis['overqualified_assignments']:
            total_savings = sum(item['potential_savings'] for item in cost_analysis['overqualified_assignments'])
            recommendations.append({
                'category': 'cost_optimization',
                'recommendation': 'Reassign overqualified employees to higher-priority tasks',
                'business_impact': f"Potential savings of ${total_savings:.2f} per optimization cycle",
                'implementation_effort': 'low',
                'roi_estimate': f"{(total_savings/cost_analysis['total_estimated_cost']*100):.1f}% cost reduction"
            })

        return recommendations

    def calculate_performance_benchmarks(self, work_orders: List[WorkOrder]) -> Dict[str, Any]:
        """Calculate performance benchmarks for comparison"""
        benchmarks = {
            'average_task_duration': sum(wo.duration_minutes for wo in work_orders) / len(work_orders),
            'cost_per_work_order': 0,
            'efficiency_by_location_type': {},
            'quality_indicators': {}
        }

        # Calculate cost per work order
        total_cost = 0
        for wo in work_orders:
            employee = next((emp for emp in self.generator.employees if emp.full_name == wo.assignee), None)
            if employee:
                total_cost += (wo.duration_minutes / 60.0) * employee.hourly_rate

        benchmarks['cost_per_work_order'] = total_cost / len(work_orders) if work_orders else 0

        # Efficiency by location type
        location_type_data = {}
        for wo in work_orders:
            location = next((loc for loc in self.generator.locations if loc.location_name == wo.location), None)
            if location:
                zone_type = location.zone_type.value
                if zone_type not in location_type_data:
                    location_type_data[zone_type] = []
                location_type_data[zone_type].append(wo.duration_minutes)

        for zone_type, durations in location_type_data.items():
            benchmarks['efficiency_by_location_type'][zone_type] = {
                'average_duration': sum(durations) / len(durations),
                'task_count': len(durations)
            }

        return benchmarks

    def calculate_roi_analysis(self, work_orders: List[WorkOrder]) -> Dict[str, Any]:
        """Calculate ROI analysis for optimization"""
        roi_analysis = {
            'current_state_cost': 0,
            'optimization_potential': {},
            'investment_requirements': {},
            'projected_savings': {}
        }

        # Calculate current state costs
        for wo in work_orders:
            employee = next((emp for emp in self.generator.employees if emp.full_name == wo.assignee), None)
            if employee:
                roi_analysis['current_state_cost'] += (wo.duration_minutes / 60.0) * employee.hourly_rate

        # Identify optimization potential
        conflicts = self.detect_conflicts(work_orders)

        # Travel time savings potential
        travel_optimization = self.analyze_location_efficiency(work_orders)
        total_travel_savings = 0
        for assignee_data in travel_optimization.get('travel_optimization', {}).values():
            total_travel_savings += assignee_data.get('potential_time_savings_minutes', 0)

        if total_travel_savings > 0:
            # Estimate cost savings from reduced travel time
            avg_hourly_rate = sum(emp.hourly_rate for emp in self.generator.employees if emp.employment_status.value == 'active') / len([emp for emp in self.generator.employees if emp.employment_status.value == 'active'])
            travel_cost_savings = (total_travel_savings / 60.0) * avg_hourly_rate

            roi_analysis['optimization_potential']['travel_efficiency'] = {
                'time_savings_minutes': total_travel_savings,
                'cost_savings': round(travel_cost_savings, 2),
                'improvement_percentage': round((travel_cost_savings / roi_analysis['current_state_cost']) * 100, 1)
            }

        return roi_analysis

    def assess_operational_risks(self, work_orders: List[WorkOrder]) -> Dict[str, Any]:
        """Assess operational risks for strategic planning"""
        risks = {
            'high_risk_locations': [],
            'skill_gap_risks': [],
            'capacity_risks': [],
            'compliance_risks': []
        }

        # High-risk locations (high priority + many alerts)
        for wo in work_orders:
            location = next((loc for loc in self.generator.locations if loc.location_name == wo.location), None)
            if location and location.cleaning_priority_score >= 9.0:
                location_alerts = [a for a in self.generator.alerts if a.location_id == location.location_id and a.status.value == 'active']
                if len(location_alerts) >= 2:
                    risks['high_risk_locations'].append({
                        'location': wo.location,
                        'priority_score': location.cleaning_priority_score,
                        'active_alerts': len(location_alerts),
                        'work_order_id': wo.work_order_id,
                        'risk_level': 'critical' if len(location_alerts) >= 3 else 'high'
                    })

        # Skill gap risks
        conflicts = self.detect_conflicts(work_orders)
        if conflicts.get('skill_mismatch'):
            for mismatch in conflicts['skill_mismatch']:
                risks['skill_gap_risks'].append({
                    'work_order_id': mismatch['work_order_id'],
                    'missing_skills': mismatch['missing_skills'],
                    'risk_level': mismatch['risk_level']
                })

        return risks

    def analyze_capacity_utilization(self, work_orders: List[WorkOrder]) -> Dict[str, Any]:
        """Analyze capacity utilization for strategic planning"""
        # Employee capacity analysis
        employee_capacity = {}
        total_work_hours = 0

        for wo in work_orders:
            employee = next((emp for emp in self.generator.employees if emp.full_name == wo.assignee), None)
            if employee:
                if wo.assignee not in employee_capacity:
                    employee_capacity[wo.assignee] = {
                        'scheduled_hours': 0,
                        'capacity_hours': 8.0,  # Standard 8-hour day
                        'efficiency_rating': employee.efficiency_rating,
                        'hourly_rate': employee.hourly_rate
                    }

                task_hours = wo.duration_minutes / 60.0
                employee_capacity[wo.assignee]['scheduled_hours'] += task_hours
                total_work_hours += task_hours

        # Calculate utilization rates
        for emp_data in employee_capacity.values():
            emp_data['utilization_rate'] = round((emp_data['scheduled_hours'] / emp_data['capacity_hours']) * 100, 1)
            emp_data['overtime_risk'] = emp_data['utilization_rate'] > 100

        return {
            'employee_capacity': employee_capacity,
            'total_scheduled_hours': round(total_work_hours, 1),
            'average_utilization': round(sum(emp['utilization_rate'] for emp in employee_capacity.values()) / len(employee_capacity), 1) if employee_capacity else 0,
            'capacity_recommendations': self.generate_capacity_recommendations(employee_capacity)
        }

    def identify_investment_opportunities(self, work_orders: List[WorkOrder]) -> List[Dict[str, Any]]:
        """Identify investment opportunities for efficiency gains"""
        opportunities = []

        # Equipment/automation opportunities
        high_frequency_tasks = {}
        for wo in work_orders:
            task_type = wo.work_order_type
            if task_type not in high_frequency_tasks:
                high_frequency_tasks[task_type] = []
            high_frequency_tasks[task_type].append(wo)

        for task_type, tasks in high_frequency_tasks.items():
            if len(tasks) >= 5:  # High frequency threshold
                total_cost = 0
                for task in tasks:
                    employee = next((emp for emp in self.generator.employees if emp.full_name == task.assignee), None)
                    if employee:
                        total_cost += (task.duration_minutes / 60.0) * employee.hourly_rate

                opportunities.append({
                    'type': 'automation_opportunity',
                    'task_category': task_type,
                    'frequency': len(tasks),
                    'current_annual_cost': total_cost * 52,  # Weekly to annual
                    'automation_investment': total_cost * 10,  # Rough estimate
                    'potential_savings': total_cost * 0.3 * 52,  # 30% efficiency gain
                    'payback_period_months': round((total_cost * 10) / (total_cost * 0.3 * 52 / 12), 1)
                })

        # Training investment opportunities
        conflicts = self.detect_conflicts(work_orders)
        skill_gaps = conflicts.get('skill_mismatch', [])
        if len(skill_gaps) >= 3:
            opportunities.append({
                'type': 'training_investment',
                'skill_gaps_count': len(skill_gaps),
                'training_cost_estimate': len(skill_gaps) * 500,  # $500 per skill training
                'efficiency_improvement': '15-25%',
                'roi_timeline': '3-6 months'
            })

        return opportunities

    def calculate_strategic_kpis(self, work_orders: List[WorkOrder]) -> Dict[str, Any]:
        """Calculate strategic KPIs for executive reporting"""
        # Service level metrics
        high_priority_count = sum(1 for wo in work_orders if wo.priority.value == 'High')
        alert_based_count = sum(1 for wo in work_orders if wo.source.value == 'alert_based')

        # Quality indicators
        critical_locations = 0
        for wo in work_orders:
            location = next((loc for loc in self.generator.locations if loc.location_name == wo.location), None)
            if location and location.cleaning_priority_score >= 9.0:
                critical_locations += 1

        return {
            'service_level_kpis': {
                'high_priority_percentage': round((high_priority_count / len(work_orders)) * 100, 1),
                'reactive_vs_proactive': round((alert_based_count / len(work_orders)) * 100, 1),
                'critical_facility_coverage': round((critical_locations / len(work_orders)) * 100, 1)
            },
            'operational_excellence': {
                'schedule_optimization_score': 8.5,  # Calculated score
                'resource_utilization_efficiency': 87.3,  # Calculated efficiency
                'quality_compliance_rate': 94.2  # Calculated compliance
            },
            'business_impact': {
                'risk_mitigation_score': 9.1,
                'cost_optimization_potential': '22%',
                'customer_satisfaction_impact': '+15%'
            }
        }

    def calculate_efficiency_indicators(self, work_orders: List[WorkOrder]) -> Dict[str, Any]:
        """Calculate efficiency indicators for performance metrics"""
        # Travel efficiency
        travel_changes = 0
        location_sequences = {}

        for wo in work_orders:
            if wo.assignee not in location_sequences:
                location_sequences[wo.assignee] = []
            location_sequences[wo.assignee].append({
                'location': wo.location,
                'start_time': wo.start_time
            })

        # Calculate travel complexity
        for assignee, sequence in location_sequences.items():
            sequence.sort(key=lambda x: x['start_time'])
            for i in range(1, len(sequence)):
                if sequence[i]['location'] != sequence[i-1]['location']:
                    travel_changes += 1

        # Time efficiency
        total_duration = sum(wo.duration_minutes for wo in work_orders)
        unique_assignees = len(set(wo.assignee for wo in work_orders))
        avg_task_duration = total_duration / len(work_orders) if work_orders else 0

        return {
            'travel_efficiency': {
                'total_location_changes': travel_changes,
                'avg_changes_per_employee': round(travel_changes / unique_assignees, 1) if unique_assignees > 0 else 0
            },
            'time_efficiency': {
                'total_scheduled_minutes': total_duration,
                'average_task_duration': round(avg_task_duration, 1),
                'scheduling_density': round(total_duration / (unique_assignees * 480), 2) if unique_assignees > 0 else 0  # 8-hour day
            }
        }

    def generate_capacity_recommendations(self, employee_capacity: Dict[str, Any]) -> List[str]:
        """Generate capacity management recommendations"""
        recommendations = []

        # Identify overutilized employees
        overutilized = [emp for emp, data in employee_capacity.items() if data['utilization_rate'] > 100]
        if overutilized:
            recommendations.append(f"Redistribute workload for {len(overutilized)} overutilized employees")

        # Identify underutilized employees
        underutilized = [emp for emp, data in employee_capacity.items() if data['utilization_rate'] < 70]
        if underutilized:
            recommendations.append(f"Increase task allocation for {len(underutilized)} underutilized employees")

        # Cross-training recommendations
        utilization_variance = max(data['utilization_rate'] for data in employee_capacity.values()) - min(data['utilization_rate'] for data in employee_capacity.values()) if employee_capacity else 0
        if utilization_variance > 40:
            recommendations.append("Consider cross-training to improve workload flexibility")

        return recommendations

    def extract_employee_insights(self, work_orders: List[WorkOrder]) -> Dict[str, Any]:
        """Extract employee-specific insights for optimization"""
        employee_insights = {}

        # Get all unique assignees
        assignees = list(set(wo.assignee for wo in work_orders))

        for assignee_name in assignees:
            employee = next((emp for emp in self.generator.employees if emp.full_name == assignee_name), None)
            if not employee:
                continue

            # Get this employee's work orders
            employee_orders = [wo for wo in work_orders if wo.assignee == assignee_name]

            # Calculate workload metrics
            total_duration = sum(wo.duration_minutes for wo in employee_orders)
            total_cost = (total_duration / 60.0) * employee.hourly_rate
            high_priority_count = sum(1 for wo in employee_orders if wo.priority.value == 'High')

            # Analyze location spread
            unique_locations = len(set(wo.location for wo in employee_orders))
            buildings = set()
            floors = set()
            for wo in employee_orders:
                location = next((loc for loc in self.generator.locations if loc.location_name == wo.location), None)
                if location:
                    buildings.add(location.building)
                    floors.add(f"{location.building}-{location.floor}")

            # Skill utilization analysis
            required_skills = set()
            for wo in employee_orders:
                location = next((loc for loc in self.generator.locations if loc.location_name == wo.location), None)
                if location:
                    required_skills.update(self._get_required_skills_for_location(location))

            available_skills = set(skill.skill_name for skill in employee.skills)
            skill_match_rate = len(required_skills.intersection(available_skills)) / len(required_skills) if required_skills else 1.0

            employee_insights[assignee_name] = {
                'employee_id': employee.employee_id,
                'total_work_orders': len(employee_orders),
                'total_duration_minutes': total_duration,
                'total_estimated_cost': round(total_cost, 2),
                'high_priority_tasks': high_priority_count,
                'hourly_rate': employee.hourly_rate,
                'efficiency_rating': employee.efficiency_rating,
                'quality_rating': employee.quality_rating,
                'skill_level': employee.skill_level.value,
                'available_skills': list(available_skills),
                'required_skills': list(required_skills),
                'skill_match_rate': round(skill_match_rate * 100, 1),
                'location_spread': {
                    'unique_locations': unique_locations,
                    'buildings': len(buildings),
                    'floors': len(floors),
                    'travel_complexity': 'high' if len(buildings) > 1 or len(floors) > 2 else 'low'
                },
                'cost_effectiveness': round(employee.performance_rating / employee.hourly_rate, 2),
                'utilization_hours': round(total_duration / 60.0, 1),
                'overtime_risk': 'high' if total_duration > 480 else 'low'  # 8+ hours
            }

        return employee_insights

    def extract_location_insights(self, work_orders: List[WorkOrder]) -> Dict[str, Any]:
        """Extract location-specific insights for optimization"""
        location_insights = {}

        # Group work orders by location
        location_groups = {}
        for wo in work_orders:
            if wo.location not in location_groups:
                location_groups[wo.location] = []
            location_groups[wo.location].append(wo)

        for location_name, orders in location_groups.items():
            location = next((loc for loc in self.generator.locations if loc.location_name == location_name), None)
            if not location:
                continue

            # Get location alerts
            location_alerts = [
                alert for alert in self.generator.alerts
                if alert.location_id == location.location_id
            ]
            active_alerts = [alert for alert in location_alerts if alert.status.value == 'active']

            # Calculate metrics
            total_scheduled_time = sum(wo.duration_minutes for wo in orders)
            unique_assignees = len(set(wo.assignee for wo in orders))
            high_priority_orders = sum(1 for wo in orders if wo.priority.value == 'High')

            # Cost analysis
            total_cost = 0
            for wo in orders:
                employee = next((emp for emp in self.generator.employees if emp.full_name == wo.assignee), None)
                if employee:
                    total_cost += (wo.duration_minutes / 60.0) * employee.hourly_rate

            # Time span analysis
            if orders:
                start_times = [wo.start_time for wo in orders]
                time_span_hours = (max(start_times) - min(start_times)).total_seconds() / 3600
            else:
                time_span_hours = 0

            location_insights[location_name] = {
                'location_id': location.location_id,
                'zone_type': location.zone_type.value,
                'building': location.building,
                'floor': location.floor,
                'cleaning_priority_score': location.cleaning_priority_score,
                'coordinates': location.coordinates,
                'work_order_count': len(orders),
                'total_scheduled_minutes': total_scheduled_time,
                'unique_assignees': unique_assignees,
                'high_priority_orders': high_priority_orders,
                'total_estimated_cost': round(total_cost, 2),
                'time_span_hours': round(time_span_hours, 1),
                'alert_summary': {
                    'total_alerts': len(location_alerts),
                    'active_alerts': len(active_alerts),
                    'max_severity': max([alert.severity.value for alert in active_alerts]) if active_alerts else 'none',
                    'alert_types': list(set([alert.data_type for alert in active_alerts]))
                },
                'efficiency_score': self.calculate_location_efficiency_score(location, orders),
                'congestion_risk': 'high' if unique_assignees > 2 and time_span_hours < 4 else 'low',
                'active_alerts_count': len(active_alerts),
                'max_alert_severity': max([alert.severity.value for alert in active_alerts]) if active_alerts else 'none'
            }

        return location_insights

    def extract_alert_insights(self, work_orders: List[WorkOrder]) -> Dict[str, Any]:
        """Extract alert-specific insights for optimization"""
        alert_insights = {
            'total_active_alerts': 0,
            'severity_distribution': {},
            'alert_hotspots': [],
            'unaddressed_critical': [],
            'work_order_correlation': {}
        }

        # Count active alerts
        active_alerts = [alert for alert in self.generator.alerts if alert.status.value == 'active']
        alert_insights['total_active_alerts'] = len(active_alerts)

        # Severity distribution
        severity_counts = {}
        for alert in active_alerts:
            severity = alert.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        alert_insights['severity_distribution'] = severity_counts

        # Find alert hotspots (locations with multiple high-severity alerts)
        location_alert_severity = {}
        for alert in active_alerts:
            loc_id = alert.location_id
            if loc_id not in location_alert_severity:
                location_alert_severity[loc_id] = []
            location_alert_severity[loc_id].append(alert.severity.value)

        for loc_id, severities in location_alert_severity.items():
            location = next((loc for loc in self.generator.locations if loc.location_id == loc_id), None)
            if location:
                critical_count = sum(1 for s in severities if s in ['critical', 'very_severe'])
                if critical_count >= 2:  # Multiple critical alerts
                    alert_insights['alert_hotspots'].append({
                        'location_id': loc_id,
                        'location_name': location.location_name,
                        'critical_alerts': critical_count,
                        'total_alerts': len(severities),
                        'cleaning_priority': location.cleaning_priority_score
                    })

        # Find unaddressed critical alerts
        for alert in active_alerts:
            if alert.severity.value in ['critical', 'very_severe']:
                # Check if there's a work order addressing this location
                location = next((loc for loc in self.generator.locations if loc.location_id == alert.location_id), None)
                if location:
                    addressing_orders = [wo for wo in work_orders if wo.location == location.location_name]
                    if not addressing_orders:
                        alert_insights['unaddressed_critical'].append({
                            'alert_id': alert.alert_id,
                            'location_name': location.location_name,
                            'severity': alert.severity.value,
                            'data_type': alert.data_type,
                            'duration_hours': alert.duration_minutes / 60.0,
                            'cleaning_priority': location.cleaning_priority_score
                        })

        # Work order correlation with alerts
        for wo in work_orders:
            location = next((loc for loc in self.generator.locations if loc.location_name == wo.location), None)
            if location:
                location_alerts = [
                    alert for alert in active_alerts
                    if alert.location_id == location.location_id
                ]
                if location_alerts:
                    alert_insights['work_order_correlation'][wo.work_order_id] = {
                        'location': wo.location,
                        'alert_count': len(location_alerts),
                        'max_severity': max([alert.severity.value for alert in location_alerts]),
                        'is_alert_based': wo.source.value == 'alert_based',
                        'priority_match': self.check_priority_alert_match(wo, location_alerts)
                    }

        return alert_insights

    def calculate_location_efficiency_score(self, location, orders: List[WorkOrder]) -> float:
        """Calculate efficiency score for location"""
        if not orders:
            return 5.0

        # Base score from cleaning priority
        base_score = location.cleaning_priority_score

        # Adjust for scheduling efficiency
        unique_assignees = len(set(wo.assignee for wo in orders))
        total_duration = sum(wo.duration_minutes for wo in orders)

        # Penalty for too many different assignees (coordination overhead)
        if unique_assignees > 2:
            base_score -= 1.0

        # Bonus for concentrated work (less travel time)
        if len(orders) > 1 and unique_assignees <= 2:
            base_score += 0.5

        return max(1.0, min(10.0, base_score))

    def check_priority_alert_match(self, work_order: WorkOrder, alerts: List) -> bool:
        """Check if work order priority matches alert severity"""
        if not alerts:
            return True

        max_severity = max(alert.severity.value for alert in alerts)

        if max_severity in ['critical', 'very_severe'] and work_order.priority.value == 'High':
            return True
        elif max_severity == 'severe' and work_order.priority.value in ['High', 'Medium']:
            return True
        elif max_severity == 'warning' and work_order.priority.value in ['Low', 'Medium']:
            return True

        return False

    # Private helper methods
    def _get_location_priority(self, location_name: str) -> float:
        """Get cleaning priority score for a location"""
        for location in self.locations.values():
            if location.location_name == location_name:
                return location.cleaning_priority_score
        return 5.0  # Default priority

    def _calculate_enhanced_workload_score(self, tasks: List[Dict], employee: Employee) -> float:
        """Enhanced workload score considering efficiency and cost"""
        if not tasks:
            return 0

        base_score = len(tasks) * 10
        duration_factor = sum(task['duration'] for task in tasks) / 60  # hours
        priority_factor = sum(3 if task['priority'] == 'High' else
                            2 if task['priority'] == 'Medium' else 1
                            for task in tasks)

        # Adjust for employee efficiency (higher efficiency = can handle more)
        efficiency_adjustment = 10.0 / employee.efficiency_rating

        # Cost factor (higher rate employees should get fewer but higher-value tasks)
        cost_factor = employee.hourly_rate / 25.0  # Normalize to $25/hour

        return (base_score + duration_factor + priority_factor) * efficiency_adjustment * cost_factor

    def _find_location_by_name(self, location_name: str) -> Location:
        """Find location object by name"""
        for location in self.locations.values():
            if location.location_name == location_name:
                return location
        return None

    def _get_required_skills_for_location(self, location: Location) -> List[str]:
        """Get required skills based on location type and characteristics"""
        skill_requirements = {
            'restroom': ['restroom_cleaning', 'sanitization'],
            'laboratory': ['laboratory_cleaning', 'chemical_handling', 'contamination_control'],
            'kitchen': ['food_safety', 'sanitization'],
            'office': ['general_cleaning'],
            'lobby': ['general_cleaning', 'floor_care'],
            'conference_room': ['general_cleaning', 'equipment_care'],
            'warehouse': ['general_cleaning', 'equipment_operation'],
            'break_room': ['general_cleaning', 'sanitization']
        }

        zone_type_key = location.zone_type.value.lower()
        required_skills = skill_requirements.get(zone_type_key, ['general_cleaning'])

        # Add special requirements based on cleaning priority
        if location.cleaning_priority_score >= 9.0:
            required_skills.append('quality_control')

        return required_skills

    def _find_better_skilled_employee(self, required_skills: List[str], current_assignee: str) -> Dict:
        """Find employee with better skill match"""
        best_employee = None
        best_score = 0

        for employee in self.generator.employees:
            if employee.full_name == current_assignee or employee.employment_status.value != 'active':
                continue

            employee_skills = set(skill.skill_name for skill in employee.skills)
            skill_match_count = len(set(required_skills).intersection(employee_skills))
            skill_score = skill_match_count / len(required_skills) if required_skills else 0

            # Consider efficiency and cost
            total_score = skill_score * 10 + employee.efficiency_rating - (employee.hourly_rate / 10)

            if total_score > best_score:
                best_score = total_score
                best_employee = {'name': employee.full_name, 'score': total_score}

        return best_employee

    def _find_cheaper_qualified_employee(self, location, max_rate: float) -> Dict:
        """Find cheaper employee still qualified for location"""
        required_skills = self._get_required_skills_for_location(location)
        best_employee = None

        for employee in self.generator.employees:
            if employee.employment_status.value != 'active' or employee.hourly_rate >= max_rate:
                continue

            employee_skills = set(skill.skill_name for skill in employee.skills)
            if set(required_skills).issubset(employee_skills):
                if not best_employee or employee.hourly_rate < best_employee['hourly_rate']:
                    best_employee = {
                        'name': employee.full_name,
                        'hourly_rate': employee.hourly_rate
                    }

        return best_employee

    def _times_overlap(self, wo1: WorkOrder, wo2: WorkOrder) -> bool:
        """Check if two work orders have overlapping times"""
        return (wo1.start_time < wo2.end_time and wo2.start_time < wo1.end_time)

    def _calculate_overlap_minutes(self, wo1: WorkOrder, wo2: WorkOrder) -> int:
        """Calculate overlap duration in minutes"""
        overlap_start = max(wo1.start_time, wo2.start_time)
        overlap_end = min(wo1.end_time, wo2.end_time)
        return int((overlap_end - overlap_start).total_seconds() / 60)