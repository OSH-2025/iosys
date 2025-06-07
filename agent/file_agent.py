import json
from typing import Dict, Any, Callable, List
from enum import Enum
from functools import wraps
from openai.types.chat import ChatCompletion

from openai import Client

from .config import AgentConfig


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
                "parameters": parameters,
            },
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
        self.fs = config.fs
        self.base_dir = config.base_dir
        self.llm_client = llm_client
        self.tools = self._collect_tools()
        self.tool_handlers = self._collect_tool_handlers()

    def _collect_tools(self) -> List[Dict[str, Any]]:
        """自动收集所有注册的工具配置"""
        tools = []
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, "_tool_config"):
                tools.append(attr._tool_config)
        return tools

    def _collect_tool_handlers(self) -> Dict[str, Callable]:
        """自动收集所有工具处理函数"""
        handlers = {}
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, "_tool_name"):
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
        # 调用LLM获取function call
        response = self._call_llm_with_tools(user_input)

        # 执行function call
        return self._execute_function_call(response)

    def _call_llm_with_tools(self, user_input: str):
        """
        调用LLM并获取function call响应

        Args:
            user_input: 用户输入

        Returns:
            LLM响应对象
        """
        return self.llm_client.chat.completions.create(
            model=self.config.llm_model,
            messages=[
                {
                    "role": "system",
                    "content": "你是一个文件管理助手，可以帮助用户进行各种文件操作。根据用户的需求，选择合适的工具来完成任务。",
                },
                {"role": "user", "content": user_input},
            ],
            tools=self.tools,
            tool_choice="auto",
        )

    def _execute_function_call(self, response: ChatCompletion) -> Dict[str, Any]:
        """
        执行function call

        Args:
            response: LLM响应

        Returns:
            Dict: 执行结果
        """
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
                if function_name in self.tool_handlers:
                    result = self.tool_handlers[function_name](function_args)
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

    def _path_to_id(self, path: str) -> str:
        """将路径转换为文件系统节点ID"""
        # 移除前导的"./"或"."
        if path.startswith("./"):
            path = path[2:]
        elif path == ".":
            path = ""
        # 使用路径作为ID，可以根据实际需要调整
        return "/" + path

    def _id_to_relative_path(self, node_id: str) -> str:
        """将节点ID转换为相对路径显示"""
        return node_id if node_id != "root" else "."

    # ------------------------------------ 工具函数定义 ------------------------------------

    @tool(
        name="create_file",
        description="创建新文件",
        parameters={
            "type": "object",
            "properties": {
                "file_name": {"type": "string", "description": "文件名"},
                "path": {"type": "string", "description": "文件路径", "default": "."},
                "content": {"type": "string", "description": "文件内容", "default": ""},
            },
            "required": ["file_name"],
        },
    )
    def _create_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """创建文件"""
        if "file_name" not in params:
            params["file_name"] = "new_file.txt"
        if "path" not in params:
            params["path"] = "."

        # 构造文件路径
        if params["path"] == ".":
            file_path = params["file_name"]
        else:
            file_path = f"{params['path']}/{params['file_name']}"

        file_id = self._path_to_id(file_path)
        content = params.get("content", "")

        # 检查文件是否已存在
        if self.fs.exists(file_id):
            return {
                "status": "error",
                "message": f"文件已存在: {params['file_name']}",
            }

        # 确保父目录存在
        parent_path = "/".join(file_id.split("/")[:-1])
        parent_id = self._path_to_id(parent_path)
        parent_node = self.fs.get_dir_node(parent_id)
        if not parent_node:
            return {
                "status": "error",
                "message": f"父目录不存在: {parent_path}",
            }

        # 创建文件节点并写入内容
        node = parent_node.insert_file(params["file_name"])
        node.write(content.encode("utf-8"))

        return {
            "status": "success",
            "message": f"文件创建成功: {params['file_name']}",
            "data": {"path": self._id_to_relative_path(file_id)},
        }

    @tool(
        name="create_directory",
        description="创建新目录",
        parameters={
            "type": "object",
            "properties": {
                "directory_name": {"type": "string", "description": "目录名"},
                "path": {"type": "string", "description": "父目录路径", "default": "."},
            },
            "required": ["directory_name"],
        },
    )
    def _create_directory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """创建目录"""
        if "directory_name" not in params:
            params["directory_name"] = "new_directory"
        if "path" not in params:
            params["path"] = "."

        # 构造目录路径
        if params["path"] == ".":
            dir_path = params["directory_name"]
        else:
            dir_path = f"{params['path']}/{params['directory_name']}"

        dir_id = self._path_to_id(dir_path)

        # 检查目录是否已存在
        if self.fs.exists(dir_id):
            return {
                "status": "error",
                "message": f"目录已存在: {params['directory_name']}",
            }

        # 确保父目录存在
        parent_id = self._path_to_id(params["path"])
        parent_node = self.fs.get_dir_node(parent_id)
        if not parent_node:
            return {
                "status": "error",
                "message": f"父目录不存在: {params['path']}",
            }

        # 创建目录节点
        parent_node.insert_dir(params["directory_name"])
        return {
            "status": "success",
            "message": f"目录创建成功: {params['directory_name']}",
            "data": {"path": self._id_to_relative_path(dir_id)},
        }

    @tool(
        name="delete_file",
        description="删除文件",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "要删除的文件路径"}
            },
            "required": ["file_path"],
        },
    )
    def _delete_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """删除文件"""
        if "file_path" not in params:
            return {"status": "error", "message": "缺少必要参数: file_path"}

        file_id = self._path_to_id(params["file_path"])

        # 检查文件是否存在
        file_node = self.fs.get_file_node(file_id)
        if not file_node:
            return {
                "status": "error",
                "message": f"文件不存在: {params['file_path']}",
            }

        # 删除文件
        self.fs.remove(file_id)

        return {
            "status": "success",
            "message": f"文件删除成功: {params['file_path']}",
        }

    @tool(
        name="delete_directory",
        description="删除目录",
        parameters={
            "type": "object",
            "properties": {
                "directory_path": {"type": "string", "description": "要删除的目录路径"}
            },
            "required": ["directory_path"],
        },
    )
    def _delete_directory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """删除目录"""
        if "directory_path" not in params:
            return {"status": "error", "message": "缺少必要参数: directory_path"}

        dir_id = self._path_to_id(params["directory_path"])

        # 检查目录是否存在
        dir_node = self.fs.get_dir_node(dir_id)
        if not dir_node:
            return {
                "status": "error",
                "message": f"目录不存在: {params['directory_path']}",
            }

        # 删除目录
        self.fs.remove(dir_id)

        return {
            "status": "success",
            "message": f"目录删除成功: {params['directory_path']}",
        }

    @tool(
        name="move_file",
        description="移动文件",
        parameters={
            "type": "object",
            "properties": {
                "source_path": {"type": "string", "description": "源文件路径"},
                "destination_path": {"type": "string", "description": "目标文件路径"},
            },
            "required": ["source_path", "destination_path"],
        },
    )
    def _move_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """移动文件"""
        if "source_path" not in params or "destination_path" not in params:
            return {
                "status": "error",
                "message": "缺少必要参数: source_path 或 destination_path",
            }

        src_id = self._path_to_id(params["source_path"])
        dst_id = self._path_to_id(params["destination_path"])

        # 检查源文件是否存在
        src_node = self.fs.get_file_node(src_id)
        if not src_node:
            return {
                "status": "error",
                "message": f"源文件不存在: {params['source_path']}",
            }

        # 检查目标文件是否已存在
        if self.fs.exists(dst_id):
            return {
                "status": "error",
                "message": f"目标文件已存在: {params['destination_path']}",
            }

        # 读取源文件内容
        content = self.fs.read(src_id)

        # 写入目标文件
        try:
            self.fs.write(dst_id, content)
        except FileNotFoundError:
            return {
                "status": "error",
                "message": f"无法创建目标文件，请确保目标目录存在: {params['destination_path']}",
            }

        # 删除源文件
        self.fs.remove(src_id)

        return {
            "status": "success",
            "message": f"文件移动成功: {params['source_path']} -> {params['destination_path']}",
            "data": {"new_path": self._id_to_relative_path(dst_id)},
        }

    @tool(
        name="move_directory",
        description="移动目录",
        parameters={
            "type": "object",
            "properties": {
                "source_path": {"type": "string", "description": "源目录路径"},
                "destination_path": {"type": "string", "description": "目标目录路径"},
            },
            "required": ["source_path", "destination_path"],
        },
    )
    def _move_directory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """移动目录"""
        if "source_path" not in params or "destination_path" not in params:
            return {
                "status": "error",
                "message": "缺少必要参数: source_path 或 destination_path",
            }

        src_id = self._path_to_id(params["source_path"])
        dst_id = self._path_to_id(params["destination_path"])

        # 检查源目录是否存在
        src_node = self.fs.get_dir_node(src_id)
        if not src_node:
            return {
                "status": "error",
                "message": f"源目录不存在: {params['source_path']}",
            }

        # 检查目标目录是否已存在
        if self.fs.exists(dst_id):
            return {
                "status": "error",
                "message": f"目标目录已存在: {params['destination_path']}",
            }

        # 目录移动功能需要文件系统的具体支持
        return {
            "status": "error",
            "message": "目录移动功能需要文件系统支持",
        }

    @tool(
        name="rename_file",
        description="重命名文件",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "要重命名的文件路径"},
                "new_name": {"type": "string", "description": "新文件名"},
            },
            "required": ["file_path", "new_name"],
        },
    )
    def _rename_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """重命名文件"""
        if "file_path" not in params or "new_name" not in params:
            return {
                "status": "error",
                "message": "缺少必要参数: file_path 或 new_name",
            }

        file_id = self._path_to_id(params["file_path"])

        # 构造新路径
        if "/" in file_id:
            dir_path = "/".join(file_id.split("/")[:-1])
            new_path = f"{dir_path}/{params['new_name']}"
        else:
            new_path = params["new_name"]

        new_id = self._path_to_id(new_path)

        # 检查源文件是否存在
        file_node = self.fs.get_file_node(file_id)
        if not file_node:
            return {
                "status": "error",
                "message": f"文件不存在: {params['file_path']}",
            }

        # 检查新文件名是否已存在
        if self.fs.exists(new_id):
            return {
                "status": "error",
                "message": f"文件已存在: {params['new_name']}",
            }

        # 读取文件内容
        content = self.fs.read(file_id)

        # 写入新文件
        self.fs.write(new_id, content)

        # 删除原文件
        self.fs.remove(file_id)

        return {
            "status": "success",
            "message": f"文件重命名成功: {params['file_path']} -> {params['new_name']}",
            "data": {"new_path": self._id_to_relative_path(new_id)},
        }

    @tool(
        name="rename_directory",
        description="重命名目录",
        parameters={
            "type": "object",
            "properties": {
                "directory_path": {
                    "type": "string",
                    "description": "要重命名的目录路径",
                },
                "new_name": {"type": "string", "description": "新目录名"},
            },
            "required": ["directory_path", "new_name"],
        },
    )
    def _rename_directory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """重命名目录"""
        if "directory_path" not in params or "new_name" not in params:
            return {
                "status": "error",
                "message": "缺少必要参数: directory_path 或 new_name",
            }

        dir_id = self._path_to_id(params["directory_path"])

        # 构造新路径
        if "/" in dir_id:
            parent_path = "/".join(dir_id.split("/")[:-1])
            new_path = f"{parent_path}/{params['new_name']}"
        else:
            new_path = params["new_name"]

        new_id = self._path_to_id(new_path)

        # 检查源目录是否存在
        dir_node = self.fs.get_dir_node(dir_id)
        if not dir_node:
            return {
                "status": "error",
                "message": f"目录不存在: {params['directory_path']}",
            }

        # 检查新目录名是否已存在
        if self.fs.exists(new_id):
            return {
                "status": "error",
                "message": f"目录已存在: {params['new_name']}",
            }

        # 目录重命名功能需要文件系统的具体支持
        return {
            "status": "error",
            "message": "目录重命名功能需要文件系统支持",
        }

    @tool(
        name="list_files",
        description="列出目录内容",
        parameters={
            "type": "object",
            "properties": {
                "directory_path": {
                    "type": "string",
                    "description": "目录路径",
                    "default": ".",
                }
            },
        },
    )
    def _list_files(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """列出目录内容"""
        if "directory_path" not in params:
            params["directory_path"] = "."

        dir_id = self._path_to_id(params["directory_path"])

        # 检查目录是否存在
        dir_node = self.fs.get_dir_node(dir_id)
        if not dir_node:
            return {
                "status": "error",
                "message": f"目录不存在: {params['directory_path']}",
            }

        # 列出目录内容
        children = dir_node.children()
        files = []
        directories = []

        for child in children:
            if child.type == "file":
                files.append(child.name)
            elif child.type == "dir":
                directories.append(child.name)

        return {
            "status": "success",
            "message": f"成功列出目录内容: {params['directory_path']}",
            "data": {"contents": {"files": files, "directories": directories}},
        }

    @tool(
        name="read_file",
        description="读取文件内容",
        parameters={
            "type": "object",
            "properties": {"file_path": {"type": "string", "description": "文件路径"}},
            "required": ["file_path"],
        },
    )
    def _read_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """读取文件内容"""
        if "file_path" not in params:
            return {"status": "error", "message": "缺少必要参数: file_path"}

        file_id = self._path_to_id(params["file_path"])

        # 检查文件是否存在
        file_node = self.fs.get_file_node(file_id)
        if not file_node:
            return {
                "status": "error",
                "message": f"文件不存在: {params['file_path']}",
            }

        # 读取文件内容
        content_bytes = self.fs.read(file_id)
        content = content_bytes.decode("utf-8")

        return {
            "status": "success",
            "message": f"成功读取文件: {params['file_path']}",
            "data": {"content": content},
        }

    @tool(
        name="write_file",
        description="写入文件内容",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "文件路径"},
                "content": {"type": "string", "description": "要写入的内容"},
                "append": {
                    "type": "boolean",
                    "description": "是否追加模式",
                    "default": False,
                },
            },
            "required": ["file_path", "content"],
        },
    )
    def _write_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """写入文件内容"""
        if "content" not in params:
            return {"status": "error", "message": "缺少必要参数: content"}

        if "file_path" not in params:
            if "file_name" in params:
                params["file_path"] = params["file_name"]
            else:
                return {"status": "error", "message": "缺少必要参数: file_path"}

        file_id = self._path_to_id(params["file_path"])
        content = params["content"]
        append = params.get("append", False)

        if append and self.fs.exists(file_id):
            # 追加模式：先读取现有内容，然后追加
            existing_content = self.fs.read(file_id).decode("utf-8")
            content = existing_content + content

        # 写入文件
        self.fs.write(file_id, content.encode("utf-8"))

        return {
            "status": "success",
            "message": f"成功{'追加' if append else '写入'}文件: {params['file_path']}",
            "data": {"path": self._id_to_relative_path(file_id)},
        }

    # 这里只返回大模型解析出的.json格式数据, 其中需要包含:
    # 特征词序列(例如要求查询和某些关键词有关的文件),
    # 限制序列(例如明确的文件名),
    # 搜索地址(也就是在哪一个文件夹下搜素)
    # 发给 GRAPH RAG 部分
    def _search_file_send(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """搜索文件"""
        # 提取搜索参数
        key_words = params.get("key_words", [])
        constraint = params.get("constraint", [])
        search_path = params.get("search_path", ".")

        # 转换为文件系统ID
        search_id = self._path_to_id(search_path)

        # 检查路径是否存在
        if not self.fs.exists(search_id):
            return {"status": "error", "message": f"搜索路径不存在: {search_path}"}

        # 手动添加file_name到限制序列
        if "file_name" in params:
            constraint.append(params["file_name"])

        # 构建发送给 GRAPH RAG 的数据结构
        search_data = {
            "key_words": key_words,  # 特征词序列
            "constraint": constraint,  # 限制序列
            "search_path": search_id,  # 搜索地址
        }

        return {
            "status": "success",
            "message": "搜索参数已准备完成，等待发送到 GRAPH RAG",
            "data": search_data,
        }

    def _search_file_receive(self, search_results: Dict[str, Any]) -> Dict[str, Any]:
        """接收搜索结果"""
        # 处理搜索结果
        file_list = search_results.get("file_list", [])
        weights = search_results.get("weights", [])
        # description = search_results.get("description", [])

        if not file_list:
            return {"status": "success", "message": "未找到相关文件"}

        return {
            "status": "success",
            "message": f"找到 {len(file_list)} 个相关文件",
            "data": {
                "file_list": file_list,
                "weights": weights,
                # "description": description
            },
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
                    "description": "特征词序列",
                },
                "constraint": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "限制序列",
                },
                "search_path": {
                    "type": "string",
                    "description": "搜索地址",
                    "default": ".",
                },
                "file_name": {"type": "string", "description": "文件名限制"},
            },
            "required": ["key_words"],
        },
    )
    def _search_file_workflow(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """搜索文件工作流，协调发送请求和接收结果"""
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
