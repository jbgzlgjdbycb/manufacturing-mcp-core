"""Manufacturing MCP Protocol Core Implementation
制造业专用的MCP协议实现

Features:
- Unified protocol for AI Agents to interact with manufacturing systems
- Real-time capacity pool management
- Intelligent routing and load balancing
- Support for multiple industrial protocols
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
import asyncio
import json
import time
import logging
from datetime import datetime

from pydantic import BaseModel, Field, validator


class ProductType(str, Enum):
    """产品类型枚举"""
    TSHIRT = "t_shirt"
    SWEATSHIRT = "sweatshirt"
    PANTS = "pants"
    JACKET = "jacket"
    CUSTOM = "custom"


class ToolDefinition(BaseModel):
    """MCP工具定义"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    
    class Config:
        arbitrary_types_allowed = True


class ManufacturingTool(BaseModel):
    """制造业工具基类"""
    tool_type: str
    factory_id: str
    capabilities: List[str] = Field(default_factory=list)
    
    @classmethod
    def create_capacity_query_tool(cls, factory_id: str) -> ToolDefinition:
        """创建产能查询工具"""
        return ToolDefinition(
            name=f"query_capacity_{factory_id}",
            description=f"查询工厂{factory_id}的可用产能",
            input_schema={
                "type": "object",
                "properties": {
                    "product_type": {
                        "type": "string",
                        "enum": [pt.value for pt in ProductType]
                    },
                    "date_range": {
                        "type": "object",
                        "properties": {
                            "start": {"type": "string", "format": "date"},
                            "end": {"type": "string", "format": "date"}
                        }
                    },
                    "min_quantity": {"type": "integer", "minimum": 1}
                },
                "required": ["product_type"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "available_capacity": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "production_line": {"type": "string"},
                                "available_slots": {"type": "array"},
                                "max_daily_output": {"type": "integer"}
                            }
                        }
                    },
                    "total_available": {"type": "integer"},
                    "utilization_rate": {"type": "number"}
                }
            }
        )
    
    @classmethod
    def create_order_tool(cls, factory_id: str) -> ToolDefinition:
        """创建订单工具"""
        return ToolDefinition(
            name=f"create_order_{factory_id}",
            description=f"在工厂{factory_id}创建生产订单",
            input_schema={
                "type": "object",
                "properties": {
                    "product_type": {"type": "string"},
                    "specifications": {
                        "type": "object",
                        "properties": {
                            "size": {"type": "array", "items": {"type": "string"}},
                            "color": {"type": "string"},
                            "material": {"type": "string"},
                            "design_url": {"type": "string", "format": "uri"}
                        }
                    },
                    "quantity": {"type": "integer", "minimum": 1},
                    "delivery_date": {"type": "string", "format": "date"},
                    "special_requirements": {"type": "string"}
                },
                "required": ["product_type", "quantity", "delivery_date"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "estimated_cost": {"type": "number"},
                    "production_schedule": {
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string", "format": "date"},
                            "completion_date": {"type": "string", "format": "date"}
                        }
                    }
                }
            }
        )


@dataclass
class FactoryNode:
    """工厂节点信息"""
    factory_id: str
    name: str
    location: str
    capabilities: List[str]
    status: str = "online"  # online, offline, busy
    last_heartbeat: float = None
    load_score: float = 0.0  # 负载评分
    
    def __post_init__(self):
        if self.last_heartbeat is None:
            self.last_heartbeat = time.time()


class MCPCluster:
    """MCP集群管理"""
    
    def __init__(self):
        self.nodes: Dict[str, FactoryNode] = {}
        self.tool_registry: Dict[str, List[str]] = {}  # tool_name -> [factory_ids]
        self.capacity_pool = {}
        
    def register_factory(self, node: FactoryNode) -> bool:
        """注册工厂节点"""
        if node.factory_id in self.nodes:
            return False
        
        self.nodes[node.factory_id] = node
        
        # 注册工厂的工具
        for capability in node.capabilities:
            tool_name = f"{capability}_{node.factory_id}"
            if tool_name not in self.tool_registry:
                self.tool_registry[tool_name] = []
            self.tool_registry[tool_name].append(node.factory_id)
            
        # 更新产能池
        self._update_capacity_pool(node)
        
        return True
    
    def unregister_factory(self, factory_id: str) -> bool:
        """注销工厂节点"""
        if factory_id not in self.nodes:
            return False
        
        # 从工具注册表中移除
        for tool_name, factory_ids in list(self.tool_registry.items()):
            if factory_id in factory_ids:
                factory_ids.remove(factory_id)
                if not factory_ids:
                    del self.tool_registry[tool_name]
        
        # 从节点中移除
        del self.nodes[factory_id]
        
        # 从产能池中移除
        if factory_id in self.capacity_pool:
            del self.capacity_pool[factory_id]
        
        return True
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """获取所有可用工具"""
        tools = []
        for tool_name, factory_ids in self.tool_registry.items():
            if factory_ids:  # 只返回有可用工厂的工具
                tools.append({
                    "name": tool_name,
                    "description": f"Available at {len(factory_ids)} factories",
                    "factory_count": len(factory_ids)
                })
        return tools
    
    def route_to_best_factory(self, tool_name: str) -> Optional[str]:
        """路由到最优工厂"""
        if tool_name not in self.tool_registry:
            return None
        
        available_factories = []
        for factory_id in self.tool_registry[tool_name]:
            node = self.nodes.get(factory_id)
            if node and node.status == "online":
                available_factories.append((node.load_score, factory_id))
        
        if not available_factories:
            return None
        
        # 选择负载最低的工厂
        available_factories.sort(key=lambda x: x[0])
        best_factory_id = available_factories[0][1]
        
        # 更新负载评分
        if best_factory_id in self.nodes:
            self.nodes[best_factory_id].load_score += 0.1
        
        return best_factory_id
    
    def get_global_capacity_view(self) -> Dict[str, Any]:
        """获取全局产能视图"""
        total_available = 0
        capacity_by_product = {}
        
        for factory_id, capacity_data in self.capacity_pool.items():
            for product_type, capacity in capacity_data.items():
                if product_type not in capacity_by_product:
                    capacity_by_product[product_type] = 0
                capacity_by_product[product_type] += capacity
                total_available += capacity
        
        return {
            "total_available_capacity": total_available,
            "capacity_by_product": capacity_by_product,
            "factory_count": len(self.nodes),
            "online_factories": len([n for n in self.nodes.values() if n.status == "online"])
        }
    
    def _update_capacity_pool(self, node: FactoryNode):
        """更新产能池（模拟）"""
        # 在实际实现中，这会从工厂的实时数据中获取
        # 这里使用模拟数据
        self.capacity_pool[node.factory_id] = {
            "t_shirt": 10000,  # 每天最多生产10000件T恤
            "sweatshirt": 5000,
            "pants": 8000,
            "jacket": 3000
        }