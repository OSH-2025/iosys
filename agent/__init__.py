import logging
from typing import Dict, Any, NotRequired, TypedDict
import json
import inspect

from .file_agent import FileAgent
from .config import AgentConfig
from .mcp import MCPClient

logger = logging.getLogger(__name__)


class ToolCallResult(TypedDict):
    """工具调用结果类型"""

    status: str  # "success" 或 "error"
    message: str  # 操作结果消息
    data: NotRequired[Dict[str, Any]]  # 附加数据，例如文件路径等


class IOSYSAgent:
    """文件管理应用"""

    def __init__(self, config: AgentConfig):
        """
        初始化文件管理应用

        Args:
            config: 配置对象, 如果为None则使用默认配置
        """
        self.config = config
        self.file_agent = FileAgent(config=self.config)
        self.mcp = MCPClient()

    async def process_command(self, user_input: str) -> Dict[str, Any]:
        """
        处理用户命令

        Args:
            user_input: 用户的自然语言输入

        Returns:
            Dict: 处理结果
        """
        logger.info(f"接收到用户输入: {user_input}")
        result = await self._process(user_input)
        logger.info(f"处理结果: {json.dumps(result, ensure_ascii=False)}")
        return dict(result)

    async def _process(self, user_input: str) -> ToolCallResult:
        # 收集工具配置和处理函数
        _id, mcp_tool_configs, mcp_tool_handlers = await self.mcp.start_session()
        tool_configs = [*self.file_agent.tool_configs, *mcp_tool_configs]
        tool_handlers = {
            **self.file_agent.tool_handlers,
            **mcp_tool_handlers,
        }

        # 调用 LLM 进行工具选择和调用
        response = self.config.llm.chat.completions.create(
            model=self.config.llm_model,
            messages=[
                {
                    "role": "system",
                    "content": "你是一个文件管理助手，可以帮助用户进行各种文件操作。根据用户的需求，选择合适的工具来完成任务。",
                },
                {"role": "user", "content": user_input},
            ],
            tools=tool_configs,  # type: ignore
            tool_choice="auto",
        )

        # 处理LLM响应
        message = response.choices[0].message.content if response.choices else None
        message = message + "\n\n---\n\n" if message else ""
        # 提取function call信息
        if hasattr(response, "choices") and response.choices:
            choice = response.choices[0]
            if (
                hasattr(choice, "message")
                and hasattr(choice.message, "tool_calls")
                and choice.message.tool_calls
            ):
                tool_call = choice.message.tool_calls[0]
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                # 使用自动收集的处理函数
                if function_name in tool_handlers:
                    result = tool_handlers[function_name](function_args)
                    if inspect.isawaitable(result):
                        result = await result
                    if result["status"] != "success":
                        return {
                            "status": "error",
                            "message": message + result.get("message", "工具调用失败"),
                        }
                    else:
                        return {
                            "status": "success",
                            "message": message + result.get("message", ""),
                            "data": result.get("data", {}),
                        }
                else:
                    return {
                        "status": "error",
                        "message": message
                        + f"工具调用失败：不支持的操作: {function_name}",
                    }
            else:
                return {
                    "status": "success",
                    "message": message + "LLM 没有调用任何工具函数",
                }
        else:
            return {"status": "error", "message": message + "无效的 LLM 响应格式"}
