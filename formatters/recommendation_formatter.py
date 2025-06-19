from typing import Dict, Any, List
from datetime import datetime
import json

class RecommendationFormatter:
    """Format recommendation results with tier-aware capabilities"""

    def format_recommendation_results(self, results: Dict[str, Any],
                                    format_type: str = "summary",
                                    customer_tier: str = "basic") -> str:
        """Format recommendation results with tier-appropriate detail level"""

        if not results.get("success"):
            return self._format_tier_aware_error(results, customer_tier)

        tier_header = self._get_tier_header(results, customer_tier)

        if format_type == "summary":
            content = self._format_tier_aware_summary(results, customer_tier)
            return f"{tier_header}\n{content}"
        elif format_type == "detailed":
            content = self._format_tier_aware_detailed(results, customer_tier)
            return f"{tier_header}\n{content}"
        elif format_type == "json":
            return self._format_tier_enhanced_json(results, customer_tier)
        else:
            content = self._format_tier_aware_summary(results, customer_tier)
            return f"{tier_header}\n{content}"

    def _get_tier_header(self, results: Dict[str, Any], customer_tier: str) -> str:
        """Generate tier-specific header"""

        tier_emojis = {
            "basic": "🥉",
            "professional": "🥈",
            "enterprise": "🥇"
        }

        emoji = tier_emojis.get(customer_tier, "🔧")
        recommendations = results.get("recommendations", {})

        header = f"{emoji} **Work Order Recommendations Generated** (Tier: {customer_tier.title()})"

        # Add recommendation count
        if "recommended_tasks" in recommendations:
            count = len(recommendations["recommended_tasks"])
            header += f"\n📋 **{count} Recommendations Generated**"
        elif isinstance(recommendations, list):
            count = len(recommendations)
            header += f"\n📋 **{count} Recommendations Generated**"

        # Add confidence info
        if recommendations.get("summary"):
            summary = recommendations["summary"]
            if "confidence_distribution" in summary:
                conf_dist = summary["confidence_distribution"]
                header += f"\n🎯 **Confidence**: {conf_dist.get('high', 0)} high, {conf_dist.get('medium', 0)} medium confidence"

        # Add cost info from results level
        if results.get("cost_info"):
            cost_info = results["cost_info"]
            if cost_info.get("billing_type") == "included":
                header += f"\n💰 **Cost**: Included ({cost_info.get('remaining_included', 0)} remaining this month)"
            else:
                header += f"\n💰 **Cost**: ${cost_info.get('total_cost', 0):.2f}"
        elif recommendations.get("summary", {}).get("total_estimated_cost"):
            cost = recommendations["summary"]["total_estimated_cost"]
            header += f"\n💰 **Total Estimated Cost**: ${cost:.2f}"

        return header

    def _format_tier_aware_summary(self, results: Dict[str, Any], customer_tier: str) -> str:
        """Format summary with tier-appropriate restrictions"""

        if customer_tier == "basic":
            return self._format_basic_tier_summary(results)
        elif customer_tier == "professional":
            return self._format_professional_tier_summary(results)
        else:  # enterprise
            return self._format_enterprise_tier_summary(results)

    def _format_basic_tier_summary(self, results: Dict[str, Any]) -> str:
        """Format basic tier summary"""
        recommendations = self._get_recommendations_data(results)

        sections = []
        sections.append("🔧 **Basic Recommendations:**")

        # Handle different recommendation formats
        tasks = self._extract_tasks(recommendations)

        if tasks:
            sections.append("\n**Recommended Tasks:**")
            for task in tasks[:3]:  # Limit to 3 for basic
                task_name = self._safe_get(task, ['task_name', 'recommended_name', 'name'], 'Unnamed Task')
                assignee = self._safe_get(task, ['recommended_assignee', 'assignee'], 'Unassigned')
                location = self._safe_get(task, ['recommended_location', 'location'], 'Unknown Location')
                cost = self._safe_get(task, ['estimated_cost', 'cost'], 0)
                confidence = self._safe_get(task, ['confidence_score', 'confidence'], 0)

                sections.append(f"  - **{task_name}**: {assignee} at {location}")
                sections.append(f"    💰 ${cost:.2f} | 🎯 Confidence: {confidence:.0%}")

        # Add upgrade prompts
        sections.append("\n🔄 **Want More Insights?**")
        sections.append("  Upgrade to Professional for:")
        sections.append("  • Performance analytics and trend analysis")
        sections.append("  • Advanced employee skill matching")
        sections.append("  • Alert correlation and metric-driven recommendations")
        sections.append("  • Cost optimization and ROI analysis")

        return "\n".join(sections)

    def _format_professional_tier_summary(self, results: Dict[str, Any]) -> str:
        """Format professional tier summary"""
        recommendations = self._get_recommendations_data(results)

        sections = []
        sections.append("📊 **Professional Recommendations with Analytics:**")

        # Handle different recommendation formats
        tasks = self._extract_tasks(recommendations)

        if tasks:
            sections.append(f"\n**Recommended Tasks ({len(tasks)}):**")
            for task in tasks[:5]:
                task_name = self._safe_get(task, ['task_name', 'recommended_name', 'name'], 'Unnamed Task')
                assignee = self._safe_get(task, ['recommended_assignee', 'assignee'], 'Unassigned')
                location = self._safe_get(task, ['recommended_location', 'location'], 'Unknown Location')
                start_time = self._safe_get(task, ['recommended_start_time', 'start_time'], 'TBD')
                duration = self._safe_get(task, ['recommended_duration_minutes', 'duration_minutes', 'duration'], 60)
                confidence = self._safe_get(task, ['confidence_score', 'confidence'], 0)
                cost = self._safe_get(task, ['estimated_cost', 'cost'], 0)
                reasoning = self._safe_get(task, ['reasoning', 'reason'], 'No reasoning provided')
                source = self._safe_get(task, ['source'], 'pattern_based')

                sections.append(f"  - **{task_name}** ({source})")
                sections.append(f"    👤 {assignee} | 📍 {location}")
                sections.append(f"    📅 {start_time} | ⏱️ {duration}min")
                sections.append(f"    🎯 {confidence:.0%} confidence | 💰 ${cost:.2f}")
                sections.append(f"    💡 {reasoning}")
                sections.append("")

        # Performance insights
        insights = self._safe_get(recommendations, ['performance_insights'], [])
        if insights:
            sections.append("**Performance Insights:**")
            for insight in insights:
                insight_text = self._safe_get(insight, ['insight', 'description'], 'No insight available')
                recommendation = self._safe_get(insight, ['recommendation', 'action'], 'No recommendation')
                impact = self._safe_get(insight, ['impact'], '')

                sections.append(f"  - **{insight_text}**")
                sections.append(f"    🎯 Action: {recommendation}")
                if impact:
                    sections.append(f"    📈 Impact: {impact}")
                sections.append("")

        # Add enterprise upgrade prompt
        sections.append("🚀 **Unlock Enterprise Features:**")
        sections.append("  • Strategic business intelligence and ROI analysis")
        sections.append("  • Predictive analytics and risk assessment")
        sections.append("  • Investment opportunity identification")
        sections.append("  • Advanced workforce planning and capacity optimization")

        return "\n".join(sections)

    def _format_enterprise_tier_summary(self, results: Dict[str, Any]) -> str:
        """Format enterprise tier summary with full capabilities"""
        recommendations = self._get_recommendations_data(results)

        sections = []
        sections.append("🏢 **Enterprise Strategic Recommendations:**")

        # Strategic recommendations
        tasks = self._extract_tasks(recommendations)

        if tasks:
            sections.append(f"\n**Strategic Task Recommendations ({len(tasks)}):**")
            for task in tasks:
                task_name = self._safe_get(task, ['task_name', 'recommended_name', 'name'], 'Unnamed Task')
                assignee = self._safe_get(task, ['recommended_assignee', 'assignee'], 'Unassigned')
                location = self._safe_get(task, ['recommended_location', 'location'], 'Unknown Location')
                priority = self._safe_get(task, ['priority', 'recommended_priority'], 'Medium')
                confidence = self._safe_get(task, ['confidence_score', 'confidence'], 0)
                source = self._safe_get(task, ['source'], 'pattern_based')
                business_impact = self._safe_get(task, ['business_impact'], '')

                sections.append(f"  - **{task_name}** ({source})")
                sections.append(f"    Priority: {priority} | Confidence: {confidence:.0%}")
                sections.append(f"    👤 {assignee} | 📍 {location}")

                if business_impact:
                    sections.append(f"    📊 Business Impact: {business_impact}")

                roi_analysis = self._safe_get(task, ['roi_analysis'], {})
                if roi_analysis:
                    roi_ratio = self._safe_get(roi_analysis, ['roi_ratio'], 0)
                    sections.append(f"    💹 ROI: {roi_ratio:.1f}x return")
                sections.append("")

        # Strategic insights
        strategic_insights = self._safe_get(recommendations, ['strategic_insights'], [])
        if strategic_insights:
            sections.append("**Strategic Insights:**")
            for insight in strategic_insights:
                category = self._safe_get(insight, ['category'], 'general').replace('_', ' ').title()
                insight_text = self._safe_get(insight, ['insight', 'description'], 'No insight available')
                recommendation = self._safe_get(insight, ['recommendation'], 'No recommendation')
                business_impact = self._safe_get(insight, ['business_impact'], '')
                investment = self._safe_get(insight, ['investment_required'], 0)

                sections.append(f"  - **{category}**: {insight_text}")
                sections.append(f"    🎯 {recommendation}")
                sections.append(f"    📈 {business_impact}")
                if investment > 0:
                    sections.append(f"    💰 Investment: ${investment:,}")
                sections.append("")

        # Business metrics
        business_metrics = self._safe_get(recommendations, ['business_metrics'], {})
        if business_metrics:
            sections.append("**Business Intelligence:**")

            financial = self._safe_get(business_metrics, ['financial_impact'], {})
            if financial:
                total_cost = self._safe_get(financial, ['total_estimated_cost'], 0)
                potential_savings = self._safe_get(financial, ['potential_savings'], 0)
                sections.append(f"  💰 **Financial**: ${total_cost:.2f} cost, ${potential_savings:.2f} savings")

            ops = self._safe_get(business_metrics, ['operational_excellence'], {})
            if ops:
                uptime = self._safe_get(ops, ['uptime_improvement'], 'N/A')
                sla = self._safe_get(ops, ['service_level_achievement'], 'N/A')
                sections.append(f"  ⚡ **Operations**: {uptime} uptime, {sla} SLA achievement")

        return "\n".join(sections)

    def _format_tier_aware_detailed(self, results: Dict[str, Any], customer_tier: str) -> str:
        """Format detailed results with tier-appropriate restrictions"""

        if customer_tier == "basic":
            return self._format_basic_tier_detailed(results)
        elif customer_tier == "professional":
            return self._format_professional_tier_detailed(results)
        else:  # enterprise
            return self._format_enterprise_tier_detailed(results)

    def _format_basic_tier_detailed(self, results: Dict[str, Any]) -> str:
        """Basic tier detailed view with upgrade prompts"""

        sections = []
        sections.append("⚠️ **Basic Tier - Limited Detailed View**")
        sections.append("Upgrade to Professional tier for comprehensive detailed analysis.\n")

        # Show basic summary instead
        basic_summary = self._format_basic_tier_summary(results)
        sections.append(basic_summary)

        sections.append("\n🔄 **Professional Tier Benefits:**")
        sections.append("  • Detailed performance analytics with confidence scoring")
        sections.append("  • Multi-source recommendation engine (patterns, alerts, metrics)")
        sections.append("  • Advanced employee skill matching and availability analysis")
        sections.append("  • Cost optimization with efficiency considerations")
        sections.append("  • Performance insights and trend analysis")

        return "\n".join(sections)

    def _format_professional_tier_detailed(self, results: Dict[str, Any]) -> str:
        """Professional tier detailed view"""

        recommendations = self._get_recommendations_data(results)

        sections = []
        sections.append("=" * 80)
        sections.append("PROFESSIONAL RECOMMENDATION ANALYSIS")
        sections.append("=" * 80)
        sections.append("")

        # Detailed recommendations
        tasks = self._extract_tasks(recommendations)

        if tasks:
            sections.append("## RECOMMENDED TASKS")
            sections.append("-" * 40)

            for i, task in enumerate(tasks, 1):
                task_name = self._safe_get(task, ['task_name', 'recommended_name', 'name'], 'Unnamed Task')
                assignee = self._safe_get(task, ['recommended_assignee', 'assignee'], 'Unassigned')
                location = self._safe_get(task, ['recommended_location', 'location'], 'Unknown Location')
                start_time = self._safe_get(task, ['recommended_start_time', 'start_time'], 'TBD')
                duration = self._safe_get(task, ['recommended_duration_minutes', 'duration_minutes', 'duration'], 60)
                priority = self._safe_get(task, ['priority', 'recommended_priority'], 'Medium')
                confidence = self._safe_get(task, ['confidence_score', 'confidence'], 0)
                source = self._safe_get(task, ['source'], 'pattern_based')
                cost = self._safe_get(task, ['estimated_cost', 'cost'], 0)
                reasoning = self._safe_get(task, ['reasoning', 'reason'], 'No reasoning provided')
                business_impact = self._safe_get(task, ['business_impact'], '')

                sections.append(f"{i}. **{task_name}**")
                sections.append(f"   Assignee: {assignee}")
                sections.append(f"   Location: {location}")
                sections.append(f"   Start Time: {start_time}")
                sections.append(f"   Duration: {duration} minutes")
                sections.append(f"   Priority: {priority}")
                sections.append(f"   Confidence: {confidence:.1%}")
                sections.append(f"   Source: {source}")
                sections.append(f"   Cost: ${cost:.2f}")
                sections.append(f"   Reasoning: {reasoning}")

                if business_impact:
                    sections.append(f"   Business Impact: {business_impact}")

                sections.append("")

        # Performance insights
        insights = self._safe_get(recommendations, ['performance_insights'], [])
        if insights:
            sections.append("## PERFORMANCE INSIGHTS")
            sections.append("-" * 40)

            for i, insight in enumerate(insights, 1):
                insight_text = self._safe_get(insight, ['insight', 'description'], 'No insight available')
                recommendation = self._safe_get(insight, ['recommendation'], 'No recommendation')
                impact = self._safe_get(insight, ['impact'], '')

                sections.append(f"{i}. **{insight_text}**")
                sections.append(f"   Recommendation: {recommendation}")
                if impact:
                    sections.append(f"   Expected Impact: {impact}")
                sections.append("")

        return "\n".join(sections)

    def _format_enterprise_tier_detailed(self, results: Dict[str, Any]) -> str:
        """Enterprise tier detailed view with strategic intelligence"""

        recommendations = self._get_recommendations_data(results)

        sections = []
        sections.append("=" * 80)
        sections.append("ENTERPRISE STRATEGIC RECOMMENDATION ANALYSIS")
        sections.append("=" * 80)
        sections.append("")

        # Strategic recommendations with full context
        tasks = self._extract_tasks(recommendations)

        if tasks:
            sections.append("## STRATEGIC TASK RECOMMENDATIONS")
            sections.append("-" * 40)

            for i, task in enumerate(tasks, 1):
                task_name = self._safe_get(task, ['task_name', 'recommended_name', 'name'], 'Unnamed Task')
                source = self._safe_get(task, ['source'], 'pattern_based')
                priority = self._safe_get(task, ['priority', 'recommended_priority'], 'Medium')
                confidence = self._safe_get(task, ['confidence_score', 'confidence'], 0)
                assignee = self._safe_get(task, ['recommended_assignee', 'assignee'], 'Unassigned')
                location = self._safe_get(task, ['recommended_location', 'location'], 'Unknown Location')
                start_time = self._safe_get(task, ['recommended_start_time', 'start_time'], 'TBD')
                duration = self._safe_get(task, ['recommended_duration_minutes', 'duration_minutes', 'duration'], 60)
                cost = self._safe_get(task, ['estimated_cost', 'cost'], 0)
                reasoning = self._safe_get(task, ['reasoning', 'reason'], 'No reasoning provided')
                business_impact = self._safe_get(task, ['business_impact'], '')

                sections.append(f"{i}. **{task_name}** ({source})")
                sections.append(f"   Strategic Priority: {priority}")
                sections.append(f"   Confidence Level: {confidence:.1%}")
                sections.append(f"   Recommended Assignee: {assignee}")
                sections.append(f"   Target Location: {location}")
                sections.append(f"   Optimal Start Time: {start_time}")
                sections.append(f"   Estimated Duration: {duration} minutes")
                sections.append(f"   Investment Required: ${cost:.2f}")
                sections.append(f"   Strategic Reasoning: {reasoning}")

                if business_impact:
                    sections.append(f"   Business Impact: {business_impact}")

                roi_analysis = self._safe_get(task, ['roi_analysis'], {})
                if roi_analysis:
                    sections.append(f"   ROI Analysis:")
                    sections.append(f"     - Investment: ${roi_analysis.get('prevention_cost', 0):.2f}")
                    sections.append(f"     - Potential Savings: ${roi_analysis.get('failure_cost', 0):.2f}")
                    sections.append(f"     - ROI Ratio: {roi_analysis.get('roi_ratio', 0):.1f}x")
                    sections.append(f"     - Payback Period: {roi_analysis.get('payback_period', 'N/A')}")

                risk_assessment = self._safe_get(task, ['risk_assessment'], '')
                if risk_assessment:
                    sections.append(f"   Risk Assessment: {risk_assessment}")

                sections.append("")

        return "\n".join(sections)

    def _format_tier_enhanced_json(self, results: Dict[str, Any], customer_tier: str) -> str:
        """Format JSON with tier-specific metadata"""

        enhanced_results = results.copy()

        # Add tier metadata
        enhanced_results['_tier_metadata'] = {
            'customer_tier': customer_tier,
            'tier_restrictions_applied': customer_tier != 'enterprise',
            'formatted_at': datetime.now().isoformat(),
            'formatter_version': f'1.0_recommendation_{customer_tier}'
        }

        # Apply tier restrictions to JSON output
        if customer_tier == "basic":
            # Limit recommendations and remove advanced features
            recommendations = enhanced_results.get("recommendations", {})
            if "recommended_tasks" in recommendations:
                recommendations["recommended_tasks"] = recommendations["recommended_tasks"][:5]

            # Remove advanced features
            advanced_features = ["strategic_insights", "business_metrics", "investment_opportunities"]
            for feature in advanced_features:
                recommendations.pop(feature, None)

        elif customer_tier == "professional":
            # Remove enterprise-only features
            recommendations = enhanced_results.get("recommendations", {})
            enterprise_features = ["strategic_insights", "investment_opportunities"]
            for feature in enterprise_features:
                recommendations.pop(feature, None)

        return json.dumps(enhanced_results, indent=2, default=str)

    def _format_tier_aware_error(self, results: Dict[str, Any], customer_tier: str) -> str:
        """Format error with tier-specific guidance"""

        error_msg = results.get('error', 'Unknown error')

        error_response = f"❌ **Recommendation Generation Failed**\n"
        error_response += f"Error: {error_msg}\n"

        # Add context if validation error
        if 'validation_error' in results:
            validation = results['validation_error']
            error_response += f"\n💡 **Issue Details:**\n"
            error_response += f"  - Customer Tier: {validation.get('tier_info', {}).get('customer_tier', 'unknown')}\n"
            error_response += f"  - Requested Features: {validation.get('tier_info', {}).get('requested_level', 'unknown')}\n"

            if validation.get('upgrade_required'):
                error_response += f"\n🔄 **Resolution:**\n"
                error_response += f"  - Upgrade your subscription tier for advanced features\n"
                error_response += f"  - Visit: {validation.get('upgrade_url', '/upgrade')}\n"

        return error_response

    # Helper methods for robust data extraction
    def _get_recommendations_data(self, results: Dict[str, Any]) -> Any:
        """Extract recommendations data from various possible locations"""
        # Try different possible locations for recommendations data
        if "recommendations" in results:
            return results["recommendations"]
        elif "optimizations" in results:
            return results["optimizations"]
        elif "tasks" in results:
            return results["tasks"]
        else:
            return {}

    def _extract_tasks(self, recommendations: Any) -> List[Dict]:
        """Extract task list from recommendations data"""
        if isinstance(recommendations, list):
            return recommendations
        elif isinstance(recommendations, dict):
            # Try different possible keys
            for key in ['recommended_tasks', 'tasks', 'recommendations']:
                if key in recommendations:
                    tasks = recommendations[key]
                    if isinstance(tasks, list):
                        return tasks
        return []

    def _safe_get(self, data: Any, keys: List[str], default: Any = None) -> Any:
        """Safely get value from dict using multiple possible keys"""
        if not isinstance(data, dict):
            return default

        for key in keys:
            if key in data:
                value = data[key]
                # Handle datetime objects
                if hasattr(value, 'strftime'):
                    return value.strftime('%Y-%m-%d %H:%M')
                return value
        return default