from typing import Dict, Any
import json
import inspect


from .types import ToolCallResult
from .file_agent import FileAgent
from .config import AgentConfig
from .mcp import MCPClient
from utils.logger import IOSYSLogger
from .memory import ConversationMemory


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
        self.memory = ConversationMemory(max_history=10)

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
        self.memory.add_interaction(user_input, result)
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

            # get conversation history
            conversation_history = self.memory.get_formatted_history(limit=5)

            # 调用 LLM 进行工具选择和调用
            response = self.config.llm.chat.completions.create(
                model=self.config.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个文件管理助手，可以帮助用户进行各种文件操作。根据用户的需求，选择合适的工具来完成任务。如果用户的要求比较复杂, 你需要将任务拆分成多个步骤，并使用合适的工具来完成每个步骤。",
                    },
                    {
                        "role": "system",
                        "content": f"以下是近期对话历史:\n{conversation_history}",
                    },
                    {"role": "user", "content": user_input},
                ],
                tools=tool_configs,  # type: ignore
                tool_choice="auto",
            )

            # 处理LLM响应
            message = response.choices[0].message.content if response.choices else None
            message = message.strip() if message else ""

            def concat_message(msg: str | None) -> str:
                result = message
                if msg:
                    msg = msg.strip()
                    if result and msg:
                        result += "\n\n---\n\n" + msg
                    elif msg:
                        result += msg
                return result

            # 提取function call信息
            if hasattr(response, "choices") and response.choices:
                choice = response.choices[0]
                if (
                    hasattr(choice, "message")
                    and hasattr(choice.message, "tool_calls")
                    and choice.message.tool_calls
                ):
                    tool_calls = choice.message.tool_calls
                    results = []
                    all_success = True
                    all_messages = []
                    all_data = {}
                    
                    for i, tool_call in enumerate(tool_calls):
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        
                        self.logger.info(f"执行工具 {i+1}/{len(tool_calls)}: {function_name}")
                        
                        # 使用自动收集的处理函数
                        if function_name in tool_handlers:
                            try:
                                result = tool_handlers[function_name](function_args)
                                if inspect.isawaitable(result):
                                    result = await result
                                
                                results.append({
                                    "tool_name": function_name,
                                    "args": function_args,
                                    "result": result,
                                    "index": i
                                })
                                
                                if result["status"] != "success":
                                    all_success = False
                                    self.logger.warning(f"工具 {function_name} 执行失败: {result.get('message', '')}")
                                else:
                                    self.logger.info(f"工具 {function_name} 执行成功")
                                
                                # 收集消息和数据
                                if result.get("message"):
                                    all_messages.append(f"[{i+1}] {function_name}: {result['message']}")
                                
                                if result.get("data"):
                                    all_data[f"tool_{i+1}_{function_name}"] = result["data"]
                                    
                            except Exception as e:
                                error_msg = f"工具 {function_name} 执行异常: {str(e)}"
                                self.logger.error(error_msg)
                                results.append({
                                    "tool_name": function_name,
                                    "args": function_args,
                                    "error": str(e),
                                    "index": i
                                })
                                all_success = False
                                all_messages.append(f"[{i+1}] {function_name}: 执行异常 - {str(e)}")
                        else:
                            error_msg = f"不支持的操作: {function_name}"
                            self.logger.error(error_msg)
                            results.append({
                                "tool_name": function_name,
                                "args": function_args,
                                "error": error_msg,
                                "index": i
                            })
                            all_success = False
                            all_messages.append(f"[{i+1}] {function_name}: {error_msg}")
                    
                    # 生成汇总结果
                    if len(tool_calls) == 1:
                        # 单个工具调用，保持原有格式
                        single_result = results[0]["result"] if "result" in results[0] else {"status": "error", "message": results[0].get("error", "执行失败")}
                        if single_result["status"] != "success":
                            return {
                                "status": "error",
                                "message": concat_message(single_result.get("message", "工具调用失败")),
                            }
                        else:
                            return {
                                "status": "success",
                                "message": concat_message(single_result.get("message", "")),
                                "data": single_result.get("data", {}),
                            }
                    else:
                        # 多个工具调用，返回汇总结果
                        success_count = sum(1 for r in results if "result" in r and r["result"]["status"] == "success")
                        total_count = len(tool_calls)
                        
                        summary_message = f"执行了 {total_count} 个操作，成功 {success_count} 个"
                        if success_count < total_count:
                            summary_message += f"，失败 {total_count - success_count} 个"
                        
                        detailed_message = "\n".join(all_messages) if all_messages else ""
                        final_message = f"{summary_message}\n\n详细结果:\n{detailed_message}" if detailed_message else summary_message
                        
                        return {
                            "status": "success" if all_success else "partial_success" if success_count > 0 else "error",
                            "message": concat_message(final_message),
                            "data": {
                                **all_data,
                                "execution_summary": {
                                    "total_operations": total_count,
                                    "successful_operations": success_count,
                                    "failed_operations": total_count - success_count,
                                    "results": results
                                }
                            }
                        }
                else:
                    return {
                        "status": "success",
                        "message": message,
                    }
            else:
                return {"status": "error", "message": message + "无效的 LLM 响应格式"}
        finally:
            await self.mcp.end_session(session_id)
