from typing import Dict, List, Any
from models.work_order import WorkOrder
from analyzers.context_analyzer import ContextAnalyzer
from generators.work_order_generator import WorkOrderGenerator
from utils.tier_validator import TierValidator

class ContextBuilder:
    """Context builder focused on orchestration and formatting - delegates analysis to ContextAnalyzer"""

    def __init__(self, generator: WorkOrderGenerator):
        self.generator = generator
        self.analyzer = ContextAnalyzer(generator)
        self.tier_validator = TierValidator()

    def build_context(self, work_orders: List[WorkOrder],
                     optimization_level: str = "basic",
                     focus: str = "all",
                     customer_tier: str = None) -> Dict[str, Any]:
        """Build comprehensive context with real model data and tier-aware features"""

        # Use customer_tier if provided, otherwise use optimization_level
        effective_tier = customer_tier or optimization_level

        # Validate tier access with enhanced business rules
        validation = self.tier_validator.validate_optimization_request(
            effective_tier, optimization_level, len(work_orders)
        )

        if not validation["valid"]:
            return {
                "error": True,
                "validation_error": validation,
                "message": f"Tier validation failed: {validation['message']}",
                "tier_info": {
                    "customer_tier": effective_tier,
                    "requested_level": optimization_level,
                    "work_order_count": len(work_orders)
                }
            }

        # Base context with enhanced data - organize analyzer results
        context = {
            'level': optimization_level,
            'customer_tier': effective_tier,
            'focus': focus,
            'work_order_count': len(work_orders),
            'cost_info': validation["cost_info"],
            'basic_info': self._format_enhanced_basic_info(work_orders),
            'employee_data': self.analyzer.extract_employee_insights(work_orders),
            'location_data': self.analyzer.extract_location_insights(work_orders),
            'alert_data': self.analyzer.extract_alert_insights(work_orders),

            # Tier-specific business metadata
            'tier_validation': validation,
            'tier_features': self._get_tier_feature_summary(effective_tier),
            'business_metrics': self._calculate_business_metrics(work_orders, effective_tier)
        }

        # Add tier-appropriate advanced features using analyzer
        if self.tier_validator.tier_manager.can_access_feature(effective_tier, "performance_analysis"):
            if optimization_level in ["professional", "enterprise"]:
                context.update({
                    'enhanced_conflicts': self.analyzer.detect_conflicts(work_orders),
                    'enhanced_workload_analysis': self.analyzer.analyze_workload_distribution(work_orders),
                    'skill_analysis': self.analyzer.analyze_skill_matching(work_orders),
                    'cost_analysis': self.analyzer.analyze_cost_efficiency(work_orders),
                    'location_optimization': self.analyzer.analyze_location_efficiency(work_orders),
                    'performance_metrics': self.analyzer.calculate_performance_metrics(work_orders)
                })

        if self.tier_validator.tier_manager.can_access_feature(effective_tier, "advanced_analytics"):
            if optimization_level == "enterprise":
                context.update({
                    'alert_impact_analysis': self.analyzer.analyze_alert_impact(work_orders),
                    'predictive_insights': self.analyzer.generate_predictive_insights(work_orders),
                    'strategic_recommendations': self.analyzer.generate_strategic_recommendations(work_orders),
                    'performance_benchmarks': self.analyzer.calculate_performance_benchmarks(work_orders),
                    'roi_analysis': self.analyzer.calculate_roi_analysis(work_orders),
                    'strategic_metrics': self.analyzer.calculate_strategic_metrics(work_orders)
                })

        # Apply tier restrictions and feature gating
        context['tier_restrictions'] = self._apply_tier_restrictions(context, effective_tier)
        gated_context = self._apply_comprehensive_feature_gating(context, effective_tier, optimization_level)

        return self._filter_by_focus(gated_context, focus)

    def _format_enhanced_basic_info(self, work_orders: List[WorkOrder]) -> List[Dict]:
        """Format basic work order info enhanced with model data"""
        enhanced_info = []

        for wo in work_orders:
            # Get employee data
            employee = next((emp for emp in self.generator.employees if emp.full_name == wo.assignee), None)

            # Get location data
            location = next((loc for loc in self.generator.locations if loc.location_name == wo.location), None)

            # Get relevant alerts
            location_alerts = []
            if location:
                location_alerts = [
                    alert for alert in self.generator.alerts
                    if alert.location_id == location.location_id and alert.status.value == 'active'
                ]

            enhanced_info.append({
                'id': wo.work_order_id,
                'name': wo.work_order_name,
                'assignee': wo.assignee,
                'start_time': wo.start_time.strftime('%Y-%m-%d %I:%M %p'),
                'end_time': wo.end_time.strftime('%Y-%m-%d %I:%M %p'),
                'duration_minutes': wo.duration_minutes,
                'location': wo.location,
                'priority': wo.priority.value,
                'source': wo.source.value,
                'work_type': wo.work_order_type,

                # Enhanced employee info
                'assignee_hourly_rate': employee.hourly_rate if employee else 0,
                'assignee_efficiency': employee.efficiency_rating if employee else 0,
                'assignee_skill_level': employee.skill_level.value if employee else 'unknown',
                'assignee_skills': [skill.skill_name for skill in employee.skills] if employee else [],

                # Enhanced location info
                'location_priority_score': location.cleaning_priority_score if location else 5.0,
                'location_zone_type': location.zone_type.value if location else 'unknown',
                'location_building': location.building if location else 'unknown',
                'location_floor': location.floor if location else 0,

                # Alert info
                'active_alerts_count': len(location_alerts),
                'max_alert_severity': max([alert.severity.value for alert in location_alerts]) if location_alerts else 'none',
                'alert_types': list(set([alert.data_type for alert in location_alerts])) if location_alerts else [],

                # Cost estimates
                'estimated_labor_cost': (wo.duration_minutes / 60.0) * employee.hourly_rate if employee else 0
            })

        return enhanced_info

    def _get_tier_feature_summary(self, customer_tier: str) -> Dict[str, Any]:
        """Get comprehensive feature summary for customer tier"""
        tier_info = self.tier_validator.tier_manager.get_tier_info(customer_tier)

        return {
            'tier_name': customer_tier.title(),
            'max_work_orders': tier_info.max_work_orders,
            'max_tokens': tier_info.max_tokens,
            'available_features': tier_info.features,
            'price_per_optimization': tier_info.price_per_optimization,
            'included_per_month': tier_info.included_optimizations_per_month,
            'feature_categories': self._categorize_features(tier_info.features)
        }

    def _categorize_features(self, features: List[str]) -> Dict[str, List[str]]:
        """Categorize features by business function"""
        categories = {
            'basic_operations': [],
            'performance_analytics': [],
            'advanced_intelligence': [],
            'strategic_planning': []
        }

        feature_mapping = {
            'conflict_resolution': 'basic_operations',
            'basic_workload_balancing': 'basic_operations',
            'simple_scheduling': 'basic_operations',
            'basic_location_grouping': 'basic_operations',

            'performance_analysis': 'performance_analytics',
            'workload_distribution': 'performance_analytics',
            'location_optimization': 'performance_analytics',
            'historical_patterns': 'performance_analytics',
            'travel_time_optimization': 'performance_analytics',
            'performance_insights': 'performance_analytics',

            'advanced_analytics': 'advanced_intelligence',
            'template_patterns': 'advanced_intelligence',
            'priority_anomalies': 'advanced_intelligence',
            'efficiency_opportunities': 'advanced_intelligence',
            'predictive_insights': 'advanced_intelligence',
            'resource_utilization': 'advanced_intelligence',

            'strategic_recommendations': 'strategic_planning',
            'scheduling_gaps': 'strategic_planning',
            'custom_rules': 'strategic_planning'
        }

        for feature in features:
            category = feature_mapping.get(feature, 'basic_operations')
            categories[category].append(feature)

        return categories

    def _calculate_business_metrics(self, work_orders: List[WorkOrder], customer_tier: str) -> Dict[str, Any]:
        """Calculate business metrics relevant to customer tier"""
        tier_info = self.tier_validator.tier_manager.get_tier_info(customer_tier)

        # Basic metrics for all tiers
        total_work_orders = len(work_orders)
        total_duration = sum(wo.duration_minutes for wo in work_orders)

        # Calculate estimated costs
        total_labor_cost = 0
        for wo in work_orders:
            employee = next((emp for emp in self.generator.employees if emp.full_name == wo.assignee), None)
            if employee:
                total_labor_cost += (wo.duration_minutes / 60.0) * employee.hourly_rate

        business_metrics = {
            'operational_metrics': {
                'total_work_orders': total_work_orders,
                'total_duration_hours': round(total_duration / 60.0, 1),
                'estimated_labor_cost': round(total_labor_cost, 2),
                'avg_cost_per_work_order': round(total_labor_cost / total_work_orders, 2) if total_work_orders > 0 else 0,
                'utilization_rate': min(100, round((total_work_orders / tier_info.max_work_orders) * 100, 1))
            },
            'tier_value_metrics': {
                'optimization_cost': tier_info.price_per_optimization,
                'cost_per_work_order_optimized': round(tier_info.price_per_optimization / total_work_orders, 2) if total_work_orders > 0 else 0,
                'potential_roi': self._calculate_tier_roi(total_labor_cost, tier_info, customer_tier)
            }
        }

        return business_metrics

    def _calculate_tier_roi(self, labor_cost: float, tier_info, customer_tier: str) -> Dict[str, Any]:
        """Calculate ROI for optimization tier"""
        roi_estimates = {
            'basic': 0.05,      # 5% efficiency improvement
            'professional': 0.15, # 15% efficiency improvement
            'enterprise': 0.25   # 25% efficiency improvement
        }

        improvement_rate = roi_estimates.get(customer_tier, 0.05)
        potential_savings = labor_cost * improvement_rate
        optimization_cost = tier_info.price_per_optimization

        return {
            'estimated_improvement_rate': f"{improvement_rate*100:.0f}%",
            'potential_labor_savings': round(potential_savings, 2),
            'optimization_investment': optimization_cost,
            'net_roi': round(potential_savings - optimization_cost, 2),
            'roi_ratio': round((potential_savings / optimization_cost) if optimization_cost > 0 else 0, 2),
            'break_even_point': f"{optimization_cost / potential_savings:.1f} optimization cycles" if potential_savings > 0 else "N/A"
        }

    def _apply_tier_restrictions(self, context: Dict[str, Any], customer_tier: str) -> Dict[str, Any]:
        """Apply tier-specific restrictions and limitations"""
        restrictions = {
            'data_limitations': [],
            'feature_limitations': [],
            'analysis_depth': customer_tier
        }

        tier_info = self.tier_validator.tier_manager.get_tier_info(customer_tier)

        # Work order count restrictions
        if context.get('work_order_count', 0) > tier_info.max_work_orders:
            restrictions['data_limitations'].append(f"Work order count limited to {tier_info.max_work_orders}")

        # Feature access restrictions
        all_features = ['advanced_analytics', 'predictive_insights', 'strategic_recommendations', 'custom_rules']
        unavailable_features = [f for f in all_features if not self.tier_validator.tier_manager.can_access_feature(customer_tier, f)]

        if unavailable_features:
            restrictions['feature_limitations'].extend(unavailable_features)

        # Analysis depth restrictions
        if customer_tier == 'basic':
            restrictions['analysis_depth'] = 'surface_level'
        elif customer_tier == 'professional':
            restrictions['analysis_depth'] = 'detailed'
        else:
            restrictions['analysis_depth'] = 'comprehensive'

        return restrictions

    def _apply_comprehensive_feature_gating(self, context: Dict[str, Any], customer_tier: str, optimization_level: str) -> Dict[str, Any]:
        """Apply comprehensive feature gating based on tier permissions"""

        # Remove features not available in customer tier
        gated_context = context.copy()

        # Basic tier restrictions
        if customer_tier == 'basic':
            # Remove advanced features
            features_to_remove = [
                'enhanced_workload_analysis', 'skill_analysis', 'cost_analysis',
                'alert_impact_analysis', 'predictive_insights', 'strategic_recommendations',
                'performance_benchmarks', 'roi_analysis', 'performance_metrics', 'strategic_metrics'
            ]
            for feature in features_to_remove:
                gated_context.pop(feature, None)

            # Limit basic_info to essential data only
            if 'basic_info' in gated_context:
                for work_order in gated_context['basic_info']:
                    # Remove advanced fields for basic tier
                    advanced_fields = [
                        'assignee_skills', 'alert_types', 'estimated_labor_cost'
                    ]
                    for field in advanced_fields:
                        work_order.pop(field, None)

        # Professional tier restrictions
        elif customer_tier == 'professional':
            # Remove enterprise-only features
            enterprise_features = [
                'predictive_insights', 'strategic_recommendations',
                'performance_benchmarks', 'roi_analysis', 'strategic_metrics'
            ]
            for feature in enterprise_features:
                gated_context.pop(feature, None)

        # Add tier access indicators
        gated_context['tier_access_level'] = customer_tier
        gated_context['available_features'] = [
            feature for feature in context.keys()
            if feature in gated_context
        ]

        return gated_context

    def _filter_by_focus(self, context: Dict[str, Any], focus: str) -> Dict[str, Any]:
        """Filter context based on optimization focus with enhanced data"""
        if focus == "all":
            return context

        focus_filters = {
            "time": ['enhanced_conflicts', 'scheduling_gaps', 'basic_info', 'employee_data'],
            "assignee": ['enhanced_workload_analysis', 'skill_analysis', 'cost_analysis', 'employee_data', 'performance_metrics'],
            "priority": ['alert_data', 'alert_impact_analysis', 'basic_info'],
            "location": ['location_data', 'location_optimization', 'travel_optimization', 'alert_data']
        }

        if focus in focus_filters:
            filtered_context = {
                'level': context['level'],
                'customer_tier': context.get('customer_tier'),
                'focus': context['focus'],
                'work_order_count': context['work_order_count'],
                'basic_info': context['basic_info'],
                'tier_features': context.get('tier_features'),
                'business_metrics': context.get('business_metrics')
            }

            for key in focus_filters[focus]:
                if key in context:
                    filtered_context[key] = context[key]

            return filtered_context

        return context