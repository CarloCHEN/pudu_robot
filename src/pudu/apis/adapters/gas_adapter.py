"""
高斯API适配器
将gas_api.py的类方法调用适配到统一接口
"""

from typing import Dict, List, Optional, Any
from ..core.api_interface import RobotAPIInterface
from ..gas_api import GaussianRobotAPI, create_gaussian_api_client


API_NAME = "gas"


class GasAdapter(RobotAPIInterface):
    """高斯API适配器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        # 创建高斯API客户端
        self.client = create_gaussian_api_client(
            base_url=self.config.get('base_url', 'https://openapi.gs-robot.com'),
            client_id=self.config.get('client_id', 'muryFD4sL4XsVanqsHwX'),
            client_secret=self.config.get('client_secret', 'sWYjrp0D9X7gnkHLP727SeR5lJ1MFbUpOIumN6rt6tHwExvOOJk'),
            open_access_key=self.config.get('open_access_key', '5d810a147b55ca9978afa82819b9625d')
        )
    
    def get_robot_details(self, sn: str) -> Dict[str, Any]:
        """获取机器人详细信息 - 适配为get_robot_status"""
        return self.client.get_robot_status(sn)
    
    def get_robot_status(self, sn: str) -> Dict[str, Any]:
        return self.client.get_robot_status(sn)
    
    def get_list_stores(self, limit: Optional[int] = None, offset: Optional[int] = None) -> Dict[str, Any]:
        """获取门店列表 - 高斯API没有直接的门店概念，返回机器人列表"""
        # 高斯API没有门店概念，这里返回一个模拟的门店列表
        # 实际使用时可能需要根据具体业务需求调整
        robots_response = self.client.list_robots(page=1, page_size=limit or 10)
        robots = robots_response.get('data', {}).get('list', [])
        
        # 模拟门店数据结构
        stores = []
        for robot in robots:
            store_id = robot.get('serial_number', '')[:8]  # 使用序列号前8位作为门店ID
            store_name = f"Store_{store_id}"
            
            # 避免重复
            if not any(s['shop_id'] == store_id for s in stores):
                stores.append({
                    'shop_id': store_id,
                    'shop_name': store_name
                })
        
        return {
            'list': stores,
            'total': len(stores)
        }
    
    def get_list_robots(self, shop_id: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Dict[str, Any]:
        """获取机器人列表"""
        page = (offset // (limit or 10)) + 1 if offset else 1
        page_size = limit or 10
        
        response = self.client.list_robots(page=page, page_size=page_size)
        robots_data = response.get('data', {}).get('list', [])
        
        # 转换为普渡API格式
        robots = []
        for robot in robots_data:
            robots.append({
                'sn': robot.get('serial_number', ''),
                'nickname': robot.get('name', ''),
                'product_code': robot.get('model', ''),
                'shop_id': shop_id or 'default_shop'
            })
        
        return {
            'list': robots,
            'total': response.get('data', {}).get('total', len(robots))
        }
    
    def get_robot_overview_data(self, start_time: str, end_time: str, shop_id: Optional[str] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        """获取机器人概览数据 - 高斯API可能没有直接对应的方法"""
        # 这里需要根据高斯API的实际能力来实现
        # 暂时返回空数据结构
        return {
            'list': [],
            'total': 0
        }
    
    def get_robot_overview_operation_data(self, start_time: str, end_time: str, shop_id: Optional[str] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        """获取机器人操作概览数据"""
        return {
            'list': [],
            'total': 0
        }
    
    def get_store_overview_data(self, start_time: str, end_time: str, shop_id: Optional[str] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        """获取门店概览数据"""
        return {
            'list': [],
            'total': 0
        }
    
    def get_store_analytics(self, start_time: str, end_time: str, shop_id: Optional[str] = None, time_unit: Optional[str] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        """获取门店分析数据"""
        return {
            'list': [],
            'total': 0
        }
    
    def get_store_analytics_list(self, start_time: str, end_time: str, shop_id: Optional[str] = None, time_unit: Optional[str] = None, offset: Optional[int] = None, limit: Optional[int] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        """获取门店分析数据列表"""
        return {
            'list': [],
            'total': 0
        }
    
    def get_machine_run_analytics(self, start_time: str, end_time: str, shop_id: Optional[str] = None, time_unit: Optional[str] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        """获取机器运行分析数据"""
        return {
            'list': [],
            'total': 0
        }
    
    def get_machine_run_analytics_list(self, start_time: str, end_time: str, shop_id: Optional[str] = None, time_unit: Optional[str] = None, offset: Optional[int] = None, limit: Optional[int] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        """获取机器运行分析数据列表"""
        return {
            'list': [],
            'total': 0
        }
    
    def get_log_list(self, start_time: str, end_time: str, shop_id: Optional[str] = None, offset: Optional[int] = None, limit: Optional[int] = None, check_step: Optional[int] = None, is_success: Optional[bool] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        """获取日志列表"""
        return {
            'list': [],
            'total': 0
        }
    
    def get_event_list(self, start_time: str, end_time: str, shop_id: Optional[str] = None, offset: Optional[int] = None, limit: Optional[int] = None, error_levels: Optional[List[int]] = None, error_types: Optional[List[str]] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        """获取事件列表"""
        return {
            'list': [],
            'total': 0
        }
    
    def get_charging_record_list(self, start_time: str, end_time: str, shop_id: Optional[str] = None, offset: Optional[int] = None, limit: Optional[int] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        """获取充电记录列表"""
        return {
            'list': [],
            'total': 0
        }
    
    def get_battery_health_list(self, start_time: str, end_time: str, shop_id: Optional[str] = None, sn: Optional[str] = None, offset: Optional[int] = None, limit: Optional[int] = None, timezone_offset: int = 0) -> Dict[str, Any]:
        """获取电池健康列表"""
        return {
            'list': [],
            'total': 0
        }
    
    def get_task_list(self, shop_id: Optional[str] = None, sn: Optional[str] = None) -> Dict[str, Any]:
        """获取任务列表"""
        if sn:
            # 获取特定机器人的任务
            response = self.client.get_task_reports(sn)
            tasks = response.get('data', {}).get('list', [])
            
            # 转换为普渡API格式
            task_list = []
            for task in tasks:
                task_list.append({
                    'task_id': task.get('id', ''),
                    'sn': sn,
                    'status': task.get('status', ''),
                    'start_time': task.get('start_time', ''),
                    'end_time': task.get('end_time', '')
                })
            
            return {
                'list': task_list,
                'total': len(task_list)
            }
        else:
            return {
                'list': [],
                'total': 0
            }
    
    def get_scheduled_task_list(self, sn: Optional[str] = None) -> Dict[str, Any]:
        """获取计划任务列表"""
        return {
            'list': [],
            'total': 0
        }
    
    def get_cleaning_report_list(self, start_time: str, end_time: str, shop_id: Optional[str] = None, sn: Optional[str] = None, offset: Optional[int] = None, limit: Optional[int] = None, timezone_offset: Optional[int] = None) -> Dict[str, Any]:
        """获取清洁报告列表"""
        if sn:
            # 转换时间格式（假设输入是字符串格式）
            import datetime
            try:
                start_dt = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                start_seconds = int(start_dt.timestamp())
                end_seconds = int(end_dt.timestamp())
            except:
                start_seconds = int(datetime.datetime.now().timestamp()) - 86400  # 默认1天前
                end_seconds = int(datetime.datetime.now().timestamp())
            
            response = self.client.get_cleaning_reports(sn, start_seconds, end_seconds)
            reports = response.get('data', {}).get('list', [])
            
            # 转换为普渡API格式
            report_list = []
            for report in reports:
                report_list.append({
                    'report_id': report.get('id', ''),
                    'sn': sn,
                    'start_time': report.get('start_time', ''),
                    'end_time': report.get('end_time', ''),
                    'area': report.get('area', 0)
                })
            
            return {
                'list': report_list,
                'total': len(report_list)
            }
        else:
            return {
                'list': [],
                'total': 0
            }
    
    def get_cleaning_report_detail(self, start_time: str, end_time: str, sn: str, report_id: str, shop_id: Optional[str] = None, timezone_offset: Optional[int] = None) -> Dict[str, Any]:
        """获取清洁报告详情"""
        # 高斯API可能没有直接的报告详情接口
        # 这里返回基本信息
        return {
            'report_id': report_id,
            'sn': sn,
            'start_time': start_time,
            'end_time': end_time,
            'area': 0
        }
    
    def get_task_schema_analytics(self, start_time: str, end_time: str, shop_id: Optional[str] = None, time_unit: Optional[str] = None, clean_mode: Optional[int] = None, sub_mode: Optional[int] = None, timezone_offset: Optional[int] = None) -> Dict[str, Any]:
        """获取任务模式分析"""
        return {
            'list': [],
            'total': 0
        }
    
    def get_task_schema_analytics_list(self, start_time: str, end_time: str, shop_id: Optional[str] = None, offset: Optional[int] = None, limit: Optional[int] = None, time_unit: Optional[str] = None, group_by: Optional[str] = None, clean_mode: Optional[int] = None, sub_mode: Optional[int] = None, timezone_offset: Optional[int] = None) -> Dict[str, Any]:
        """获取任务模式分析列表"""
        return {
            'list': [],
            'total': 0
        }
    
    def get_task_distribution_schema_analytics(self, start_time: str, end_time: str, shop_id: Optional[str] = None, clean_mode: Optional[int] = None, sub_mode: Optional[int] = None, timezone_offset: Optional[int] = None) -> Dict[str, Any]:
        """获取任务分布模式分析"""
        return {
            'list': [],
            'total': 0
        }
    
    def get_list_maps(self, shop_id: str) -> Dict[str, Any]:
        """获取地图列表"""
        return {
            'list': [],
            'total': 0
        }
    
    def get_map_details(self, shop_id: str, map_name: str, device_width: int, device_height: int) -> Dict[str, Any]:
        """获取地图详情"""
        return {}
    
    def get_robot_current_position(self, shop_id: str, sn: str) -> Dict[str, Any]:
        """获取机器人当前位置"""
        return {}
    
    # ==================== 高仙API独有功能实现 ====================
    
    def batch_get_robot_statuses(self, serial_numbers: List[str]) -> Dict[str, Any]:
        """批量获取机器人状态 - 高仙API独有"""
        return self.client.batch_get_robot_statuses(serial_numbers)
    
    def generate_robot_task_report_png(self, serial_number: str, task_report_id: str, **kwargs) -> Dict[str, Any]:
        """生成机器人任务报告PNG - 高仙API独有"""
        return self.client.generate_robot_task_report_png(serial_number, task_report_id, **kwargs)
    
    def get_map_download_uri(self, serial_number: str, map_id: str) -> Dict[str, Any]:
        """获取地图下载链接 - 高仙API独有"""
        return self.client.get_map_download_uri(serial_number, map_id)
    
    def upload_robot_map(self, serial_number: str, map_file: str) -> Dict[str, Any]:
        """上传机器人地图 - 高仙API独有"""
        return self.client.upload_robot_map(serial_number, map_file)
    
    def get_upload_status(self, serial_number: str, record_id: str) -> Dict[str, Any]:
        """获取上传状态 - 高仙API独有"""
        return self.client.get_upload_status(serial_number, record_id)
    
    def list_robot_commands(self, serial_number: str, page: int = 1, page_size: int = 5, **kwargs) -> Dict[str, Any]:
        """获取机器人命令列表 - 高仙API独有"""
        return self.client.list_robot_commands(serial_number, page, page_size, **kwargs)
    
    def get_robot_command(self, serial_number: str, command_id: str) -> Dict[str, Any]:
        """获取机器人命令详情 - 高仙API独有"""
        return self.client.get_robot_command(serial_number, command_id)
    
    def create_remote_task_command(self, serial_number: str, command_type: str, **kwargs) -> Dict[str, Any]:
        """创建远程任务命令 - 高仙API独有"""
        return self.client.create_remote_task_command(serial_number, command_type, **kwargs)
    
    def create_remote_navigation_command(self, serial_number: str, command_type: str, **kwargs) -> Dict[str, Any]:
        """创建远程导航命令 - 高仙API独有"""
        return self.client.create_remote_navigation_command(serial_number, command_type, **kwargs)


def create_adapter(config: Optional[Dict[str, Any]] = None) -> GasAdapter:
    """创建高斯API适配器实例"""
    return GasAdapter(config)
