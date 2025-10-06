# 机器人API统一框架

## 概述

这是一个简洁的Factory+Adapter模式实现，用于统一管理普渡API和高仙API。通过统一的接口，业务代码可以根据机器人类型自动选择对应的API。

## 核心特性

- **统一接口**：通过foxx_api提供统一的服务接口
- **类型驱动**：根据robot_type参数自动选择API
- **简洁架构**：Factory+Adapter模式，层次清晰
- **易于扩展**：新增机器人类型只需添加适配器
- **向后兼容**：保持原有API不变
- **配置管理**：通过配置文件管理API设置

## 架构设计

### 简洁的Factory+Adapter模式

```
apis/
├── core/                           # 工厂层
│   ├── __init__.py
│   ├── api_interface.py           # 统一API接口定义
│   ├── api_registry.py            # API注册中心
│   ├── api_factory.py             # API工厂
│   └── config_manager.py          # 配置管理器
├── adapters/                       # 适配器层
│   ├── __init__.py
│   ├── pudu_adapter.py            # 普渡API适配器
│   └── gas_adapter.py             # 高仙API适配器
├── configs/                        # 配置层
│   ├── api_config.yaml            # API配置
│   └── api_mapping.yaml           # API映射配置
├── pudu_api.py                    # 普渡API基础库
├── gas_api.py                     # 高仙API基础库
├── utils.py                       # 工具函数
└── foxx_api.py                    # 统一对外服务接口
```

### 架构层次

1. **基础API库层**：`pudu_api.py`, `gas_api.py` - 原始API实现
2. **适配器层**：`adapters/` - 将不同API适配到统一接口
3. **工厂层**：`core/` - 根据机器人类型创建对应API实例
4. **服务层**：`foxx_api.py` - 对外提供统一接口
5. **配置层**：`configs/` - 管理API配置和映射

## 核心组件

### 1. 基础API库
- **pudu_api.py**: 普渡API的原始实现
- **gas_api.py**: 高仙API的原始实现

### 2. 适配器层
- **pudu_adapter.py**: 将普渡API适配到统一接口
- **gas_adapter.py**: 将高仙API适配到统一接口

### 3. 工厂层
- **api_factory.py**: 根据机器人类型创建API实例
- **api_interface.py**: 定义统一的API接口
- **api_registry.py**: 管理适配器注册
- **config_manager.py**: 管理配置

### 4. 服务层
- **foxx_api.py**: 对外提供统一的服务接口

### 5. 配置层
- **api_config.yaml**: API配置
- **api_mapping.yaml**: API方法映射

## 使用方法

### 推荐使用方式（通过foxx_api）

```python
# 导入统一接口
from foxx_api import get_robot_status, get_ongoing_tasks_table

# 普渡机器人
pudu_status = get_robot_status("robot_001", robot_type="pudu")

# 高仙机器人
gas_status = get_robot_status("robot_001", robot_type="gas")

# 获取任务表
pudu_tasks = get_ongoing_tasks_table(robot_type="pudu")
gas_tasks = get_ongoing_tasks_table(robot_type="gas")
```

### 高级使用方式（直接使用API工厂）

```python
from core.api_factory import APIFactory

# 获取API工厂实例
api_factory = APIFactory()

# 获取不同机器人类型的API实例
pudu_api = api_factory.create_api("pudu")
gas_api = api_factory.create_api("gas")

# 使用普渡API
robot_details = pudu_api.get_robot_details("robot_001")

# 使用高仙API
robot_status = gas_api.get_robot_status("robot_001")
```

## 配置文件

### API配置 (configs/api_config.yaml)

```yaml
default_api: "pudu"

apis:
  pudu:
    enabled: true
    priority: 1
    config:
      base_url: "https://api.pudu.com"
      
  gas:
    enabled: true
    priority: 2
    config:
      base_url: "https://openapi.gs-robot.com"
      client_id: "your_client_id"
      client_secret: "your_client_secret"
      open_access_key: "your_access_key"
```

### API映射配置 (configs/api_mapping.yaml)

```yaml
function_mapping:
  get_robot_details:
    pudu: "get_robot_details"
    gas: "get_robot_status"
    
  get_list_stores:
    pudu: "get_list_stores"
    gas: "list_robots"  # 高仙API没有门店概念，使用机器人列表
```

## 扩展指南

### 添加新的机器人类型

1. 在`adapters/`目录下添加新的适配器
2. 在`configs/api_config.yaml`中添加配置
3. 在`core/api_registry.py`中注册适配器
4. 业务代码中指定新的`robot_type`

### 添加新的API方法

1. 在`core/api_interface.py`中添加方法定义
2. 在各个适配器中实现该方法
3. 在`foxx_api.py`中添加对应的服务方法

## 示例代码

### 业务代码中的使用

```python
# 导入统一接口
from foxx_api import get_robot_status, get_ongoing_tasks_table

def process_robot_request(robot_sn, robot_type):
    """处理机器人请求"""
    # 获取机器人状态
    status = get_robot_status(robot_sn, robot_type)
    
    # 获取任务表
    tasks = get_ongoing_tasks_table(robot_sn=robot_sn, robot_type=robot_type)
    
    return status, tasks

# 使用示例
pudu_status, pudu_tasks = process_robot_request("robot_001", "pudu")
gas_status, gas_tasks = process_robot_request("robot_001", "gas")
```

## 总结

这个简洁的Factory+Adapter模式架构提供了：

- **统一接口**：通过foxx_api提供统一的服务接口
- **类型驱动**：根据robot_type参数自动选择API
- **简洁架构**：Factory+Adapter模式，层次清晰
- **易于扩展**：新增机器人类型只需添加适配器
- **向后兼容**：保持原有API不变

业务代码只需要指定`robot_type`参数，就能自动使用对应的API，无需关心底层实现细节。