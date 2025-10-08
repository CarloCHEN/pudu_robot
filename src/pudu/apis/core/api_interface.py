"""
统一API接口定义
定义所有机器人API需要实现的标准接口
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any


class RobotAPIInterface(ABC):
    """机器人API统一接口"""

    # ==================== 核心接口（所有API必须实现） ====================

    @abstractmethod
    def get_robot_details(self, sn: str) -> Dict[str, Any]:
        """获取机器人详细信息"""
        pass

    @abstractmethod
    def get_robot_status(self, sn: str) -> Dict[str, Any]:
        """获取机器人状态"""
        pass

    @abstractmethod
    def get_list_robots(self, shop_id: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Dict[str, Any]:
        """获取机器人列表"""
        pass

    # ==================== 可选接口（API可能不支持） ====================

    def get_list_stores(self, limit: Optional[int] = None, offset: Optional[int] = None) -> Dict[str, Any]:
        """获取门店列表 - 可选接口"""
        return self._not_supported_response("get_list_stores")

    def get_robot_overview_data(self, start_time: str, end_time: str, shop_id: Optional[str] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        """获取机器人概览数据 - 可选接口"""
        return self._not_supported_response("get_robot_overview_data")

    def get_robot_overview_operation_data(self, start_time: str, end_time: str, shop_id: Optional[str] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        """获取机器人操作概览数据 - 可选接口"""
        return self._not_supported_response("get_robot_overview_operation_data")

    def get_store_overview_data(self, start_time: str, end_time: str, shop_id: Optional[str] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        """获取门店概览数据 - 可选接口"""
        return self._not_supported_response("get_store_overview_data")

    def get_store_analytics(self, start_time: str, end_time: str, shop_id: Optional[str] = None, time_unit: Optional[str] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        """获取门店分析数据 - 可选接口"""
        return self._not_supported_response("get_store_analytics")

    def get_store_analytics_list(self, start_time: str, end_time: str, shop_id: Optional[str] = None, time_unit: Optional[str] = None, offset: Optional[int] = None, limit: Optional[int] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        """获取门店分析数据列表 - 可选接口"""
        return self._not_supported_response("get_store_analytics_list")

    def get_machine_run_analytics(self, start_time: str, end_time: str, shop_id: Optional[str] = None, time_unit: Optional[str] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        """获取机器运行分析数据 - 可选接口"""
        return self._not_supported_response("get_machine_run_analytics")

    def get_machine_run_analytics_list(self, start_time: str, end_time: str, shop_id: Optional[str] = None, time_unit: Optional[str] = None, offset: Optional[int] = None, limit: Optional[int] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        """获取机器运行分析数据列表 - 可选接口"""
        return self._not_supported_response("get_machine_run_analytics_list")

    def get_log_list(self, start_time: str, end_time: str, shop_id: Optional[str] = None, offset: Optional[int] = None, limit: Optional[int] = None, check_step: Optional[int] = None, is_success: Optional[bool] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        """获取日志列表 - 可选接口"""
        return self._not_supported_response("get_log_list")

    def get_event_list(self, start_time: str, end_time: str, shop_id: Optional[str] = None, offset: Optional[int] = None, limit: Optional[int] = None, error_levels: Optional[List[int]] = None, error_types: Optional[List[str]] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        """获取事件列表 - 可选接口"""
        return self._not_supported_response("get_event_list")

    def get_charging_record_list(self, start_time: str, end_time: str, shop_id: Optional[str] = None, offset: Optional[int] = None, limit: Optional[int] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        """获取充电记录列表 - 可选接口"""
        return self._not_supported_response("get_charging_record_list")

    def get_battery_health_list(self, start_time: str, end_time: str, shop_id: Optional[str] = None, sn: Optional[str] = None, offset: Optional[int] = None, limit: Optional[int] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        """获取电池健康列表 - 可选接口"""
        return self._not_supported_response("get_battery_health_list")

    def get_task_list(self, shop_id: Optional[str] = None, sn: Optional[str] = None) -> Dict[str, Any]:
        """获取任务列表 - 可选接口"""
        return self._not_supported_response("get_task_list")

    def get_scheduled_task_list(self, sn: Optional[str] = None) -> Dict[str, Any]:
        """获取计划任务列表 - 可选接口"""
        return self._not_supported_response("get_scheduled_task_list")

    def get_cleaning_report_list(self, start_time: str, end_time: str, shop_id: Optional[str] = None, sn: Optional[str] = None, offset: Optional[int] = None, limit: Optional[int] = None, timezone_offset: Optional[int] = None) -> Dict[str, Any]:
        """获取清洁报告列表 - 可选接口"""
        return self._not_supported_response("get_cleaning_report_list")

    def get_cleaning_report_detail(self, start_time: str, end_time: str, sn: str, report_id: str, shop_id: Optional[str] = None, timezone_offset: Optional[int] = None) -> Dict[str, Any]:
        """获取清洁报告详情 - 可选接口"""
        return self._not_supported_response("get_cleaning_report_detail")

    def get_task_schema_analytics(self, start_time: str, end_time: str, shop_id: Optional[str] = None, time_unit: Optional[str] = None, clean_mode: Optional[int] = None, sub_mode: Optional[int] = None, timezone_offset: Optional[int] = None) -> Dict[str, Any]:
        """获取任务模式分析 - 可选接口"""
        return self._not_supported_response("get_task_schema_analytics")

    def get_task_schema_analytics_list(self, start_time: str, end_time: str, shop_id: Optional[str] = None, offset: Optional[int] = None, limit: Optional[int] = None, time_unit: Optional[str] = None, group_by: Optional[str] = None, clean_mode: Optional[int] = None, sub_mode: Optional[int] = None, timezone_offset: Optional[int] = None) -> Dict[str, Any]:
        """获取任务模式分析列表 - 可选接口"""
        return self._not_supported_response("get_task_schema_analytics_list")

    def get_task_distribution_schema_analytics(self, start_time: str, end_time: str, shop_id: Optional[str] = None, clean_mode: Optional[int] = None, sub_mode: Optional[int] = None, timezone_offset: Optional[int] = None) -> Dict[str, Any]:
        """获取任务分布模式分析 - 可选接口"""
        return self._not_supported_response("get_task_distribution_schema_analytics")

    def get_list_maps(self, shop_id: str) -> Dict[str, Any]:
        """获取地图列表 - 可选接口"""
        return self._not_supported_response("get_list_maps")

    def get_map_details(self, shop_id: str, map_name: str, device_width: int, device_height: int) -> Dict[str, Any]:
        """获取地图详情 - 可选接口"""
        return self._not_supported_response("get_map_details")

    def get_robot_current_position(self, shop_id: str, sn: str) -> Dict[str, Any]:
        """获取机器人当前位置 - 可选接口"""
        return self._not_supported_response("get_robot_current_position")

    # ==================== 高仙API独有功能 ====================

    def batch_get_robot_statuses(self, serial_numbers: List[str]) -> Dict[str, Any]:
        """批量获取机器人状态 - 高仙API独有"""
        return self._not_supported_response("batch_get_robot_statuses")

    def generate_robot_task_report_png(self, serial_number: str, task_report_id: str, **kwargs) -> Dict[str, Any]:
        """生成机器人任务报告PNG - 高仙API独有"""
        return self._not_supported_response("generate_robot_task_report_png")

    def get_map_download_uri(self, serial_number: str, map_id: str) -> Dict[str, Any]:
        """获取地图下载链接 - 高仙API独有"""
        return self._not_supported_response("get_map_download_uri")

    def upload_robot_map(self, serial_number: str, map_file: str) -> Dict[str, Any]:
        """上传机器人地图 - 高仙API独有"""
        return self._not_supported_response("upload_robot_map")

    def get_upload_status(self, serial_number: str, record_id: str) -> Dict[str, Any]:
        """获取上传状态 - 高仙API独有"""
        return self._not_supported_response("get_upload_status")

    def list_robot_commands(self, serial_number: str, page: int = 1, page_size: int = 5, **kwargs) -> Dict[str, Any]:
        """获取机器人命令列表 - 高仙API独有"""
        return self._not_supported_response("list_robot_commands")

    def get_robot_command(self, serial_number: str, command_id: str) -> Dict[str, Any]:
        """获取机器人命令详情 - 高仙API独有"""
        return self._not_supported_response("get_robot_command")

    def create_remote_task_command(self, serial_number: str, command_type: str, **kwargs) -> Dict[str, Any]:
        """创建远程任务命令 - 高仙API独有"""
        return self._not_supported_response("create_remote_task_command")

    def create_remote_navigation_command(self, serial_number: str, command_type: str, **kwargs) -> Dict[str, Any]:
        """创建远程导航命令 - 高仙API独有"""
        return self._not_supported_response("create_remote_navigation_command")

    # ==================== 普渡API独有功能 ====================

    def get_robot_overview_operation_data(self, start_time: str, end_time: str, shop_id: Optional[str] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        """获取机器人操作概览数据 - 普渡API独有"""
        return self._not_supported_response("get_robot_overview_operation_data")

    def get_store_overview_data(self, start_time: str, end_time: str, shop_id: Optional[str] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        """获取门店概览数据 - 普渡API独有"""
        return self._not_supported_response("get_store_overview_data")

    def get_store_analytics(self, start_time: str, end_time: str, shop_id: Optional[str] = None, time_unit: Optional[str] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        """获取门店分析数据 - 普渡API独有"""
        return self._not_supported_response("get_store_analytics")

    def get_store_analytics_list(self, start_time: str, end_time: str, shop_id: Optional[str] = None, time_unit: Optional[str] = None, offset: Optional[int] = None, limit: Optional[int] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        """获取门店分析数据列表 - 普渡API独有"""
        return self._not_supported_response("get_store_analytics_list")

    def get_machine_run_analytics(self, start_time: str, end_time: str, shop_id: Optional[str] = None, time_unit: Optional[str] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        """获取机器运行分析数据 - 普渡API独有"""
        return self._not_supported_response("get_machine_run_analytics")

    def get_machine_run_analytics_list(self, start_time: str, end_time: str, shop_id: Optional[str] = None, time_unit: Optional[str] = None, offset: Optional[int] = None, limit: Optional[int] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        """获取机器运行分析数据列表 - 普渡API独有"""
        return self._not_supported_response("get_machine_run_analytics_list")

    def get_battery_health_list(self, start_time: str, end_time: str, shop_id: Optional[str] = None, sn: Optional[str] = None, offset: Optional[int] = None, limit: Optional[int] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        """获取电池健康列表 - 普渡API独有"""
        return self._not_supported_response("get_battery_health_list")

    def get_task_schema_analytics(self, start_time: str, end_time: str, shop_id: Optional[str] = None, time_unit: Optional[str] = None, clean_mode: Optional[int] = None, sub_mode: Optional[int] = None, timezone_offset: Optional[int] = None) -> Dict[str, Any]:
        """获取任务模式分析 - 普渡API独有"""
        return self._not_supported_response("get_task_schema_analytics")

    def get_task_schema_analytics_list(self, start_time: str, end_time: str, shop_id: Optional[str] = None, offset: Optional[int] = None, limit: Optional[int] = None, time_unit: Optional[str] = None, group_by: Optional[str] = None, clean_mode: Optional[int] = None, sub_mode: Optional[int] = None, timezone_offset: Optional[int] = None) -> Dict[str, Any]:
        """获取任务模式分析列表 - 普渡API独有"""
        return self._not_supported_response("get_task_schema_analytics_list")

    def get_task_distribution_schema_analytics(self, start_time: str, end_time: str, shop_id: Optional[str] = None, clean_mode: Optional[int] = None, sub_mode: Optional[int] = None, timezone_offset: Optional[int] = None) -> Dict[str, Any]:
        """获取任务分布模式分析 - 普渡API独有"""
        return self._not_supported_response("get_task_distribution_schema_analytics")

    # ==================== 辅助方法 ====================

    def _not_supported_response(self, method_name: str) -> Dict[str, Any]:
        """返回不支持的方法响应"""
        return {
            "error": f"Method {method_name} not supported by this API",
            "supported": False,
            "list": [],
            "total": 0
        }

    def is_method_supported(self, method_name: str) -> bool:
        """检查方法是否被支持"""
        # 检查方法是否被重写（不是默认的_not_supported_response实现）
        method = getattr(self, method_name)
        return method.__func__ != RobotAPIInterface.__dict__[method_name].__func__

    def get_supported_methods(self) -> List[str]:
        """获取支持的方法列表"""
        supported = []
        for method_name in dir(self):
            if method_name.startswith('get_') or method_name.startswith('list_') or method_name.startswith('create_') or method_name.startswith('batch_'):
                if self.is_method_supported(method_name):
                    supported.append(method_name)
        return supported