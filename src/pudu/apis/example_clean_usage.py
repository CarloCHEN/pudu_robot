#!/usr/bin/env python3
"""
简洁的Factory+Adapter模式使用示例
展示如何通过foxx_api统一接口调用不同机器人类型的API
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from foxx_api import get_robot_status, get_ongoing_tasks_table


def demonstrate_clean_usage():
    """演示简洁的使用方式"""
    print("=== 简洁的Factory+Adapter模式使用示例 ===")
    
    # 1. 普渡机器人调用
    print("\n1. 普渡机器人调用")
    try:
        pudu_status = get_robot_status("robot_001", robot_type="pudu")
        print(f"普渡机器人状态: {pudu_status}")
    except Exception as e:
        print(f"普渡机器人调用失败: {e}")
    
    # 2. 高仙机器人调用
    print("\n2. 高仙机器人调用")
    try:
        gas_status = get_robot_status("robot_001", robot_type="gas")
        print(f"高仙机器人状态: {gas_status}")
    except Exception as e:
        print(f"高仙机器人调用失败: {e}")
    
    # 3. 获取普渡机器人任务表
    print("\n3. 获取普渡机器人任务表")
    try:
        pudu_tasks = get_ongoing_tasks_table(robot_type="pudu")
        print(f"普渡机器人任务数量: {len(pudu_tasks)}")
    except Exception as e:
        print(f"普渡机器人任务表获取失败: {e}")
    
    # 4. 获取高仙机器人任务表
    print("\n4. 获取高仙机器人任务表")
    try:
        gas_tasks = get_ongoing_tasks_table(robot_type="gas")
        print(f"高仙机器人任务数量: {len(gas_tasks)}")
    except Exception as e:
        print(f"高仙机器人任务表获取失败: {e}")


def demonstrate_business_logic():
    """演示业务逻辑中的使用"""
    print("\n=== 业务逻辑中的使用 ===")
    
    def process_robot_request(robot_sn, robot_type):
        """处理机器人请求"""
        print(f"处理 {robot_type} 机器人 {robot_sn} 的请求")
        
        # 获取机器人状态
        status = get_robot_status(robot_sn, robot_type)
        print(f"机器人状态: {status}")
        
        # 获取任务表
        tasks = get_ongoing_tasks_table(robot_sn=robot_sn, robot_type=robot_type)
        print(f"任务数量: {len(tasks)}")
        
        return status, tasks
    
    # 模拟不同的业务请求
    process_robot_request("robot_001", "pudu")
    process_robot_request("robot_002", "gas")


def demonstrate_error_handling():
    """演示错误处理"""
    print("\n=== 错误处理 ===")
    
    def safe_get_robot_status(robot_sn, robot_type):
        """安全的机器人状态获取"""
        try:
            return get_robot_status(robot_sn, robot_type)
        except Exception as e:
            return {"error": f"获取机器人状态失败: {str(e)}"}
    
    # 测试不同的情况
    result1 = safe_get_robot_status("robot_001", "pudu")
    result2 = safe_get_robot_status("robot_001", "gas")
    result3 = safe_get_robot_status("robot_001", "unknown")
    
    print(f"普渡机器人结果: {result1}")
    print(f"高仙机器人结果: {result2}")
    print(f"未知类型结果: {result3}")


def main():
    """主函数"""
    print("简洁的Factory+Adapter模式使用示例")
    print("=" * 50)
    
    # 基本使用
    demonstrate_clean_usage()
    
    # 业务逻辑
    demonstrate_business_logic()
    
    # 错误处理
    demonstrate_error_handling()
    
    print("\n示例完成！")


if __name__ == "__main__":
    main()
