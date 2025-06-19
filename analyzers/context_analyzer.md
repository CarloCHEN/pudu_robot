# ContextAnalyzer Documentation

## Overview

The `ContextAnalyzer` is the core analysis engine of the work order optimization system, responsible for all data analysis and computation. Following clean architecture principles, it focuses solely on "What does this data mean?" while delegating organization and formatting to the `ContextBuilder`.

## Architecture Philosophy

**Single Responsibility**: Pure data analysis and computation
**Input**: Work orders, employee data, location data, alert data
**Output**: Analyzed insights, metrics, and recommendations
**No Formatting**: Raw analytical results only - formatting handled by ContextBuilder

## Tier-Aware Analysis System

The ContextAnalyzer provides different levels of analysis depth based on business tiers, with all methods available but results filtered and restricted by the ContextBuilder during organization.

---

## Implementation Details

### Initialization and Data Setup

```python
def __init__(self, generator: WorkOrderGenerator):
    self.generator = generator
    self.employees = {emp.full_name: emp for emp in generator.employees
                     if emp.employment_status == EmploymentStatus.ACTIVE}
    self.locations = {loc.location_id: loc for loc in generator.locations}
    self.alerts = generator.alerts
```

The analyzer initializes with:
- **Active employees only**: Filters to currently employed staff
- **Location mapping**: Quick lookup by location ID
- **Full alert dataset**: All alerts regardless of status for pattern analysis

---

## Core Analysis Methods

### 1. Workload Distribution Analysis

#### `analyze_workload_distribution(work_orders: List[WorkOrder]) -> Dict[str, Any]`

**Purpose**: Analyzes employee workload distribution with efficiency and cost considerations

#### Implementation Details:
- **Employee Data Integration**: Links work orders to complete employee profiles
- **Cost Calculation**: `(duration_minutes / 60.0) * hourly_rate`
- **Efficiency Adjustment**: `adjusted_duration = total_duration / efficiency_factor`
- **Enhanced Scoring**: Uses `_calculate_enhanced_workload_score()` for comprehensive workload assessment

#### Basic Tier Analysis:
- **Scope**: Essential workload metrics with hourly rate awareness
- **Data Used**: Employee hourly rates, basic efficiency ratings
- **Calculations**:
  - Total duration per employee
  - Basic cost estimates (duration × hourly rate)
  - Simple task count distribution
- **Output**: Basic workload summary with cost awareness

#### Professional Tier Analysis:
- **Scope**: Comprehensive cost optimization with efficiency considerations
- **Cost Analysis**:
  - Detailed cost breakdown by priority, employee, location
  - Overqualified assignment detection (high-rate employees on low-priority tasks)
  - Cost-effectiveness ratios (performance/hourly_rate)
  - Alternative assignment cost comparisons
- **Optimization Opportunities**:
  - Skill-based cost optimization
  - Efficiency-adjusted cost calculations
  - Resource reallocation recommendations
- **Output**: Detailed cost optimization with actionable recommendations

#### Enterprise Tier Analysis:
- **Scope**: Strategic cost analysis with ROI and investment planning
- **Cost Analysis**:
  - Complete financial modeling with ROI calculations
  - Investment opportunity identification (automation, training)
  - Long-term cost trend analysis
  - Budget optimization recommendations
- **Strategic Insights**:
  - Cost center analysis
  - Resource investment planning
  - Financial performance benchmarking
- **Output**: Strategic financial intelligence with investment recommendations

```python
# Example Output Structure
{
    "John Doe": {
        "employee_id": "EMP001",
        "total_tasks": 4,
        "total_duration_minutes": 240,
        "adjusted_duration_minutes": 275,  # Professional+
        "total_cost_estimate": 100.00,
        "efficiency_rating": 8.7,  # Professional+
        "workload_score": 45.2,  # Professional+
        "cost_effectiveness": 0.35,  # Professional+
        "preferred_zones": ["office", "lobby"]  # Enterprise
    }
}
```

---

### 2. Conflict Detection Analysis

#### `detect_conflicts(work_orders: List[WorkOrder]) -> Dict[str, List[Dict]]`

**Purpose**: Identifies and analyzes various types of conflicts with cost and business impact

#### Implementation Features:
- **Time Overlap Detection**: `_times_overlap()` method for precise conflict identification
- **Cost Impact Calculation**: Monetizes conflicts using employee hourly rates
- **Workload Imbalance**: 30% deviation threshold from average workload
- **Skill Requirement Matching**: Location-specific skill validation

#### Conflict Types Detected:

##### Time-Assignee Conflicts:
```python
# Overlap calculation with cost impact
overlap_minutes = self._calculate_overlap_minutes(wo1, wo2)
cost_impact = (overlap_minutes / 60.0) * employee.hourly_rate
```

##### Location-Time Conflicts:
- Identifies multiple assignees at same location/time
- Considers location capacity and zone type
- Calculates facility utilization impact

##### Workload Imbalance:
```python
# 30% deviation threshold
deviation = abs(data['workload_score'] - avg_workload)
if deviation > avg_workload * 0.3:
    # Flag as imbalanced
```

##### Skill Mismatches:
- Validates required skills against employee capabilities
- Risk assessment based on location priority
- Alternative employee recommendations

##### Cost Inefficiencies:
- Detects overqualified assignments ($30+ hourly rate on <6.0 priority locations)
- Calculates potential savings from reassignment

#### Basic Tier Analysis:
- **Scope**: Essential conflict detection with basic cost awareness
- **Conflicts Detected**:
  - Time-assignee overlaps
  - Location-time conflicts for high-priority locations (8.0+ only)
- **Cost Impact**: Simple overlap duration × hourly rate
- **Output**: Basic conflict list with essential cost information

#### Professional Tier Analysis:
- **Scope**: Comprehensive conflict analysis with efficiency considerations
- **Conflicts Detected**:
  - All time-assignee conflicts with detailed cost impact
  - Location-time conflicts for all priority levels
  - Workload imbalance detection (30% deviation threshold)
  - Basic skill mismatches for location requirements
- **Advanced Calculations**:
  - Employee efficiency impact on conflict resolution
  - Location priority scoring influence
  - Workload deviation percentages
- **Output**: Detailed conflict analysis with performance metrics

#### Enterprise Tier Analysis:
- **Scope**: Strategic conflict analysis with business intelligence
- **Conflicts Detected**:
  - All professional-tier conflicts plus:
  - Cost inefficiency detection (overqualified assignments)
  - Risk-level assessment for skill mismatches
  - Compliance and safety risk evaluation
- **Strategic Analysis**:
  - Business impact assessment for each conflict
  - Resource optimization opportunities
  - Risk mitigation recommendations
- **Output**: Comprehensive conflict intelligence with strategic insights

---

### 3. Alert Impact Analysis

#### `analyze_alert_impact(work_orders: List[WorkOrder]) -> Dict[str, Any]`

**Purpose**: Analyzes alert patterns and their impact on work order optimization

#### Implementation Strategy:
- **Location Grouping**: Groups active alerts by location for hotspot identification
- **Severity Analysis**: Comprehensive severity distribution tracking
- **Work Order Correlation**: Links alerts to addressing work orders
- **Priority Matching**: Validates work order priority against alert severity

#### Key Algorithms:

##### Alert Hotspot Detection:
```python
# Locations with multiple critical alerts
critical_count = sum(1 for s in severities if s in ['critical', 'very_severe'])
if critical_count >= 2:  # Hotspot threshold
```

##### Unaddressed Critical Alert Detection:
```python
# Critical alerts without corresponding work orders
addressing_orders = [wo for wo in work_orders if wo.location == location.location_name]
if not addressing_orders:
    # Flag as unaddressed
```

#### Basic Tier Analysis:
- **Scope**: Basic alert acknowledgment for warning-level alerts only
- **Data Used**: Active warning alerts, basic location correlation
- **Analysis**:
  - Count of active alerts per location
  - Simple severity distribution (warnings only)
  - Basic work order correlation
- **Output**: Essential alert information for immediate conflicts

#### Professional Tier Analysis:
- **Scope**: Comprehensive alert analysis with business impact
- **Data Used**: All alert severities, detailed location data, work order correlation
- **Analysis**:
  - Complete severity distribution (warning → critical)
  - Alert hotspot identification (multiple severe+ alerts)
  - Work order addressing analysis
  - Unaddressed critical alert detection
- **Output**: Detailed alert intelligence with business impact

#### Enterprise Tier Analysis:
- **Scope**: Strategic alert analysis with predictive capabilities
- **Data Used**: Historical alert patterns, business continuity data, compliance requirements
- **Analysis**:
  - Predictive alert escalation patterns
  - Business continuity risk assessment
  - Compliance impact evaluation
  - Facility risk scoring
- **Output**: Strategic alert intelligence with predictive insights

---

### 4. Skill Matching Analysis

#### `analyze_skill_matching(work_orders: List[WorkOrder]) -> Dict[str, Any]`

**Purpose**: Analyzes employee skill alignment with task requirements

#### Implementation Details:

##### Skill Requirement Engine:
```python
skill_requirements = {
    'restroom': ['restroom_cleaning', 'sanitization'],
    'laboratory': ['laboratory_cleaning', 'chemical_handling', 'contamination_control'],
    'kitchen': ['food_safety', 'sanitization'],
    # ... additional zone types
}
```

##### Better Employee Matching Algorithm:
```python
# Multi-factor scoring for optimal assignment
skill_score = skill_match_count / len(required_skills)
total_score = skill_score * 10 + employee.efficiency_rating - (employee.hourly_rate / 10)
```

#### Analysis Components:
- **Skill Gap Identification**: Missing skills per work order
- **Alternative Employee Scoring**: Multi-factor optimization
- **Risk Assessment**: Based on location priority and skill criticality
- **Training Recommendations**: Skill gap frequency analysis

---

### 5. Cost Efficiency Analysis

#### `analyze_cost_efficiency(work_orders: List[WorkOrder]) -> Dict[str, Any]`

**Purpose**: Analyzes cost optimization opportunities across work orders

#### Implementation Features:

##### Overqualified Assignment Detection:
```python
# High-rate employees on low-priority tasks
if (employee.hourly_rate > 30.0 and location.cleaning_priority_score < 6.0):
    potential_savings = (employee.hourly_rate - 20.0) * (wo.duration_minutes / 60.0)
```

##### Cheaper Alternative Finding:
```python
def _find_cheaper_qualified_employee(self, location, max_rate: float):
    # Find qualified employee with lower hourly rate
    if set(required_skills).issubset(employee_skills):
        # Return cheaper alternative
```

#### Analysis Components:
- **Total Cost Calculation**: Comprehensive project costing
- **Priority-Based Breakdown**: Cost distribution by work order priority
- **Rate Distribution**: Employee cost tier analysis
- **Optimization Opportunities**: Specific reassignment recommendations

---

### 6. Location Efficiency Analysis

#### `analyze_location_efficiency(work_orders: List[WorkOrder]) -> Dict[str, Any]`

**Purpose**: Analyzes location-based optimization opportunities including travel and clustering

#### Travel Optimization Algorithm:
```python
# Calculate building and floor changes
if prev_loc.building != curr_loc.building:
    current_building_changes += 1
elif prev_loc.floor != curr_loc.floor:
    current_floor_changes += 1

# Estimate time savings (20min building, 5min floor)
travel_savings = (current_building_changes - optimal_building_changes) * 20 + \
                (current_floor_changes - optimal_floor_changes) * 5
```

#### Basic Tier Analysis:
- **Scope**: Basic location grouping for high-priority locations (8.0+)
- **Analysis**:
  - Simple building-based grouping
  - Basic travel time considerations for same building
  - Essential location conflict resolution
- **Output**: Basic location optimization for immediate efficiency

#### Professional Tier Analysis:
- **Scope**: Comprehensive location intelligence with travel optimization
- **Analysis**:
  - Detailed travel pattern analysis (building/floor changes)
  - Clustering opportunity identification
  - Travel time savings calculations (20min building change, 5min floor change)
  - Location efficiency scoring based on assignee coordination
- **Optimization Strategies**:
  - Optimal building/floor sequencing
  - Assignee-location matching for minimal travel
  - Time-based location clustering
- **Output**: Comprehensive location optimization with quantified travel savings

#### Enterprise Tier Analysis:
- **Scope**: Strategic facility management with predictive optimization
- **Analysis**:
  - Facility utilization patterns
  - Predictive maintenance scheduling
  - Space optimization recommendations
  - Compliance and safety route optimization
- **Strategic Insights**:
  - Facility investment recommendations
  - Long-term space planning
  - Operational efficiency benchmarking
- **Output**: Strategic facility intelligence with investment planning

---

## Performance Analysis Methods

### 7. Performance Metrics Calculation

#### `calculate_performance_metrics(work_orders: List[WorkOrder]) -> Dict[str, Any]`

**Purpose**: Calculates comprehensive performance metrics for workforce and facility optimization

#### Implementation Components:

##### Employee Performance Tracking:
- Task completion rates and efficiency
- Utilization rate calculations
- Skill utilization scoring
- Performance trend identification

##### Location Utilization Analysis:
- Zone-type performance analysis
- Location efficiency scoring
- Alert frequency correlation

#### Professional Tier Analysis:
- **Employee Performance**:
  - Task completion efficiency
  - Utilization rate calculations
  - Skill utilization scoring
  - Performance trend identification
- **Location Utilization**:
  - Zone-type performance analysis
  - Location efficiency scoring
  - Alert frequency correlation
- **Output**: Operational performance insights

#### Enterprise Tier Analysis:
- **Strategic Performance**:
  - Workforce productivity benchmarking
  - Facility performance optimization
  - Predictive performance modeling
  - Competitive performance analysis
- **Business Intelligence**:
  - ROI-based performance scoring
  - Strategic KPI development
  - Performance-based investment recommendations
- **Output**: Strategic performance intelligence

---

## Strategic Analysis Methods (Enterprise Tier)

### 8. Strategic Metrics Calculation

#### `calculate_strategic_metrics(work_orders: List[WorkOrder]) -> Dict[str, Any]`

**Purpose**: Provides enterprise-level strategic analysis for business intelligence

**Components**:
- Risk assessment through `assess_operational_risks()`
- Capacity planning through `analyze_capacity_utilization()`
- Investment analysis through `identify_investment_opportunities()`
- Strategic KPIs through `calculate_strategic_kpis()`

#### Risk Assessment Implementation:
```python
# High-risk location identification
if location.cleaning_priority_score >= 9.0:
    location_alerts = [a for a in alerts if a.location_id == location.location_id]
    if len(location_alerts) >= 2:
        # Flag as high-risk
```

#### Capacity Planning Algorithm:
```python
# Employee capacity analysis
employee_capacity = {
    'scheduled_hours': task_hours,
    'capacity_hours': 8.0,  # Standard 8-hour day
    'utilization_rate': (scheduled_hours / capacity_hours) * 100,
    'overtime_risk': utilization_rate > 100
}
```

### 9. Predictive Insights Generation

#### `generate_predictive_insights(work_orders: List[WorkOrder]) -> List[Dict]`

**Purpose**: Generates predictive analytics for proactive optimization

#### Prediction Algorithms:

##### Alert Pattern Prediction:
```python
# Locations with 3+ alerts likely to generate more
if len(location_alerts) >= 3:
    confidence = 0.75  # Based on pattern frequency
```

##### Workforce Utilization Prediction:
```python
# Near-overtime threshold detection
if data['utilization_hours'] > 7.5:
    prediction = "approaching overtime threshold"
    confidence = 0.85
```

### 10. Strategic Recommendations Generation

#### `generate_strategic_recommendations(work_orders: List[WorkOrder]) -> List[Dict]`

**Purpose**: Generates strategic business recommendations with ROI analysis

#### Recommendation Engine:

##### Skill Gap Analysis:
```python
# Identify training needs
skill_gaps = all_required_skills - available_skills
if skill_gaps:
    # Generate training recommendation with ROI
```

##### Cost Optimization:
```python
# Calculate savings potential
total_savings = sum(item['potential_savings'] for item in overqualified_assignments)
roi_percentage = (total_savings/total_cost) * 100
```

### 11. Investment Opportunity Analysis

#### `identify_investment_opportunities(work_orders: List[WorkOrder]) -> List[Dict[str, Any]]`

**Purpose**: Identifies automation and training investment opportunities with ROI analysis

#### Investment Detection:

##### Automation Opportunities:
```python
# High-frequency task identification
if len(tasks) >= 5:  # Frequency threshold
    automation_roi = {
        'current_annual_cost': total_cost * 52,
        'automation_investment': total_cost * 10,
        'potential_savings': total_cost * 0.3 * 52,
        'payback_period_months': investment / (savings / 12)
    }
```

---

## Data Extraction Methods

### 12. Employee Insights Extraction

#### `extract_employee_insights(work_orders: List[WorkOrder]) -> Dict[str, Any]`

**Purpose**: Extracts comprehensive employee performance and utilization data

#### Implementation Details:

##### Skill Match Rate Calculation:
```python
skill_match_rate = len(required_skills.intersection(available_skills)) / len(required_skills)
```

##### Travel Complexity Assessment:
```python
travel_complexity = 'high' if len(buildings) > 1 or len(floors) > 2 else 'low'
```

##### Cost Effectiveness Scoring:
```python
cost_effectiveness = employee.performance_rating / employee.hourly_rate
```

### 13. Location Insights Extraction

#### `extract_location_insights(work_orders: List[WorkOrder]) -> Dict[str, Any]`

**Purpose**: Extracts detailed location performance and risk data

#### Key Metrics:
- **Efficiency Scoring**: Custom algorithm considering assignee coordination
- **Congestion Risk**: Based on assignee count and time span
- **Alert Correlation**: Links location performance to alert patterns

### 14. Alert Insights Extraction

#### `extract_alert_insights(work_orders: List[WorkOrder]) -> Dict[str, Any]`

**Purpose**: Extracts alert patterns and work order correlation data

#### Analysis Components:
- **Hotspot Identification**: Multiple critical alerts per location
- **Severity Distribution**: Complete alert severity breakdown
- **Work Order Correlation**: Priority-alert alignment analysis
- **Unaddressed Critical Detection**: Safety and compliance gaps

---

## Utility and Helper Methods

### Supporting Analysis Functions:

#### `calculate_efficiency_indicators()`
Calculates travel and time efficiency metrics:
```python
# Travel efficiency calculation
travel_changes = sum(location changes per employee)
avg_changes_per_employee = travel_changes / unique_assignees

# Time efficiency metrics
scheduling_density = total_duration / (assignees * 480)  # 8-hour day
```

#### `calculate_location_efficiency_score()`
Location-specific efficiency scoring:
```python
# Adjust for scheduling efficiency
if unique_assignees > 2:
    base_score -= 1.0  # Coordination penalty
if len(orders) > 1 and unique_assignees <= 2:
    base_score += 0.5  # Concentration bonus
```

#### `check_priority_alert_match()`
Priority-alert severity alignment:
```python
# Match work order priority to alert severity
if max_severity in ['critical', 'very_severe'] and priority == 'High':
    return True
# Additional matching logic...
```

### Private Helper Methods:

#### `_calculate_enhanced_workload_score()`
Multi-factor workload scoring:
```python
base_score = len(tasks) * 10
duration_factor = sum(task['duration']) / 60
priority_factor = sum(priority_weights)
efficiency_adjustment = 10.0 / employee.efficiency_rating
cost_factor = employee.hourly_rate / 25.0

return (base_score + duration_factor + priority_factor) * efficiency_adjustment * cost_factor
```

#### `_get_required_skills_for_location()`
Location-based skill requirement engine:
```python
# Zone-specific skill requirements
skill_requirements = {
    'restroom': ['restroom_cleaning', 'sanitization'],
    'laboratory': ['laboratory_cleaning', 'chemical_handling'],
    # ... additional mappings
}

# Priority-based additional requirements
if location.cleaning_priority_score >= 9.0:
    required_skills.append('quality_control')
```

---

## Integration with ContextBuilder

The ContextAnalyzer maintains clean separation of concerns:

**ContextAnalyzer Responsibilities**:
- Pure data analysis and computation
- Algorithm implementation
- Statistical calculations
- Pattern recognition
- Insight generation

**ContextBuilder Responsibilities**:
- Orchestrating analyzer method calls
- Applying tier restrictions to results
- Business logic and validation
- Context formatting and organization
- Feature gating implementation

This architecture ensures maintainable, testable, and scalable analysis capabilities while preserving clear business tier distinctions and upgrade value propositions.

---

## Performance Characteristics

### Computational Complexity:
- **Work Order Processing**: O(n) for basic analysis, O(n²) for conflict detection
- **Employee Analysis**: O(n×m) where n=work orders, m=employees
- **Location Analysis**: O(n×l) where l=locations
- **Memory Usage**: Efficient with dictionary-based lookups and set operations

### Optimization Strategies:
- **Early Filtering**: Active employees and relevant data only
- **Cached Lookups**: Pre-built employee and location dictionaries
- **Algorithmic Efficiency**: Set operations for skill matching, optimized overlap detection

### Scalability Considerations:
- **Modular Design**: Independent analysis methods for parallel processing
- **Data Structure Optimization**: Efficient grouping and aggregation
- **Incremental Analysis**: Capability for partial work order processing