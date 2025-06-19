from typing import Dict, Any, Optional, List
from .optimization_levels import OptimizationTierManager
import logging

class TierValidator:
    """Validates tier access and enforces business rules"""

    def __init__(self):
        self.tier_manager = OptimizationTierManager()
        self.logger = logging.getLogger(__name__)

    def validate_optimization_request(self,
                                    customer_tier: str,
                                    requested_level: str,
                                    work_order_count: int,
                                    monthly_usage: int = 0) -> Dict[str, Any]:
        """Comprehensive validation for optimization request"""

        # Validate tier access
        tier_access = self.tier_manager.validate_tier_access(customer_tier, requested_level)
        if not tier_access["allowed"]:
            return {
                "valid": False,
                "error": "TIER_ACCESS_DENIED",
                "message": tier_access["message"],
                "upgrade_required": True,
                "upgrade_url": tier_access.get("upgrade_url")
            }

        # Validate work order limits
        work_order_validation = self.tier_manager.validate_work_order_limit(customer_tier, work_order_count)
        if not work_order_validation["allowed"]:
            return {
                "valid": False,
                "error": "WORK_ORDER_LIMIT_EXCEEDED",
                "message": work_order_validation["message"],
                "limit": work_order_validation["limit"],
                "requested": work_order_validation["requested"]
            }

        # Calculate costs
        cost_info = self.tier_manager.calculate_optimization_cost(
            customer_tier, work_order_count, monthly_usage
        )

        return {
            "valid": True,
            "tier_info": self.tier_manager.get_tier_info(customer_tier),
            "cost_info": cost_info,
            "work_order_validation": work_order_validation
        }

    def filter_features_by_tier(self, customer_tier: str, requested_features: List[str]) -> Dict[str, Any]:
        """Filter features based on customer tier"""
        tier_info = self.tier_manager.get_tier_info(customer_tier)
        allowed_features = []
        denied_features = []

        for feature in requested_features:
            if self.tier_manager.can_access_feature(customer_tier, feature):
                allowed_features.append(feature)
            else:
                denied_features.append(feature)

        return {
            "allowed_features": allowed_features,
            "denied_features": denied_features,
            "tier_features": tier_info.features
        }