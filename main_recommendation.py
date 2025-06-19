from datetime import datetime
import json
from typing import Dict, List
from processors.recommendation_builder import RecommendationBuilder
from optimizers.recommendation_optimizer import RecommendationOptimizer
from formatters.recommendation_formatter import RecommendationFormatter
from utils.tier_validator import TierValidator

def main():
    """Main entry point for work order recommendation system"""

    print("🤖 Work Order Recommendation System")
    print("=" * 50)

    # Configuration
    customer_tier = "professional"  # basic, professional, enterprise
    max_recommendations = 10
    output_format = "summary"  # summary, detailed, json

    # Recommendation criteria
    criteria = {
        'locations': ['HQ-F1-RR', 'RC-F1-LA', 'HQ-F2-CR'],  # Specific locations or None for all
        'work_order_types': ['cleaning', 'maintenance', 'inspection'],
        'lookback_days': 30,
        'min_confidence': 0.7,
        'alert_severity_threshold': 'severe',
        'variance_threshold': 0.2,
        'max_recommendations': max_recommendations,
        'buffer_days': 2  # Days before predicted date to recommend
    }

    print(f"👤 Customer Tier: {customer_tier}")
    print(f"🎯 Max Recommendations: {max_recommendations}")
    print(f"📊 Output Format: {output_format}")
    print("")

    # Step 1: Validate tier access
    tier_validator = TierValidator()
    validation = tier_validator.validate_optimization_request(
        customer_tier, "recommendation", max_recommendations
    )

    if not validation["valid"]:
        print(f"❌ Access Denied: {validation['message']}")
        if validation.get("upgrade_required"):
            print(f"💳 Upgrade at: {validation.get('upgrade_url', '/upgrade')}")
        return

    # Show cost information
    cost_info = validation["cost_info"]
    if cost_info["billing_type"] == "included":
        print(f"💰 Cost: Included ({cost_info['remaining_included']} remaining this month)")
    else:
        print(f"💰 Cost: ${cost_info['total_cost']:.2f}")

    print("")

    # Step 2: Build recommendations
    print("🔍 Analyzing historical patterns and current conditions...")

    # Initialize with database connection (placeholder)
    db_connection = None  # Your database connection here
    recommendation_builder = RecommendationBuilder(db_connection)

    context = recommendation_builder.build_recommendations(criteria, customer_tier)

    # Check for validation errors
    if context.get("error"):
        print(f"❌ Recommendation building failed: {context['message']}")
        return

    print(f"✅ Generated {context['recommendation_count']} recommendations")
    print("")
    print(context)

    # Step 3: AI enhancement (optional)
    print("🤖 Enhancing recommendations with AI analysis...")

    # optimizer = RecommendationOptimizer()
    # ai_results = optimizer.generate_recommendations(context, customer_tier)

    # # Add cost info to results
    # if ai_results.get("success"):
    #     ai_results["cost_info"] = cost_info

    # # Step 4: Format and display results
    # print("")
    # formatter = RecommendationFormatter()
    # formatted_results = formatter.format_recommendation_results(
    #     ai_results, output_format, customer_tier
    # )

    # print(formatted_results)

    # # Optional: Save detailed results to file
    # if ai_results.get("success"):
    #     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    #     filename = f"recommendation_results_{customer_tier}_{timestamp}.json"

    #     # Add metadata to saved results
    #     ai_results["metadata"] = {
    #         "customer_tier": customer_tier,
    #         "criteria": criteria,
    #         "cost_info": cost_info,
    #         "validation_info": validation,
    #         "generated_at": datetime.now().isoformat()
    #     }

    #     with open(filename, 'w') as f:
    #         json.dump(ai_results, f, indent=2, default=str)

    #     print(f"💾 Detailed results saved to: {filename}")

if __name__ == "__main__":
    main()

# =============================================================================
# Database Integration Layer (Example)
# =============================================================================

class DatabaseManager:
    """Database integration for recommendation system"""

    def __init__(self, connection_string):
        self.connection = self._connect(connection_string)

    def query_historical_work_orders(self, location_id: str, work_order_type: str,
                                   lookback_days: int) -> List[Dict]:
        """Query historical work orders from Table 1 and Table 2"""

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

        return self._execute_query(query, [f"%{location_id}%", work_order_type, lookback_days])

    def query_active_alerts(self, location_id: str) -> List[Dict]:
        """Query active alerts from Table 8"""

        query = """
        SELECT alert_id, location_id, data_type, severity, value, threshold,
               duration_minutes, timestamp, description
        FROM alerts
        WHERE location_id = %s
        AND status = 'active'
        ORDER BY severity DESC, timestamp DESC
        """

        return self._execute_query(query, [location_id])

    def query_recent_metrics(self, location_id: str, days: int) -> Dict[str, List[float]]:
        """Query recent metric values from metrics table"""

        query = """
        SELECT data_type, value, timestamp
        FROM metrics
        WHERE location_id = %s
        AND timestamp >= DATE_SUB(NOW(), INTERVAL %s DAY)
        ORDER BY data_type, timestamp
        """

        results = self._execute_query(query, [location_id, days])

        # Group by data_type
        metrics_by_type = {}
        for row in results:
            data_type = row['data_type']
            if data_type not in metrics_by_type:
                metrics_by_type[data_type] = []
            metrics_by_type[data_type].append(row['value'])

        return metrics_by_type

    def query_employee_workload(self, employee_id: str, date) -> List[Dict]:
        """Query employee's workload for specific date"""

        query = """
        SELECT work_order_id, work_order_name, start_time, end_time,
               duration_minutes, location, priority
        FROM work_orders
        WHERE assignee_id = %s
        AND DATE(start_time) = %s
        AND status IN ('pending', 'in_progress')
        ORDER BY start_time
        """

        return self._execute_query(query, [employee_id, date])

    def _execute_query(self, query: str, params: List) -> List[Dict]:
        """Execute database query and return results"""
        # Implementation depends on your database library
        # This is a placeholder for the actual database implementation
        pass

    def _connect(self, connection_string):
        """Establish database connection"""
        # Implementation depends on your database
        pass
