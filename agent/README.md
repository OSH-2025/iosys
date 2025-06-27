# 基于LLM的文件管理Agent

## 项目概述
> BloomFall

---

此为小组大作业中的 Agent 部分. 该 Agent 能够理解自然语言指令，将其转换为结构化的文件操作命令，并执行相应的文件管理任务。通过集成对话记忆功能，该 Agent 能够记住与用户的交互历史，提供更加智能和个性化的文件管理体验。

## 核心功能

- **自然语言交互**: 理解和处理用户的自然语言指令
- **文件管理操作**: 执行创建、删除、移动、重命名等文件操作
- **上下文记忆**: 记录用户与Agent的交互历史，实现连续对话
- **扩展工具支持**: 通过MCP协议支持扩展工具接口

## 项目结构
```
agent/
├── README.md           # 项目说明文档
├── __init__.py         # IOSYSAgent 类的实现
├── config.py           # Agent 配置类
├── file_agent.py       # 文件管理 Agent 的实现
├── mcp.py              # MCPClient 类的实现
├── memory.py           # 对话记忆管理类
└── types.py            # 定义工具调用结果类
```

## 系统架构

### 核心组件
- `IOSYSAgent`: 主类，负责处理用户输入并调用相应的工具，管理对话流程
- `AgentConfig`: 配置类，包含 LLM 模型、文件系统、RAG 检索系统和日志级别等配置
- `FileAgent`: 文件管理 Agent，负责解析用户指令并执行文件操作，通过工具装饰器自动注册文件操作工具
- `MCPClient`: 用于与 MCP（Model Context Protocol）进行通信的客户端，支持扩展工具
- `ConversationMemory`: 对话记忆管理类，记录用户与 Agent 的交互历史，实现上下文连续对话

### 工作流程
1. 用户输入自然语言指令
2. `IOSYSAgent` 接收指令，提取近期对话历史
3. 将指令和历史发送给 LLM 进行处理
4. LLM 选择合适的工具并提供参数
5. `IOSYSAgent` 执行工具调用并返回结果
6. 记录交互到对话历史中

## 文件系统操作

Agent支持以下文件操作：

| 操作类型 | 工具名称 | 描述 |
|---------|---------|------|
| 创建文件 | create_file | 在指定路径创建新文件 |
| 创建目录 | create_directory | 在指定路径创建新目录 |
| 删除文件 | delete_file | 删除指定路径的文件 |
| 删除目录 | delete_directory | 删除指定路径的目录及其内容 |
| 移动文件 | move_file | 将文件从源路径移动到目标路径 |
| 移动目录 | move_directory | 将目录从源路径移动到目标路径 |
| 重命名文件 | rename_file | 修改文件的名称 |
| 重命名目录 | rename_directory | 修改目录的名称 |
| 列出目录 | list_files | 列出指定目录下的所有文件和子目录 |
| 读取文件 | read_file | 读取指定文件的内容 |
| 写入文件 | write_file | 向指定文件写入或追加内容 |

## 上下文记忆功能

Agent使用`ConversationMemory`类管理对话历史记录，实现了以下功能：

- 保存用户输入和系统响应的完整历史
- 限制保存的最大对话轮数，避免上下文过长
- 提供格式化的历史记录，适合发送给LLM
- 支持清除历史记录的操作

通过上下文记忆功能，用户可以进行更自然的连续对话，如：
- "刚才创建的文件是什么名字？"
- "把它移动到documents目录"
- "现在帮我列出该目录的内容"

## 快速开始

1. 安装依赖
```bash
pip install openai
```

2. 按照整个项目下的 `CONTRIBUTING.md` 文件中的说明进行配置

## 使用示例

### 创建文件
```
用户输入: 创建一个名为notes.txt的文件
```

处理结果:
```json
{
  "path": "/notes.txt"
}
```

### 创建目录
```
用户输入: 创建一个名为documents的目录
```

处理结果:
```json
{
  "path": "/documents"
}
```

### 连续对话示例
用户输入: 创建一个名为report.txt的文件, 并写入"# title"
处理结果:
```json
{
  "path": "/report.txt"
}
```

用户输入: 将它移动到documents目录
处理结果:
```json
{
  "new_path": "/documents/report.txt"
}
```

用户输入: 现在目录中有什么文件？
处理结果:
```json
{
  "children": [
    {
      "path": "/documents/report.txt",
      "name": "report.txt"
    }
  ]
}
```

## 扩展开发

### 添加新的文件操作工具

可以通过在`FileAgent`类中添加新的工具函数来扩展文件操作功能：

```python
@tool(
    name="new_tool_name",
    description="新工具的描述",
    parameters={
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "参数1描述"},
            "param2": {"type": "string", "description": "参数2描述"},
        },
        "required": ["param1"],
    },
)
def _new_tool_function(self, params: Dict[str, Any]) -> ToolCallResult:
    """实现新工具的函数"""
    # 处理逻辑
    return {
        "status": "success",
        "message": "操作成功",
        "data": {"result": "some_data"}
    }
```