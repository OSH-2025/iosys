---
outline: [2, 4]
---

# 可行性报告

## 项目介绍

## 创新点

## 理论依据

## 技术依据

### Tool & Function Calling

#### 简介

Tool calls 也叫 function calls，是大模型操作外部工具的一种方式。它允许模型在生成响应时调用外部 API 或函数，以便获取额外的信息或执行特定的操作。通过这种方式，模型可以更好地处理复杂的任务，提供更准确和实用的答案。

对于 iosys 来说，tool calling 也是 LLM 操作文件系统的接口。

#### 通过 OpenAI SDK 调用

OpenAI SDK 支持 tool calling。以下是提供 LLM 调用天气信息获取工具的示例[^1]：

```python
from openai import OpenAI

client = OpenAI()

tools = [{
  "type": "function",
  "function": {
    "name": "get_weather",
    "description": "Get current temperature for a given location.",
    "parameters": {
      "type": "object",
      "properties": {
        "location": {
          "type": "string",
          "description": "City and country e.g. Bogotá, Colombia"
        }
      },
      "required": [
        "location"
      ],
      "additionalProperties": False
    },
    "strict": True
  }
}]

completion = client.chat.completions.create(
  model="gpt-4o",
  messages=[{"role": "user", "content": "What is the weather like in Paris today?"}],
  tools=tools
)
```

预期可以得到如下的结果：

```json
// print(completion.choices[0].message.tool_calls)
[
  {
    "id": "call_12345xyz",
    "type": "function",
    "function": {
      "name": "get_weather",
      "arguments": "{\"location\":\"Paris, France\"}"
    }
  }
]
```

#### 模型支持

大部分大模型都支持 tool calling，包括 GPT-4o, Gemini Flash 2.0, DeepSeek V3/R1 等。

#### 指令生成

Tool calling 除了用来让模型调用工具以获取信息以外，也可以用来让模型生成指令。这是 tool calling 在 iosys 中的一个重要用途。

我们可以定义多个用于操作文件的工具，并让模型根据用户的输入生成相应的指令。比如：

- 创建/读取/修改/删除文件
- 关联/取消关联文件
- ...

通过这种方式，就可以通过 LLM 来操作文件系统。

## 技术路线

## 参考文献

[^1]: https://platform.openai.com/docs/guides/function-calling
