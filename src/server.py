"""
MCP服务器实现
制造业MCP协议服务器
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import json
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from .protocol import (
    MCPCluster, FactoryNode, ManufacturingTool, 
    ToolDefinition, ProductType
)


class MCPServer:
    """制造业MCP服务器"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        self.host = host
        self.port = port
        self.cluster = MCPCluster()
        self.app = None
        self.websocket_connections = {}
        
        self._setup_app()
    
    def _setup_app(self):
        """设置FastAPI应用"""
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """应用生命周期管理"""
            # 启动时注册示例工厂
            await self._register_example_factories()
            yield
            # 关闭时清理
            self.websocket_connections.clear()
        
        self.app = FastAPI(
            title="Manufacturing MCP Server",
            description="制造业MCP协议服务器",
            version="0.1.0",
            lifespan=lifespan
        )
        
        # 添加CORS中间件
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self._setup_routes()
    
    def _setup_routes(self):
        """设置路由"""
        
        @self.app.get("/")
        async def root():
            """根端点"""
            return {
                "service": "Manufacturing MCP Server",
                "version": "0.1.0",
                "cluster_status": {
                    "factory_count": len(self.cluster.nodes),
                    "online_factories": len([
                        n for n in self.cluster.nodes.values() 
                        if n.status == "online"
                    ])
                }
            }
        
        @self.app.get("/.well-known/mcp.json")
        async def get_mcp_info():
            """MCP协议信息"""
            return {
                "name": "manufacturing-mcp-server",
                "version": "0.1.0",
                "protocol_version": "2024-10-01",
                "capabilities": {
                    "tools": self.cluster.get_available_tools()
                }
            }
        
        @self.app.get("/tools")
        async def list_tools():
            """列出所有可用工具"""
            return self.cluster.get_available_tools()
        
        @self.app.get("/tools/{tool_name}")
        async def get_tool_info(tool_name: str):
            """获取工具信息"""
            # 在实际实现中，这里会返回工具的具体定义
            return {
                "name": tool_name,
                "description": f"Manufacturing tool: {tool_name}",
                "factory_id": tool_name.split("_")[-1]
            }
        
        @self.app.post("/tools/{tool_name}")
        async def execute_tool(tool_name: str, input_data: Dict[str, Any]):
            """执行工具"""
            # 路由到最佳工厂
            factory_id = self.cluster.route_to_best_factory(tool_name)
            if not factory_id:
                raise HTTPException(
                    status_code=404,
                    detail=f"No available factory for tool: {tool_name}"
                )
            
            # 模拟工具执行
            result = await self._simulate_tool_execution(
                tool_name, factory_id, input_data
            )
            
            return result
        
        @self.app.get("/capacity/global")
        async def get_global_capacity():
            """获取全局产能视图"""
            return self.cluster.get_global_capacity_view()
        
        @self.app.get("/factories")
        async def list_factories():
            """列出所有工厂"""
            factories = []
            for factory_id, node in self.cluster.nodes.items():
                factories.append({
                    "factory_id": factory_id,
                    "name": node.name,
                    "location": node.location,
                    "status": node.status,
                    "capabilities": node.capabilities,
                    "load_score": node.load_score
                })
            return factories
        
        @self.app.get("/factories/search")
        async def search_factories(
            product_types: str,
            min_capacity: Optional[int] = None,
            location: Optional[str] = None
        ):
            """搜索工厂"""
            # 解析产品类型
            product_type_list = product_types.split(",")
            
            results = []
            for factory_id, node in self.cluster.nodes.items():
                if node.status != "online":
                    continue
                
                # 检查产品类型支持
                supported = any(
                    f"query_capacity_{factory_id}" in tool_name
                    for tool_name in self.cluster.tool_registry.keys()
                )
                
                if supported:
                    factory_info = {
                        "factory_id": factory_id,
                        "name": node.name,
                        "location": node.location,
                        "capabilities": node.capabilities,
                        "load_score": node.load_score
                    }
                    
                    # 添加模拟的产能数据
                    if factory_id in self.cluster.capacity_pool:
                        factory_info["capacity"] = self.cluster.capacity_pool[factory_id]
                    
                    results.append(factory_info)
            
            return results
        
        @self.app.post("/factories/register")
        async def register_factory(factory_data: Dict[str, Any]):
            """注册新工厂"""
            node = FactoryNode(
                factory_id=factory_data["factory_id"],
                name=factory_data.get("name", "Unknown Factory"),
                location=factory_data.get("location", "Unknown"),
                capabilities=factory_data.get("capabilities", [])
            )
            
            success = self.cluster.register_factory(node)
            
            if success:
                return {
                    "status": "success",
                    "factory_id": node.factory_id,
                    "message": f"Factory {node.factory_id} registered successfully"
                }
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Factory {node.factory_id} already registered"
                )
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket端点"""
            await websocket.accept()
            
            client_id = id(websocket)
            self.websocket_connections[client_id] = websocket
            
            try:
                # 发送欢迎消息
                await websocket.send_json({
                    "type": "welcome",
                    "message": "Connected to Manufacturing MCP Server",
                    "client_id": client_id
                })
                
                while True:
                    # 接收消息
                    data = await websocket.receive_json()
                    
                    # 处理消息
                    await self._handle_websocket_message(
                        client_id, websocket, data
                    )
                    
            except WebSocketDisconnect:
                # 断开连接
                if client_id in self.websocket_connections:
                    del self.websocket_connections[client_id]
    
    async def _simulate_tool_execution(
        self, 
        tool_name: str, 
        factory_id: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """模拟工具执行"""
        
        if tool_name.startswith("query_capacity"):
            # 产能查询工具
            product_type = input_data.get("product_type", "t_shirt")
            min_quantity = input_data.get("min_quantity", 1)
            
            return {
                "factory_id": factory_id,
                "product_type": product_type,
                "available_slots": [
                    {
                        "start_date": "2024-04-25",
                        "end_date": "2024-04-30",
                        "max_quantity": 5000,
                        "unit_price": 15.5,
                        "lead_time_days": 7
                    },
                    {
                        "start_date": "2024-05-01",
                        "end_date": "2024-05-07",
                        "max_quantity": 3000,
                        "unit_price": 14.8,
                        "lead_time_days": 10
                    }
                ],
                "total_available": 8000,
                "utilization_rate": 0.65
            }
        
        elif tool_name.startswith("create_order"):
            # 订单创建工具
            product_type = input_data.get("product_type", "t_shirt")
            quantity = input_data.get("quantity", 100)
            
            import uuid
            order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
            
            return {
                "status": "success",
                "order_id": order_id,
                "factory_id": factory_id,
                "product_type": product_type,
                "quantity": quantity,
                "estimated_cost": quantity * 15.5,
                "production_schedule": {
                    "start_date": "2024-04-25",
                    "completion_date": "2024-04-30",
                    "quality_check_date": "2024-05-01"
                },
                "next_steps": [
                    "支付30%定金",
                    "确认设计文件",
                    "安排生产排期"
                ]
            }
        
        else:
            return {
                "error": f"Tool {tool_name} not implemented",
                "input_data": input_data
            }
    
    async def _handle_websocket_message(
        self,
        client_id: int,
        websocket: WebSocket,
        data: Dict[str, Any]
    ):
        """处理WebSocket消息"""
        message_type = data.get("type", "unknown")
        
        if message_type == "heartbeat":
            # 心跳
            await websocket.send_json({
                "type": "heartbeat_response",
                "timestamp": asyncio.get_event_loop().time()
            })
        
        elif message_type == "capacity_subscribe":
            # 产能订阅
            product_type = data.get("product_type")
            
            # 模拟实时产能更新
            await websocket.send_json({
                "type": "capacity_update",
                "product_type": product_type,
                "data": self.cluster.get_global_capacity_view()
            })
        
        elif message_type == "order_status_query":
            # 订单状态查询
            order_id = data.get("order_id")
            
            await websocket.send_json({
                "type": "order_status",
                "order_id": order_id,
                "status": "in_production",
                "progress": 0.45,
                "estimated_completion": "2024-04-30"
            })
    
    async def _register_example_factories(self):
        """注册示例工厂"""
        example_factories = [
            FactoryNode(
                factory_id="factory_001",
                name="广州某服装厂",
                location="广州",
                capabilities=["query_capacity", "create_order"]
            ),
            FactoryNode(
                factory_id="factory_002", 
                name="杭州服装制造",
                location="杭州",
                capabilities=["query_capacity", "create_order"]
            ),
            FactoryNode(
                factory_id="factory_003",
                name="深圳智能工厂",
                location="深圳",
                capabilities=["query_capacity", "create_order", "quality_check"]
            )
        ]
        
        for factory in example_factories:
            self.cluster.register_factory(factory)
        
        print(f"Registered {len(example_factories)} example factories")
    
    def run(self):
        """运行服务器"""
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            reload=True
        )


def create_app() -> FastAPI:
    """创建FastAPI应用（用于部署）"""
    server = MCPServer()
    return server.app


if __name__ == "__main__":
    server = MCPServer()
    server.run()