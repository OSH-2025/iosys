from typing import Dict, Any
import json
import inspect
from openai.types.chat import ChatCompletionMessageParam


from .types import ToolCallResult
from .file_agent import FileAgent
from .config import AgentConfig
from .mcp import MCPClient
from utils.logger import IOSYSLogger


class IOSYSAgent:
    """文件管理应用"""

    def __init__(self, config: AgentConfig):
        """
        初始化文件管理应用

        Args:
            config: 配置对象, 如果为None则使用默认配置
        """
        self.logger = IOSYSLogger("Agent")
        self.config = config
        self.file_agent = FileAgent(config=self.config)
        self.mcp = MCPClient()
        self.history: list[ChatCompletionMessageParam] = [
            {
                "role": "system",
                "content": "你是一个文件管理助手，可以帮助用户进行各种文件操作。根据用户的需求，选择合适的工具来完成任务。如果用户的要求比较复杂, 你需要将任务拆分成多个步骤，并使用合适的工具来完成每个步骤。",
            },
        ]

    async def process_command(self, user_input: str) -> Dict[str, Any]:
        """
        处理用户命令

        Args:
            user_input: 用户的自然语言输入

        Returns:
            Dict: 处理结果
        """
        self.logger.info(f"接收到用户输入: {user_input}")
        result = await self._process(user_input)
        self.logger.info(f"处理结果: {json.dumps(result, ensure_ascii=False)}")
        return dict(result)

    async def _process(self, user_input: str) -> ToolCallResult:
        # 收集工具配置和处理函数
        session_id, mcp_tool_configs, mcp_tool_handlers = await self.mcp.start_session()
        try:
            tool_configs = [*self.file_agent.tool_configs, *mcp_tool_configs]
            tool_handlers = {
                **self.file_agent.tool_handlers,
                **mcp_tool_handlers,
            }

            self.history.append({"role": "user", "content": user_input})

            final_message = ""
            final_data = {}
            all_results = []
            all_messages = []
            all_success = True

            while True:
                response = self.config.llm.chat.completions.create(
                    model=self.config.llm_model,
                    messages=self.history,
                    tools=tool_configs,  # type: ignore
                    tool_choice="auto",
                )

                # 处理LLM响应
                message = response.choices[0].message.content if response.choices else None
                message = message.strip() if message else ""

                self.history.append(
                    {
                        "role": "assistant",
                        "content": message,
                        "tool_calls": response.choices[0].message.tool_calls
                        if response.choices
                        else [],  # type: ignore
                    }
                )

                # 检查是否有工具调用
                if hasattr(response, "choices") and response.choices:
                    choice = response.choices[0]
                    if (
                        hasattr(choice, "message")
                        and hasattr(choice.message, "tool_calls")
                        and choice.message.tool_calls
                    ):
                        tool_calls = choice.message.tool_calls
                        results = []
                        step_success = True
                        step_messages = []
                        step_data = {}

                        for i, tool_call in enumerate(tool_calls):
                            function_name = tool_call.function.name
                            function_args = json.loads(tool_call.function.arguments)

                            self.logger.info(
                                f"执行工具 {i + 1}/{len(tool_calls)}: {function_name}"
                            )

                            if function_name in tool_handlers:
                                try:
                                    result = tool_handlers[function_name](function_args)
                                    if inspect.isawaitable(result):
                                        result = await result

                                    results.append(
                                        {
                                            "tool_name": function_name,
                                            "args": function_args,
                                            "result": result,
                                            "index": i,
                                        }
                                    )

                                    if result["status"] != "success":
                                        step_success = False
                                        self.logger.warning(
                                            f"工具 {function_name} 执行失败: {result.get('message', '')}"
                                        )
                                    else:
                                        self.logger.info(f"工具 {function_name} 执行成功")

                                    if result.get("message"):
                                        step_messages.append(
                                            f"[{i + 1}] {function_name}: {result['message']}"
                                        )

                                    if result.get("data"):
                                        step_data[f"tool_{i + 1}_{function_name}"] = result[
                                            "data"
                                        ]

                                    # 将工具调用结果添加到历史记录
                                    self.history.append({
                                        "role": "tool",
                                        "tool_call_id": tool_call.id,
                                        "content": json.dumps(result, ensure_ascii=False)
                                    })

                                except Exception as e:
                                    error_msg = f"工具 {function_name} 执行异常: {str(e)}"
                                    self.logger.error(error_msg)
                                    results.append(
                                        {
                                            "tool_name": function_name,
                                            "args": function_args,
                                            "error": str(e),
                                            "index": i,
                                        }
                                    )
                                    step_success = False
                                    step_messages.append(
                                        f"[{i + 1}] {function_name}: 执行异常 - {str(e)}"
                                    )
                                    error_result = {
                                        "status": "error",
                                        "message": error_msg
                                    }
                                    self.history.append({
                                        "role": "tool",
                                        "tool_call_id": tool_call.id,
                                        "content": json.dumps(error_result, ensure_ascii=False)
                                    })
                            else:
                                error_msg = f"不支持的操作: {function_name}"
                                self.logger.error(error_msg)
                                results.append(
                                    {
                                        "tool_name": function_name,
                                        "args": function_args,
                                        "error": error_msg,
                                        "index": i,
                                    }
                                )
                                step_success = False
                                step_messages.append(
                                    f"[{i + 1}] {function_name}: {error_msg}"
                                )
                                error_result = {
                                    "status": "error",
                                    "message": error_msg
                                }
                                self.history.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": json.dumps(error_result, ensure_ascii=False)
                                })

                        # 汇总本轮结果
                        all_results.extend(results)
                        all_messages.extend(step_messages)
                        all_success = all_success and step_success
                        final_data.update(step_data)
                        # 再次循环，直到LLM不再调用工具
                        continue
                    else:
                        # 没有工具调用，流程结束
                        final_message = message
                        break
                else:
                    final_message = message + "无效的 LLM 响应格式"
                    all_success = False
                    break

            # 汇总最终结果
            if not all_results:
                return {
                    "status": "success" if all_success else "error",
                    "message": final_message,
                }
            else:
                # 统计成功/失败
                success_count = sum(
                    1
                    for r in all_results
                    if "result" in r and r["result"]["status"] == "success"
                )
                total_count = len(all_results)
                summary_message = (
                    f"执行了 {total_count} 个操作，成功 {success_count} 个"
                )
                if success_count < total_count:
                    summary_message += (
                        f"，失败 {total_count - success_count} 个"
                    )
                detailed_message = (
                    "\n".join(all_messages) if all_messages else ""
                )
                combined_message = (
                    f"{summary_message}\n\n详细结果:\n{detailed_message}"
                    if detailed_message
                    else summary_message
                )
                return {
                    "status": "success"
                    if all_success
                    else "partial_success"
                    if success_count > 0
                    else "error",
                    "message": final_message + ("\n\n---\n\n" + combined_message if combined_message else ""),
                    "data": {
                        **final_data,
                        "execution_summary": {
                            "total_operations": total_count,
                            "successful_operations": success_count,
                            "failed_operations": total_count - success_count,
                            "results": all_results,
                        },
                    },
                }
        finally:
            await self.mcp.end_session(session_id)
