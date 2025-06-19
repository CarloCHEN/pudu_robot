from typing import Dict, Any, List

class PromptBuilder:
    """Prompt builder leveraging rich model data with strategic and performance metrics"""

    def build_optimization_prompt(self, context: Dict[str, Any]) -> str:
        """Build enhanced prompts with real model data"""

        level = context.get('level', 'basic')
        focus = context.get('focus', 'all')

        if level == "basic":
            return self._build_enhanced_basic_prompt(context, focus)
        elif level == "professional":
            return self._build_enhanced_professional_prompt(context, focus)
        elif level == "enterprise":
            return self._build_enhanced_enterprise_prompt(context, focus)
        else:
            raise ValueError(f"Unknown optimization level: {level}")

    def _build_enhanced_basic_prompt(self, context: Dict[str, Any], focus: str) -> str:
        """Enhanced basic prompt with real model data"""
        work_orders_summary = self._format_enhanced_work_orders_basic(context['basic_info'])
        cost_summary = self._format_cost_summary(context.get('cost_info', {}))
        focus_instruction = self._get_enhanced_focus_instruction(focus)

        return f"""
**BASIC WORK ORDER OPTIMIZATION WITH REAL-TIME DATA**

{cost_summary}

Analyze these {context['work_order_count']} work orders with enhanced employee and location data:

{work_orders_summary}

**Enhanced Data Available:**
- Employee hourly rates and efficiency ratings
- Location cleaning priority scores (1-10 scale)
- Active alert counts and severity levels
- Estimated labor costs per task

**Primary Objectives:**
1. Eliminate time conflicts (same assignee, overlapping times)
2. Resolve location conflicts (multiple people, same location/time)
3. Basic workload balancing considering hourly rates
4. Priority alignment with location cleaning scores

{focus_instruction}

**Consider:**
- High-priority locations (score 8.0+) should get immediate attention
- Employee efficiency ratings affect actual task duration
- Active alerts indicate urgent cleaning needs
- Cost-effective task assignment

**Output Format:**
Provide optimization recommendations in JSON format with these EXACT field names:
{{
  "time": [
    {{
      "id": 1001,
      "original_time": "2025-05-06 10:00 AM",
      "recommended_time": "2025-05-06 11:30 AM",
      "reason": "Conflicts with task 1002 for same assignee"
    }}
  ],
  "assignee": [
    {{
      "id": 1003,
      "original_assignee": "John Doe",
      "recommended_assignee": "Jane Smith",
      "reason": "Workload balancing - John overloaded, Jane available"
    }}
  ],
  "location": [
    {{
      "id": 1004,
      "original_location": "Building A - Floor 1",
      "recommended_location": "Building A - Floor 2",
      "reason": "Group tasks by floor to reduce travel time"
    }}
  ],
  "priority": [
    {{
      "id": 1005,
      "original_priority": "Low",
      "recommended_priority": "High",
      "reason": "Location has cleaning priority score 9.2 and 3 active alerts"
    }}
  ]
}}
"""

    def _build_enhanced_professional_prompt(self, context: Dict[str, Any], focus: str) -> str:
        """Enhanced professional prompt with comprehensive model data"""

        work_orders_summary = self._format_enhanced_work_orders_detailed(context['basic_info'])
        employee_insights = self._format_employee_insights(context.get('employee_data', {}))
        location_insights = self._format_location_insights(context.get('location_data', {}))
        alert_insights = self._format_alert_insights(context.get('alert_data', {}))
        conflicts_summary = self._format_enhanced_conflicts(context.get('enhanced_conflicts', {}))
        skill_analysis = self._format_skill_analysis(context.get('skill_analysis', {}))
        cost_analysis = self._format_cost_analysis(context.get('cost_analysis', {}))
        performance_metrics = self._format_performance_metrics(context.get('performance_metrics', {}))
        cost_summary = self._format_cost_summary(context.get('cost_info', {}))
        focus_instruction = self._get_enhanced_focus_instruction(focus)

        return f"""
**PROFESSIONAL WORK ORDER OPTIMIZATION WITH ADVANCED ANALYTICS**

{cost_summary}

Comprehensive analysis of {context['work_order_count']} work orders using real employee skills, location priorities, and alert data:

## Enhanced Work Orders Overview:
{work_orders_summary}

## Employee Performance & Skills Analysis:
{employee_insights}

## Location Intelligence & Priority Analysis:
{location_insights}

## Alert Impact & Severity Analysis:
{alert_insights}

## Advanced Conflict Detection:
{conflicts_summary}

## Skill Matching Analysis:
{skill_analysis}

## Cost Efficiency Analysis:
{cost_analysis}

## Performance Optimization Metrics:
{performance_metrics}

**Professional Objectives:**
1. Resolve all conflicts with cost impact consideration
2. Optimize skill-to-task matching for quality assurance
3. Balance workload using efficiency ratings and hourly rates
4. Prioritize based on location cleaning scores and alert severity
5. Minimize travel time and maximize location clustering
6. Ensure cost-effective resource allocation

{focus_instruction}

**Advanced Considerations:**
- Employee skill levels and certifications for task suitability
- Location cleaning priority scores (9.0+ = critical facilities)
- Alert severity levels (critical/very_severe require immediate response)
- Cost per hour variations ($18-$35/hour range)
- Efficiency ratings (6.0-9.5 scale) affecting actual completion times
- Building and floor layouts for travel optimization

**Output Format:**
Provide detailed optimization recommendations in JSON format with performance reasoning using these EXACT field names:
{{
  "time": [
    {{
      "id": 1001,
      "original_time": "2025-05-06 10:00 AM",
      "recommended_time": "2025-05-06 11:30 AM",
      "reason": "Conflicts with task 1002 for same assignee (cost impact: $45.50)"
    }}
  ],
  "assignee": [
    {{
      "id": 1003,
      "original_assignee": "John Doe ($25/hr)",
      "recommended_assignee": "Jane Smith ($30/hr)",
      "reason": "Jane has laboratory certification required for this location (priority 9.2)"
    }}
  ],
  "location": [
    {{
      "id": 1004,
      "original_location": "Headquarters - Floor 1 - Lobby",
      "recommended_location": "Headquarters - Floor 1 - Restroom A",
      "reason": "Group Floor 1 tasks for John Doe - saves 20min travel time"
    }}
  ],
  "priority": [
    {{
      "id": 1005,
      "original_priority": "Low",
      "recommended_priority": "High",
      "reason": "Location priority score 9.2 + 2 SEVERE alerts require immediate attention"
    }}
  ],
  "performance_insights": [
    {{
      "insight": "Jane Smith (efficiency 9.0) completes lab tasks 25% faster than average",
      "recommendation": "Assign all laboratory cleaning to Jane Smith",
      "impact": "Save 40min daily + ensure chemical safety compliance"
    }}
  ]
}}
"""

    def _build_enhanced_enterprise_prompt(self, context: Dict[str, Any], focus: str) -> str:
        """Enhanced enterprise prompt with strategic business intelligence"""

        work_orders_summary = self._format_enhanced_work_orders_detailed(context['basic_info'])
        employee_insights = self._format_employee_insights(context.get('employee_data', {}))
        location_insights = self._format_location_insights(context.get('location_data', {}))
        alert_insights = self._format_alert_insights(context.get('alert_data', {}))
        conflicts_summary = self._format_enhanced_conflicts(context.get('enhanced_conflicts', {}))
        skill_analysis = self._format_skill_analysis(context.get('skill_analysis', {}))
        cost_analysis = self._format_cost_analysis(context.get('cost_analysis', {}))

        # Enterprise-specific sections
        performance_metrics = self._format_performance_metrics(context.get('performance_metrics', {}))
        strategic_metrics = self._format_strategic_metrics(context.get('strategic_metrics', {}))
        predictive_insights = self._format_predictive_insights(context.get('predictive_insights', []))
        strategic_recommendations = self._format_strategic_recommendations(context.get('strategic_recommendations', []))
        performance_benchmarks = self._format_performance_benchmarks(context.get('performance_benchmarks', {}))
        roi_analysis = self._format_roi_analysis(context.get('roi_analysis', {}))
        cost_summary = self._format_cost_summary(context.get('cost_info', {}))
        focus_instruction = self._get_enhanced_focus_instruction(focus)

        return f"""
**ENTERPRISE WORK ORDER OPTIMIZATION WITH STRATEGIC BUSINESS INTELLIGENCE**

{cost_summary}

Executive-level analysis of {context['work_order_count']} work orders with comprehensive data analytics, predictive insights, and strategic recommendations:

## Enhanced Work Orders with Full Context:
{work_orders_summary}

## Workforce Intelligence & Performance Analytics:
{employee_insights}

## Facility Intelligence & Risk Assessment:
{location_insights}

## Alert Intelligence & Impact Analysis:
{alert_insights}

## Advanced Conflict & Risk Analysis:
{conflicts_summary}

## Skills Gap & Training Analysis:
{skill_analysis}

## Financial Optimization & Cost Analysis:
{cost_analysis}

## Performance Optimization Metrics:
{performance_metrics}

## Strategic Risk & Capacity Analysis:
{strategic_metrics}

## Predictive Analytics & Future Planning:
{predictive_insights}

## Strategic Business Recommendations:
{strategic_recommendations}

## Performance Benchmarks & KPIs:
{performance_benchmarks}

## ROI Analysis & Investment Planning:
{roi_analysis}

**Enterprise Objectives:**
1. Strategic workforce optimization with full cost-benefit analysis
2. Predictive maintenance scheduling based on alert patterns
3. Skills development planning and certification management
4. Facility risk assessment and priority-based resource allocation
5. Cost optimization with ROI tracking and budget planning
6. Quality assurance through skill-task matching and performance monitoring
7. Business continuity planning for critical facility areas

{focus_instruction}

**Strategic Considerations:**
- **Workforce Development**: Skill gaps, training ROI, certification requirements
- **Financial Optimization**: Cost per task, overtime prediction, budget allocation
- **Risk Management**: Critical facility areas, alert escalation, service disruption prevention
- **Performance Management**: Efficiency benchmarks, quality metrics, productivity tracking
- **Predictive Analytics**: Alert patterns, maintenance scheduling, resource planning
- **Compliance**: Safety certifications, regulatory requirements, audit readiness

**Output Format:**
Provide comprehensive optimization with strategic insights using these EXACT field names:
{{
  "time": [
    {{
      "id": 1001,
      "original_time": "2025-05-06 10:00 AM",
      "recommended_time": "2025-05-06 11:30 AM",
      "reason": "Conflicts resolved with $67.50 cost savings and 15% efficiency gain"
    }}
  ],
  "assignee": [
    {{
      "id": 1003,
      "original_assignee": "John Doe ($25/hr, efficiency 7.8)",
      "recommended_assignee": "Jane Smith ($30/hr, efficiency 9.0, lab certified)",
      "reason": "ROI positive: +$50 quality bonus outweighs +$5/hr cost for critical lab work"
    }}
  ],
  "location": [
    {{
      "id": 1004,
      "original_location": "Research Center - Floor 1 - Lab A",
      "recommended_location": "Research Center - Floor 1 - Lab B",
      "reason": "Lab B priority 9.8 vs Lab A 8.5 + 3 CRITICAL alerts require immediate attention"
    }}
  ],
  "priority": [
    {{
      "id": 1005,
      "original_priority": "Low",
      "recommended_priority": "High",
      "reason": "Business impact: Critical facility (score 9.8) + compliance risk + $2000/day disruption cost"
    }}
  ],
  "strategic_recommendations": [
    {{
      "category": "workforce_development",
      "recommendation": "Implement laboratory certification program for 3 additional employees",
      "business_impact": "Reduce single-point-of-failure risk and increase scheduling flexibility",
      "implementation_effort": "medium",
      "roi_estimate": "ROI 300% within 6 months through improved availability and reduced overtime"
    }}
  ],
  "predictive_insights": [
    {{
      "prediction": "Research Center Lab A will require emergency maintenance within 7 days based on alert escalation pattern",
      "confidence": 0.89,
      "recommended_action": "Schedule preventive deep cleaning and equipment inspection for Lab A by May 13th",
      "business_impact": "Prevent $5000 equipment damage and 2-day facility shutdown"
    }}
  ],
  "performance_metrics": {{
    "optimization_score": 9.2,
    "conflict_resolution_rate": "98%",
    "cost_efficiency_improvement": "27%",
    "quality_risk_reduction": "45%",
    "estimated_annual_savings": "$45,600",
    "employee_satisfaction_impact": "+15%",
    "facility_uptime_improvement": "99.7%"
  }}
}}
"""

    # Formatting helper methods
    def _format_enhanced_work_orders_basic(self, work_orders: List[Dict]) -> str:
        """Format work orders with enhanced basic information"""
        formatted = []
        for wo in work_orders[:10]:  # Limit for basic tier
            cost_info = f" (${wo['estimated_labor_cost']:.2f})" if wo['estimated_labor_cost'] > 0 else ""
            alert_info = f" [{wo['active_alerts_count']} alerts]" if wo['active_alerts_count'] > 0 else ""

            formatted.append(
                f"ID:{wo['id']}, {wo['name']}, {wo['assignee']} (${wo['assignee_hourly_rate']:.0f}/hr), "
                f"{wo['start_time']}-{wo['end_time']}, {wo['location']} (priority:{wo['location_priority_score']:.1f}){alert_info}, "
                f"{wo['priority']}{cost_info}"
            )

        if len(work_orders) > 10:
            formatted.append(f"... and {len(work_orders) - 10} more work orders")

        return "\n".join(formatted)

    def _format_enhanced_work_orders_detailed(self, work_orders: List[Dict]) -> str:
        """Format work orders with comprehensive details"""
        formatted = []
        for wo in work_orders:
            skills_info = f" [Skills: {', '.join(wo['assignee_skills'][:3])}]" if wo['assignee_skills'] else ""
            alert_info = f" [Alerts: {wo['active_alerts_count']} active, max severity: {wo['max_alert_severity']}]" if wo['active_alerts_count'] > 0 else ""

            formatted.append(
                f"ID:{wo['id']} | {wo['name']} | {wo['assignee']} (${wo['assignee_hourly_rate']:.0f}/hr, "
                f"efficiency:{wo['assignee_efficiency']:.1f}, {wo['assignee_skill_level']}){skills_info} | "
                f"{wo['start_time']} to {wo['end_time']} ({wo['duration_minutes']}min) | "
                f"{wo['location']} (zone:{wo['location_zone_type']}, priority:{wo['location_priority_score']:.1f}, "
                f"{wo['location_building']} Floor {wo['location_floor']}){alert_info} | "
                f"Priority: {wo['priority']} | Source: {wo['source']} | Cost: ${wo['estimated_labor_cost']:.2f}"
            )
        return "\n".join(formatted)

    def _format_employee_insights(self, employee_data: Dict) -> str:
        """Format employee performance and skills insights"""
        if not employee_data:
            return "No employee analysis available."

        sections = []
        sections.append("**Employee Performance & Skills Summary:**")

        for name, data in employee_data.items():
            utilization = "HIGH" if data['utilization_hours'] > 7 else "OPTIMAL" if data['utilization_hours'] > 5 else "LOW"
            overtime_risk = "⚠️ OVERTIME RISK" if data['overtime_risk'] == 'high' else ""

            sections.append(
                f"  - **{name}**: ${data['hourly_rate']:.0f}/hr, efficiency {data['efficiency_rating']:.1f}, "
                f"{data['total_work_orders']} tasks ({data['utilization_hours']:.1f}h, {utilization}) "
                f"| Skills: {', '.join(data['available_skills'][:4])} | "
                f"Skill match: {data['skill_match_rate']:.0f}% | Cost effectiveness: {data['cost_effectiveness']:.2f} "
                f"{overtime_risk}"
            )
            if data['location_spread']['travel_complexity'] == 'high':
                sections.append(f"    📍 High travel complexity: {data['location_spread']['buildings']} buildings, {data['location_spread']['floors']} floors")

        return "\n".join(sections)

    def _format_location_insights(self, location_data: Dict) -> str:
        """Format location intelligence and priority analysis"""
        if not location_data:
            return "No location analysis available."

        sections = []
        sections.append("**Location Intelligence & Priority Analysis:**")

        # Sort by priority score (highest first)
        sorted_locations = sorted(location_data.items(), key=lambda x: x[1]['cleaning_priority_score'], reverse=True)

        for location_name, data in sorted_locations[:8]:  # Show top 8 locations
            risk_indicators = []
            if data['active_alerts_count'] > 2:
                risk_indicators.append(f"{data['active_alerts_count']} alerts")
            if data['congestion_risk'] == 'high':
                risk_indicators.append("congestion risk")
            if data['max_alert_severity'] in ['critical', 'very_severe']:
                risk_indicators.append("critical alerts")

            risk_text = f" ⚠️ [{', '.join(risk_indicators)}]" if risk_indicators else ""

            sections.append(
                f"  - **{location_name}**: Priority {data['cleaning_priority_score']:.1f} "
                f"({data['zone_type']}, {data['building']} Floor {data['floor']}) | "
                f"{data['work_order_count']} tasks, {data['unique_assignees']} assignees | "
                f"Cost: ${data['total_estimated_cost']:.2f} | "
                f"Efficiency: {data['efficiency_score']:.1f}/10{risk_text}"
            )

        return "\n".join(sections)

    def _format_alert_insights(self, alert_data: Dict) -> str:
        """Format alert impact and severity analysis"""
        if not alert_data:
            return "No alert analysis available."

        sections = []
        sections.append(f"**Alert Impact Analysis: {alert_data['total_active_alerts']} active alerts**")

        # Severity distribution
        if alert_data['severity_distribution']:
            severity_text = ", ".join([f"{count} {severity}" for severity, count in alert_data['severity_distribution'].items()])
            sections.append(f"  - **Severity Distribution**: {severity_text}")

        # Alert hotspots
        if alert_data['alert_hotspots']:
            sections.append("  - **Alert Hotspots** (multiple critical alerts):")
            for hotspot in alert_data['alert_hotspots'][:5]:
                sections.append(
                    f"    🔥 {hotspot['location_name']}: {hotspot['critical_alerts']} critical alerts "
                    f"(priority {hotspot['cleaning_priority']:.1f})"
                )

        # Unaddressed critical alerts
        if alert_data['unaddressed_critical']:
            sections.append("  - **🚨 UNADDRESSED CRITICAL ALERTS**:")
            for alert in alert_data['unaddressed_critical'][:3]:
                sections.append(
                    f"    ❌ {alert['location_name']}: {alert['severity']} {alert['data_type']} alert "
                    f"({alert['duration_hours']:.1f}h duration) - NO WORK ORDER ASSIGNED"
                )

        return "\n".join(sections)

    def _format_enhanced_conflicts(self, conflicts: Dict) -> str:
        """Format enhanced conflict analysis with cost impact"""
        if not conflicts:
            return "No conflicts detected."

        sections = []

        if conflicts.get('time_assignee'):
            sections.append(f"**Time-Assignee Conflicts: {len(conflicts['time_assignee'])} detected**")
            for conflict in conflicts['time_assignee'][:3]:
                sections.append(
                    f"  - WO {conflict['work_order_1']} & {conflict['work_order_2']}: "
                    f"{conflict['assignee']} double-booked | Cost impact: ${conflict['cost_impact']:.2f}"
                )

        if conflicts.get('skill_mismatch'):
            sections.append(f"**Skill Mismatches: {len(conflicts['skill_mismatch'])} detected**")
            for mismatch in conflicts['skill_mismatch'][:3]:
                sections.append(
                    f"  - WO {mismatch['work_order_id']}: {mismatch['assignee']} lacks {', '.join(mismatch['missing_skills'])} "
                    f"for {mismatch['location_type']} (risk: {mismatch['risk_level']})"
                )

        if conflicts.get('cost_inefficiency'):
            total_potential_savings = sum(item['potential_savings'] for item in conflicts['cost_inefficiency'])
            sections.append(f"**Cost Inefficiencies: ${total_potential_savings:.2f} potential savings**")
            for inefficiency in conflicts['cost_inefficiency'][:3]:
                sections.append(
                    f"  - WO {inefficiency['work_order_id']}: ${inefficiency['hourly_rate']:.0f}/hr employee "
                    f"on priority {inefficiency['location_priority']:.1f} task | Save: ${inefficiency['potential_savings']:.2f}"
                )

        return "\n".join(sections)

    def _format_skill_analysis(self, skill_analysis: Dict) -> str:
        """Format skill matching and gap analysis"""
        if not skill_analysis:
            return "No skill analysis available."

        sections = []
        sections.append("**Skills & Training Analysis:**")

        if skill_analysis.get('mismatched_assignments'):
            sections.append(f"  - **Skill Mismatches**: {len(skill_analysis['mismatched_assignments'])} assignments need attention")
            for mismatch in skill_analysis['mismatched_assignments'][:3]:
                better_option = f" → Suggest: {mismatch['better_assignee']}" if mismatch['better_assignee'] else ""
                sections.append(
                    f"    ⚠️ WO {mismatch['work_order_id']}: {mismatch['current_assignee']} "
                    f"missing {', '.join(mismatch['missing_skills'])}{better_option}"
                )

        return "\n".join(sections)

    def _format_cost_analysis(self, cost_analysis: Dict) -> str:
        """Format cost efficiency analysis"""
        if not cost_analysis:
            return "No cost analysis available."

        sections = []
        sections.append(f"**Cost Analysis: ${cost_analysis['total_estimated_cost']:.2f} total**")

        # Cost by priority
        if cost_analysis.get('cost_by_priority'):
            priority_costs = cost_analysis['cost_by_priority']
            sections.append(
                f"  - **By Priority**: High: ${priority_costs['High']:.2f}, "
                f"Medium: ${priority_costs['Medium']:.2f}, Low: ${priority_costs['Low']:.2f}"
            )

        # Overqualified assignments
        if cost_analysis.get('overqualified_assignments'):
            total_savings = sum(item['potential_savings'] for item in cost_analysis['overqualified_assignments'])
            sections.append(f"  - **Overqualified Assignments**: ${total_savings:.2f} potential savings identified")

        return "\n".join(sections)

    def _format_performance_metrics(self, performance_metrics: Dict) -> str:
        """Format performance optimization metrics for Professional+ tiers"""
        if not performance_metrics:
            return "No performance metrics available."

        sections = []
        sections.append("**Performance Optimization Metrics:**")

        # Employee performance insights
        if performance_metrics.get('employee_performance'):
            sections.append("  - **Employee Efficiency Patterns:**")
            for emp_name, perf_data in list(performance_metrics['employee_performance'].items())[:5]:
                utilization = round((perf_data['total_duration'] / 480) * 100, 1)  # % of 8-hour day
                sections.append(
                    f"    • {emp_name}: {perf_data['task_count']} tasks, "
                    f"{perf_data['total_duration']/60:.1f}h ({utilization}% utilization), "
                    f"efficiency {perf_data['efficiency_rating']:.1f}, ${perf_data['hourly_rate']}/hr"
                )

        # Location utilization patterns
        if performance_metrics.get('location_utilization'):
            sections.append("  - **Location Type Performance:**")
            for zone_type, util_data in performance_metrics['location_utilization'].items():
                avg_duration = util_data['total_duration'] / util_data['task_count'] if util_data['task_count'] > 0 else 0
                sections.append(
                    f"    • {zone_type.title()}: {util_data['task_count']} tasks, "
                    f"avg {avg_duration:.0f}min, priority {util_data['avg_priority']:.1f}"
                )

        # Efficiency indicators
        if performance_metrics.get('efficiency_indicators'):
            eff_data = performance_metrics['efficiency_indicators']
            sections.append("  - **Travel & Time Efficiency:**")

            if eff_data.get('travel_efficiency'):
                travel_eff = eff_data['travel_efficiency']
                sections.append(
                    f"    • Travel: {travel_eff['total_location_changes']} location changes, "
                    f"avg {travel_eff['avg_changes_per_employee']:.1f} per employee"
                )

            if eff_data.get('time_efficiency'):
                time_eff = eff_data['time_efficiency']
                sections.append(
                    f"    • Time: {time_eff['total_scheduled_minutes']/60:.1f}h total, "
                    f"avg {time_eff['average_task_duration']:.0f}min per task, "
                    f"density {time_eff['scheduling_density']:.2f}"
                )

        return "\n".join(sections)

    def _format_strategic_metrics(self, strategic_metrics: Dict) -> str:
        """Format strategic risk and capacity analysis for Enterprise tier"""
        if not strategic_metrics:
            return "No strategic metrics available."

        sections = []
        sections.append("**Strategic Risk & Capacity Analysis:**")

        # Risk assessment
        if strategic_metrics.get('risk_assessment'):
            risk_data = strategic_metrics['risk_assessment']

            if risk_data.get('high_risk_locations'):
                sections.append(f"  - **🚨 High-Risk Locations ({len(risk_data['high_risk_locations'])} critical):**")
                for risk_loc in risk_data['high_risk_locations'][:3]:
                    sections.append(
                        f"    • {risk_loc['location']}: Priority {risk_loc['priority_score']:.1f}, "
                        f"{risk_loc['active_alerts']} alerts, {risk_loc['risk_level'].upper()} risk"
                    )

            if risk_data.get('skill_gap_risks'):
                sections.append(f"  - **⚠️ Skill Gap Risks ({len(risk_data['skill_gap_risks'])} assignments):**")
                for skill_risk in risk_data['skill_gap_risks'][:3]:
                    sections.append(
                        f"    • WO {skill_risk['work_order_id']}: Missing {', '.join(skill_risk['missing_skills'])}, "
                        f"{skill_risk['risk_level']} risk"
                    )

        # Capacity planning
        if strategic_metrics.get('capacity_planning'):
            capacity_data = strategic_metrics['capacity_planning']

            sections.append(f"  - **Capacity Utilization: {capacity_data.get('total_scheduled_hours', 0):.1f}h total, "
                          f"{capacity_data.get('average_utilization', 0):.1f}% avg utilization**")

            if capacity_data.get('employee_capacity'):
                overutilized = [emp for emp, data in capacity_data['employee_capacity'].items()
                              if data.get('utilization_rate', 0) > 100]
                underutilized = [emp for emp, data in capacity_data['employee_capacity'].items()
                               if data.get('utilization_rate', 0) < 70]

                if overutilized:
                    sections.append(f"    • ⚠️ Overutilized: {', '.join(overutilized[:3])}")
                if underutilized:
                    sections.append(f"    • 📉 Underutilized: {', '.join(underutilized[:3])}")

            if capacity_data.get('capacity_recommendations'):
                sections.append("    • Recommendations:")
                for rec in capacity_data['capacity_recommendations'][:2]:
                    sections.append(f"      - {rec}")

        # Investment opportunities
        if strategic_metrics.get('investment_opportunities'):
            inv_data = strategic_metrics['investment_opportunities']
            sections.append(f"  - **Investment Opportunities ({len(inv_data)} identified):**")
            for opportunity in inv_data[:2]:
                if opportunity['type'] == 'automation_opportunity':
                    sections.append(
                        f"    • Automation for {opportunity['task_category']}: "
                        f"{opportunity['frequency']} tasks, "
                        f"${opportunity['potential_savings']:.0f}/year savings, "
                        f"{opportunity['payback_period_months']:.1f}mo payback"
                    )
                elif opportunity['type'] == 'training_investment':
                    sections.append(
                        f"    • Training: {opportunity['skill_gaps_count']} skill gaps, "
                        f"${opportunity['training_cost_estimate']} investment, "
                        f"{opportunity['efficiency_improvement']} improvement"
                    )

        return "\n".join(sections)

    def _format_cost_summary(self, cost_info: Dict) -> str:
        """Format cost summary for billing display"""
        if not cost_info:
            return ""

        if cost_info.get('billing_type') == 'included':
            return f"💰 **Billing**: Included in plan ({cost_info.get('remaining_included', 0)} optimizations remaining this month)\n"
        else:
            return f"💰 **Billing**: ${cost_info.get('total_cost', 0):.2f} (Base: ${cost_info.get('base_cost', 0):.2f} + Work orders: ${cost_info.get('work_order_cost', 0):.2f})\n"

    def _format_predictive_insights(self, insights: List[Dict]) -> str:
        """Format predictive analytics insights"""
        if not insights:
            return "No predictive insights available."

        sections = []
        sections.append("**Predictive Analytics & Future Planning:**")

        for insight in insights[:5]:  # Show top 5 insights
            confidence_text = f" (confidence: {insight['confidence']:.0%})" if 'confidence' in insight else ""
            sections.append(
                f"  - **{insight['type'].replace('_', ' ').title()}**: {insight['prediction']}{confidence_text}"
            )
            sections.append(f"    💡 Action: {insight['recommended_action']}")
            if 'business_impact' in insight:
                sections.append(f"    📈 Impact: {insight['business_impact']}")

        return "\n".join(sections)

    def _format_strategic_recommendations(self, recommendations: List[Dict]) -> str:
        """Format strategic business recommendations"""
        if not recommendations:
            return "No strategic recommendations available."

        sections = []
        sections.append("**Strategic Business Recommendations:**")

        for rec in recommendations:
            sections.append(f"  - **{rec['category'].replace('_', ' ').title()}**: {rec['recommendation']}")
            sections.append(f"    📊 Impact: {rec['business_impact']}")
            sections.append(f"    ⚡ Effort: {rec['implementation_effort']} | ROI: {rec['roi_estimate']}")

        return "\n".join(sections)

    def _format_performance_benchmarks(self, benchmarks: Dict) -> str:
        """Format performance benchmarks and KPIs"""
        if not benchmarks:
            return "No performance benchmarks available."

        sections = []
        sections.append("**Performance Benchmarks & KPIs:**")

        sections.append(f"  - **Average Task Duration**: {benchmarks.get('average_task_duration', 0):.0f} minutes")
        sections.append(f"  - **Cost per Work Order**: ${benchmarks.get('cost_per_work_order', 0):.2f}")

        if benchmarks.get('efficiency_by_location_type'):
            sections.append("  - **Efficiency by Location Type**:")
            for zone_type, data in benchmarks['efficiency_by_location_type'].items():
                sections.append(f"    • {zone_type.title()}: {data['average_duration']:.0f}min avg ({data['task_count']} tasks)")

        return "\n".join(sections)

    def _format_roi_analysis(self, roi_analysis: Dict) -> str:
        """Format ROI analysis and investment planning"""
        if not roi_analysis:
            return "No ROI analysis available."

        sections = []
        sections.append(f"**ROI Analysis: ${roi_analysis.get('current_state_cost', 0):.2f} current operational cost**")

        if roi_analysis.get('optimization_potential'):
            sections.append("  - **Optimization Opportunities**:")
            for category, data in roi_analysis['optimization_potential'].items():
                sections.append(
                    f"    • {category.replace('_', ' ').title()}: "
                    f"{data.get('time_savings_minutes', 0)}min saved = ${data.get('cost_savings', 0):.2f} "
                    f"({data.get('improvement_percentage', 0):.1f}% improvement)"
                )

        return "\n".join(sections)

    def _get_enhanced_focus_instruction(self, focus: str) -> str:
        """Get enhanced focus instructions with model considerations"""
        focus_instructions = {
            "time": """**FOCUS: TIME OPTIMIZATION WITH COST IMPACT** - Prioritize resolving scheduling conflicts while considering hourly rates and efficiency ratings. Calculate cost impact of conflicts and overtime risks.""",

            "assignee": """**FOCUS: WORKFORCE OPTIMIZATION** - Prioritize skill-based task assignment, workload balancing using efficiency ratings, and cost-effective resource allocation. Consider employee hourly rates, skill certifications, and performance metrics.""",

            "priority": """**FOCUS: PRIORITY & RISK OPTIMIZATION** - Prioritize based on location cleaning priority scores (8.0+ critical), alert severity levels (critical/very_severe = urgent), and business impact. Align work order priorities with facility risk levels.""",

            "location": """**FOCUS: LOCATION & FACILITY OPTIMIZATION** - Prioritize location efficiency using cleaning priority scores, travel time reduction between buildings/floors, alert hotspot management, and zone-based task clustering. Consider facility risk levels and compliance requirements.""",

            "all": """**FOCUS: COMPREHENSIVE OPTIMIZATION** - Balance all optimization objectives using real-time data: employee skills & costs, location priorities & alerts, time efficiency, and strategic business impact."""
        }
        return focus_instructions.get(focus, focus_instructions["all"])