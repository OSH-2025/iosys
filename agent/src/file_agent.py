import os
import shutil
import json
from typing import Dict, Any, Callable, List
from enum import Enum
from functools import wraps

from openai import Client

from agent.src.config import AgentConfig


class OperationType(str, Enum):
    """支持的文件操作类型枚举"""

    CREATE_FILE = "create_file"
    CREATE_DIRECTORY = "create_directory"
    DELETE_FILE = "delete_file"
    DELETE_DIRECTORY = "delete_directory"
    MOVE_FILE = "move_file"
    MOVE_DIRECTORY = "move_directory"
    RENAME_FILE = "rename_file"
    RENAME_DIRECTORY = "rename_directory"
    LIST_FILES = "list_files"
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"


def tool(name: str, description: str, parameters: Dict[str, Any]):
    """
    工具装饰器，用于注册文件操作工具

    Args:
        name: 工具名称
        description: 工具描述
        parameters: 工具参数配置
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # 将工具配置信息附加到函数上
        wrapper._tool_config = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters
            }
        }
        wrapper._tool_name = name
        return wrapper
    return decorator


class FileAgent:
    """基于LLM的文件管理Agent"""

    def __init__(self, config: AgentConfig, llm_client: Client):
        """
        初始化文件管理Agent

        Args:
            config: Agent配置
            llm_client: LLM客户端(例如OpenAI API客户端)
        """
        self.config = config
        self.base_dir = os.path.abspath(config.base_dir)
        self.llm_client = llm_client
        self.tools = self._collect_tools()
        self.tool_handlers = self._collect_tool_handlers()

    def _collect_tools(self) -> List[Dict[str, Any]]:
        """自动收集所有注册的工具配置"""
        tools = []
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, '_tool_config'):
                tools.append(attr._tool_config)
        return tools

    def _collect_tool_handlers(self) -> Dict[str, Callable]:
        """自动收集所有工具处理函数"""
        handlers = {}
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, '_tool_name'):
                handlers[attr._tool_name] = attr
        return handlers

    def process(self, user_input: str) -> Dict[str, Any]:
        """
        处理用户输入并执行相应的文件操作

        Args:
            user_input: 用户的自然语言输入

        Returns:
            Dict: 包含操作结果的字典
        """
        try:
            # 调用LLM获取function call
            response = self._call_llm_with_tools(user_input)

            # 执行function call
            result = self._execute_function_call(response)
            return result

        except Exception as e:
            return {"status": "error", "message": f"处理请求时出错: {str(e)}"}

    def _call_llm_with_tools(self, user_input: str) -> Any:
        """
        调用LLM并获取function call响应

        Args:
            user_input: 用户输入

        Returns:
            LLM响应对象
        """
        try:
            response = self.llm_client.chat.completions.create(
                model=self.config.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个文件管理助手，可以帮助用户进行各种文件操作。根据用户的需求，选择合适的工具来完成任务。"
                    },
                    {"role": "user", "content": user_input}
                ],
                tools=self.tools,
                tool_choice="auto"
            )
            return response
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"LLM API调用异常: {str(e)}")
            raise e

    def _execute_function_call(self, response) -> Dict[str, Any]:
        """
        执行function call

        Args:
            response: LLM响应

        Returns:
            Dict: 执行结果
        """
        try:
            # 提取function call信息
            if hasattr(response, 'choices') and response.choices:
                choice = response.choices[0]
                if hasattr(choice, 'message') and hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
                    tool_call = choice.message.tool_calls[0]
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)

                    # 使用自动收集的处理函数
                    if function_name in self.tool_handlers:
                        return self.tool_handlers[function_name](function_args)
                    else:
                        return {"status": "error", "message": f"不支持的操作: {function_name}"}
                else:
                    return {"status": "error", "message": "LLM没有调用任何工具函数"}
            else:
                return {"status": "error", "message": "无效的LLM响应格式"}

        except Exception as e:
            return {"status": "error", "message": f"执行function call时出错: {str(e)}"}

    # ------------------------------------ 工具函数定义 ------------------------------------

    @tool(
        name="create_file",
        description="创建新文件",
        parameters={
            "type": "object",
            "properties": {
                "file_name": {"type": "string", "description": "文件名"},
                "path": {"type": "string", "description": "文件路径", "default": "."},
                "content": {"type": "string", "description": "文件内容", "default": ""}
            },
            "required": ["file_name"]
        }
    )
    def _create_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """创建文件"""
        if "file_name" not in params or "path" not in params:
            # 设置默认文件名为 new_file.txt
            params["file_name"] = "new_file.txt"
            # 默认路径为当前目录
            params["path"] = "."

        try:
            file_path = self._normalize_path(
                os.path.join(params["path"], params["file_name"])
            )
            content = params.get("content", "")

            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # 检查文件是否已存在
            if os.path.exists(file_path):
                return {
                    "status": "error",
                    "message": f"文件已存在: {params['file_name']}",
                    "data": {}
                }

            # 创建文件
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            return {
                "status": "success",
                "message": f"文件创建成功: {params['file_name']}",
                "data": {"path": os.path.relpath(file_path, self.base_dir)}
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    @tool(
        name="create_directory",
        description="创建新目录",
        parameters={
            "type": "object",
            "properties": {
                "directory_name": {"type": "string", "description": "目录名"},
                "path": {"type": "string", "description": "父目录路径", "default": "."}
            },
            "required": ["directory_name"]
        }
    )
    def _create_directory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """创建目录"""
        if "directory_name" not in params or "path" not in params:
            # 设置默认目录名为 new_directory
            params["directory_name"] = "new_directory"
            # 默认路径为当前目录
            params["path"] = "."

        try:
            dir_path = self._normalize_path(
                os.path.join(params["path"], params["directory_name"])
            )

            # 检查目录是否已存在
            if os.path.exists(dir_path):
                return {
                    "status": "error",
                    "message": f"目录已存在: {params['directory_name']}",
                    "data": {}
                }

            # 创建目录
            os.makedirs(dir_path, exist_ok=True)

            return {
                "status": "success",
                "message": f"目录创建成功: {params['directory_name']}",
                "data": {"path": os.path.relpath(dir_path, self.base_dir)}
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    @tool(
        name="delete_file",
        description="删除文件",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "要删除的文件路径"}
            },
            "required": ["file_path"]
        }
    )
    def _delete_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """删除文件"""
        if "file_path" not in params:
            params["file_path"] = "."

        try:
            file_path = self._normalize_path(params["file_path"])

            # 检查文件是否存在
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                return {
                    "status": "error",
                    "message": f"文件不存在: {params['file_path']}",
                    "data": {}
                }

            # 删除文件
            os.remove(file_path)

            return {
                "status": "success",
                "message": f"文件删除成功: {params['file_path']}"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    @tool(
        name="delete_directory",
        description="删除目录",
        parameters={
            "type": "object",
            "properties": {
                "directory_path": {"type": "string", "description": "要删除的目录路径"}
            },
            "required": ["directory_path"]
        }
    )
    def _delete_directory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """删除目录"""
        if "directory_path" not in params:
            return {"status": "error", "message": "缺少必要参数: directory_path"}

        try:
            dir_path = self._normalize_path(params["directory_path"])

            # 检查目录是否存在
            if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
                return {
                    "status": "error",
                    "message": f"目录不存在: {params['directory_path']}",
                    "data": {}
                }

            # 删除目录
            shutil.rmtree(dir_path)

            return {
                "status": "success",
                "message": f"目录删除成功: {params['directory_path']}"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    @tool(
        name="move_file",
        description="移动文件",
        parameters={
            "type": "object",
            "properties": {
                "source_path": {"type": "string", "description": "源文件路径"},
                "destination_path": {"type": "string", "description": "目标文件路径"}
            },
            "required": ["source_path", "destination_path"]
        }
    )
    def _move_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """移动文件"""
        if "source_path" not in params or "destination_path" not in params:
            return {
                "status": "error",
                "message": "缺少必要参数: source_path 或 destination_path"
            }

        try:
            src_path = self._normalize_path(params["source_path"])
            dst_path = self._normalize_path(params["destination_path"])

            # 检查源文件是否存在
            if not os.path.exists(src_path) or not os.path.isfile(src_path):
                return {
                    "status": "error",
                    "message": f"源文件不存在: {params['source_path']}",
                    "data": {}
                }

            # 确保目标目录存在
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)

            # 检查目标文件是否已存在
            if os.path.exists(dst_path):
                return {
                    "status": "error",
                    "message": f"目标文件已存在: {params['destination_path']}",
                    "data": {}
                }

            # 移动文件
            shutil.move(src_path, dst_path)

            return {
                "status": "success",
                "message": f"文件移动成功: {params['source_path']} -> {params['destination_path']}",
                "data": {"new_path": os.path.relpath(dst_path, self.base_dir)}
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    @tool(
        name="move_directory",
        description="移动目录",
        parameters={
            "type": "object",
            "properties": {
                "source_path": {"type": "string", "description": "源目录路径"},
                "destination_path": {"type": "string", "description": "目标目录路径"}
            },
            "required": ["source_path", "destination_path"]
        }
    )
    def _move_directory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """移动目录"""
        if "source_path" not in params or "destination_path" not in params:
            return {
                "status": "error",
                "message": "缺少必要参数: source_path 或 destination_path"
            }

        try:
            src_path = self._normalize_path(params["source_path"])
            dst_path = self._normalize_path(params["destination_path"])

            # 检查源目录是否存在
            if not os.path.exists(src_path) or not os.path.isdir(src_path):
                return {
                    "status": "error",
                    "message": f"源目录不存在: {params['source_path']}",
                    "data": {}
                }

            # 检查目标目录是否已存在
            if os.path.exists(dst_path):
                return {
                    "status": "error",
                    "message": f"目标目录已存在: {params['destination_path']}",
                    "data": {}
                }

            # 确保目标父目录存在
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)

            # 移动目录
            shutil.move(src_path, dst_path)

            return {
                "status": "success",
                "message": f"目录移动成功: {params['source_path']} -> {params['destination_path']}",
                "data": {"new_path": os.path.relpath(dst_path, self.base_dir)}
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    @tool(
        name="rename_file",
        description="重命名文件",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "要重命名的文件路径"},
                "new_name": {"type": "string", "description": "新文件名"}
            },
            "required": ["file_path", "new_name"]
        }
    )
    def _rename_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """重命名文件"""
        if "file_path" not in params or "new_name" not in params:
            params["new_name"] = "rename_file.txt"
            params["file_path"] = "."

        try:
            file_path = self._normalize_path(params["file_path"])
            dir_path = os.path.dirname(file_path)
            new_path = os.path.join(dir_path, params["new_name"])

            # 检查源文件是否存在
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                return {
                    "status": "error",
                    "message": f"文件不存在: {params['file_path']}",
                    "data": {}
                }

            # 检查新文件名是否已存在
            if os.path.exists(new_path):
                return {
                    "status": "error",
                    "message": f"文件已存在: {params['new_name']}",
                    "data": {}
                }

            # 重命名文件
            os.rename(file_path, new_path)

            return {
                "status": "success",
                "message": f"文件重命名成功: {params['file_path']} -> {params['new_name']}",
                "data": {"new_path": os.path.relpath(new_path, self.base_dir)}
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    @tool(
        name="rename_directory",
        description="重命名目录",
        parameters={
            "type": "object",
            "properties": {
                "directory_path": {"type": "string", "description": "要重命名的目录路径"},
                "new_name": {"type": "string", "description": "新目录名"}
            },
            "required": ["directory_path", "new_name"]
        }
    )
    def _rename_directory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """重命名目录"""
        if "directory_path" not in params or "new_name" not in params:
            params["new_name"] = "rename_dir"
            params["directory_path"] = "."

        try:
            dir_path = self._normalize_path(params["directory_path"])
            parent_dir = os.path.dirname(dir_path)
            new_path = os.path.join(parent_dir, params["new_name"])

            # 检查源目录是否存在
            if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
                return {
                    "status": "error",
                    "message": f"目录不存在: {params['directory_path']}",
                    "data": {}
                }

            # 检查新目录名是否已存在
            if os.path.exists(new_path):
                return {
                    "status": "error",
                    "message": f"目录已存在: {params['new_name']}",
                    "data": {}
                }

            # 重命名目录
            os.rename(dir_path, new_path)

            return {
                "status": "success",
                "message": f"目录重命名成功: {params['directory_path']} -> {params['new_name']}",
                "data": {"new_path": os.path.relpath(new_path, self.base_dir)}
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    @tool(
        name="list_files",
        description="列出目录内容",
        parameters={
            "type": "object",
            "properties": {
                "directory_path": {"type": "string", "description": "目录路径", "default": "."}
            }
        }
    )
    def _list_files(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """列出目录内容"""
        if "directory_path" not in params:
            params["directory_path"] = "."

        try:
            dir_path = self._normalize_path(params["directory_path"])

            # 检查目录是否存在
            if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
                return {
                    "status": "error",
                    "message": f"目录不存在: {params['directory_path']}",
                    "data": {}
                }

            # 列出目录内容
            items = os.listdir(dir_path)
            files = []
            directories = []

            for item in items:
                item_path = os.path.join(dir_path, item)
                if os.path.isfile(item_path):
                    files.append(item)
                elif os.path.isdir(item_path):
                    directories.append(item)

            return {
                "status": "success",
                "message": f"成功列出目录内容: {params['directory_path']}",
                "data": {"contents": {"files": files, "directories": directories}}
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    @tool(
        name="read_file",
        description="读取文件内容",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "文件路径"}
            },
            "required": ["file_path"]
        }
    )
    def _read_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """读取文件内容"""
        if "file_path" not in params:
            params["file_path"] = "."

        try:
            file_path = self._normalize_path(params["file_path"])

            # 检查文件是否存在
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                return {
                    "status": "error",
                    "message": f"文件不存在: {params['file_path']}",
                    "data": {}
                }

            # 读取文件内容
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            return {
                "status": "success",
                "message": f"成功读取文件: {params['file_path']}",
                "data": {"content": content}
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    @tool(
        name="write_file",
        description="写入文件内容",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "文件路径"},
                "content": {"type": "string", "description": "要写入的内容"},
                "append": {"type": "boolean", "description": "是否追加模式", "default": False}
            },
            "required": ["file_path", "content"]
        }
    )
    def _write_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """写入文件内容"""
        if "file_path" not in params and "content" in params:
            if "file_name" in params:
                params["file_path"] = params["file_name"]
            else:
                params["file_path"] = "."

        if "content" not in params:
            return {"status": "error", "message": "缺少必要参数: content"}

        try:
            file_path = self._normalize_path(params["file_path"])
            content = params["content"]
            append = params.get("append", False)

            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # 写入文件
            mode = "a" if append else "w"
            with open(file_path, mode, encoding="utf-8") as f:
                f.write(content)

            return {
                "status": "success",
                "message": f"成功{'追加' if append else '写入'}文件: {params['file_path']}",
                "data": {"path": os.path.relpath(file_path, self.base_dir)}
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    # 这里只返回大模型解析出的.json格式数据, 其中需要包含:
    # 特征词序列(例如要求查询和某些关键词有关的文件),
    # 限制序列(例如明确的文件名),
    # 搜索地址(也就是在哪一个文件夹下搜素)
    # 发给 GRAPH RAG 部分
    def _search_file_send(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """搜索文件"""
        try:
            # 提取搜索参数
            key_words = params.get("key_words", [])
            constraint = params.get("constraint", [])
            search_path = params.get("search_path", ".")

            # 标准化搜索路径
            normalized_search_path = self._normalize_path(search_path)

            # 检查路径是否存在
            if not os.path.exists(normalized_search_path):
                return {
                    "status": "error",
                    "message": f"搜索路径不存在: {search_path}"
                }

            # 手动添加file_name到限制序列
            if "file_name" in params:
                constraint.append(params["file_name"])

            # 构建发送给 GRAPH RAG 的数据结构
            search_data = {
                "key_words": key_words,  # 特征词序列
                "constraint": constraint,      # 限制序列
                # "search_path": os.path.relpath(normalized_search_path, self.base_dir)  # 搜索地址
                "search_path": normalized_search_path  # 搜索地址
            }

            return {
                "status": "success",
                "message": "搜索参数已准备完成，等待发送到 GRAPH RAG",
                "data": search_data
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"准备搜索参数时出错: {str(e)}"
            }

    def _search_file_receive(self, search_results: Dict[str, Any]) -> Dict[str, Any]:
        """接收搜索结果"""
        try:
            # 处理搜索结果
            file_list = search_results.get("file_list", [])
            weights = search_results.get("weights", [])
            # description = search_results.get("description", [])

            if not file_list:
                return {
                    "status": "success",
                    "message": "未找到相关文件"
                }

            return {
                "status": "success",
                "message": f"找到 {len(file_list)} 个相关文件",
                "data": {
                    "file_list": file_list,
                    "weights": weights
                    # "description": description
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"处理搜索结果时出错: {str(e)}"
            }

    @tool(
        name="search_file",
        description="搜索文件工作流",
        parameters={
            "type": "object",
            "properties": {
                "key_words": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "特征词序列"
                },
                "constraint": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "限制序列"
                },
                "search_path": {
                    "type": "string",
                    "description": "搜索地址",
                    "default": "."
                },
                "file_name": {
                    "type": "string",
                    "description": "文件名限制"
                }
            },
            "required": ["key_words"]
        }
    )
    def _search_file_workflow(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """搜索文件工作流，协调发送请求和接收结果"""
        try:
            # 1. 发送搜索请求到 GRAPH RAG
            send_result = self._search_file_send(params)

            # 检查发送是否成功
            if send_result["status"] == "error":
                return send_result

            # 2. 这里应该调用 GRAPH RAG 进行搜索
            # 注意：这部分需要您实际集成 GRAPH RAG 系统
            # 以下是一个模拟的 GRAPH RAG 调用示例
            # 实际使用时请替换为真正的接口调用

            # 模拟 GRAPH RAG 的搜索结果
            # 在实际应用中，应该使用 GRAPH RAG 系统的返回结果
            # search_results = call_graph_rag(search_data)

            # 3. 接收并处理搜索结果
            # 处理 GRAPH RAG 返回的结果
            # return self._search_file_receive(search_results)
            return send_result
        except Exception as e:
            return {
                "status": "error",
                "message": f"搜索文件工作流执行出错: {str(e)}"
            }

    def _normalize_path(self, path: str) -> str:
        """标准化路径, 确保在基础目录下操作"""
        norm_path = os.path.normpath(os.path.join(self.base_dir, path))
        # 安全检查, 确保路径不超出基础目录
        if not norm_path.startswith(self.base_dir):
            raise ValueError(f"安全限制: 路径必须在 {self.base_dir} 内")
        return norm_path
