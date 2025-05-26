# 基于LLM的文件管理Agent

## 项目概述
> BloomFall

---

此为小组大作业中关于 agent 的部分，主要是对基于LLM的文件管理Agent的设计与实现。该Agent能够将用户的自然语言指令解析为结构化数据，并执行相应的文件操作。

## 项目结构
```
agent/
├── README.md           # 项目说明文档
├── requirements.txt    # 依赖项列表
├── run_demo.py         # 演示和交互式入口
├── src/                # 源代码目录
│   ├── file_agent.py   # 文件管理Agent核心实现
│   ├── config.py       # 配置类
│   └── app.py          # 应用类，整合Agent和配置
└── test_commands.txt   # 测试命令样例
```

## Agent结构
Agent由以下三层组成：

1. **交互层**：负责接收用户自然语言输入，并将输出结果返回用户。
2. **解析层**：将用户自然语言输入解析为结构化JSON数据，以便后续处理。
3. **执行层**：根据解析层输出的JSON数据，执行具体的文件管理操作。

## 支持的文件操作
- 创建文件/文件夹
- 删除文件/文件夹
- 移动文件/文件夹
- 重命名文件/文件夹
- 列出目录内容
- 读取文件内容
- 写入文件内容

## 快速开始

### 安装依赖
```bash
pip install openai  # 或其他LLM API客户端
```

### 设置环境变量（可选）
```bash
# Windows
set LLM_API_KEY=your_api_key_here

# Linux/macOS
export LLM_API_KEY=your_api_key_here
```

### 运行程序
```bash
# 执行单条命令
python run_demo.py --command "创建一个名为test.txt的文件"

# 演示模式
python run_demo.py --demo
```


# 从文件执行命令

## 使用示例
以下是一些常见的使用示例：

### 创建文件
```
创建一个名为notes.txt的文件
```

解析结果：
```json
{
  "operation": "create_file",
  "parameters": {
    "file_name": "notes.txt",
    "path": ".",
    "content": ""
  }
}
```

### 创建目录
```
创建一个名为documents的目录
```

解析结果：
```json
{
  "operation": "create_directory",
  "parameters": {
    "directory_name": "documents",
    "path": "."
  }
}
```

### 移动文件
```
将report.txt移动到documents目录
```

解析结果：
```json
{
  "operation": "move_file",
  "parameters": {
    "source_path": "report.txt",
    "destination_path": "documents/report.txt"
  }
}
```