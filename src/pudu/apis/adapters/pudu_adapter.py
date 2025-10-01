"""
普渡API适配器
将pudu_api.py的函数调用适配到统一接口
"""

from typing import Dict, List, Optional, Any
from ..core.api_interface import RobotAPIInterface
from ..pudu_api import *


API_NAME = "pudu"


class PuduAdapter(RobotAPIInterface):
    """普渡API适配器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
    
    def get_robot_details(self, sn: str) -> Dict[str, Any]:
        return get_robot_details(sn)
    
    def get_robot_status(self, sn: str) -> Dict[str, Any]:
        # 普渡API没有直接的get_robot_status，使用get_robot_details
        return get_robot_details(sn)
    
    def get_list_stores(self, limit: Optional[int] = None, offset: Optional[int] = None) -> Dict[str, Any]:
        return get_list_stores(limit=limit, offset=offset)
    
    def get_list_robots(self, shop_id: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Dict[str, Any]:
        return get_list_robots(shop_id=shop_id, limit=limit, offset=offset)
    
    def get_robot_overview_data(self, start_time: str, end_time: str, shop_id: Optional[str] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        return get_robot_overview_data(start_time, end_time, shop_id=shop_id, timezone_offset=timezone_offset)
    
    def get_robot_overview_operation_data(self, start_time: str, end_time: str, shop_id: Optional[str] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        return get_robot_overview_operation_data(start_time, end_time, shop_id=shop_id, timezone_offset=timezone_offset)
    
    def get_store_overview_data(self, start_time: str, end_time: str, shop_id: Optional[str] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        return get_store_overview_data(start_time, end_time, shop_id=shop_id, timezone_offset=timezone_offset)
    
    def get_store_analytics(self, start_time: str, end_time: str, shop_id: Optional[str] = None, time_unit: Optional[str] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        return get_store_analytics(start_time, end_time, shop_id=shop_id, time_unit=time_unit, timezone_offset=timezone_offset)
    
    def get_store_analytics_list(self, start_time: str, end_time: str, shop_id: Optional[str] = None, time_unit: Optional[str] = None, offset: Optional[int] = None, limit: Optional[int] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        return get_store_analytics_list(start_time, end_time, shop_id=shop_id, time_unit=time_unit, offset=offset, limit=limit, timezone_offset=timezone_offset)
    
    def get_machine_run_analytics(self, start_time: str, end_time: str, shop_id: Optional[str] = None, time_unit: Optional[str] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        return get_machine_run_analytics(start_time, end_time, shop_id=shop_id, time_unit=time_unit, timezone_offset=timezone_offset)
    
    def get_machine_run_analytics_list(self, start_time: str, end_time: str, shop_id: Optional[str] = None, time_unit: Optional[str] = None, offset: Optional[int] = None, limit: Optional[int] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        return get_machine_run_analytics_list(start_time, end_time, shop_id=shop_id, time_unit=time_unit, offset=offset, limit=limit, timezone_offset=timezone_offset)
    
    def get_log_list(self, start_time: str, end_time: str, shop_id: Optional[str] = None, offset: Optional[int] = None, limit: Optional[int] = None, check_step: Optional[int] = None, is_success: Optional[bool] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        return get_log_list(start_time, end_time, shop_id=shop_id, offset=offset, limit=limit, check_step=check_step, is_success=is_success, timezone_offset=timezone_offset)
    
    def get_event_list(self, start_time: str, end_time: str, shop_id: Optional[str] = None, offset: Optional[int] = None, limit: Optional[int] = None, error_levels: Optional[List[int]] = None, error_types: Optional[List[str]] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        return get_event_list(start_time, end_time, shop_id=shop_id, offset=offset, limit=limit, error_levels=error_levels, error_types=error_types, timezone_offset=timezone_offset)
    
    def get_charging_record_list(self, start_time: str, end_time: str, shop_id: Optional[str] = None, offset: Optional[int] = None, limit: Optional[int] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        return get_charging_record_list(start_time, end_time, shop_id=shop_id, offset=offset, limit=limit, timezone_offset=timezone_offset)
    
    def get_battery_health_list(self, start_time: str, end_time: str, shop_id: Optional[str] = None, sn: Optional[str] = None, offset: Optional[int] = None, limit: Optional[int] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        return get_battery_health_list(start_time, end_time, shop_id=shop_id, sn=sn, offset=offset, limit=limit, timezone_offset=timezone_offset)
    
    def get_task_list(self, shop_id: Optional[str] = None, sn: Optional[str] = None) -> Dict[str, Any]:
        return get_task_list(shop_id=shop_id, sn=sn)
    
    def get_scheduled_task_list(self, sn: Optional[str] = None) -> Dict[str, Any]:
        return get_scheduled_task_list(sn=sn)
    
    def get_cleaning_report_list(self, start_time: str, end_time: str, shop_id: Optional[str] = None, sn: Optional[str] = None, offset: Optional[int] = None, limit: Optional[int] = None, timezone_offset: Optional[int] = None) -> Dict[str, Any]:
        return get_cleaning_report_list(start_time, end_time, shop_id=shop_id, sn=sn, offset=offset, limit=limit, timezone_offset=timezone_offset)
    
    def get_cleaning_report_detail(self, start_time: str, end_time: str, sn: str, report_id: str, shop_id: Optional[str] = None, timezone_offset: Optional[int] = None) -> Dict[str, Any]:
        return get_cleaning_report_detail(start_time, end_time, sn, report_id, shop_id=shop_id, timezone_offset=timezone_offset)
    
    def get_task_schema_analytics(self, start_time: str, end_time: str, shop_id: Optional[str] = None, time_unit: Optional[str] = None, clean_mode: Optional[int] = None, sub_mode: Optional[int] = None, timezone_offset: Optional[int] = None) -> Dict[str, Any]:
        return get_task_schema_analytics(start_time, end_time, shop_id=shop_id, time_unit=time_unit, clean_mode=clean_mode, sub_mode=sub_mode, timezone_offset=timezone_offset)
    
    def get_task_schema_analytics_list(self, start_time: str, end_time: str, shop_id: Optional[str] = None, offset: Optional[int] = None, limit: Optional[int] = None, time_unit: Optional[str] = None, group_by: Optional[str] = None, clean_mode: Optional[int] = None, sub_mode: Optional[int] = None, timezone_offset: Optional[int] = None) -> Dict[str, Any]:
        return get_task_schema_analytics_list(start_time, end_time, shop_id=shop_id, offset=offset, limit=limit, time_unit=time_unit, group_by=group_by, clean_mode=clean_mode, sub_mode=sub_mode, timezone_offset=timezone_offset)
    
    def get_task_distribution_schema_analytics(self, start_time: str, end_time: str, shop_id: Optional[str] = None, clean_mode: Optional[int] = None, sub_mode: Optional[int] = None, timezone_offset: Optional[int] = None) -> Dict[str, Any]:
        return get_task_distribution_schema_analytics(start_time, end_time, shop_id=shop_id, clean_mode=clean_mode, sub_mode=sub_mode, timezone_offset=timezone_offset)
    
    def get_list_maps(self, shop_id: str) -> Dict[str, Any]:
        return get_list_maps(shop_id)
    
    def get_map_details(self, shop_id: str, map_name: str, device_width: int, device_height: int) -> Dict[str, Any]:
        return get_map_details(shop_id, map_name, device_width, device_height)
    
    def get_robot_current_position(self, shop_id: str, sn: str) -> Dict[str, Any]:
        return get_robot_current_position(shop_id, sn)


def create_adapter(config: Optional[Dict[str, Any]] = None) -> PuduAdapter:
    """创建普渡API适配器实例"""
    return PuduAdapter(config)
