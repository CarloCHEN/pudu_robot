import random
from datetime import datetime, timedelta
from typing import List, Dict
from models.work_order import WorkOrder, WorkOrderSource, Priority, WorkOrderStatus
from models.employee import Employee, EmployeeSkill, SkillLevel, EmploymentStatus
from models.location import Location, Zone, ZoneType, CleaningPriorityLevel
from models.alert import Alert, AlertSeverity, AlertStatus

class WorkOrderGenerator:
    """Work order generator using real data models"""

    def __init__(self):
        self.employees = self._create_employees()
        self.zones = self._create_zones()
        self.locations = self._create_locations()
        self.alerts = self._create_alerts()
        self.task_templates = self._create_task_templates()

    def _create_employees(self) -> List[Employee]:
        """Create realistic employee data with skills and rates"""
        employees = []

        # Senior cleaning specialist
        employees.append(Employee(
            employee_id="EMP001",
            first_name="John",
            last_name="Doe",
            email="john.doe@company.com",
            hourly_rate=25.0,
            overtime_rate=37.5,
            skill_level=SkillLevel.SENIOR,
            performance_rating=8.7,
            efficiency_rating=9.2,
            quality_rating=8.5,
            skills=[
                EmployeeSkill("restroom_cleaning", "cleaning", SkillLevel.EXPERT, 5.0),
                EmployeeSkill("floor_maintenance", "cleaning", SkillLevel.SENIOR, 4.0),
                EmployeeSkill("equipment_operation", "maintenance", SkillLevel.SENIOR, 3.5)
            ],
            preferred_zones=["HQ-F1", "HQ-F2"]
        ))

        # Laboratory specialist
        employees.append(Employee(
            employee_id="EMP002",
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@company.com",
            hourly_rate=30.0,
            overtime_rate=45.0,
            skill_level=SkillLevel.EXPERT,
            performance_rating=9.5,
            efficiency_rating=9.0,
            quality_rating=9.8,
            skills=[
                EmployeeSkill("laboratory_cleaning", "cleaning", SkillLevel.EXPERT, 6.0, True),
                EmployeeSkill("chemical_handling", "safety", SkillLevel.EXPERT, 5.5, True),
                EmployeeSkill("contamination_control", "safety", SkillLevel.EXPERT, 4.0, True)
            ],
            preferred_zones=["RC-F1", "RC-F2"]
        ))

        # General maintenance worker
        employees.append(Employee(
            employee_id="EMP003",
            first_name="Mike",
            last_name="Johnson",
            email="mike.johnson@company.com",
            hourly_rate=22.0,
            overtime_rate=33.0,
            skill_level=SkillLevel.JUNIOR,
            performance_rating=7.8,
            efficiency_rating=7.5,
            quality_rating=8.0,
            skills=[
                EmployeeSkill("general_cleaning", "cleaning", SkillLevel.SENIOR, 3.0),
                EmployeeSkill("equipment_setup", "maintenance", SkillLevel.JUNIOR, 2.0),
                EmployeeSkill("waste_management", "cleaning", SkillLevel.SENIOR, 3.5)
            ],
            preferred_zones=["WH-F1", "HQ-F1"]
        ))

        # Multi-skilled supervisor
        employees.append(Employee(
            employee_id="EMP004",
            first_name="Sarah",
            last_name="Williams",
            email="sarah.williams@company.com",
            hourly_rate=35.0,
            overtime_rate=52.5,
            skill_level=SkillLevel.EXPERT,
            performance_rating=9.0,
            efficiency_rating=8.8,
            quality_rating=9.2,
            skills=[
                EmployeeSkill("team_leadership", "management", SkillLevel.EXPERT, 7.0),
                EmployeeSkill("quality_inspection", "inspection", SkillLevel.EXPERT, 6.0, True),
                EmployeeSkill("emergency_response", "safety", SkillLevel.EXPERT, 5.0, True),
                EmployeeSkill("customer_service", "communication", SkillLevel.EXPERT, 8.0)
            ],
            preferred_zones=["HQ-F1", "HQ-F2", "RC-F1"]
        ))

        # Add more employees with varying skill levels...
        for i in range(4, 8):
            employees.append(Employee(
                employee_id=f"EMP{i+1:03d}",
                first_name=random.choice(["Alex", "Maria", "David", "Emily"]),
                last_name=random.choice(["Chen", "Rodriguez", "Brown", "Davis"]),
                email=f"employee{i+1}@company.com",
                hourly_rate=random.uniform(18.0, 28.0),
                overtime_rate=lambda r: r * 1.5,
                skill_level=random.choice(list(SkillLevel)),
                performance_rating=random.uniform(6.5, 9.0),
                efficiency_rating=random.uniform(6.0, 9.5),
                quality_rating=random.uniform(7.0, 9.0),
                skills=[
                    EmployeeSkill(
                        random.choice(["general_cleaning", "floor_care", "window_cleaning", "sanitization"]),
                        "cleaning",
                        random.choice(list(SkillLevel)),
                        random.uniform(1.0, 5.0)
                    )
                ]
            ))

        return employees

    def _create_zones(self) -> List[Zone]:
        """Create zones with realistic cleaning priority scores"""
        zones = [
            Zone("HQ-F1-RR", "Headquarters Floor 1 Restrooms", "HQ-001", 1,
                 ZoneType.RESTROOM, 9.2, 300.0, 10, "public", ["deep_cleaning", "sanitization"]),
            Zone("HQ-F1-LB", "Headquarters Floor 1 Lobby", "HQ-001", 1,
                 ZoneType.LOBBY, 8.5, 1200.0, 50, "public", ["high_traffic"]),
            Zone("HQ-F2-CR", "Headquarters Floor 2 Conference Rooms", "HQ-001", 2,
                 ZoneType.CONFERENCE_ROOM, 7.8, 800.0, 20, "restricted", ["av_equipment"]),
            Zone("HQ-F2-BR", "Headquarters Floor 2 Break Room", "HQ-001", 2,
                 ZoneType.BREAK_ROOM, 8.0, 400.0, 15, "public", ["food_safety"]),
            Zone("RC-F1-LA", "Research Center Floor 1 Labs", "RC-001", 1,
                 ZoneType.LABORATORY, 9.8, 600.0, 8, "restricted", ["contamination_control", "chemical_safety"]),
            Zone("RC-F2-MR", "Research Center Floor 2 Meeting Rooms", "RC-001", 2,
                 ZoneType.CONFERENCE_ROOM, 6.5, 300.0, 12, "restricted"),
            Zone("WH-F1-SA", "Warehouse Floor 1 Section A", "WH-001", 1,
                 ZoneType.WAREHOUSE, 4.2, 5000.0, 30, "public"),
            Zone("WH-F1-SB", "Warehouse Floor 1 Section B", "WH-001", 1,
                 ZoneType.WAREHOUSE, 4.8, 4500.0, 25, "public"),
        ]
        return zones

    def _create_locations(self) -> List[Location]:
        """Create specific locations within zones"""
        locations = []

        for zone in self.zones:
            if zone.zone_type == ZoneType.RESTROOM:
                locations.extend([
                    Location(f"{zone.zone_id}-M", f"{zone.zone_name} - Men's", zone.zone_id,
                            zone.building, zone.floor, zone.zone_type, zone.cleaning_priority_score,
                            {"x": random.uniform(0, 100), "y": random.uniform(0, 100)}),
                    Location(f"{zone.zone_id}-W", f"{zone.zone_name} - Women's", zone.zone_id,
                            zone.building, zone.floor, zone.zone_type, zone.cleaning_priority_score,
                            {"x": random.uniform(0, 100), "y": random.uniform(0, 100)})
                ])
            elif zone.zone_type == ZoneType.LABORATORY:
                for i in range(1, 4):  # 3 lab rooms
                    locations.append(
                        Location(f"{zone.zone_id}-{i:02d}", f"{zone.zone_name} - Room {i}", zone.zone_id,
                                zone.building, zone.floor, zone.zone_type, zone.cleaning_priority_score,
                                {"x": random.uniform(0, 100), "y": random.uniform(0, 100)},
                                ["fume_hood", "chemical_storage"], ["badge_access", "safety_training"])
                    )
            else:
                # Single location for other zone types
                locations.append(
                    Location(f"{zone.zone_id}-01", zone.zone_name, zone.zone_id,
                            zone.building, zone.floor, zone.zone_type, zone.cleaning_priority_score,
                            {"x": random.uniform(0, 100), "y": random.uniform(0, 100)})
                )

        return locations

    def _create_alerts(self) -> List[Alert]:
        """Create realistic alerts for locations"""
        alerts = []
        alert_id = 1

        for location in self.locations:
            # High-priority locations get more alerts
            if location.cleaning_priority_score >= 8.0:
                num_alerts = random.randint(2, 5)
            else:
                num_alerts = random.randint(0, 2)

            for _ in range(num_alerts):
                data_type = random.choice([
                    "air_quality", "temperature", "humidity", "noise_level",
                    "occupancy", "cleanliness_sensor", "odor_detection"
                ])

                # Severity based on location priority
                if location.cleaning_priority_score >= 9.0:
                    severity = random.choice([AlertSeverity.SEVERE, AlertSeverity.VERY_SEVERE, AlertSeverity.CRITICAL])
                elif location.cleaning_priority_score >= 7.0:
                    severity = random.choice([AlertSeverity.WARNING, AlertSeverity.SEVERE])
                else:
                    severity = AlertSeverity.WARNING

                alerts.append(Alert(
                    alert_id=alert_id,
                    zone_id=location.zone_id,
                    location_id=location.location_id,
                    data_type=data_type,
                    severity=severity,
                    value=random.uniform(50, 150),
                    threshold=random.uniform(70, 100),
                    timestamp=datetime.now() - timedelta(hours=random.randint(1, 24)),
                    duration_minutes=random.randint(30, 480),
                    description=f"{data_type} alert in {location.location_name}"
                ))
                alert_id += 1

        return alerts

    def _create_task_templates(self) -> Dict[str, Dict]:
        """Create task templates based on zone types and priorities"""
        return {
            "restroom_deep_clean": {
                "name": "Deep Clean Restroom",
                "duration_base": 90,
                "required_skills": ["restroom_cleaning"],
                "zone_types": [ZoneType.RESTROOM],
                "priority_adjustment": 1.5
            },
            "laboratory_sanitization": {
                "name": "Laboratory Sanitization",
                "duration_base": 120,
                "required_skills": ["laboratory_cleaning", "chemical_handling"],
                "zone_types": [ZoneType.LABORATORY],
                "priority_adjustment": 2.0
            },
            "general_cleaning": {
                "name": "General Area Cleaning",
                "duration_base": 60,
                "required_skills": ["general_cleaning"],
                "zone_types": [ZoneType.OFFICE, ZoneType.LOBBY, ZoneType.CONFERENCE_ROOM],
                "priority_adjustment": 1.0
            },
            "break_room_maintenance": {
                "name": "Break Room Maintenance",
                "duration_base": 45,
                "required_skills": ["general_cleaning"],
                "zone_types": [ZoneType.BREAK_ROOM],
                "priority_adjustment": 1.2
            }
        }

    def generate_work_orders(self, num_orders: int = None,
                           conflict_probability: float = 0.4) -> List[WorkOrder]:
        """Generate work orders using real data models"""
        if num_orders is None:
            num_orders = random.randint(20, 30)

        work_orders = []
        base_date = datetime(2025, 5, 6, 8, 0, 0)

        for i in range(num_orders):
            # Select location (with preference for high-priority locations)
            location = self._select_location_by_priority()

            # Select appropriate task based on location
            task_template = self._select_task_for_location(location)

            # Select best employee for this task
            employee = self._select_best_employee_for_task(task_template, location)

            # Calculate duration based on employee efficiency and location priority
            duration = self._calculate_task_duration(task_template, employee, location)

            # Generate time with some conflicts
            start_time = self._generate_start_time(base_date, employee, work_orders, conflict_probability)
            end_time = start_time + timedelta(minutes=duration)

            # Determine priority based on alerts and location priority
            priority = self._calculate_work_order_priority(location)

            # Determine source based on alerts and location characteristics
            source = self._determine_work_order_source(location)

            work_order = WorkOrder(
                work_order_id=1000 + i,
                work_order_name=task_template["name"],
                assignee=employee.full_name,
                start_time=start_time,
                end_time=end_time,
                location=location.location_name,
                priority=priority,
                source=source,
                work_order_type=self._get_work_order_type(task_template),
                duration_minutes=duration,
                template_id=hash(task_template["name"]) % 1000  # Simple template ID
            )

            work_orders.append(work_order)

        return work_orders

    def _select_location_by_priority(self) -> Location:
        """Select location with preference for higher priority"""
        weights = [loc.cleaning_priority_score for loc in self.locations]
        return random.choices(self.locations, weights=weights)[0]

    def _select_task_for_location(self, location: Location) -> Dict:
        """Select appropriate task template for location"""
        suitable_tasks = [
            task for task in self.task_templates.values()
            if location.zone_type in task["zone_types"]
        ]
        return random.choice(suitable_tasks) if suitable_tasks else list(self.task_templates.values())[0]

    def _select_best_employee_for_task(self, task_template: Dict, location: Location) -> Employee:
        """Select best employee based on skills and location preference"""
        scored_employees = []

        for employee in self.employees:
            if employee.employment_status != EmploymentStatus.ACTIVE:
                continue

            score = 0.0

            # Skill matching
            required_skills = task_template.get("required_skills", [])
            for skill_name in required_skills:
                if employee.has_skill(skill_name):
                    skill = next((s for s in employee.skills if s.skill_name == skill_name), None)
                    if skill:
                        score += skill.get_proficiency_score() * 2.0

            # Location preference
            zone_id = location.zone_id.split("-")[0] + "-" + location.zone_id.split("-")[1]  # Building-Floor
            if zone_id in employee.preferred_zones:
                score += 3.0

            # Performance ratings
            score += employee.efficiency_rating * 0.5
            score += employee.quality_rating * 0.3

            # Cost efficiency (lower cost gets slight bonus)
            cost_factor = 50.0 / employee.hourly_rate  # Normalize around $50/hour
            score += cost_factor * 0.2

            scored_employees.append((employee, score))

        # Select from top performers with some randomness
        scored_employees.sort(key=lambda x: x[1], reverse=True)
        top_candidates = scored_employees[:min(3, len(scored_employees))]
        return random.choice(top_candidates)[0]

    def _calculate_task_duration(self, task_template: Dict, employee: Employee, location: Location) -> int:
        """Calculate duration based on employee efficiency and task complexity"""
        base_duration = task_template["duration_base"]

        # Employee efficiency adjustment
        efficiency_factor = 2.0 - (employee.efficiency_rating / 10.0)  # 1.1 to 1.4 range

        # Location complexity adjustment
        priority_factor = location.cleaning_priority_score / 10.0 + 0.5  # 0.6 to 1.5 range

        # Zone type adjustment
        zone_multiplier = location.Zone.get_cleaning_frequency_multiplier() if hasattr(location, 'Zone') else 1.0

        duration = int(base_duration * efficiency_factor * priority_factor * zone_multiplier)

        # Add some randomness
        duration += random.randint(-15, 15)

        return max(30, duration)  # Minimum 30 minutes

    def _generate_start_time(self, base_date: datetime, employee: Employee,
                           existing_orders: List[WorkOrder], conflict_probability: float) -> datetime:
        """Generate start time with controlled conflicts"""
        # Check for intentional conflicts
        if random.random() < conflict_probability and existing_orders:
            # Create conflict with existing order for same employee
            employee_orders = [wo for wo in existing_orders if wo.assignee == employee.full_name]
            if employee_orders:
                conflicting_order = random.choice(employee_orders)
                # Start during or shortly after existing order
                conflict_offset = random.randint(-30, 30)  # minutes
                return conflicting_order.start_time + timedelta(minutes=conflict_offset)

        # Generate normal time within work hours
        hours_offset = random.uniform(0, 8)  # 8 AM to 4 PM
        minutes_offset = random.randint(0, 59)
        return base_date + timedelta(hours=hours_offset, minutes=minutes_offset)

    def _calculate_work_order_priority(self, location: Location) -> Priority:
        """Calculate priority based on location priority and alerts"""
        location_alerts = [a for a in self.alerts
                          if a.location_id == location.location_id and a.status == AlertStatus.ACTIVE]

        # Base priority from location cleaning score
        if location.cleaning_priority_score >= 8.5:
            base_priority = Priority.HIGH
        elif location.cleaning_priority_score >= 6.0:
            base_priority = Priority.MEDIUM
        else:
            base_priority = Priority.LOW

        # Upgrade priority based on active alerts
        if location_alerts:
            max_severity = max(alert.get_severity_value() for alert in location_alerts)
            if max_severity in [AlertSeverity.CRITICAL, AlertSeverity.VERY_SEVERE]:
                return Priority.HIGH
            elif max_severity == AlertSeverity.SEVERE and base_priority != Priority.HIGH:
                return Priority.MEDIUM if base_priority == Priority.LOW else Priority.HIGH

        return base_priority

    def _determine_work_order_source(self, location: Location) -> WorkOrderSource:
        """Determine source based on alerts and patterns"""
        location_alerts = [a for a in self.alerts
                          if a.location_id == location.location_id and a.status == AlertStatus.ACTIVE]

        if location_alerts:
            return WorkOrderSource.ALERT_BASED
        elif location.cleaning_priority_score >= 8.0:
            return WorkOrderSource.SCHEDULED
        else:
            return random.choice([
                WorkOrderSource.MANUAL,
                WorkOrderSource.SCHEDULED,
                WorkOrderSource.AI_RECOMMENDED
            ])

    def _get_work_order_type(self, task_template: Dict) -> str:
        """Get work order type from task template"""
        type_mapping = {
            "restroom_deep_clean": "cleaning",
            "laboratory_sanitization": "cleaning",
            "general_cleaning": "cleaning",
            "break_room_maintenance": "maintenance"
        }
        return type_mapping.get(task_template.get("name", "").lower().replace(" ", "_"), "cleaning")

    def get_location_analytics(self) -> Dict:
        """Get analytics about locations for optimization context"""
        analytics = {}

        for location in self.locations:
            location_alerts = [a for a in self.alerts if a.location_id == location.location_id]
            active_alerts = [a for a in location_alerts if a.status == AlertStatus.ACTIVE]

            analytics[location.location_id] = {
                "location_name": location.location_name,
                "zone_type": location.zone_type.value,
                "cleaning_priority_score": location.cleaning_priority_score,
                "total_alerts": len(location_alerts),
                "active_alerts": len(active_alerts),
                "avg_alert_severity": sum(a.get_severity_score() for a in location_alerts) / len(location_alerts) if location_alerts else 0,
                "coordinates": location.coordinates,
                "special_requirements": location.access_requirements
            }

        return analytics

    def get_employee_analytics(self) -> Dict:
        """Get analytics about employees for optimization context"""
        analytics = {}

        for employee in self.employees:
            if employee.employment_status != EmploymentStatus.ACTIVE:
                continue

            analytics[employee.employee_id] = {
                "full_name": employee.full_name,
                "hourly_rate": employee.hourly_rate,
                "skill_level": employee.skill_level.value,
                "performance_rating": employee.performance_rating,
                "efficiency_rating": employee.efficiency_rating,
                "quality_rating": employee.quality_rating,
                "skills": [
                    {
                        "name": skill.skill_name,
                        "category": skill.skill_category,
                        "proficiency": skill.proficiency_level.value,
                        "experience_years": skill.years_experience
                    }
                    for skill in employee.skills
                ],
                "preferred_zones": employee.preferred_zones,
                "cost_effectiveness": employee.performance_rating / employee.hourly_rate
            }

        return analytics