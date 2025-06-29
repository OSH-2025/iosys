from typing import Dict, Any, Callable, List
from functools import wraps
from openai.types.shared_params.function_parameters import FunctionParameters


from .types import ToolCallResult
from .config import AgentConfig


def tool(name: str, description: str, parameters: FunctionParameters):
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
        wrapper._tool_config = {  # type: ignore
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
        }
        wrapper._tool_name = name  # type: ignore
        return wrapper

    return decorator


class FileAgent:
    """基于LLM的文件管理Agent"""

    def __init__(self, config: AgentConfig):
        """
        初始化文件管理Agent

        Args:
            config: Agent配置
            llm_client: LLM客户端(例如OpenAI API客户端)
        """
        self.config = config
        self.fs = config.fs
        self.llm_client = config.llm
        self.tool_configs = self._collect_tool_configs()
        self.tool_handlers = self._collect_tool_handlers()

    def _collect_tool_configs(self) -> List[Dict[str, Any]]:
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

    def _normalize_path(self, path: str) -> str:
        """将路径转换为文件系统节点ID"""
        # if not path:
        #     return "/"

        path = path.strip()
        # 移除前导的"./"或"."
        if path.startswith("./"):
            path = path[2:]
        elif path == ".":
            path = ""
        # 使用路径作为ID，可以根据实际需要调整
        return ("/" + path).replace("\\", "/").replace("//", "/").rstrip("/")

    def get_tool_configs(self) -> List[Dict[str, Any]]:
        """获取所有工具配置"""
        return self.tool_configs

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
    def _create_file(self, params: Dict[str, Any]) -> ToolCallResult:
        """创建文件"""
        parent_path = self._normalize_path(params.get("path", ""))
        file_name = params.get("file_name", "new_file.txt")
        content = params.get("content", "")

        # 构建完整的文件路径
        path = self._normalize_path(f"{parent_path}/{file_name}")
        print(f"创建文件: {path}")

        # 检查文件是否已存在
        if self.fs.get_node(path):
            return {
                "status": "success",
                "message": f"文件已存在: {path}",
            }

        # self.fs.write_file(path, content.encode("utf-8"))

        # return {
        #     "status": "success",
        #     "message": f"文件创建成功: {params['file_name']}",
        #     "data": {"path": path},
        # }
        try:
            self.fs.write_file(path, content.encode("utf-8"))
            return {
                "status": "success",
                "message": f"文件创建成功: {params['file_name']}",
                "data": {"path": path},
            }
        except Exception as e:
            return {
                "status": "success",
                "message": f"文件创建失败: {str(e)}",
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
    def _create_directory(self, params: Dict[str, Any]) -> ToolCallResult:
        """创建目录"""
        parent_path = self._normalize_path(params.get("path", "/"))
        directory_name = params.get("directory_name", "new_directory")

        if not directory_name:
            return {"status": "error", "message": "目录名不能为空"}
        dir_path = self._normalize_path(f"{parent_path}/{directory_name}")

        # 检查目录是否已存在
        if self.fs.get_node(dir_path):
            return {
                "status": "success",
                "message": f"目录已存在: {params['directory_name']}",
            }

        # 创建目录节点
        # self.fs.ensure_directory(dir_path)
        # return {
        #     "status": "success",
        #     "message": f"目录创建成功: {dir_path}",
        #     "data": {"path": dir_path},
        # }

        # 手动创建目录结构
        self.fs.create_directory(dir_path)
        return {
            "status": "success",
            "message": f"目录创建成功: {dir_path}",
            "data": {"path": dir_path},
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
    def _delete_file(self, params: Dict[str, Any]) -> ToolCallResult:
        """删除文件"""
        if "file_path" not in params:
            return {"status": "error", "message": "缺少必要参数: file_path"}

        file_id = self._normalize_path(params["file_path"])

        # 检查文件是否存在
        file_node = self.fs.get_node(file_id)
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
    def _delete_directory(self, params: Dict[str, Any]) -> ToolCallResult:
        """删除目录"""
        if "directory_path" not in params:
            return {"status": "error", "message": "缺少必要参数: directory_path"}

        dir_id = self._normalize_path(params["directory_path"])

        # 检查目录是否存在
        # dir_node = self.fs.get_dir_node(dir_id)
        dir_node = self.fs.get_node(dir_id)
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
    def _move_file(self, params: Dict[str, Any]) -> ToolCallResult:
        """移动文件"""
        if "source_path" not in params or "destination_path" not in params:
            return {
                "status": "error",
                "message": "缺少必要参数: source_path 或 destination_path",
            }

        src_id = self._normalize_path(params["source_path"])
        dst_id = self._normalize_path(params["destination_path"])

        # 检查源文件是否存在
        # src_node = self.fs.get_file_node(src_id)
        src_node = self.fs.get_node(src_id)
        if not src_node:
            return {
                "status": "error",
                "message": f"源文件不存在: {params['source_path']}",
            }

        # 检查目标文件是否已存在
        # if self.fs.exists(dst_id):
        if self.fs.get_node(dst_id):
            return {
                "status": "error",
                "message": f"目标文件已存在: {params['destination_path']}",
            }

        # 读取源文件内容
        content = self.fs.read(src_id)

        # 写入目标文件
        try:
            self.fs.write_file(dst_id, content)
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
            "data": {"new_path": dst_id},
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
    def _move_directory(self, params: Dict[str, Any]) -> ToolCallResult:
        """移动目录"""
        if "source_path" not in params or "destination_path" not in params:
            return {
                "status": "error",
                "message": "缺少必要参数: source_path 或 destination_path",
            }

        # 需要手动把源目录名添加到路径中
        # params["destination_path"] += "/" + params["source_path"].split("/")[-1]

        src_id = self._normalize_path(params["source_path"])
        dst_id = self._normalize_path(params["destination_path"])

        # 检查源目录是否存在
        # src_node = self.fs.get_dir_node(src_id)
        src_node = self.fs.get_node(src_id)
        if not src_node:
            return {
                "status": "error",
                "message": f"源目录不存在: {params['source_path']}",
            }

        # 检查目标目录是否已存在
        # if self.fs.exists(dst_id):
        if self.fs.get_node(dst_id):
            return {
                "status": "error",
                "message": f"目标目录已存在: {params['destination_path']}",
            }

        self.fs.move(src_id, dst_id)

        return {
            "status": "success",
            "message": f"目录移动成功: {params['source_path']} -> {params['destination_path']}",
            "data": {"new_path": dst_id},
        }

        # 目录移动功能需要文件系统的具体支持
        # return {
        #     "status": "error",
        #     "message": "目录移动功能需要文件系统支持",
        # }

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
    def _rename_file(self, params: Dict[str, Any]) -> ToolCallResult:
        """重命名文件"""
        if "file_path" not in params or "new_name" not in params:
            return {
                "status": "error",
                "message": "缺少必要参数: file_path 或 new_name",
            }

        file_id = self._normalize_path(params["file_path"])

        # 构造新路径
        if "/" in file_id:
            dir_path = "/".join(file_id.split("/")[:-1])
            new_path = f"{dir_path}/{params['new_name']}"
        else:
            new_path = params["new_name"]

        new_id = self._normalize_path(new_path)

        # 检查源文件是否存在
        # file_node = self.fs.get_file_node(file_id)
        file_node = self.fs.get_node(file_id)
        if not file_node:
            return {
                "status": "error",
                "message": f"文件不存在: {params['file_path']}",
            }

        # 检查新文件名是否已存在
        # if self.fs.exists(new_id):
        if self.fs.get_node(new_id):
            return {
                "status": "error",
                "message": f"文件已存在: {params['new_name']}",
            }

        # 读取文件内容
        content = self.fs.read(file_id)

        # 写入新文件
        self.fs.write_file(new_id, content)

        # 删除原文件
        self.fs.remove(file_id)

        return {
            "status": "success",
            "message": f"文件重命名成功: {params['file_path']} -> {params['new_name']}",
            "data": {"new_path": new_id},
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
    def _rename_directory(self, params: Dict[str, Any]) -> ToolCallResult:
        """重命名目录"""
        if "directory_path" not in params or "new_name" not in params:
            return {
                "status": "error",
                "message": "缺少必要参数: directory_path 或 new_name",
            }

        dir_id = self._normalize_path(params["directory_path"])

        # 构造新路径
        if "/" in dir_id:
            parent_path = "/".join(dir_id.split("/")[:-1])
            new_path = f"{parent_path}/{params['new_name']}"
        else:
            new_path = params["new_name"]

        new_id = self._normalize_path(new_path)

        # 检查源目录是否存在
        # dir_node = self.fs.get_dir_node(dir_id)
        dir_node = self.fs.get_node(dir_id)
        if not dir_node:
            return {
                "status": "error",
                "message": f"目录不存在: {params['directory_path']}",
            }

        # 检查新目录名是否已存在
        # if self.fs.exists(new_id):
        if self.fs.get_node(new_id):
            return {
                "status": "error",
                "message": f"目录已存在: {params['new_name']}",
            }

        # 目录重命名功能需要文件系统的具体支持
        # return {
        #     "status": "error",
        #     "message": "目录重命名功能需要文件系统支持",
        # }
        self.fs.move(dir_id, new_id)
        return {
            "status": "success",
            "message": f"目录重命名成功: {params['directory_path']} -> {params['new_name']}",
            "data": {"new_path": new_id},
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
    def _list_files(self, params: Dict[str, Any]) -> ToolCallResult:
        """列出目录内容"""
        if "directory_path" not in params:
            params["directory_path"] = "."

        dir_id = self._normalize_path(params["directory_path"])

        # 检查目录是否存在
        dir_node = self.fs.get_node(dir_id)
        if not dir_node:
            return {
                "status": "error",
                "message": f"目录不存在: {params['directory_path']}",
            }

        # 列出目录内容
        children = []

        for child in dir_node.children():
            children.append(
                {
                    "path": child.path,
                    "name": child.name,
                }
            )

        return {
            "status": "success",
            "message": f"成功列出目录内容: {params['directory_path']}",
            "data": {"children": children},
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
    def _read_file(self, params: Dict[str, Any]) -> ToolCallResult:
        """读取文件内容"""
        if "file_path" not in params:
            params["file_path"] = params.get("file_name", "/")
            # return {"status": "error", "message": "缺少必要参数: file_path"}

        file_id = self._normalize_path(params["file_path"])

        # 检查文件是否存在
        file_node = self.fs.get_node(file_id)
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
    def _write_file(self, params: Dict[str, Any]) -> ToolCallResult:
        """写入文件内容"""
        if "content" not in params:
            return {"status": "error", "message": "缺少必要参数: content"}

        if "file_path" not in params:
            if "file_name" in params:
                params["file_path"] = params["file_name"]
            else:
                return {"status": "error", "message": "缺少必要参数: file_path"}

        file_id = self._normalize_path(params["file_path"])
        content = params["content"]
        append = params.get("append", False)

        # if append and self.fs.exists(file_id):
        if append and self.fs.get_node(file_id):
            # 追加模式：先读取现有内容，然后追加
            existing_content = self.fs.read(file_id).decode("utf-8")
            content = existing_content + content

        # 写入文件
        self.fs.write_file(file_id, content.encode("utf-8"))

        return {
            "status": "success",
            "message": f"成功{'追加' if append else '写入'}文件: {params['file_path']}",
            "data": {"path": file_id},
        }

    def _search_file_receive(self, search_results: Dict[str, Any]) -> ToolCallResult:
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
        name="semantic_search_files",
        description="基于语义embedding模型搜索文件",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "自然语言查询内容",
                },
            },
            "required": ["query"],
        },
    )
    async def _semantic_search_files(self, params: Dict[str, Any]) -> ToolCallResult:
        """基于embedding模型的语义文件搜索"""
        try:
            query = params["query"]

            # 调试信息
            print(f"语义搜索查询: {query}")

            # 使用RAG查询接口
            result = await self.config.rag.query.query_nodes(
                query,
                include_glob=["**/*"],
                exclude_glob=[],
            )

            # print(f"response: {result.response}\nfiles: {result.files}\nnodes: {result.nodes}")
            files = result.files
            nodes = result.nodes

            data = []

            for i, file in enumerate(files):
                data.append(
                    {
                        "file": file,
                        "score": abs(nodes[i].score),  # type: ignore
                    }
                )

            data = sorted(data, key=lambda x: x["score"], reverse=False)

            return {
                "status": "success",
                "message": f"成功找到 {len(data)} 个相关文件",
                "data": data,  # type: ignore
            }

        except Exception as e:
            print(f"语义搜索错误: {str(e)}")
            return {
                "status": "error",
                "message": f"语义搜索失败: {str(e)}",
                "data": {"query": params.get("query", "")},
            }

    @tool(
        name="get_file_info",
        description="获取文件或目录信息",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string", "description": "文件或目录路径"}},
            "required": ["path"],
        },
    )
    def _get_file_info(self, params: Dict[str, Any]) -> ToolCallResult:
        """获取文件或目录信息"""
        if "path" not in params:
            return {"status": "error", "message": "缺少必要参数: path"}

        path_id = self._normalize_path(params["path"])

        # 检查节点是否存在
        node = self.fs.get_node(path_id)
        if not node:
            return {
                "status": "error",
                "message": f"路径不存在: {params['path']}",
            }

        # 获取节点信息
        info = {
            "path": node.path,
            "name": node.name,
            "type": node.get_meta("type", "unknown"),
            "metadata": node._meta.copy(),
        }

        # 如果是目录，添加子项数量
        if node.get_meta("type") == "directory":
            try:
                children = node.children()
                info["children_count"] = len(children)
                info["children_names"] = [child.name for child in children]
            except Exception:
                info["children_count"] = 0
                info["children_names"] = []
        else:
            # 如果是文件，添加文件大小
            try:
                content = node.read()
                info["size_bytes"] = len(content)
            except Exception:
                info["size_bytes"] = 0

        return {
            "status": "success",
            "message": f"成功获取路径信息: {params['path']}",
            "data": info,
        }
