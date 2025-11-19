# 简洁的Factory+Adapter模式架构

## 架构概述

这是一个简洁的Factory+Adapter模式实现，用于统一管理普渡API和高仙API。

## 架构层次

```
┌─────────────────────────────────────────────────────────────┐
│                    业务层 (Business Layer)                    │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                foxx_api.py                            │ │
│  │           统一对外服务接口                              │ │
│  │  - get_robot_status(sn, robot_type)                  │ │
│  │  - get_ongoing_tasks_table(robot_type)               │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                    工厂层 (Factory Layer)                    │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                core/api_factory.py                    │ │
│  │           根据机器人类型创建API实例                      │ │
│  │  - create_api(robot_type)                             │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                   适配器层 (Adapter Layer)                    │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              adapters/pudu_adapter.py                 │ │
│  │              adapters/gas_adapter.py                  │ │
│  │           将不同API适配到统一接口                        │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                  基础API库层 (Base API Layer)                 │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                pudu_api.py                            │ │
│  │                gas_api.py                             │ │
│  │           原始API实现                                   │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. 基础API库层
- **pudu_api.py**: 普渡API的原始实现
- **gas_api.py**: 高仙API的原始实现

### 2. 适配器层
- **pudu_adapter.py**: 将普渡API适配到统一接口
- **gas_adapter.py**: 将高仙API适配到统一接口

### 3. 工厂层
- **api_factory.py**: 根据机器人类型创建对应的API实例
- **api_interface.py**: 定义统一的API接口
- **api_registry.py**: 管理适配器注册
- **config_manager.py**: 管理配置

### 4. 服务层
- **foxx_api.py**: 对外提供统一的服务接口

## 使用方式

### 业务代码调用

```python
# 导入统一接口
from foxx_api import get_robot_status, get_ongoing_tasks_table

# 普渡机器人
pudu_status = get_robot_status("robot_001", robot_type="pudu")

# 高仙机器人
gas_status = get_robot_status("robot_001", robot_type="gas")
```

### 内部实现

```python
# foxx_api.py 内部实现
def get_robot_status(sn, robot_type="pudu"):
    api = get_robot_api(robot_type)  # 获取对应API实例
    return api.get_robot_details(sn)  # 调用统一接口
```

## 优势

1. **简洁明了**: 架构层次清晰，职责分明
2. **易于扩展**: 新增API只需添加适配器
3. **统一接口**: 业务代码只需调用foxx_api
4. **类型安全**: 通过robot_type明确指定机器人类型
5. **向后兼容**: 保持原有API不变

## 扩展方式

### 添加新的机器人类型

1. 在`adapters/`目录下添加新的适配器
2. 在`configs/api_config.yaml`中添加配置
3. 在`core/api_registry.py`中注册适配器
4. 业务代码中指定新的`robot_type`

### 添加新的API方法

1. 在`core/api_interface.py`中添加方法定义
2. 在各个适配器中实现该方法
3. 在`foxx_api.py`中添加对应的服务方法

## 配置示例

### api_config.yaml
```yaml
apis:
  pudu:
    enabled: true
    priority: 1
    config:
      base_url: "https://api.pudu.com"
      timeout: 30
  
  gas:
    enabled: true
    priority: 2
    config:
      base_url: "https://openapi.gs-robot.com"
      client_id: "your_client_id"
      client_secret: "your_client_secret"
```

## 总结

这个架构设计简洁、清晰，通过Factory+Adapter模式实现了：
- 多机器人类型支持
- 统一的服务接口
- 易于扩展和维护
- 业务代码的简洁性

业务代码只需要指定`robot_type`参数，就能自动使用对应的API，无需关心底层的实现细节。
