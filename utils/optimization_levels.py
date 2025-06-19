from enum import Enum
from typing import Dict, List, Any
from dataclasses import dataclass
import json

class OptimizationLevel(Enum):
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"

@dataclass
class TierFeatures:
    level: str
    max_work_orders: int
    max_tokens: int
    features: List[str]
    price_per_optimization: float
    price_per_work_order: float
    included_optimizations_per_month: int

class OptimizationTierManager:
    """Manages optimization tiers, pricing, and feature access"""

    def __init__(self):
        self.tiers = {
            OptimizationLevel.BASIC.value: TierFeatures(
                level="basic",
                max_work_orders=50,
                max_tokens=2000,
                features=[
                    "conflict_resolution",
                    "basic_workload_balancing",
                    "simple_scheduling",
                    "basic_location_grouping"
                ],
                price_per_optimization=5.00,
                price_per_work_order=0.10,
                included_optimizations_per_month=10
            ),
            OptimizationLevel.PROFESSIONAL.value: TierFeatures(
                level="professional",
                max_work_orders=200,
                max_tokens=4000,
                features=[
                    "conflict_resolution",
                    "basic_workload_balancing",
                    "simple_scheduling",
                    "basic_location_grouping",
                    "performance_analysis",
                    "workload_distribution",
                    "location_optimization",
                    "historical_patterns",
                    "travel_time_optimization",
                    "performance_insights"
                ],
                price_per_optimization=15.00,
                price_per_work_order=0.25,
                included_optimizations_per_month=50
            ),
            OptimizationLevel.ENTERPRISE.value: TierFeatures(
                level="enterprise",
                max_work_orders=1000,
                max_tokens=8000,
                features=[
                    "conflict_resolution",
                    "basic_workload_balancing",
                    "simple_scheduling",
                    "basic_location_grouping",
                    "performance_analysis",
                    "workload_distribution",
                    "location_optimization",
                    "historical_patterns",
                    "travel_time_optimization",
                    "performance_insights",
                    "advanced_analytics",
                    "template_patterns",
                    "priority_anomalies",
                    "efficiency_opportunities",
                    "predictive_insights",
                    "strategic_recommendations",
                    "resource_utilization",
                    "scheduling_gaps",
                    "custom_rules"
                ],
                price_per_optimization=35.00,
                price_per_work_order=0.50,
                included_optimizations_per_month=200
            )
        }

    def get_tier_info(self, level: str) -> TierFeatures:
        """Get tier information"""
        return self.tiers.get(level)

    def validate_tier_access(self, customer_tier: str, requested_level: str) -> Dict[str, Any]:
        """Validate if customer can access requested optimization level"""
        tier_hierarchy = {
            "basic": 1,
            "professional": 2,
            "enterprise": 3
        }

        customer_level = tier_hierarchy.get(customer_tier, 0)
        requested_level_num = tier_hierarchy.get(requested_level, 0)

        if customer_level >= requested_level_num:
            return {
                "allowed": True,
                "message": f"Access granted to {requested_level} optimization"
            }
        else:
            return {
                "allowed": False,
                "message": f"Upgrade required. Current tier: {customer_tier}, Requested: {requested_level}",
                "upgrade_url": f"/upgrade?from={customer_tier}&to={requested_level}"
            }

    def validate_work_order_limit(self, customer_tier: str, work_order_count: int) -> Dict[str, Any]:
        """Check if work order count is within tier limits"""
        tier_info = self.get_tier_info(customer_tier)

        if work_order_count <= tier_info.max_work_orders:
            return {
                "allowed": True,
                "remaining": tier_info.max_work_orders - work_order_count
            }
        else:
            return {
                "allowed": False,
                "limit": tier_info.max_work_orders,
                "requested": work_order_count,
                "excess": work_order_count - tier_info.max_work_orders,
                "message": f"Work order limit exceeded. Limit: {tier_info.max_work_orders}, Requested: {work_order_count}"
            }

    def can_access_feature(self, customer_tier: str, feature: str) -> bool:
        """Check if customer tier can access specific feature"""
        tier_info = self.get_tier_info(customer_tier)
        return feature in tier_info.features if tier_info else False

    def calculate_optimization_cost(self, customer_tier: str, work_order_count: int,
                                  usage_this_month: int = 0) -> Dict[str, Any]:
        """Calculate cost for optimization based on tier and usage"""
        tier_info = self.get_tier_info(customer_tier)

        # Check if within included optimizations
        remaining_included = max(0, tier_info.included_optimizations_per_month - usage_this_month)

        if remaining_included > 0:
            cost = 0.0
            billing_type = "included"
        else:
            # Calculate overage cost
            base_cost = tier_info.price_per_optimization
            work_order_cost = work_order_count * tier_info.price_per_work_order
            cost = base_cost + work_order_cost
            billing_type = "pay_per_use"

        return {
            "total_cost": cost,
            "billing_type": billing_type,
            "base_cost": tier_info.price_per_optimization,
            "work_order_cost": work_order_count * tier_info.price_per_work_order,
            "work_order_count": work_order_count,
            "remaining_included": remaining_included,
            "tier": customer_tier
        }

    def get_tier_comparison(self) -> Dict[str, Any]:
        """Get comparison of all tiers for pricing page"""
        comparison = {}
        for level, tier_info in self.tiers.items():
            comparison[level] = {
                "max_work_orders": tier_info.max_work_orders,
                "features": tier_info.features,
                "price_per_optimization": tier_info.price_per_optimization,
                "included_per_month": tier_info.included_optimizations_per_month,
                "processing_power": f"{tier_info.max_tokens} tokens"
            }
        return comparison