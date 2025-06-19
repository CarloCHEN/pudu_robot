import anthropic
import json
import os
from typing import Dict, List, Any
from dotenv import load_dotenv
from models.recommendation import TaskRecommendation

class RecommendationOptimizer:
    """Handles Claude API interactions for work order recommendations"""

    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

        self.client = anthropic.Anthropic(api_key=self.api_key)

    def generate_recommendations(self, context: Dict[str, Any],
                               customer_tier: str = "basic") -> Dict[str, Any]:
        """Generate AI-powered work order recommendations"""

        prompt = self._build_recommendation_prompt(context, customer_tier)

        # Adjust parameters based on tier
        max_tokens = self._get_max_tokens(customer_tier)
        temperature = 0.2  # Slightly higher than optimization for creativity

        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            response_text = message.content[0].text

            # Parse JSON response
            try:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1

                if json_start != -1 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    recommendation_result = json.loads(json_str)

                    return {
                        "success": True,
                        "recommendations": recommendation_result,
                        "raw_response": response_text,
                        "usage": {
                            "input_tokens": message.usage.input_tokens,
                            "output_tokens": message.usage.output_tokens,
                            "total_tokens": message.usage.input_tokens + message.usage.output_tokens
                        },
                        "customer_tier": customer_tier
                    }
                else:
                    return {
                        "success": False,
                        "error": "No valid JSON found in response",
                        "raw_response": response_text
                    }

            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": f"Failed to parse JSON: {e}",
                    "raw_response": response_text
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"API call failed: {e}"
            }

    def _build_recommendation_prompt(self, context: Dict[str, Any], customer_tier: str) -> str:
        """Build tier-specific recommendation prompt"""

        if customer_tier == "basic":
            return self._build_basic_recommendation_prompt(context)
        elif customer_tier == "professional":
            return self._build_professional_recommendation_prompt(context)
        elif customer_tier == "enterprise":
            return self._build_enterprise_recommendation_prompt(context)
        else:
            return self._build_basic_recommendation_prompt(context)

    def _build_basic_recommendation_prompt(self, context: Dict[str, Any]) -> str:
        """Basic tier recommendation prompt"""

        recommendations_summary = self._format_basic_recommendations(context.get('recommendations', []))

        return f"""
**BASIC WORK ORDER RECOMMENDATION SYSTEM**

Analyze the following data to provide simple, high-confidence work order recommendations:

## Current Recommendations:
{recommendations_summary}

## Analysis Context:
- Historical patterns from completed work orders
- Current employee availability and skills
- Basic location priorities
- Simple cost considerations

**Objectives:**
1. Recommend work orders based on clear historical patterns
2. Ensure recommended assignees are available and qualified
3. Balance workload across available employees
4. Prioritize high-confidence recommendations only

**Output Format:**
Provide recommendations in JSON format:
{{
  "recommended_tasks": [
    {{
      "task_id": "REC_001",
      "task_name": "Weekly Restroom Deep Clean",
      "recommended_assignee": "John Doe",
      "recommended_location": "HQ Building - Floor 1 Restrooms",
      "recommended_start_time": "2025-05-12 09:00 AM",
      "recommended_duration_minutes": 90,
      "priority": "Medium",
      "confidence_score": 0.85,
      "reasoning": "Historical pattern shows restroom cleaning needed every 7 days",
      "estimated_cost": 37.50
    }}
  ],
  "summary": {{
    "total_recommendations": 3,
    "high_confidence_count": 2,
    "total_estimated_cost": 125.50
  }}
}}
"""

    def _build_professional_recommendation_prompt(self, context: Dict[str, Any]) -> str:
        """Professional tier recommendation prompt with enhanced analytics"""

        recommendations_summary = self._format_detailed_recommendations(context.get('recommendations', []))
        insights_summary = self._format_insights(context.get('insights', []))

        return f"""
**PROFESSIONAL WORK ORDER RECOMMENDATION SYSTEM WITH ANALYTICS**

Comprehensive analysis for intelligent work order recommendations:

## Current Recommendation Analysis:
{recommendations_summary}

## Performance Insights:
{insights_summary}

## Enhanced Context:
- Historical completion patterns with quality/efficiency scores
- Alert correlation analysis and escalation predictions
- Employee skill matching and performance ratings
- Location-specific metrics and degradation patterns
- Cost optimization with efficiency considerations

**Professional Objectives:**
1. Generate recommendations based on multiple data sources (patterns, alerts, metrics)
2. Optimize assignee selection using skill matching and performance data
3. Predict optimal timing based on historical patterns and current conditions
4. Balance cost efficiency with quality requirements
5. Provide actionable insights for process improvement

**Advanced Considerations:**
- Employee efficiency ratings (6.0-9.5 scale)
- Location cleaning priority scores (1-10 scale)
- Alert severity levels and escalation patterns
- Metric variance thresholds and performance trends
- Workload balancing and capacity optimization

**Output Format:**
Provide comprehensive recommendations in JSON format:
{{
  "recommended_tasks": [
    {{
      "task_id": "REC_001",
      "task_name": "Preventive Laboratory Maintenance",
      "recommended_assignee": "Jane Smith",
      "recommended_location": "Research Center - Lab A",
      "recommended_start_time": "2025-05-12 14:00 PM",
      "recommended_duration_minutes": 120,
      "priority": "High",
      "confidence_score": 0.92,
      "reasoning": "Lab A showing 25% degradation in air quality metrics, due for maintenance based on 14-day pattern",
      "estimated_cost": 60.00,
      "source": "metric_driven",
      "business_impact": "Prevent equipment damage and maintain compliance",
      "alternative_assignees": ["Mike Johnson"],
      "skill_requirements": ["laboratory_cleaning", "chemical_handling"]
    }}
  ],
  "performance_insights": [
    {{
      "insight": "60% of recommendations are reactive (alert-driven)",
      "recommendation": "Increase preventive maintenance frequency",
      "impact": "Reduce emergency responses by 30%"
    }}
  ],
  "optimization_opportunities": [
    {{
      "opportunity": "Skill gap in laboratory certification",
      "recommendation": "Train 2 additional employees in lab procedures",
      "roi_estimate": "200% ROI within 4 months"
    }}
  ],
  "summary": {{
    "total_recommendations": 8,
    "confidence_distribution": {{"high": 5, "medium": 3, "low": 0}},
    "source_breakdown": {{"pattern_based": 4, "alert_triggered": 2, "metric_driven": 2}},
    "total_estimated_cost": 485.50,
    "estimated_time_savings": "3.5 hours per week"
  }}
}}
"""

    def _build_enterprise_recommendation_prompt(self, context: Dict[str, Any]) -> str:
        """Enterprise tier recommendation prompt with strategic intelligence"""

        recommendations_summary = self._format_detailed_recommendations(context.get('recommendations', []))
        insights_summary = self._format_insights(context.get('insights', []))
        business_impact_summary = self._format_business_impact(context.get('business_impact', {}))

        return f"""
**ENTERPRISE WORK ORDER RECOMMENDATION SYSTEM WITH STRATEGIC INTELLIGENCE**

Executive-level work order recommendations with comprehensive business analytics:

## Strategic Recommendation Analysis:
{recommendations_summary}

## Performance Intelligence:
{insights_summary}

## Business Impact Analysis:
{business_impact_summary}

## Strategic Context:
- Predictive analytics for maintenance scheduling and resource planning
- ROI analysis for preventive vs reactive maintenance strategies
- Risk assessment for critical facility areas and compliance requirements
- Workforce development planning and skill gap analysis
- Strategic KPIs and performance benchmarking
- Cost optimization with budget planning and variance analysis

**Enterprise Objectives:**
1. Strategic workforce planning with predictive capacity modeling
2. Risk-based priority assignment for business continuity
3. Financial optimization with ROI tracking and budget impact
4. Compliance management and regulatory requirement alignment
5. Performance benchmarking and competitive analysis
6. Long-term strategic planning and investment recommendations

**Strategic Considerations:**
- **Business Continuity**: Critical facility protection and service level maintenance
- **Financial Impact**: Cost optimization, budget variance, and ROI maximization
- **Risk Management**: Predictive failure analysis and preventive intervention
- **Compliance**: Regulatory requirements and audit readiness
- **Strategic Planning**: Long-term resource needs and investment planning
- **Performance Excellence**: Continuous improvement and best practice implementation

**Output Format:**
Provide strategic recommendations with comprehensive business intelligence:
{{
  "recommended_tasks": [
    {{
      "task_id": "REC_001",
      "task_name": "Critical Infrastructure Preventive Maintenance",
      "recommended_assignee": "Jane Smith",
      "recommended_location": "Data Center - Cooling System",
      "recommended_start_time": "2025-05-12 06:00 AM",
      "recommended_duration_minutes": 180,
      "priority": "Critical",
      "confidence_score": 0.94,
      "reasoning": "Predictive model indicates 89% probability of cooling failure within 72 hours based on temperature variance patterns",
      "estimated_cost": 135.00,
      "source": "predictive_analytics",
      "business_impact": "Prevent $50,000 equipment damage and 8-hour service disruption",
      "risk_assessment": "High business impact, critical system failure prevention",
      "compliance_impact": "Maintains SLA requirements and regulatory compliance",
      "roi_analysis": {{
        "prevention_cost": 135.00,
        "failure_cost": 50000.00,
        "roi_ratio": 370.37,
        "payback_period": "immediate"
      }},
      "strategic_value": "Mission-critical system protection and business continuity"
    }}
  ],
  "strategic_insights": [
    {{
      "category": "risk_management",
      "insight": "3 critical systems showing early warning indicators",
      "recommendation": "Implement advanced monitoring and predictive maintenance",
      "business_impact": "Reduce unplanned downtime by 85%",
      "investment_required": 25000,
      "annual_savings": 150000
    }}
  ],
  "workforce_intelligence": {{
    "capacity_utilization": 78.5,
    "skill_gap_analysis": {{
      "critical_gaps": ["advanced_hvac", "industrial_automation"],
      "training_recommendations": "Certify 3 employees in industrial systems",
      "investment_roi": "300% within 6 months"
    }},
    "performance_trends": {{
      "efficiency_improvement": "+12% over 6 months",
      "quality_scores": "Average 9.2/10",
      "cost_optimization": "15% reduction in reactive maintenance"
    }}
  }},
  "business_metrics": {{
    "financial_impact": {{
      "total_estimated_cost": 1250.00,
      "potential_savings": 45000.00,
      "roi_percentage": 3600,
      "budget_variance": "+2.3% (under budget)"
    }},
    "operational_excellence": {{
      "uptime_improvement": "99.7% vs 97.2% baseline",
      "service_level_achievement": "98.5%",
      "customer_satisfaction_impact": "+18%"
    }},
    "strategic_kpis": {{
      "preventive_vs_reactive": "75% preventive",
      "mean_time_to_resolution": "2.3 hours",
      "cost_per_incident": "$125 vs $450 industry average"
    }}
  }},
  "investment_opportunities": [
    {{
      "opportunity": "Automated monitoring system implementation",
      "investment_required": 75000,
      "annual_savings": 180000,
      "payback_period_months": 5,
      "strategic_benefit": "Predictive maintenance capability and reduced manual monitoring"
    }}
  ],
  "summary": {{
    "total_recommendations": 12,
    "critical_priority": 3,
    "high_priority": 5,
    "confidence_distribution": {{"high": 8, "medium": 4, "low": 0}},
    "source_breakdown": {{"predictive_analytics": 4, "pattern_based": 4, "alert_triggered": 2, "metric_driven": 2}},
    "total_estimated_cost": 1250.00,
    "total_potential_savings": 45000.00,
    "net_roi": 3500.00,
    "business_impact_score": 9.2
  }}
}}
"""

    def _get_max_tokens(self, customer_tier: str) -> int:
        """Get appropriate max tokens based on customer tier"""
        token_limits = {
            "basic": 2000,
            "professional": 4000,
            "enterprise": 8000
        }
        return token_limits.get(customer_tier, 2000)

    def _format_basic_recommendations(self, recommendations: List) -> str:
        """Format recommendations for basic tier prompt"""
        if not recommendations:
            return "No current recommendations available."

        formatted = []
        for rec in recommendations[:5]:  # Limit for basic tier
            formatted.append(
                f"- {rec.recommended_name}: {rec.recommended_assignee} at {rec.recommended_location}, "
                f"confidence {rec.confidence_score:.2f}, cost ${rec.estimated_cost:.2f}"
            )

        return "\n".join(formatted)

    def _format_detailed_recommendations(self, recommendations: List) -> str:
        """Format recommendations for professional/enterprise tiers"""
        if not recommendations:
            return "No current recommendations available."

        formatted = []
        for rec in recommendations:
            formatted.append(
                f"- **{rec.recommended_name}** ({rec.source.value})\n"
                f"  Assignee: {rec.recommended_assignee} | Location: {rec.recommended_location}\n"
                f"  Priority: {rec.recommended_priority.value} | Confidence: {rec.confidence_score:.2f}\n"
                f"  Reasoning: {rec.reasoning}\n"
                f"  Cost: ${rec.estimated_cost:.2f} | Duration: {rec.estimated_duration_minutes}min\n"
            )

        return "\n".join(formatted)

    def _format_insights(self, insights: List) -> str:
        """Format performance insights"""
        if not insights:
            return "No insights available."

        formatted = []
        for insight in insights:
            formatted.append(
                f"- **{insight['type'].replace('_', ' ').title()}**: {insight['insight']}\n"
                f"  Recommendation: {insight['recommendation']}"
            )

        return "\n".join(formatted)

    def _format_business_impact(self, business_impact: Dict) -> str:
        """Format business impact analysis"""
        if not business_impact:
            return "No business impact analysis available."

        sections = []

        if 'financial_metrics' in business_impact:
            financial = business_impact['financial_metrics']
            sections.append(
                f"**Financial Impact**: Total cost ${financial.get('total_cost', 0):.2f}, "
                f"potential savings ${financial.get('potential_savings', 0):.2f}"
            )

        if 'risk_metrics' in business_impact:
            risk = business_impact['risk_metrics']
            sections.append(
                f"**Risk Analysis**: {risk.get('high_risk_items', 0)} high-risk items, "
                f"{risk.get('compliance_items', 0)} compliance-related"
            )

        return "\n".join(sections)