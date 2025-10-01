# Metrics Calculation Reference

This document provides a comprehensive reference for all metrics calculated in the robot performance reporting system, including data sources, calculation formulas, and time periods used.

---

## Table of Contents
1. [Fleet Performance & Robot Metrics](#fleet-performance--robot-metrics)
2. [Cleaning Performance - Tasks & Coverage](#cleaning-performance---tasks--coverage)
3. [Charging Performance](#charging-performance)
4. [Resource Utilization & Efficiency](#resource-utilization--efficiency)
5. [Financial Performance & ROI](#financial-performance--roi)
6. [Event Analysis](#event-analysis)
7. [Facility-Specific Metrics](#facility-specific-metrics)
8. [Map Coverage Metrics](#map-coverage-metrics)
9. [Trend Data](#trend-data)

---

## Fleet Performance & Robot Metrics

### Category: Robot Status & Availability

| Metric | Calculation | Database Fields | Time Period | Function |
|--------|-------------|-----------------|-------------|----------|
| **robots_online_rate** | `(robots_online / total_robots) × 100` | `robot_status.status` (count non-null) | Current snapshot | `calculate_fleet_availability()` |
| **total_robots** | `COUNT(robot_status.robot_sn)` | `robot_status.robot_sn` | Current snapshot | `calculate_fleet_availability()` |
| **robots_online** | Count of robots with `status IS NOT NULL` | `robot_status.status` | Current snapshot | `calculate_fleet_availability()` |
| **total_running_hours** | `SUM(robot_task.duration) / 3600` | `robot_task.duration` (seconds) | Current period | `calculate_fleet_availability()` |
| **average_robot_utilization** | `total_running_hours / total_robots` | Calculated from above | Current period | `calculate_fleet_availability()` |
| **avg_daily_running_hours_per_robot** | Average of: `SUM(duration per robot per day) / days_with_tasks` | `robot_task.duration`, `robot_task.start_time` | Current period | `calculate_avg_daily_running_hours_per_robot()` |
| **days_with_tasks** | `COUNT(DISTINCT DATE(robot_task.start_time))` | `robot_task.start_time` | Current period | `calculate_days_with_tasks()` |

---

## Cleaning Performance - Tasks & Coverage

### Category: Task Completion & Quality

| Metric | Calculation | Database Fields | Time Period | Function |
|--------|-------------|-----------------|-------------|----------|
| **total_tasks** | `COUNT(robot_task.*)` | `robot_task.*` | Current period | `calculate_task_performance_metrics()` |
| **completed_tasks** | `COUNT WHERE status LIKE '%end%' OR '%complet%' OR '%finish%'` | `robot_task.status` | Current period | `calculate_task_performance_metrics()` |
| **cancelled_tasks** | `COUNT WHERE status LIKE '%cancel%'` | `robot_task.status` | Current period | `calculate_task_performance_metrics()` |
| **interrupted_tasks** | `COUNT WHERE status LIKE '%interrupt%' OR '%abort%'` | `robot_task.status` | Current period | `calculate_task_performance_metrics()` |
| **completion_rate** | `(completed_tasks / total_tasks) × 100` | Calculated from above | Current period | `calculate_task_performance_metrics()` |
| **incomplete_task_rate** | `((cancelled_tasks + interrupted_tasks) / total_tasks) × 100` | Calculated from above | Current period | `calculate_task_performance_metrics()` |

### Category: Area Coverage & Efficiency

| Metric | Calculation | Database Fields | Time Period | Function |
|--------|-------------|-----------------|-------------|----------|
| **total_area_cleaned** | `SUM(robot_task.actual_area)` in m² | `robot_task.actual_area` | Current period | `calculate_task_performance_metrics()` |
| **total_area_cleaned_sqft** | `SUM(robot_task.actual_area) × 10.764` | `robot_task.actual_area` | Current period | `calculate_resource_utilization_metrics()` |
| **coverage_efficiency** | `(SUM(actual_area) / SUM(plan_area)) × 100` | `robot_task.actual_area`, `robot_task.plan_area` | Current period | `calculate_task_performance_metrics()` |
| **avg_task_duration_minutes** | `MEAN(robot_task.duration) / 60` | `robot_task.duration` (seconds) | Current period | `calculate_average_task_duration()` |
| **weekend_schedule_completion** | `(completed_weekend_tasks / total_weekend_tasks) × 100` where weekday IN (5,6) | `robot_task.status`, `robot_task.start_time` | Current period | `calculate_weekend_schedule_completion()` |

### Category: Weekday Performance

| Metric | Calculation | Database Fields | Time Period | Function |
|--------|-------------|-----------------|-------------|----------|
| **highest_day** | Weekday with max `(completed / total) × 100` | `robot_task.status`, `robot_task.start_time` | Current period | `calculate_weekday_completion_rates()` |
| **highest_rate** | Completion rate for highest day | Calculated from above | Current period | `calculate_weekday_completion_rates()` |
| **lowest_day** | Weekday with min `(completed / total) × 100` | `robot_task.status`, `robot_task.start_time` | Current period | `calculate_weekday_completion_rates()` |
| **lowest_rate** | Completion rate for lowest day | Calculated from above | Current period | `calculate_weekday_completion_rates()` |

### Category: Task Mode Distribution

| Metric | Calculation | Database Fields | Time Period | Function |
|--------|-------------|-----------------|-------------|----------|
| **task_modes** | `COUNT GROUP BY robot_task.mode` | `robot_task.mode` | Current period | `calculate_task_performance_metrics()` |

---

## Charging Performance

### Category: Charging Sessions & Duration

| Metric | Calculation | Database Fields | Time Period | Function |
|--------|-------------|-----------------|-------------|----------|
| **total_sessions** | `COUNT(robot_charging.*)` | `robot_charging.*` | Current period | `calculate_charging_performance_metrics()` |
| **avg_charging_duration_minutes** | `MEAN(parsed duration from "Xh Ymin")` | `robot_charging.duration` | Current period | `calculate_charging_performance_metrics()` |
| **median_charging_duration_minutes** | `MEDIAN(parsed duration from "Xh Ymin")` | `robot_charging.duration` | Current period | `calculate_charging_performance_metrics()` |
| **total_charging_time** | `SUM(all durations in minutes)` | `robot_charging.duration` | Current period | `calculate_charging_performance_metrics()` |

### Category: Power Gain

| Metric | Calculation | Database Fields | Time Period | Function |
|--------|-------------|-----------------|-------------|----------|
| **avg_power_gain_percent** | `MEAN(parsed from "+X%")` | `robot_charging.power_gain` | Current period | `calculate_charging_performance_metrics()` |
| **median_power_gain_percent** | `MEDIAN(parsed from "+X%")` | `robot_charging.power_gain` | Current period | `calculate_charging_performance_metrics()` |

---

## Resource Utilization & Efficiency

### Category: Energy Consumption

| Metric | Calculation | Database Fields | Time Period | Function |
|--------|-------------|-----------------|-------------|----------|
| **total_energy_consumption_kwh** | `SUM(robot_task.consumption)` | `robot_task.consumption` (kWh) | Current period | `calculate_resource_utilization_metrics()` |
| **area_per_kwh** | `total_area_sqft / total_energy_consumption_kwh` | Calculated from above | Current period | `calculate_resource_utilization_metrics()` |

### Category: Water Usage

| Metric | Calculation | Database Fields | Time Period | Function |
|--------|-------------|-----------------|-------------|----------|
| **total_water_consumption_floz** | `SUM(robot_task.water_consumption)` | `robot_task.water_consumption` (fl oz) | Current period | `calculate_resource_utilization_metrics()` |
| **area_per_gallon** | `total_area_sqft / (total_water_floz / 128)` | Calculated from above | Current period | `calculate_resource_utilization_metrics()` |

---

## Financial Performance & ROI

### Category: Cost Analysis (Current Period)

| Metric | Calculation | Database Fields | Time Period | Function |
|--------|-------------|-----------------|-------------|----------|
| **cost_per_sqft** | `total_cost / total_area_sqft` where `total_cost = (water × $0) + (energy × $0)` | `robot_task.water_consumption`, `robot_task.consumption` | Current period | `calculate_cost_analysis_metrics()` |
| **total_cost** | `(water_consumption × $0/floz) + (energy_consumption × $0/kWh)` | `robot_task.water_consumption`, `robot_task.consumption` | Current period | `calculate_cost_analysis_metrics()` |
| **hours_saved** | `total_area_sqft / 8000` (human speed) | `robot_task.actual_area` | Current period | `calculate_cost_analysis_metrics()` |
| **human_cost** | `hours_saved × $25/hour` | Calculated from above | Current period | `calculate_cost_analysis_metrics()` |
| **savings** | `human_cost - total_cost` | Calculated from above | Current period | `calculate_cost_analysis_metrics()` |
| **annual_projected_savings** | `savings × 12` | Calculated from above | Current period | `calculate_cost_analysis_metrics()` |
| **cost_efficiency_improvement** | `(savings / human_cost) × 100` | Calculated from above | Current period | `calculate_cost_analysis_metrics()` |

### Category: ROI (All-Time Cumulative)

| Metric | Calculation | Database Fields | Time Period | Function |
|--------|-------------|-----------------|-------------|----------|
| **total_roi_percent** | `(total_savings / total_investment) × 100` | Calculated from below | **All-time** (first task to current_end) | `calculate_roi_metrics()` |
| **total_investment** | `SUM(monthly_lease_price × months_elapsed per robot)` | Derived from `robot_task.start_time` (first task date) | **All-time** | `calculate_roi_metrics()` |
| **total_savings** | `human_cost - total_cost` for all tasks | `robot_task.actual_area` | **All-time** | `calculate_roi_metrics()` |
| **monthly_savings_rate** | `total_savings / max_months_elapsed` | Calculated from above | **All-time** | `calculate_roi_metrics()` |
| **payback_period** | `total_investment / monthly_savings_rate` | Calculated from above | **All-time** | `calculate_roi_metrics()` |
| **cumulative_savings** | Same as `total_savings` | `robot_task.actual_area` | **All-time** | `calculate_roi_metrics()` |

**Note**: ROI uses **all-time data** from the first task ever recorded to the current period end date for each robot.

### Category: Robot-Level ROI Breakdown

| Metric | Calculation | Database Fields | Time Period | Function |
|--------|-------------|-----------------|-------------|----------|
| **months_elapsed** | Months from first task to current_end (rounded up) | `robot_task.start_time` (MIN per robot) | **All-time** | `_calculate_months_elapsed()` |
| **investment** | `monthly_lease_price × months_elapsed` | Derived from above | **All-time** | `calculate_roi_metrics()` |
| **savings** | `SUM((area_sqft / 8000 × $25))` per robot | `robot_task.actual_area` WHERE `robot_sn = X` | **All-time** | `_calculate_cumulative_savings_vectorized()` |
| **roi_percent** | `(savings / investment) × 100` per robot | Calculated from above | **All-time** | `calculate_roi_metrics()` |

---

## Event Analysis

### Category: Event Counts by Severity

| Metric | Calculation | Database Fields | Time Period | Function |
|--------|-------------|-----------------|-------------|----------|
| **total_events** | `COUNT(robot_events.*)` | `robot_events.*` | Current period | `calculate_event_analysis_metrics()` |
| **critical_events** | `COUNT WHERE event_level LIKE '%critical%' OR '%fatal%'` | `robot_events.event_level` | Current period | `calculate_event_analysis_metrics()` |
| **error_events** | `COUNT WHERE event_level LIKE '%error%'` | `robot_events.event_level` | Current period | `calculate_event_analysis_metrics()` |
| **warning_events** | `COUNT WHERE event_level LIKE '%warning%' OR '%warn%'` | `robot_events.event_level` | Current period | `calculate_event_analysis_metrics()` |
| **info_events** | `COUNT WHERE event_level LIKE '%info%' OR '%notice%' OR '%debug%'` | `robot_events.event_level` | Current period | `calculate_event_analysis_metrics()` |

### Category: Event Type Distribution

| Metric | Calculation | Database Fields | Time Period | Function |
|--------|-------------|-----------------|-------------|----------|
| **event_types** | `COUNT GROUP BY robot_events.event_type` | `robot_events.event_type` | Current period | `calculate_event_analysis_metrics()` |
| **event_levels** | `COUNT GROUP BY robot_events.event_level` | `robot_events.event_level` | Current period | `calculate_event_analysis_metrics()` |

### Category: Event Location Mapping

| Metric | Calculation | Database Fields | Time Period | Function |
|--------|-------------|-----------------|-------------|----------|
| **events by building** | `COUNT GROUP BY location.building_name` (via robot_sn join) | `robot_events.robot_sn` → `robot_status.location_id` → `location.building_name` | Current period | `calculate_event_location_mapping()` |
| **event_type_by_location** | `COUNT GROUP BY event_type, building_name` | Same as above + `robot_events.event_type` | Current period | `calculate_event_type_by_location()` |

---

## Facility-Specific Metrics

### Category: Facility Task Performance

| Metric | Calculation | Database Fields | Time Period | Function |
|--------|-------------|-----------------|-------------|----------|
| **total_tasks (per facility)** | `COUNT WHERE robot_sn IN (facility_robots)` | `robot_task.*`, joined via `location.building_name` | Current period | `_calculate_all_facility_metrics_batch()` |
| **completed_tasks (per facility)** | `COUNT WHERE status LIKE '%complet%' AND robot_sn IN (facility_robots)` | `robot_task.status` | Current period | `_calculate_all_facility_metrics_batch()` |
| **completion_rate (per facility)** | `(completed / total) × 100` per facility | Calculated from above | Current period | `_calculate_all_facility_metrics_batch()` |
| **area_cleaned (per facility)** | `SUM(actual_area) × 10.764` per facility | `robot_task.actual_area` | Current period | `_calculate_all_facility_metrics_batch()` |
| **coverage_efficiency (per facility)** | `(SUM(actual_area) / SUM(plan_area)) × 100` per facility | `robot_task.actual_area`, `robot_task.plan_area` | Current period | `_calculate_all_facility_metrics_batch()` |
| **running_hours (per facility)** | `SUM(duration) / 3600` per facility | `robot_task.duration` | Current period | `_calculate_all_facility_metrics_batch()` |
| **days_with_tasks (per facility)** | `COUNT(DISTINCT DATE(start_time))` per facility | `robot_task.start_time` | Current period | `_calculate_all_facility_metrics_batch()` |

### Category: Facility Efficiency

| Metric | Calculation | Database Fields | Time Period | Function |
|--------|-------------|-----------------|-------------|----------|
| **water_efficiency (per facility)** | `area_sqft / water_consumption` | `robot_task.actual_area`, `robot_task.water_consumption` | Current period | `calculate_facility_efficiency_metrics()` |
| **time_efficiency (per facility)** | `area_sqft / running_hours` | `robot_task.actual_area`, `robot_task.duration` | Current period | `calculate_facility_efficiency_metrics()` |
| **power_efficiency (per facility)** | `area_sqft / energy_consumption` | `robot_task.actual_area`, `robot_task.consumption` | Current period | `_calculate_all_facility_metrics_batch()` |

### Category: Facility Resource Usage

| Metric | Calculation | Database Fields | Time Period | Function |
|--------|-------------|-----------------|-------------|----------|
| **energy_consumption_kwh (per facility)** | `SUM(consumption)` per facility | `robot_task.consumption` | Current period | `_calculate_all_facility_metrics_batch()` |
| **water_consumption_floz (per facility)** | `SUM(water_consumption)` per facility | `robot_task.water_consumption` | Current period | `_calculate_all_facility_metrics_batch()` |

### Category: Facility Charging

| Metric | Calculation | Database Fields | Time Period | Function |
|--------|-------------|-----------------|-------------|----------|
| **total_sessions (per facility)** | `COUNT(robot_charging)` per facility | `robot_charging.*` | Current period | `_calculate_all_facility_metrics_batch()` |
| **avg_duration_minutes (per facility)** | `MEAN(parsed duration)` per facility | `robot_charging.duration` | Current period | `_calculate_all_facility_metrics_batch()` |
| **avg_power_gain_percent (per facility)** | `MEAN(parsed power_gain)` per facility | `robot_charging.power_gain` | Current period | `_calculate_all_facility_metrics_batch()` |

---

## Map Coverage Metrics

### Category: Map-Level Performance

| Metric | Calculation | Database Fields | Time Period | Function |
|--------|-------------|-----------------|-------------|----------|
| **coverage_percentage (per map)** | `(SUM(actual_area) / SUM(plan_area)) × 100` per map | `robot_task.actual_area`, `robot_task.plan_area`, `robot_task.map_name` | Current period | `calculate_map_performance_by_building()` |
| **area_cleaned (per map)** | `SUM(actual_area) × 10.764` per map | `robot_task.actual_area`, `robot_task.map_name` | Current period | `calculate_map_performance_by_building()` |
| **completion_rate (per map)** | `(completed_tasks / total_tasks) × 100` per map | `robot_task.status`, `robot_task.map_name` | Current period | `calculate_map_performance_by_building()` |
| **running_hours (per map)** | `SUM(duration) / 3600` per map | `robot_task.duration`, `robot_task.map_name` | Current period | `calculate_map_performance_by_building()` |
| **power_efficiency (per map)** | `area_sqft / energy_consumption` per map | `robot_task.actual_area`, `robot_task.consumption`, `robot_task.map_name` | Current period | `calculate_map_performance_by_building()` |
| **water_efficiency (per map)** | `area_sqft / water_consumption` per map | `robot_task.actual_area`, `robot_task.water_consumption`, `robot_task.map_name` | Current period | `calculate_map_performance_by_building()` |
| **days_with_tasks (per map)** | `COUNT(DISTINCT DATE(start_time))` per map | `robot_task.start_time`, `robot_task.map_name` | Current period | `calculate_map_performance_by_building()` |

---

## Trend Data

### Category: Daily Trends (Current Period)

| Metric | Calculation | Database Fields | Time Period | Function |
|--------|-------------|-----------------|-------------|----------|
| **charging_sessions_trend** | `COUNT(robot_charging) GROUP BY DATE(start_time)` | `robot_charging.start_time` | Current period (daily) | `calculate_daily_trends()` |
| **charging_duration_trend** | `MEAN(parsed duration) GROUP BY DATE(start_time)` | `robot_charging.duration` | Current period (daily) | `calculate_daily_trends()` |
| **energy_consumption_trend** | `SUM(consumption) GROUP BY DATE(start_time)` | `robot_task.consumption` | Current period (daily) | `calculate_daily_trends()` |
| **water_usage_trend** | `SUM(water_consumption) GROUP BY DATE(start_time)` | `robot_task.water_consumption` | Current period (daily) | `calculate_daily_trends()` |
| **cost_savings_trend** | `SUM((area_sqft / 8000 × $25)) GROUP BY DATE(start_time)` | `robot_task.actual_area` | Current period (daily) | `calculate_daily_trends()` |

### Category: Daily ROI Trends (Current Period with All-Time Context)

| Metric | Calculation | Database Fields | Time Period | Function |
|--------|-------------|-----------------|-------------|----------|
| **daily_savings_trend** | Daily savings for current period | `robot_task.actual_area` | Current period (daily) | `calculate_daily_roi_trends()` |
| **roi_trend** | `(cumulative_savings / total_investment) × 100` per day | `robot_task.actual_area` (all-time cumulative) | **All-time cumulative + current period daily** | `calculate_daily_roi_trends()` |

**Note**: ROI trend shows cumulative ROI growth over the current period, but cumulative_savings includes all-time data up to each day.

### Category: Financial Trends (Current Period)

| Metric | Calculation | Database Fields | Time Period | Function |
|--------|-------------|-----------------|-------------|----------|
| **hours_saved_trend** | `(area_sqft / 1000) GROUP BY DATE` | `robot_task.actual_area` | Current period (daily) | `calculate_daily_financial_trends()` |
| **savings_trend** | `(hours_saved × $25) GROUP BY DATE` | Calculated from above | Current period (daily) | `calculate_daily_financial_trends()` |

---

## Individual Robot Performance

### Category: Robot-Level Metrics

| Metric | Calculation | Database Fields | Time Period | Function |
|--------|-------------|-----------------|-------------|----------|
| **total_tasks (per robot)** | `COUNT WHERE robot_sn = X` | `robot_task.*` | Current period | `calculate_individual_robot_performance()` |
| **tasks_completed (per robot)** | `COUNT WHERE robot_sn = X AND status LIKE '%complet%'` | `robot_task.status` | Current period | `calculate_individual_robot_performance()` |
| **total_area_cleaned (per robot)** | `SUM(actual_area) × 10.764 WHERE robot_sn = X` | `robot_task.actual_area` | Current period | `calculate_individual_robot_performance()` |
| **average_coverage (per robot)** | `(SUM(actual_area) / SUM(plan_area)) × 100 WHERE robot_sn = X` | `robot_task.actual_area`, `robot_task.plan_area` | Current period | `calculate_individual_robot_performance()` |
| **days_with_tasks (per robot)** | `COUNT(DISTINCT DATE(start_time)) WHERE robot_sn = X` | `robot_task.start_time` | Current period | `calculate_individual_robot_performance()` |
| **running_hours (per robot)** | `SUM(duration) / 3600 WHERE robot_sn = X` | `robot_task.duration` | Current period | `calculate_individual_robot_performance()` |
| **charging_sessions (per robot)** | `COUNT WHERE robot_sn = X` | `robot_charging.*` | Current period | `calculate_individual_robot_performance()` |
| **battery_level (per robot)** | Current snapshot value | `robot_status.battery_level` | Current snapshot | `calculate_individual_robot_performance()` |

---

## Constants Used in Calculations

| Constant | Value | Used In |
|----------|-------|---------|
| **HOURLY_WAGE** | $25.00/hour | Cost analysis, ROI, savings calculations |
| **HUMAN_CLEANING_SPEED** | 8000 sq ft/hour | Hours saved, cost analysis |
| **HUMAN_CLEANING_SPEED (financial)** | 1000 sq ft/hour | Financial trends |
| **COST_PER_FL_OZ_WATER** | $0.00/fl oz | Cost analysis (currently free) |
| **COST_PER_KWH** | $0.00/kWh | Cost analysis (currently free) |
| **MONTHLY_LEASE_PRICE** | $1500.00/month | ROI calculations |
| **SQM_TO_SQFT_CONVERSION** | 10.764 | Area conversions |
| **FLOZ_TO_GALLON_CONVERSION** | 128 fl oz/gallon | Water efficiency |

---

## Time Period Definitions

| Period Type | Definition | Used By |
|-------------|------------|---------|
| **Current Period** | `start_date` to `end_date` specified in report config | Most metrics |
| **Previous Period** | Same length as current, ending 1 second before current starts | Comparison metrics |
| **All-Time** | From first task ever (`MIN(robot_task.start_time)` per robot) to `end_date` | ROI calculations only |
| **Current Snapshot** | Data state at report generation time | Robot status metrics |
| **Daily** | Aggregated by `DATE(start_time)` within current period | Trend data |

---

## Database Tables & Key Fields

### robot_task
- `robot_sn` - Robot serial number (FK)
- `start_time` - Task start timestamp
- `duration` - Task duration in **seconds**
- `actual_area` - Actual area cleaned in **m²**
- `plan_area` - Planned area in **m²**
- `consumption` - Energy consumption in **kWh**
- `water_consumption` - Water usage in **fl oz**
- `status` - Task status string
- `mode` - Task mode/type
- `map_name` - Map identifier

### robot_charging
- `robot_sn` - Robot serial number (FK)
- `start_time` - Charging start timestamp
- `duration` - Duration string format: "Xh Ymin"
- `power_gain` - Power gain string format: "+X%"
- `initial_power` - Starting battery %
- `final_power` - Ending battery %

### robot_status
- `robot_sn` - Robot serial number (PK)
- `status` - Current operational status
- `location_id` - Location identifier (FK)
- `battery_level` - Current battery %
- `water_level` - Current water tank level
- `sewage_level` - Current sewage tank level

### robot_events
- `robot_sn` - Robot serial number (FK)
- `task_time` - Event timestamp
- `event_level` - Severity level (critical/error/warning/info)
- `event_type` - Event type classification

### location
- `building_id` - Building identifier (PK)
- `building_name` - Facility name
- `city`, `state`, `country` - Location details

---

## Notes

1. **Unit Conversions**: Always applied consistently
   - Duration: seconds → hours (÷ 3600) or minutes (÷ 60)
   - Area: m² → sq ft (× 10.764)
   - Water: fl oz → gallons (÷ 128)

2. **Null Handling**: All calculations use `.fillna(0)` or skip null values

3. **String Parsing**:
   - Status matching uses case-insensitive LIKE patterns
   - Duration parsing handles "Xh Ymin" format
   - Power gain parsing handles "+X%" format

4. **All-Time vs Period**: Only ROI uses all-time data; all other metrics use current period only

5. **Batch Optimization**: Facility metrics calculated in single pass for performance