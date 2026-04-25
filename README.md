# Manufacturing MCP Cluster (MMC)

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![Documentation](https://img.shields.io/badge/docs-latest-brightgreen.svg)](https://manufacturing-ai.github.io/mmc-docs/)

**制造业MCP集群** - 为制造业AI Agent建立统一的交互标准

## 🎯 项目愿景

将制造业的"暗产能"转化为可编程的数字化服务，构建AI Agent自主交易的全球制造网络。

## ✨ 核心特性

- **统一协议**: 基于MCP(Model Context Protocol)的标准化接口
- **实时产能池**: 秒级同步的全局产能状态视图
- **智能路由**: 基于负载和性能的智能请求路由
- **安全可靠**: 端到端加密与权限控制
- **易于集成**: 支持多种工业协议和系统

## 🚀 快速开始

### 安装

```bash
pip install manufacturing-mcp
```

### 基本使用

```python
from manufacturing_mcp import MCPClient, ManufacturingTools

# 连接到MCP集群
client = MCPClient(cluster_url="https://mmc.example.com")

# 查询产能
capacity = await client.query_capacity(
    product_type="t_shirt",
    min_quantity=1000
)

# 创建订单
order = await client.create_order(
    product_type="t_shirt",
    specifications={
        "size": ["M", "L"],
        "color": "白色",
        "material": "纯棉"
    },
    quantity=5000,
    delivery_date="2024-05-30"
)
```

## 📖 文档

- [完整文档](https://manufacturing-ai.github.io/mmc-docs/)
- [API参考](https://manufacturing-ai.github.io/mmc-docs/api/)
- [示例项目](https://github.com/manufacturing-ai/mmc-examples)
- [贡献指南](CONTRIBUTING.md)

## 🏗️ 架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   AI Agents     │    │   MCP Cluster   │    │   Factories     │
│                 │◄──▶│    Gateway      │◄──▶│   (MCP Servers) │
│ • LangChain     │    │                 │    │                 │
│ • AutoGen       │    │ • 智能路由       │    │ • 产能查询      │
│ • Custom Agents │    │ • 负载均衡       │    │ • 订单创建      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📊 支持的协议和系统

| 类别 | 支持的系统 |
|------|------------|
| 工业协议 | OPC UA, Modbus, MQTT, Ethernet/IP |
| ERP系统 | SAP, Oracle, 用友, 金蝶 |
| MES系统 | Siemens, Rockwell, 自定义系统 |
| 电商平台 | 淘宝, 京东, Shopify, Amazon |

## 🤝 贡献

我们欢迎所有形式的贡献！请阅读[贡献指南](CONTRIBUTING.md)。

## 📄 许可证

本项目采用 [Apache License 2.0](LICENSE)。

## 🏢 商业支持

需要企业级支持或定制开发？请访问我们的[商业支持页面](https://manufacturing-ai.com/support)。

## 🎯 项目状态

| 阶段 | 状态 | 完成度 |
|------|------|--------|
| 核心协议 | ✅ 已完成 | 100% |
| 服务器实现 | ✅ 已完成 | 100% |
| 客户端实现 | ✅ 已完成 | 100% |
| 文档完善 | 🚧 进行中 | 80% |
| 社区建设 | 🚧 进行中 | 30% |
| 用户获取 | 🚧 进行中 | 10% |

**最新更新**: v0.1.0 已发布 - 基础MCP协议实现完成

## 🌐 社区

- [GitHub Issues](https://github.com/manufacturing-ai/mmc-core/issues)
- [Discord 频道](https://discord.gg/manufacturing-ai)
- [Twitter](https://twitter.com/manufacturing_ai)
- [技术博客](https://blog.manufacturing-ai.org)

## 🚀 加入我们

制造业的AI时代已经来临！加入我们一起构建未来：

1. **开发者**: 贡献代码，扩展功能
2. **制造商**: 试用系统，提供反馈
3. **研究者**: 参与研究，发表论文
4. **投资者**: 支持项目，共同成长

**立即开始**: `git clone https://github.com/manufacturing-ai/mmc-core.git`