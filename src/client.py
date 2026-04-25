"""
MCP客户端实现
用于连接制造业MCP集群的客户端
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import aiohttp
from enum import Enum

from .protocol import ProductType, ToolDefinition


class MCPClientError(Exception):
    """MCP客户端错误"""
    pass


@dataclass
class CapacitySlot:
    """产能时间段"""
    start_date: str
    end_date: str
    max_quantity: int
    unit_price: float
    lead_time_days: int


@dataclass
class FactoryCapacity:
    """工厂产能信息"""
    factory_id: str
    product_type: str
    available_slots: List[CapacitySlot]
    total_available: int
    utilization_rate: float


class MCPClient:
    """制造业MCP客户端"""
    
    def __init__(self, cluster_url: str, api_key: Optional[str] = None):
        """
        初始化MCP客户端
        
        Args:
            cluster_url: MCP集群URL
            api_key: API密钥（可选）
        """
        self.cluster_url = cluster_url.rstrip('/')
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
        self._tools_cache = {}
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.disconnect()
    
    async def connect(self):
        """连接到MCP集群"""
        if self.session is None:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            self.session = aiohttp.ClientSession(
                base_url=self.cluster_url,
                headers=headers
            )
    
    async def disconnect(self):
        """断开连接"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def list_available_tools(self) -> List[Dict[str, Any]]:
        """列出所有可用工具"""
        await self.connect()
        
        async with self.session.get("/tools") as response:
            if response.status != 200:
                raise MCPClientError(f"Failed to list tools: {response.status}")
            
            return await response.json()
    
    async def query_capacity(
        self,
        product_type: ProductType,
        min_quantity: Optional[int] = None,
        date_range: Optional[Dict[str, str]] = None
    ) -> List[FactoryCapacity]:
        """
        查询可用产能
        
        Args:
            product_type: 产品类型
            min_quantity: 最小数量要求
            date_range: 日期范围 {start: "YYYY-MM-DD", end: "YYYY-MM-DD"}
            
        Returns:
            可用产能列表
        """
        await self.connect()
        
        # 构建查询参数
        query_data = {"product_type": product_type.value}
        if min_quantity:
            query_data["min_quantity"] = min_quantity
        if date_range:
            query_data["date_range"] = date_range
        
        # 查找产能查询工具
        tools = await self.list_available_tools()
        capacity_tools = [
            t for t in tools 
            if t["name"].startswith("query_capacity")
        ]
        
        if not capacity_tools:
            raise MCPClientError("No capacity query tools available")
        
        results = []
        for tool in capacity_tools[:5]:  # 查询前5个工厂
            try:
                async with self.session.post(
                    f"/tools/{tool['name']}",
                    json=query_data
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        results.append(
                            FactoryCapacity(
                                factory_id=tool["name"].replace("query_capacity_", ""),
                                product_type=product_type.value,
                                available_slots=[
                                    CapacitySlot(
                                        start_date=slot["start_date"],
                                        end_date=slot["end_date"],
                                        max_quantity=slot["max_quantity"],
                                        unit_price=slot["unit_price"],
                                        lead_time_days=slot["lead_time_days"]
                                    )
                                    for slot in data.get("available_slots", [])
                                ],
                                total_available=data.get("total_available", 0),
                                utilization_rate=data.get("utilization_rate", 0.0)
                            )
                        )
            except Exception as e:
                print(f"Error querying tool {tool['name']}: {e}")
        
        return results
    
    async def create_order(
        self,
        factory_id: str,
        product_type: ProductType,
        specifications: Dict[str, Any],
        quantity: int,
        delivery_date: str,
        special_requirements: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建生产订单
        
        Args:
            factory_id: 工厂ID
            product_type: 产品类型
            specifications: 规格参数
            quantity: 数量
            delivery_date: 交货日期
            special_requirements: 特殊要求
            
        Returns:
            订单创建结果
        """
        await self.connect()
        
        order_data = {
            "product_type": product_type.value,
            "specifications": specifications,
            "quantity": quantity,
            "delivery_date": delivery_date
        }
        
        if special_requirements:
            order_data["special_requirements"] = special_requirements
        
        tool_name = f"create_order_{factory_id}"
        
        async with self.session.post(
            f"/tools/{tool_name}",
            json=order_data
        ) as response:
            if response.status != 200:
                error_data = await response.json()
                raise MCPClientError(
                    f"Failed to create order: {error_data.get('error', 'Unknown error')}"
                )
            
            return await response.json()
    
    async def get_global_capacity_view(self) -> Dict[str, Any]:
        """获取全局产能视图"""
        await self.connect()
        
        async with self.session.get("/capacity/global") as response:
            if response.status != 200:
                raise MCPClientError(f"Failed to get global capacity: {response.status}")
            
            return await response.json()
    
    async def search_factories(
        self,
        product_types: List[ProductType],
        min_capacity: Optional[int] = None,
        location: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索符合条件的工厂
        
        Args:
            product_types: 支持的产品类型列表
            min_capacity: 最小产能要求
            location: 地理位置（模糊匹配）
            
        Returns:
            工厂列表
        """
        await self.connect()
        
        search_params = {
            "product_types": [pt.value for pt in product_types]
        }
        if min_capacity:
            search_params["min_capacity"] = min_capacity
        if location:
            search_params["location"] = location
        
        async with self.session.get("/factories/search", params=search_params) as response:
            if response.status != 200:
                raise MCPClientError(f"Failed to search factories: {response.status}")
            
            return await response.json()
    
    async def estimate_cost(
        self,
        factory_id: str,
        product_type: ProductType,
        specifications: Dict[str, Any],
        quantity: int
    ) -> Dict[str, Any]:
        """
        估算生产成本
        
        Args:
            factory_id: 工厂ID
            product_type: 产品类型
            specifications: 规格参数
            quantity: 数量
            
        Returns:
            成本估算结果
        """
        # 在实际实现中，这会调用专门的成本估算工具
        # 这里返回模拟数据
        return {
            "factory_id": factory_id,
            "product_type": product_type.value,
            "quantity": quantity,
            "estimated_cost": quantity * 15.5,  # 模拟单价
            "breakdown": {
                "material_cost": quantity * 8.0,
                "labor_cost": quantity * 4.0,
                "overhead": quantity * 2.0,
                "profit_margin": quantity * 1.5
            },
            "currency": "CNY"
        }


class AsyncMCPClient(MCPClient):
    """异步MCP客户端（提供async/await接口）"""
    
    pass  # MCPClient已经是异步的