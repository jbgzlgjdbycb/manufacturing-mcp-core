# 贡献指南

感谢您对制造业MCP集群项目的兴趣！以下是如何为项目做贡献的指南。

## 🐛 报告问题

在创建Issue之前：
1. 搜索是否已有类似问题
2. 确保在最新版本中问题仍然存在

Issue模板包括：
- Bug报告
- 功能请求
- 文档改进

## 🔧 开发环境设置

### 克隆仓库
```bash
git clone https://github.com/manufacturing-ai/mmc-core.git
cd mmc-core
```

### 安装依赖
```bash
# 使用 poetry
poetry install

# 或使用 pip
pip install -e ".[dev]"
```

### 运行测试
```bash
pytest tests/
```

## 📝 代码风格

我们使用：
- **Black** 代码格式化
- **isort** 导入排序
- **mypy** 类型检查
- **flake8** 代码质量

提交前请运行：
```bash
make format  # 自动格式化
make lint    # 代码检查
make test    # 运行测试
```

## 🚀 开发流程

1. Fork 仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开 Pull Request

## 🧪 编写测试

- 新功能必须包含测试
- 测试覆盖率不应降低
- 使用 pytest 和 pytest-asyncio

## 📚 文档

- 公共API必须包含文档字符串
- 使用Google风格的文档字符串格式
- 重大更改需要更新文档

## 🏷️ 版本管理

我们使用语义化版本：
- MAJOR: 不兼容的API更改
- MINOR: 向后兼容的功能性新增
- PATCH: 向后兼容的问题修复

## 🏢 企业贡献

如果您代表企业贡献代码，请确保：
1. 您有贡献代码的权限
2. 代码不包含商业机密
3. 符合许可证要求

## ❓ 需要帮助？

- 查看 [文档](https://manufacturing-ai.github.io/mmc-docs/)
- 加入 [Discord](https://discord.gg/manufacturing-ai)
- 在GitHub Issues中提问