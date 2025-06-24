from enum import Enum
from typing import List, Dict, Any
from dataclasses import dataclass, field


class ReportType(Enum):
    CLIENT = "client"
    PERFORMANCE = "performance"
    INTERNAL = "internal"


class ContentCategory(Enum):
    INSIGHTS = "insights"
    ENVIRONMENT = "environment"
    OCCUPANCY = "occupancy"
    CONSUMABLE_WASTE = "consumable_waste"
    TASK_MANAGEMENT = "task_management"
    AUTONOMOUS_EQUIPMENT = "autonomous_equipment"
    FINANCIAL = "financial"


@dataclass
class ReportContent:
    """Represents a single content item in a report"""
    id: str
    name: str
    category: ContentCategory
    allowed_report_types: List[ReportType]
    enabled_by_default: bool = False


@dataclass
class ReportConfiguration:
    """Configuration for a report"""
    report_type: ReportType
    report_name: str
    time_range: str
    locations: Dict[str, Any]
    selected_content: List[str]
    analysis_depth: str = "detailed"
    output_format: str = "pdf"
    delivery_options: Dict[str, Any] = field(default_factory=dict)


# Define all available report content
REPORT_CONTENT_CATALOG = [
    # Insights & Analytics
    ReportContent("problem-hotspots", "Problem Hotspots Analysis", ContentCategory.INSIGHTS,
                  [ReportType.INTERNAL], True),
    ReportContent("cleaning-priorities", "Cleaning Priorities", ContentCategory.INSIGHTS,
                  [ReportType.PERFORMANCE, ReportType.INTERNAL], True),
    ReportContent("correlation-analysis", "Correlation Analysis (What Affects What)", ContentCategory.INSIGHTS,
                  [ReportType.INTERNAL], False),
    ReportContent("work-performance", "Work Performance Metrics", ContentCategory.INSIGHTS,
                  [ReportType.CLIENT, ReportType.PERFORMANCE, ReportType.INTERNAL], True),
    ReportContent("recommendations", "AI-Generated Recommendations", ContentCategory.INSIGHTS,
                  [ReportType.CLIENT, ReportType.INTERNAL], False),
    ReportContent("executive-summary", "Executive Summary", ContentCategory.INSIGHTS,
                  [ReportType.CLIENT], False),
    ReportContent("service-highlights", "Service Delivery Highlights", ContentCategory.INSIGHTS,
                  [ReportType.CLIENT], False),

    # Environment Management
    ReportContent("critical-conditions", "Critical Environmental Conditions", ContentCategory.ENVIRONMENT,
                  [ReportType.CLIENT, ReportType.INTERNAL], False),
    ReportContent("quality-recommendations", "Environmental Quality Recommendations", ContentCategory.ENVIRONMENT,
                  [ReportType.INTERNAL], False),
    ReportContent("env-trends", "Monthly Environmental Trends", ContentCategory.ENVIRONMENT,
                  [ReportType.CLIENT, ReportType.PERFORMANCE], False),
    ReportContent("env-compliance", "Environmental Compliance Status", ContentCategory.ENVIRONMENT,
                  [ReportType.CLIENT], False),

    # Occupancy Analysis
    ReportContent("people-distribution", "People Distribution Across Locations", ContentCategory.OCCUPANCY,
                  [ReportType.INTERNAL], False),
    ReportContent("occupancy-insights", "Key Occupancy Insights", ContentCategory.OCCUPANCY,
                  [ReportType.PERFORMANCE, ReportType.INTERNAL], False),
    ReportContent("schedule-adjustments", "Recommended Schedule Adjustments", ContentCategory.OCCUPANCY,
                  [ReportType.INTERNAL], False),

    # Consumable & Waste Management
    ReportContent("critical-consumables", "Critical Consumables Needing Attention", ContentCategory.CONSUMABLE_WASTE,
                  [ReportType.INTERNAL], False),
    ReportContent("waste-issues", "Critical Waste Issues", ContentCategory.CONSUMABLE_WASTE,
                  [ReportType.INTERNAL], False),
    ReportContent("waste-trends", "Waste Analytics & Trends", ContentCategory.CONSUMABLE_WASTE,
                  [ReportType.PERFORMANCE, ReportType.INTERNAL], False),
    ReportContent("sustainability-metrics", "Sustainability Metrics", ContentCategory.CONSUMABLE_WASTE,
                  [ReportType.PERFORMANCE], False),

    # Task Management
    ReportContent("inspection-summary", "Inspection Summary & Scores", ContentCategory.TASK_MANAGEMENT,
                  [ReportType.CLIENT, ReportType.PERFORMANCE, ReportType.INTERNAL], True),
    ReportContent("work-orders", "Work Orders Analysis", ContentCategory.TASK_MANAGEMENT,
                  [ReportType.PERFORMANCE, ReportType.INTERNAL], False),
    ReportContent("frequency-compliance", "Frequency Management Compliance", ContentCategory.TASK_MANAGEMENT,
                  [ReportType.PERFORMANCE, ReportType.INTERNAL], False),
    ReportContent("sla-compliance", "SLA Compliance Overview", ContentCategory.TASK_MANAGEMENT,
                  [ReportType.CLIENT], False),
    ReportContent("task-optimization", "Task Optimization Opportunities", ContentCategory.TASK_MANAGEMENT,
                  [ReportType.INTERNAL], False),

    # Autonomous Equipment
    ReportContent("robot-performance", "Performance Analysis (Uptime/Downtime)", ContentCategory.AUTONOMOUS_EQUIPMENT,
                  [ReportType.PERFORMANCE, ReportType.INTERNAL], False),
    ReportContent("cost-comparison", "Cost Analysis (Manual vs Autonomous)", ContentCategory.AUTONOMOUS_EQUIPMENT,
                  [ReportType.INTERNAL], False),
    ReportContent("robot-efficiency", "Efficiency Metrics", ContentCategory.AUTONOMOUS_EQUIPMENT,
                  [ReportType.PERFORMANCE, ReportType.INTERNAL], False),

    # Financial
    ReportContent("cost-savings", "Cost Savings Achieved", ContentCategory.FINANCIAL,
                  [ReportType.CLIENT], False),
    ReportContent("value-delivered", "Value Delivered Summary", ContentCategory.FINANCIAL,
                  [ReportType.CLIENT], False),
    ReportContent("budget-performance", "Budget vs Actual Performance", ContentCategory.FINANCIAL,
                  [ReportType.CLIENT], False),
]


def get_content_by_report_type(report_type: ReportType) -> List[ReportContent]:
    """Get all content items available for a specific report type"""
    return [content for content in REPORT_CONTENT_CATALOG
            if report_type in content.allowed_report_types]


def get_default_content(report_type: ReportType) -> List[str]:
    """Get default enabled content IDs for a report type"""
    return [content.id for content in REPORT_CONTENT_CATALOG
            if report_type in content.allowed_report_types and content.enabled_by_default]