from typing import Dict, List, Any
from datetime import datetime, timedelta
from analyzers.recommendation_analyzer import RecommendationAnalyzer
from models.recommendation import TaskRecommendation, RecommendationSource, RecommendationPriority
from utils.tier_validator import TierValidator

class RecommendationBuilder:
    """Builds recommendation context and orchestrates analysis"""

    def __init__(self, database_connection):
        self.db = database_connection
        self.analyzer = RecommendationAnalyzer(database_connection)
        self.tier_validator = TierValidator()

    def build_recommendations(self, criteria: Dict[str, Any],
                            customer_tier: str = "basic") -> Dict[str, Any]:
        """Build comprehensive recommendations based on criteria"""

        # Validate tier access
        validation = self.tier_validator.validate_optimization_request(
            customer_tier, "recommendation", criteria.get('max_recommendations', 10)
        )

        if not validation["valid"]:
            return {
                "error": True,
                "validation_error": validation,
                "message": f"Tier validation failed: {validation['message']}"
            }

        recommendations = []

        # Generate recommendations based on different sources
        if self._tier_allows_feature(customer_tier, "pattern_analysis"):
            pattern_recommendations = self._generate_pattern_recommendations(criteria)
            recommendations.extend(pattern_recommendations)

        if self._tier_allows_feature(customer_tier, "alert_analysis"):
            alert_recommendations = self._generate_alert_recommendations(criteria)
            recommendations.extend(alert_recommendations)

        if self._tier_allows_feature(customer_tier, "metric_analysis"):
            metric_recommendations = self._generate_metric_recommendations(criteria)
            recommendations.extend(metric_recommendations)

        # Apply tier-specific filtering
        recommendations = self._apply_tier_filtering(recommendations, customer_tier)

        # Sort by confidence and priority
        recommendations.sort(key=lambda x: (x.confidence_score, x.recommended_priority.value), reverse=True)

        # Generate insights
        insights = []
        if customer_tier in ["professional", "enterprise"]:
            insights = self.analyzer.generate_performance_insights(recommendations)

        # Calculate business impact for enterprise tier
        business_impact = {}
        if customer_tier == "enterprise":
            business_impact = self._calculate_aggregate_business_impact(recommendations)

        return {
            "recommendations": recommendations,
            "insights": insights,
            "business_impact": business_impact,
            "tier_info": validation["tier_info"],
            "cost_info": validation["cost_info"],
            "recommendation_count": len(recommendations),
            "confidence_distribution": self._analyze_confidence_distribution(recommendations)
        }

    def _generate_pattern_recommendations(self, criteria: Dict[str, Any]) -> List[TaskRecommendation]:
        """Generate recommendations based on historical patterns"""
        recommendations = []

        # Get locations to analyze
        locations = criteria.get('locations', self._get_all_locations())

        for location_id in locations:
            for work_order_type in criteria.get('work_order_types', ['cleaning', 'maintenance']):

                pattern_analysis = self.analyzer.analyze_historical_patterns(
                    location_id, work_order_type, criteria.get('lookback_days', 30)
                )

                if (pattern_analysis['sufficient_data'] and
                    pattern_analysis['recommendation_confidence'] >= criteria.get('min_confidence', 0.7)):

                    # Check if recommendation is due
                    if self._is_recommendation_due(pattern_analysis, criteria.get('buffer_days', 2)):

                        # Create recommendation
                        rec = self._create_pattern_recommendation(
                            location_id, work_order_type, pattern_analysis
                        )
                        recommendations.append(rec)

        return recommendations

    def _generate_alert_recommendations(self, criteria: Dict[str, Any]) -> List[TaskRecommendation]:
        """Generate recommendations based on active alerts"""
        recommendations = []

        locations = criteria.get('locations', self._get_all_locations())

        for location_id in locations:
            alert_analysis = self.analyzer.analyze_alert_triggers(
                location_id, criteria.get('alert_severity_threshold', 'severe')
            )

            if alert_analysis['should_trigger']:
                rec = self._create_alert_recommendation(location_id, alert_analysis)
                recommendations.append(rec)

        return recommendations

    def _generate_metric_recommendations(self, criteria: Dict[str, Any]) -> List[TaskRecommendation]:
        """Generate recommendations based on performance metrics"""
        recommendations = []

        locations = criteria.get('locations', self._get_all_locations())

        for location_id in locations:
            for work_order_type in criteria.get('work_order_types', ['cleaning', 'maintenance']):

                metric_analysis = self.analyzer.analyze_metric_performance(
                    location_id, work_order_type, criteria.get('variance_threshold', 0.2)
                )

                if metric_analysis['intervention_needed']:
                    rec = self._create_metric_recommendation(
                        location_id, work_order_type, metric_analysis
                    )
                    recommendations.append(rec)

        return recommendations

    def _create_pattern_recommendation(self, location_id: str, work_order_type: str,
                                     analysis: Dict[str, Any]) -> TaskRecommendation:
        """Create recommendation based on pattern analysis"""

        recommended_time = analysis['predicted_next_date']
        optimal_assignee = analysis['most_common_assignee']

        # Analyze employee availability
        availability = self.analyzer.analyze_employee_availability(
            recommended_time, [optimal_assignee] if optimal_assignee else []
        )

        # Select best available assignee
        best_assignee = self._select_best_assignee(availability, optimal_assignee)

        return TaskRecommendation(
            recommendation_id=f"PATTERN_{location_id}_{work_order_type}_{int(recommended_time.timestamp())}",
            template_id=self._get_template_id(work_order_type),
            recommended_name=f"Scheduled {work_order_type} - {location_id}",
            recommended_assignee=best_assignee,
            recommended_location=location_id,
            recommended_start_time=recommended_time,
            recommended_end_time=recommended_time + timedelta(hours=2),  # Default duration
            recommended_priority=RecommendationPriority.MEDIUM,
            source=RecommendationSource.PATTERN_BASED,
            work_order_type=work_order_type,
            confidence_score=analysis['recommendation_confidence'],
            reasoning=f"Historical pattern shows {work_order_type} needed every {analysis['avg_completion_interval_days']:.1f} days",
            business_impact=f"Maintain {analysis['avg_quality_score']:.1f} quality score and prevent service degradation",
            estimated_cost=self._estimate_cost(best_assignee, 120),  # 2 hours default
            estimated_duration_minutes=120,
            trigger_data={
                'pattern_strength': analysis['pattern_strength'],
                'historical_data_points': len(analysis.get('assignee_distribution', {})),
                'avg_interval_days': analysis['avg_completion_interval_days']
            }
        )

    def _create_alert_recommendation(self, location_id: str, analysis: Dict[str, Any]) -> TaskRecommendation:
        """Create recommendation based on alert analysis"""

        # Determine urgency based on alert severity
        if analysis['critical_alerts'] > 0:
            priority = RecommendationPriority.URGENT
            start_time = datetime.now() + timedelta(minutes=30)
        elif analysis['severe_alerts'] >= 2:
            priority = RecommendationPriority.HIGH
            start_time = datetime.now() + timedelta(hours=2)
        else:
            priority = RecommendationPriority.MEDIUM
            start_time = datetime.now() + timedelta(hours=4)

        return TaskRecommendation(
            recommendation_id=f"ALERT_{location_id}_{int(datetime.now().timestamp())}",
            template_id=None,  # Alert-based may not have template
            recommended_name=f"Alert Response - {location_id}",
            recommended_assignee=self._get_emergency_assignee(location_id),
            recommended_location=location_id,
            recommended_start_time=start_time,
            recommended_end_time=start_time + timedelta(hours=1),
            recommended_priority=priority,
            source=RecommendationSource.ALERT_TRIGGERED,
            work_order_type="emergency_response",
            confidence_score=analysis['trigger_score'],
            reasoning="; ".join(analysis['trigger_reasons']),
            business_impact=f"Prevent escalation of {analysis['critical_alerts']} critical alerts",
            estimated_cost=self._estimate_emergency_cost(),
            estimated_duration_minutes=60,
            trigger_data={
                'active_alerts_count': analysis['active_alerts_count'],
                'critical_alerts': analysis['critical_alerts'],
                'escalation_probability': analysis['escalation_probability']
            }
        )

    # Helper methods
    def _tier_allows_feature(self, customer_tier: str, feature: str) -> bool:
        """Check if customer tier allows specific feature"""
        tier_features = {
            "basic": ["pattern_analysis"],
            "professional": ["pattern_analysis", "alert_analysis", "metric_analysis"],
            "enterprise": ["pattern_analysis", "alert_analysis", "metric_analysis", "advanced_insights"]
        }
        return feature in tier_features.get(customer_tier, [])

    def _apply_tier_filtering(self, recommendations: List[TaskRecommendation],
                            customer_tier: str) -> List[TaskRecommendation]:
        """Apply tier-specific filtering to recommendations"""

        # Limit recommendations based on tier
        tier_limits = {
            "basic": 5,
            "professional": 15,
            "enterprise": 50
        }

        limit = tier_limits.get(customer_tier, 5)

        # Filter by confidence for lower tiers
        if customer_tier == "basic":
            recommendations = [r for r in recommendations if r.confidence_score >= 0.8]
        elif customer_tier == "professional":
            recommendations = [r for r in recommendations if r.confidence_score >= 0.6]

        return recommendations[:limit]

    def _get_all_locations(self) -> List[str]:
        """Get all available location IDs"""
        if hasattr(self.analyzer, 'locations'):
            return list(self.analyzer.locations.keys())
        else:
            # Fallback: query from database
            try:
                query = "SELECT DISTINCT location_id FROM locations WHERE active = 1"
                results = self.db.execute_query(query, [])
                return [row['location_id'] for row in results]
            except:
                # Default locations if database unavailable
                return ['HQ-F1-RR', 'HQ-F1-LB', 'HQ-F2-CR', 'RC-F1-LA', 'WH-F1-SA']

    def _is_recommendation_due(self, pattern_analysis: Dict[str, Any], buffer_days: int) -> bool:
        """Check if recommendation is due based on pattern analysis"""
        from datetime import datetime, timedelta

        predicted_date = pattern_analysis.get('predicted_next_date')
        if not predicted_date:
            return False

        # Recommend if we're within buffer_days of predicted date
        buffer_date = predicted_date - timedelta(days=buffer_days)
        return datetime.now() >= buffer_date

    def _get_template_id(self, work_order_type: str) -> int:
        """Get template ID for work order type"""
        # Map work order types to template IDs
        template_mapping = {
            'cleaning': 1001,
            'maintenance': 1002,
            'inspection': 1003,
            'emergency_response': 1004
        }
        return template_mapping.get(work_order_type, 1000)

    def _select_best_assignee(self, availability: Dict[str, Any], preferred_assignee: str) -> str:
        """Select best available assignee"""
        if not availability:
            return preferred_assignee or "Unassigned"

        # If preferred assignee is available, use them
        if preferred_assignee and preferred_assignee in availability:
            pref_data = availability[preferred_assignee]
            if pref_data.get('availability_percentage', 0) > 20 and not pref_data.get('has_conflicts', True):
                return preferred_assignee

        # Otherwise, find best available
        best_assignee = None
        best_score = 0

        for assignee, data in availability.items():
            if data.get('availability_percentage', 0) > 20 and not data.get('has_conflicts', True):
                score = data.get('recommendation_score', 0)
                if score > best_score:
                    best_score = score
                    best_assignee = assignee

        return best_assignee or preferred_assignee or "Unassigned"

    def _estimate_cost(self, assignee_name: str, duration_minutes: int) -> float:
        """Estimate cost for task"""
        # Get hourly rate from analyzer if available
        if hasattr(self.analyzer, 'employees') and assignee_name in self.analyzer.employees:
            hourly_rate = self.analyzer.employees[assignee_name].hourly_rate
        else:
            hourly_rate = 25.0  # Default rate

        return (duration_minutes / 60.0) * hourly_rate

    def _get_emergency_assignee(self, location_id: str) -> str:
        """Get emergency assignee for location"""
        # Try to find qualified emergency responder
        if hasattr(self.analyzer, 'employees'):
            for emp_name, employee in self.analyzer.employees.items():
                if employee.has_skill('emergency_response'):
                    return emp_name

        # Fallback to any available assignee
        return "Emergency Team"

    def _estimate_emergency_cost(self) -> float:
        """Estimate cost for emergency response"""
        return 150.0  # Emergency premium rate

    def _create_metric_recommendation(self, location_id: str, work_order_type: str,
                                    analysis: Dict[str, Any]) -> TaskRecommendation:
        """Create recommendation based on metric analysis"""
        from datetime import datetime, timedelta

        # Determine urgency based on degradation
        degradation_score = analysis.get('degradation_score', 0)
        if degradation_score > 0.8:
            priority = RecommendationPriority.HIGH
            start_time = datetime.now() + timedelta(hours=4)
        elif degradation_score > 0.6:
            priority = RecommendationPriority.MEDIUM
            start_time = datetime.now() + timedelta(hours=12)
        else:
            priority = RecommendationPriority.LOW
            start_time = datetime.now() + timedelta(days=1)

        # Get best assignee for this type of work
        best_assignee = self._get_best_assignee_for_type(work_order_type)

        return TaskRecommendation(
            recommendation_id=f"METRIC_{location_id}_{work_order_type}_{int(datetime.now().timestamp())}",
            template_id=self._get_template_id(work_order_type),
            recommended_name=f"Performance Restoration - {location_id}",
            recommended_assignee=best_assignee,
            recommended_location=location_id,
            recommended_start_time=start_time,
            recommended_end_time=start_time + timedelta(hours=2),
            recommended_priority=priority,
            source=RecommendationSource.METRIC_DRIVEN,
            work_order_type=work_order_type,
            confidence_score=analysis.get('confidence', 0.8),
            reasoning=f"Performance metrics show {degradation_score*100:.1f}% degradation",
            business_impact=f"Restore performance to baseline levels: {analysis.get('predicted_improvement', 'significant improvement expected')}",
            estimated_cost=self._estimate_cost(best_assignee, 120),
            estimated_duration_minutes=120,
            trigger_data={
                'degradation_score': degradation_score,
                'affected_metrics': list(analysis.get('performance_indicators', {}).keys()),
                'intervention_urgency': 'high' if degradation_score > 0.7 else 'medium'
            }
        )

    def _get_best_assignee_for_type(self, work_order_type: str) -> str:
        """Get best assignee for specific work order type"""
        # Map work types to preferred skills
        skill_requirements = {
            'cleaning': ['general_cleaning'],
            'maintenance': ['equipment_operation', 'maintenance'],
            'inspection': ['quality_inspection'],
            'emergency_response': ['emergency_response']
        }

        required_skills = skill_requirements.get(work_order_type, ['general_cleaning'])

        if hasattr(self.analyzer, 'employees'):
            best_assignee = None
            best_score = 0

            for emp_name, employee in self.analyzer.employees.items():
                score = 0
                # Check skill match
                for skill_name in required_skills:
                    if employee.has_skill(skill_name):
                        score += 2

                # Add efficiency bonus
                score += employee.efficiency_rating / 10.0

                if score > best_score:
                    best_score = score
                    best_assignee = emp_name

            return best_assignee or "Unassigned"

        return "Unassigned"

    def _calculate_aggregate_business_impact(self, recommendations: List[TaskRecommendation]) -> Dict[str, Any]:
        """Calculate aggregate business impact for enterprise tier"""
        total_cost = sum(rec.estimated_cost for rec in recommendations)

        # Estimate potential savings (this would be more sophisticated in practice)
        potential_savings = 0
        for rec in recommendations:
            if rec.source == RecommendationSource.ALERT_TRIGGERED:
                potential_savings += 500  # Prevent escalation
            elif rec.source == RecommendationSource.METRIC_DRIVEN:
                potential_savings += 300  # Performance restoration
            elif rec.source == RecommendationSource.PATTERN_BASED:
                potential_savings += 100  # Efficiency improvement

        return {
            'financial_metrics': {
                'total_cost': total_cost,
                'potential_savings': potential_savings,
                'net_roi': potential_savings - total_cost,
                'roi_percentage': ((potential_savings - total_cost) / total_cost * 100) if total_cost > 0 else 0
            },
            'risk_metrics': {
                'high_risk_items': sum(1 for rec in recommendations if rec.recommended_priority in [RecommendationPriority.HIGH, RecommendationPriority.URGENT]),
                'compliance_items': sum(1 for rec in recommendations if 'compliance' in rec.reasoning.lower()),
                'preventive_items': sum(1 for rec in recommendations if rec.source == RecommendationSource.PATTERN_BASED)
            },
            'operational_metrics': {
                'locations_covered': len(set(rec.recommended_location for rec in recommendations)),
                'assignees_involved': len(set(rec.recommended_assignee for rec in recommendations)),
                'avg_confidence': sum(rec.confidence_score for rec in recommendations) / len(recommendations) if recommendations else 0
            }
        }

    def _analyze_confidence_distribution(self, recommendations: List[TaskRecommendation]) -> Dict[str, int]:
        """Analyze confidence distribution of recommendations"""
        distribution = {'high': 0, 'medium': 0, 'low': 0}

        for rec in recommendations:
            if rec.confidence_score >= 0.8:
                distribution['high'] += 1
            elif rec.confidence_score >= 0.6:
                distribution['medium'] += 1
            else:
                distribution['low'] += 1

        return distribution