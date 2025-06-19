from typing import Dict, Any, List
from datetime import datetime
import json

class ResultFormatter:
    """Result formatter with tier-aware capabilities and comprehensive formatting"""

    def format_optimization_results(self, results: Dict[str, Any],
                                  format_type: str = "summary",
                                  customer_tier: str = "basic") -> str:
        """Format optimization results with tier-appropriate detail level and business context"""

        if not results.get("success"):
            return self._format_tier_aware_error(results, customer_tier)

        # Handle case where we have a note about parsing issues
        if results.get("note"):
            print(f"ℹ️  Note: {results['note']}")

        # Add enhanced tier-specific header
        tier_header = self._get_enhanced_tier_header(results, customer_tier)

        if format_type == "summary":
            base_summary = self._format_tier_aware_summary(results, customer_tier)
            return f"{tier_header}\n{base_summary}"
        elif format_type == "detailed":
            detailed_content = self._format_tier_aware_detailed(results, customer_tier)
            return f"{tier_header}\n{detailed_content}"
        elif format_type == "json":
            return self._format_tier_enhanced_json(results, customer_tier)
        else:
            base_summary = self._format_tier_aware_summary(results, customer_tier)
            return f"{tier_header}\n{base_summary}"

    def _format_error_response(self, results: Dict[str, Any]) -> str:
        """Format error responses with helpful context (from original ResultFormatter)"""
        error_msg = results.get('error', 'Unknown error')

        error_response = f"❌ **Optimization Failed**\n"
        error_response += f"Error: {error_msg}\n"

        # Add context if validation error
        if 'validation_error' in results:
            validation = results['validation_error']
            error_response += f"\n💡 **Issue Details:**\n"
            error_response += f"  - Customer Tier: {validation.get('tier_info', {}).get('customer_tier', 'unknown')}\n"
            error_response += f"  - Requested Level: {validation.get('tier_info', {}).get('requested_level', 'unknown')}\n"
            error_response += f"  - Work Orders: {validation.get('tier_info', {}).get('work_order_count', 0)}\n"

            if validation.get('upgrade_required'):
                error_response += f"\n🔄 **Resolution:**\n"
                error_response += f"  - Upgrade your subscription tier\n"
                error_response += f"  - Or reduce the number of work orders\n"
                error_response += f"  - Visit: {validation.get('upgrade_url', '/upgrade')}\n"

        if 'raw_response' in results:
            error_response += f"\n🔍 **Raw Response Preview:**\n"
            error_response += f"{results['raw_response'][:200]}...\n"

        return error_response

    def _format_tier_aware_error(self, results: Dict[str, Any], customer_tier: str) -> str:
        """Format error with tier-specific upgrade guidance (from TierAwareResultFormatter)"""
        base_error = self._format_error_response(results)

        if 'validation_error' in results and results['validation_error'].get('upgrade_required'):
            validation = results['validation_error']

            tier_upgrade_info = f"""
🔄 **Tier Upgrade Benefits:**

**Current Tier**: {customer_tier.title()}
**Recommended Tier**: {validation.get('tier_info', {}).get('requested_level', 'professional').title()}

**What You'll Get:**
"""

            if customer_tier == "basic":
                tier_upgrade_info += """
✅ **Professional Tier Upgrade**:
  - Employee skill matching and performance analytics
  - Location priority scoring and travel optimization
  - Cost analysis with hourly rate optimization
  - Alert severity analysis and hotspot detection
  - Up to 200 work orders per optimization
  - Advanced conflict detection with cost impact

✅ **Enterprise Tier (Premium)**:
  - Everything in Professional +
  - Predictive analytics and future planning
  - Strategic business recommendations
  - ROI analysis and investment planning
  - Up to 1,000 work orders per optimization
  - Custom optimization rules and compliance tracking
"""
            elif customer_tier == "professional":
                tier_upgrade_info += """
✅ **Enterprise Tier Upgrade**:
  - Predictive analytics (89% accuracy alert forecasting)
  - Strategic business recommendations with ROI calculations
  - Investment opportunity analysis (automation ROI, training ROI)
  - Performance benchmarking and competitive analysis
  - Risk assessment and compliance management
  - Custom optimization rules and business logic
  - Up to 1,000 work orders per optimization
"""

            tier_upgrade_info += f"\n💳 **Upgrade Now**: {validation.get('upgrade_url', '/upgrade')}"

            return base_error + tier_upgrade_info

        return base_error

    def _get_enhanced_tier_header(self, results: Dict[str, Any], customer_tier: str) -> str:
        """Generate enhanced tier-specific header with business intelligence (from TierAwareResultFormatter)"""
        level = results.get("optimization_level", "basic")
        usage = results.get("usage", {})
        optimizations = results.get("optimizations", {})

        tier_emojis = {
            "basic": "🥉",
            "professional": "🥈",
            "enterprise": "🥇"
        }

        emoji = tier_emojis.get(customer_tier, "🔧")

        header = f"{emoji} **{level.title()} Optimization Complete** (Customer Tier: {customer_tier.title()})"

        # Add token usage
        if usage:
            header += f"\n📊 **Token Usage**: {usage.get('input_tokens', 0)} in, {usage.get('output_tokens', 0)} out (Total: {usage.get('total_tokens', 0)})"

        # Add cost information
        if "cost_info" in optimizations:
            cost_info = optimizations["cost_info"]
            if cost_info.get("billing_type") == "included":
                header += f"\n💰 **Cost**: Included in plan ({cost_info.get('remaining_included', 0)} optimizations remaining this month)"
            else:
                header += f"\n💰 **Cost**: ${cost_info.get('total_cost', 0):.2f} (Pay-per-use)"

        # Add business value indicators
        if customer_tier == "basic":
            header += f"\n🔧 **Capability**: Conflict resolution and basic scheduling optimization"
        elif customer_tier == "professional":
            header += f"\n📊 **Capability**: Performance analytics, skill matching, and cost optimization"

            # Add business metrics if available
            if "business_metrics" in optimizations:
                metrics = optimizations["business_metrics"]
                if "operational_metrics" in metrics:
                    op_metrics = metrics["operational_metrics"]
                    header += f"\n📈 **Business Impact**: ${op_metrics.get('estimated_labor_cost', 0):.2f} labor cost optimized"
        else:  # enterprise
            header += f"\n🏢 **Capability**: Strategic optimization with predictive analytics and business intelligence"

            # Add strategic metrics if available
            if "performance_metrics" in optimizations:
                perf_metrics = optimizations["performance_metrics"]
                estimated_savings = perf_metrics.get('estimated_annual_savings', 'N/A')
                header += f"\n💼 **Strategic Impact**: {estimated_savings} potential annual savings"

        # Add token efficiency
        if usage and "cost_info" in optimizations:
            cost = optimizations["cost_info"].get('total_cost', 1)
            if cost > 0:
                tokens_per_dollar = usage.get('total_tokens', 0) / cost
                header += f"\n⚡ **Efficiency**: {tokens_per_dollar:.0f} tokens/$"

        return header

    def _format_enhanced_summary(self, results: Dict[str, Any]) -> str:
        """Format enhanced summary with rich model data (from original ResultFormatter)"""
        optimizations = results["optimizations"]
        usage = results["usage"]
        level = results["optimization_level"]

        sections = []

        # Header with enhanced info
        sections.append(f"✅ **{level.title()} Optimization Complete**")
        sections.append(f"📊 **Token Usage**: {usage['input_tokens']} in, {usage['output_tokens']} out (Total: {usage['total_tokens']})")

        # Cost information if available
        if "cost_info" in optimizations:
            cost_info = optimizations["cost_info"]
            cost_text = self._format_cost_summary(cost_info)
            if cost_text:
                sections.append(cost_text)

        sections.append("")

        # Enhanced optimization summary
        recommendation_counts = {}
        total_cost_impact = 0

        for rec_type in ["time", "assignee", "location", "priority"]:
            if rec_type in optimizations and isinstance(optimizations[rec_type], list) and optimizations[rec_type]:
                recommendation_counts[rec_type] = len(optimizations[rec_type])

                # Extract cost impact if available
                for rec in optimizations[rec_type]:
                    if isinstance(rec, dict) and 'cost_impact' in rec:
                        try:
                            cost_impact = float(str(rec['cost_impact']).replace('$', '').replace(',', ''))
                            total_cost_impact += cost_impact
                        except:
                            pass

        if recommendation_counts:
            sections.append("🔧 **Optimization Summary:**")
            for rec_type, count in recommendation_counts.items():
                sections.append(f"  - {rec_type.title()} optimizations: {count}")

            if total_cost_impact > 0:
                sections.append(f"  - **Total Cost Impact**: ${total_cost_impact:.2f}")
            sections.append("")

        # Enhanced key recommendations
        sections.append("📋 **Key Recommendations:**")

        for rec_type in ["time", "assignee", "location", "priority"]:
            if rec_type in optimizations and isinstance(optimizations[rec_type], list) and optimizations[rec_type]:
                sections.append(f"**{rec_type.title()} Optimizations:**")

                for rec in optimizations[rec_type][:3]:  # Show first 3
                    formatted_rec = self._format_recommendation(rec, rec_type)
                    sections.append(formatted_rec)

                if len(optimizations[rec_type]) > 3:
                    sections.append(f"  ... and {len(optimizations[rec_type]) - 3} more optimizations")
                sections.append("")

        # Enhanced insights display
        insights_displayed = False

        # Performance insights
        if "performance_insights" in optimizations and isinstance(optimizations["performance_insights"], list):
            sections.append("💡 **Performance Insights:**")
            insights_displayed = True

            for insight in optimizations["performance_insights"][:3]:
                formatted_insight = self._format_performance_insight(insight)
                sections.append(formatted_insight)
            sections.append("")

        # Strategic recommendations
        if "strategic_recommendations" in optimizations and isinstance(optimizations["strategic_recommendations"], list):
            sections.append("🎯 **Strategic Recommendations:**")
            insights_displayed = True

            for rec in optimizations["strategic_recommendations"][:2]:
                formatted_strategic = self._format_strategic_recommendation(rec)
                sections.append(formatted_strategic)
            sections.append("")

        # Optimization summary/metrics
        if "optimization_summary" in optimizations:
            summary = optimizations["optimization_summary"]
            sections.append("📈 **Optimization Impact:**")

            if "projected_improvements" in summary:
                improvements = summary["projected_improvements"]
                for metric, value in improvements.items():
                    metric_name = metric.replace('_', ' ').title()
                    sections.append(f"  - **{metric_name}**: {value}")

            if "critical_actions" in summary:
                sections.append("\n🎯 **Priority Actions:**")
                for action in summary["critical_actions"][:3]:
                    sections.append(f"  - {action}")
            sections.append("")

        # Performance metrics (enterprise level)
        if "performance_metrics" in optimizations:
            metrics = optimizations["performance_metrics"]
            sections.append("📊 **Performance Metrics:**")

            for metric, value in metrics.items():
                metric_name = metric.replace('_', ' ').title()
                sections.append(f"  - **{metric_name}**: {value}")
            sections.append("")

        # If no enhanced insights were displayed, show basic analysis
        if not insights_displayed and not recommendation_counts:
            sections.append("📄 **Analysis Results:**")
            if isinstance(optimizations, dict) and "analysis" not in optimizations:
                sections.append(str(optimizations)[:300] + "..." if len(str(optimizations)) > 300 else str(optimizations))
            else:
                sections.append("Optimization analysis completed. See detailed view for more information.")

        return "\n".join(sections)

    def _format_tier_aware_summary(self, results: Dict[str, Any], customer_tier: str) -> str:
        """Format summary with tier-appropriate restrictions and upgrade prompts"""

        if customer_tier == "basic":
            return self._format_basic_tier_summary(results)
        elif customer_tier == "professional":
            return self._format_professional_tier_summary(results)
        else:  # enterprise
            return self._format_enterprise_tier_summary(results)

    def _format_basic_tier_summary(self, results: Dict[str, Any]) -> str:
        """Format basic tier summary with upgrade prompts (from TierAwareResultFormatter)"""
        optimizations = results["optimizations"]

        sections = []
        sections.append("🔧 **Basic Optimization Results:**")

        # Show basic recommendations only
        basic_features = ["time", "assignee", "location", "priority"]
        recommendation_counts = {}

        for rec_type in basic_features:
            if rec_type in optimizations and isinstance(optimizations[rec_type], list) and optimizations[rec_type]:
                recommendation_counts[rec_type] = len(optimizations[rec_type])

        if recommendation_counts:
            sections.append("\n**Conflicts Resolved:**")
            for rec_type, count in recommendation_counts.items():
                sections.append(f"  - {rec_type.title()}: {count} optimizations")

        # Show simplified recommendations
        sections.append("\n**Key Changes:**")
        for rec_type in basic_features:
            if rec_type in optimizations and optimizations[rec_type]:
                for rec in optimizations[rec_type][:2]:  # Limit to 2 for basic
                    if isinstance(rec, dict):
                        rec_id = rec.get('id', 'Unknown')
                        reason = rec.get('reason', 'Optimization needed')
                        sections.append(f"  - WO {rec_id}: {reason}")

        # Add upgrade prompts
        sections.append("\n🔄 **Want More Insights?**")
        sections.append("  Upgrade to Professional for:")
        sections.append("  • Employee skill matching and performance analytics")
        sections.append("  • Cost analysis with hourly rate optimization")
        sections.append("  • Location priority scoring and travel optimization")
        sections.append("  • Alert severity analysis and business impact")

        return "\n".join(sections)

    def _format_professional_tier_summary(self, results: Dict[str, Any]) -> str:
        """Format professional tier summary with enterprise upgrade prompts (from TierAwareResultFormatter)"""
        # Use enhanced summary but add enterprise upgrade prompts
        base_summary = self._format_enhanced_summary(results)
        optimizations = results["optimizations"]

        # Add professional-specific business metrics
        if "business_metrics" in optimizations:
            metrics = optimizations["business_metrics"]

            base_summary += "\n\n📊 **Professional Business Intelligence:**\n"

            if "operational_metrics" in metrics:
                op_metrics = metrics["operational_metrics"]
                base_summary += f"  - **Labor Cost Optimized**: ${op_metrics.get('estimated_labor_cost', 0):.2f}\n"
                base_summary += f"  - **Utilization Rate**: {op_metrics.get('utilization_rate', 0):.1f}%\n"

            if "tier_value_metrics" in metrics:
                value_metrics = metrics["tier_value_metrics"]
                roi_ratio = value_metrics.get('potential_roi', {}).get('roi_ratio', 0)
                if roi_ratio > 0:
                    base_summary += f"  - **ROI**: {roi_ratio:.1f}x return on optimization investment\n"

        # Add enterprise upgrade prompt
        base_summary += "\n🚀 **Unlock Enterprise Features:**\n"
        base_summary += "  • Predictive analytics (prevent issues before they occur)\n"
        base_summary += "  • Strategic business recommendations with ROI analysis\n"
        base_summary += "  • Investment opportunity identification\n"
        base_summary += "  • Risk assessment and compliance management\n"
        base_summary += "  • Performance benchmarking and competitive analysis\n"

        return base_summary

    def _format_enterprise_tier_summary(self, results: Dict[str, Any]) -> str:
        """Format enterprise tier summary with full capabilities"""
        return self._format_enhanced_summary(results)

    def _format_tier_aware_detailed(self, results: Dict[str, Any], customer_tier: str) -> str:
        """Format detailed results with tier-appropriate restrictions"""

        if customer_tier == "basic":
            return self._format_basic_tier_detailed(results)
        elif customer_tier == "professional":
            return self._format_professional_tier_detailed(results)
        else:  # enterprise
            return self._format_enhanced_detailed(results)

    def _format_enhanced_detailed(self, results: Dict[str, Any]) -> str:
        """Format detailed results with comprehensive model data (from original ResultFormatter)"""
        optimizations = results["optimizations"]

        sections = []
        sections.append("=" * 80)
        sections.append(f"DETAILED OPTIMIZATION RESULTS ({results['optimization_level'].upper()})")
        sections.append("=" * 80)
        sections.append("")

        # Cost and billing information
        if "cost_info" in optimizations:
            cost_summary = self._format_cost_summary(optimizations["cost_info"])
            if cost_summary:
                sections.append(cost_summary)
                sections.append("")

        # Detailed recommendations by type
        for rec_type in ["time", "assignee", "location", "priority"]:
            if rec_type in optimizations and isinstance(optimizations[rec_type], list) and optimizations[rec_type]:
                sections.append(f"## {rec_type.upper()} OPTIMIZATIONS")
                sections.append("-" * 40)

                for i, rec in enumerate(optimizations[rec_type], 1):
                    sections.append(f"{i}. {self._format_detailed_recommendation(rec, rec_type)}")
                    sections.append("")

                sections.append("")

        # Enhanced insights sections
        if "performance_insights" in optimizations and isinstance(optimizations["performance_insights"], list):
            sections.append("## PERFORMANCE INSIGHTS")
            sections.append("-" * 40)

            for i, insight in enumerate(optimizations["performance_insights"], 1):
                sections.append(f"{i}. {self._format_detailed_performance_insight(insight)}")
                sections.append("")

            sections.append("")

        if "strategic_recommendations" in optimizations and isinstance(optimizations["strategic_recommendations"], list):
            sections.append("## STRATEGIC RECOMMENDATIONS")
            sections.append("-" * 40)

            for i, rec in enumerate(optimizations["strategic_recommendations"], 1):
                sections.append(f"{i}. {self._format_detailed_strategic_recommendation(rec)}")
                sections.append("")

            sections.append("")

        # Performance metrics and business intelligence
        if "performance_metrics" in optimizations:
            sections.append("## PERFORMANCE METRICS & BUSINESS INTELLIGENCE")
            sections.append("-" * 40)

            metrics = optimizations["performance_metrics"]
            for metric, value in metrics.items():
                metric_name = metric.replace('_', ' ').title()
                sections.append(f"**{metric_name}**: {value}")

            sections.append("")

        # Optimization summary
        if "optimization_summary" in optimizations:
            sections.append("## OPTIMIZATION SUMMARY")
            sections.append("-" * 40)

            summary = optimizations["optimization_summary"]

            if "projected_improvements" in summary:
                sections.append("**Projected Improvements:**")
                for metric, value in summary["projected_improvements"].items():
                    sections.append(f"  - {metric.replace('_', ' ').title()}: {value}")
                sections.append("")

            if "critical_actions" in summary:
                sections.append("**Critical Actions:**")
                for action in summary["critical_actions"]:
                    sections.append(f"  - {action}")
                sections.append("")

        return "\n".join(sections)

    def _format_basic_tier_detailed(self, results: Dict[str, Any]) -> str:
        """Format basic tier detailed view with feature limitations (from TierAwareResultFormatter)"""
        sections = []
        sections.append("⚠️ **Basic Tier - Limited Detailed View**")
        sections.append("Upgrade to Professional tier for comprehensive detailed reports.\n")

        # Show basic summary instead
        basic_summary = self._format_basic_tier_summary(results)
        sections.append(basic_summary)

        sections.append("\n🔄 **Professional Tier Benefits:**")
        sections.append("  • Detailed performance analysis with employee efficiency ratings")
        sections.append("  • Cost breakdown with hourly rate comparisons")
        sections.append("  • Location intelligence with cleaning priority scores")
        sections.append("  • Alert impact analysis with severity levels")
        sections.append("  • Travel time optimization calculations")
        sections.append("  • Skill matching recommendations")

        return "\n".join(sections)

    def _format_professional_tier_detailed(self, results: Dict[str, Any]) -> str:
        """Format professional tier detailed view with enterprise teasers (from TierAwareResultFormatter)"""
        # Use enhanced detailed format but remove enterprise-only sections
        optimizations = results["optimizations"]

        sections = []
        sections.append("=" * 80)
        sections.append(f"PROFESSIONAL OPTIMIZATION ANALYSIS ({results['optimization_level'].upper()})")
        sections.append("=" * 80)
        sections.append("")

        # Cost and billing information
        if "cost_info" in optimizations:
            cost_summary = self._format_cost_summary(optimizations["cost_info"])
            if cost_summary:
                sections.append(cost_summary)
                sections.append("")

        # Professional-level sections
        professional_sections = ["time", "assignee", "location", "priority", "performance_insights"]

        for section in professional_sections:
            if section in optimizations and isinstance(optimizations[section], list) and optimizations[section]:
                sections.append(f"## {section.upper().replace('_', ' ')} ANALYSIS")
                sections.append("-" * 40)

                for i, item in enumerate(optimizations[section], 1):
                    if section == "performance_insights":
                        sections.append(f"{i}. {self._format_detailed_performance_insight(item)}")
                    else:
                        sections.append(f"{i}. {self._format_detailed_recommendation(item, section)}")
                    sections.append("")

                sections.append("")

        # Business metrics for professional tier
        if "business_metrics" in optimizations:
            sections.append("## BUSINESS INTELLIGENCE")
            sections.append("-" * 40)

            metrics = optimizations["business_metrics"]

            if "operational_metrics" in metrics:
                sections.append("**Operational Metrics:**")
                op_metrics = metrics["operational_metrics"]
                for metric, value in op_metrics.items():
                    sections.append(f"  - {metric.replace('_', ' ').title()}: {value}")
                sections.append("")

            if "tier_value_metrics" in metrics:
                sections.append("**Value Analysis:**")
                value_metrics = metrics["tier_value_metrics"]
                for metric, value in value_metrics.items():
                    if isinstance(value, dict):
                        sections.append(f"  - {metric.replace('_', ' ').title()}:")
                        for sub_metric, sub_value in value.items():
                            sections.append(f"    • {sub_metric.replace('_', ' ').title()}: {sub_value}")
                    else:
                        sections.append(f"  - {metric.replace('_', ' ').title()}: {value}")
                sections.append("")

        # Enterprise teaser
        sections.append("## 🚀 ENTERPRISE FEATURES PREVIEW")
        sections.append("-" * 40)
        sections.append("**Available in Enterprise Tier:**")
        sections.append("  • Strategic Recommendations with ROI Analysis")
        sections.append("  • Predictive Analytics and Future Planning")
        sections.append("  • Investment Opportunity Analysis")
        sections.append("  • Risk Assessment and Compliance Management")
        sections.append("  • Performance Benchmarking")
        sections.append("  • Custom Business Rules and Automation")
        sections.append("")
        sections.append("Upgrade to Enterprise for complete business intelligence!")

        return "\n".join(sections)

    def _format_recommendation(self, rec: Dict, rec_type: str) -> str:
        """Format individual recommendation with enhanced data (from original ResultFormatter)"""
        if not isinstance(rec, dict):
            return f"  - {str(rec)[:100]}..."

        # Handle new expected format first
        rec_id = rec.get('id') or rec.get('work_order_id') or rec.get('wo_id', 'Unknown')
        reason = rec.get('reason') or rec.get('explanation', 'No reason provided')

        base_text = f"  - **WO {rec_id}**: {reason}"

        # Add specific details based on type
        if rec_type == "time":
            original = rec.get('original_time') or rec.get('current_time', 'N/A')
            recommended = rec.get('recommended_time') or rec.get('new_time', 'N/A')
            change_text = f"\n    📅 {original} → {recommended}"

            # Add cost impact if available
            cost_impact = rec.get('cost_impact')
            if cost_impact:
                change_text += f" | 💰 Impact: ${cost_impact}"

        elif rec_type == "assignee":
            original = rec.get('original_assignee') or rec.get('current_assignee', 'N/A')
            recommended = rec.get('recommended_assignee') or rec.get('new_assignee', 'N/A')
            change_text = f"\n    👥 {original} → {recommended}"

            # Add skill/rate info if available
            skill_info = rec.get('skill_info')
            if skill_info:
                change_text += f" | 🎯 Skills: {skill_info}"

        elif rec_type == "location":
            original = rec.get('original_location') or rec.get('current_location', 'N/A')
            recommended = rec.get('recommended_location') or rec.get('new_location', 'N/A')
            change_text = f"\n    📍 {original} → {recommended}"

            # Add travel savings if available
            travel_savings = rec.get('travel_savings')
            if travel_savings:
                change_text += f" | ⏱️ Saves: {travel_savings}"

        elif rec_type == "priority":
            original = rec.get('original_priority') or rec.get('current_priority', 'N/A')
            recommended = rec.get('recommended_priority') or rec.get('new_priority', 'N/A')
            change_text = f"\n    ⚡ {original} → {recommended}"

            # Add alert info if available
            alert_info = rec.get('alert_info')
            if alert_info:
                change_text += f" | 🚨 Alerts: {alert_info}"
        else:
            change_text = ""

        return base_text + change_text

    def _format_performance_insight(self, insight: Dict) -> str:
        """Format performance insight with enhanced data (from original ResultFormatter)"""
        if not isinstance(insight, dict):
            return f"  - {str(insight)[:100]}..."

        insight_text = insight.get('insight') or insight.get('description', str(insight))
        recommendation = insight.get('recommendation') or insight.get('action', '')
        impact = insight.get('impact', '')

        formatted = f"  - **💡 {insight_text}**"

        if recommendation:
            formatted += f"\n    🎯 **Action**: {recommendation}"

        if impact:
            formatted += f"\n    📈 **Impact**: {impact}"

        return formatted

    def _format_strategic_recommendation(self, rec: Dict) -> str:
        """Format strategic recommendation with business context (from original ResultFormatter)"""
        if not isinstance(rec, dict):
            return f"  - {str(rec)[:100]}..."

        recommendation = rec.get('recommendation') or rec.get('description', str(rec))
        category = rec.get('category', 'general').replace('_', ' ').title()
        impact = rec.get('business_impact') or rec.get('impact', '')
        effort = rec.get('implementation_effort', 'unknown')
        roi = rec.get('roi_estimate', '')

        formatted = f"  - **🎯 {category}**: {recommendation}"

        if impact:
            formatted += f"\n    📊 **Business Impact**: {impact}"

        if effort and roi:
            formatted += f"\n    ⚡ **Implementation**: {effort} effort | ROI: {roi}"

        return formatted

    def _format_cost_summary(self, cost_info: Dict) -> str:
        """Format cost summary with enhanced billing details (from original ResultFormatter)"""
        if not cost_info:
            return ""

        if cost_info.get('billing_type') == 'included':
            remaining = cost_info.get('remaining_included', 0)
            return f"💰 **Cost**: Included in plan ({remaining} optimizations remaining this month)"
        else:
            total_cost = cost_info.get('total_cost', 0)
            base_cost = cost_info.get('base_cost', 0)
            work_order_cost = cost_info.get('work_order_cost', 0)
            work_order_count = cost_info.get('work_order_count', 0)

            cost_text = f"💰 **Cost**: ${total_cost:.2f}"

            if base_cost > 0 and work_order_cost > 0:
                cost_text += f" (Base: ${base_cost:.2f} + ${work_order_cost:.2f} for {work_order_count} work orders)"

            return cost_text

    def _format_detailed_recommendation(self, rec: Dict, rec_type: str) -> str:
        """Format detailed recommendation with all available data (from original ResultFormatter)"""
        if not isinstance(rec, dict):
            return f"Recommendation: {str(rec)}"

        rec_id = rec.get('id') or rec.get('work_order_id') or rec.get('wo_id', 'Unknown')
        reason = rec.get('reason') or rec.get('explanation', 'No reason provided')

        details = [f"Work Order ID: {rec_id}"]

        if rec_type == "time":
            original = rec.get('original_time') or rec.get('current_time')
            recommended = rec.get('recommended_time') or rec.get('new_time')
            if original:
                details.append(f"Original Time: {original}")
            if recommended:
                details.append(f"Recommended Time: {recommended}")

            cost_impact = rec.get('cost_impact')
            if cost_impact:
                details.append(f"Cost Impact: ${cost_impact}")

        elif rec_type == "assignee":
            original = rec.get('original_assignee') or rec.get('current_assignee')
            recommended = rec.get('recommended_assignee') or rec.get('new_assignee')
            if original:
                details.append(f"Original Assignee: {original}")
            if recommended:
                details.append(f"Recommended Assignee: {recommended}")

            # Add skill and rate information
            skill_match = rec.get('skill_match_improvement')
            if skill_match:
                details.append(f"Skill Match Improvement: {skill_match}")

            cost_change = rec.get('cost_change')
            if cost_change:
                details.append(f"Cost Change: {cost_change}")

        elif rec_type == "location":
            original = rec.get('original_location') or rec.get('current_location')
            recommended = rec.get('recommended_location') or rec.get('new_location')
            if original:
                details.append(f"Original Location: {original}")
            if recommended:
                details.append(f"Recommended Location: {recommended}")

            travel_savings = rec.get('travel_time_savings')
            if travel_savings:
                details.append(f"Travel Time Savings: {travel_savings}")

        elif rec_type == "priority":
            original = rec.get('original_priority') or rec.get('current_priority')
            recommended = rec.get('recommended_priority') or rec.get('new_priority')
            if original:
                details.append(f"Original Priority: {original}")
            if recommended:
                details.append(f"Recommended Priority: {recommended}")

            alert_context = rec.get('alert_context')
            if alert_context:
                details.append(f"Alert Context: {alert_context}")

        details.append(f"Reason: {reason}")

        return "\n   ".join(details)

    def _format_detailed_performance_insight(self, insight: Dict) -> str:
        """Format detailed performance insight (from original ResultFormatter)"""
        if not isinstance(insight, dict):
            return f"Insight: {str(insight)}"

        insight_text = insight.get('insight') or insight.get('description', '')
        recommendation = insight.get('recommendation') or insight.get('action', '')
        impact = insight.get('impact', '')
        confidence = insight.get('confidence')
        data_source = insight.get('data_source', 'performance analysis')

        details = []

        if insight_text:
            details.append(f"Insight: {insight_text}")

        if recommendation:
            details.append(f"Recommendation: {recommendation}")

        if impact:
            details.append(f"Expected Impact: {impact}")

        if confidence:
            details.append(f"Confidence Level: {confidence:.0%}" if isinstance(confidence, float) else f"Confidence: {confidence}")

        details.append(f"Data Source: {data_source}")

        return "\n   ".join(details)

    def _format_detailed_strategic_recommendation(self, rec: Dict) -> str:
        """Format detailed strategic recommendation (from original ResultFormatter)"""
        if not isinstance(rec, dict):
            return f"Recommendation: {str(rec)}"

        recommendation = rec.get('recommendation') or rec.get('description', '')
        category = rec.get('category', 'general')
        business_impact = rec.get('business_impact') or rec.get('impact', '')
        implementation_effort = rec.get('implementation_effort', '')
        roi_estimate = rec.get('roi_estimate', '')
        timeline = rec.get('timeline', '')
        prerequisites = rec.get('prerequisites', [])

        details = []

        details.append(f"Category: {category.replace('_', ' ').title()}")

        if recommendation:
            details.append(f"Recommendation: {recommendation}")

        if business_impact:
            details.append(f"Business Impact: {business_impact}")

        if implementation_effort:
            details.append(f"Implementation Effort: {implementation_effort}")

        if roi_estimate:
            details.append(f"ROI Estimate: {roi_estimate}")

        if timeline:
            details.append(f"Timeline: {timeline}")

        if prerequisites:
            details.append(f"Prerequisites: {', '.join(prerequisites)}")

        return "\n   ".join(details)

    def _format_enhanced_json(self, results: Dict[str, Any]) -> str:
        """Format as enhanced pretty JSON with metadata (from original ResultFormatter)"""
        # Add formatting metadata
        enhanced_results = results.copy()
        enhanced_results['_metadata'] = {
            'formatted_at': datetime.now().isoformat(),
            'formatter_version': '2.0_enhanced',
            'optimization_level': results.get('optimization_level', 'unknown'),
            'model_integration': 'enhanced_employee_location_alert_data'
        }

        return json.dumps(enhanced_results, indent=2, default=str)

    def _format_tier_enhanced_json(self, results: Dict[str, Any], customer_tier: str) -> str:
        """Format JSON with tier-specific metadata and restrictions (from TierAwareResultFormatter)"""
        enhanced_results = results.copy()

        # Add tier metadata
        enhanced_results['_tier_metadata'] = {
            'customer_tier': customer_tier,
            'optimization_level': results.get('optimization_level', 'unknown'),
            'tier_restrictions_applied': customer_tier != 'enterprise',
            'available_features': self._get_tier_available_features(customer_tier),
            'upgrade_benefits': self._get_upgrade_benefits(customer_tier)
        }

        # Apply tier restrictions to JSON output
        if customer_tier == "basic":
            # Remove advanced features from JSON
            optimizations = enhanced_results.get("optimizations", {})
            restricted_optimizations = {}

            # Keep only basic features
            basic_features = ["time", "assignee", "location", "priority"]
            for feature in basic_features:
                if feature in optimizations:
                    restricted_optimizations[feature] = optimizations[feature]

            # Add basic metadata
            if "cost_info" in optimizations:
                restricted_optimizations["cost_info"] = optimizations["cost_info"]

            enhanced_results["optimizations"] = restricted_optimizations

        elif customer_tier == "professional":
            # Remove enterprise-only features
            optimizations = enhanced_results.get("optimizations", {})
            enterprise_features = ["strategic_recommendations", "predictive_insights", "performance_metrics"]

            for feature in enterprise_features:
                optimizations.pop(feature, None)

        enhanced_results['_formatted_at'] = datetime.now().isoformat()
        enhanced_results['_formatter_version'] = f'3.0_unified_tier_aware_{customer_tier}'

        return json.dumps(enhanced_results, indent=2, default=str)

    def _get_tier_available_features(self, customer_tier: str) -> List[str]:
        """Get list of available features for tier (from TierAwareResultFormatter)"""
        tier_features = {
            "basic": [
                "conflict_resolution",
                "basic_workload_balancing",
                "simple_scheduling",
                "basic_location_grouping"
            ],
            "professional": [
                "conflict_resolution", "basic_workload_balancing", "simple_scheduling", "basic_location_grouping",
                "performance_analysis", "workload_distribution", "location_optimization",
                "historical_patterns", "travel_time_optimization", "performance_insights",
                "skill_analysis", "cost_analysis", "alert_impact_analysis"
            ],
            "enterprise": [
                "all_professional_features",
                "advanced_analytics", "template_patterns", "priority_anomalies",
                "efficiency_opportunities", "predictive_insights", "strategic_recommendations",
                "resource_utilization", "scheduling_gaps", "custom_rules",
                "risk_assessment", "compliance_management", "roi_analysis"
            ]
        }

        return tier_features.get(customer_tier, tier_features["basic"])

    def _get_upgrade_benefits(self, customer_tier: str) -> Dict[str, List[str]]:
        """Get upgrade benefits for current tier (from TierAwareResultFormatter)"""
        if customer_tier == "basic":
            return {
                "professional": [
                    "Employee skill matching and performance analytics",
                    "Cost analysis with hourly rate optimization",
                    "Location priority scoring and travel optimization",
                    "Alert severity analysis and business impact",
                    "Advanced conflict detection with cost impact",
                    "Up to 200 work orders per optimization"
                ],
                "enterprise": [
                    "Everything in Professional +",
                    "Predictive analytics and future planning",
                    "Strategic business recommendations with ROI",
                    "Investment opportunity analysis",
                    "Risk assessment and compliance management",
                    "Up to 1,000 work orders per optimization"
                ]
            }
        elif customer_tier == "professional":
            return {
                "enterprise": [
                    "Predictive analytics (89% accuracy forecasting)",
                    "Strategic business recommendations with ROI calculations",
                    "Investment opportunity analysis (automation ROI, training ROI)",
                    "Performance benchmarking and competitive analysis",
                    "Risk assessment and compliance management",
                    "Custom optimization rules and business logic",
                    "Up to 1,000 work orders per optimization"
                ]
            }
        else:
            return {}