import os
import shutil
import json
from typing import Dict, Any
from enum import Enum

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

# functino_result 类
class FunctionResult:
    """函数执行结果类"""
    
    def __init__(self, status: str, message: str, data: Dict[str, Any] = None):
        """
        初始化函数执行结果
        
        Args:
            status: 执行状态, "success" 或 "error"
            message: 执行结果消息
            data: 附加数据, 默认为None
        """
        self.status = status
        self.message = message
        self.data = data or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """将结果转换为字典格式"""
        return {
            "status": self.status,
            "message": self.message,
            "data": self.data
        }

class FileAgent:
    """基于LLM的文件管理Agent"""
    
    def __init__(self, llm_client, base_dir: str = "./"):
        """
        初始化文件管理Agent
        
        Args:
            llm_client: LLM客户端(例如OpenAI API客户端)
            base_dir: 基础目录, 所有操作将在此目录下执行
        """
        self.llm_client = llm_client
        self.base_dir = os.path.abspath(base_dir)
        
    def process(self, user_input: str) -> Dict[str, Any]:
        """
        处理用户输入并执行相应的文件操作
        
        Args:
            user_input: 用户的自然语言输入
            
        Returns:
            Dict: 包含操作结果的字典
        """
        # 1. 解析层: 将自然语言转换为JSON结构
        parsed_data = self._parse_input(user_input)
        
        # 2. 执行层: 根据解析结果执行操作
        if "error" in parsed_data:
            return parsed_data
        
        result = self._execute_operation(parsed_data)
        return result
    
    def _parse_input(self, user_input: str) -> Dict[str, Any]:
        """
        解析层: 将用户自然语言输入解析为结构化JSON
        
        Args:
            user_input: 用户的自然语言输入
            
        Returns:
            Dict: 结构化的JSON数据
        """
        # 构建LLM提示
        prompt = self._create_parse_prompt(user_input)
        
        try:
            # 调用LLM解析用户输入
            response = self._call_llm_with_prompt(prompt)
            parsed_data = json.loads(response)
            
            # 验证解析结果
            if not self._validate_parsed_data(parsed_data):
                return {
                    "error": "无法理解请求, 请提供更明确的文件操作指令"
                }
            
            return parsed_data
        except Exception as e:
            return {
                "error": f"解析输入时出错: {str(e)}"
            }
    
    def _create_parse_prompt(self, user_input: str) -> str:
        """
        创建用于解析用户输入的提示模板
        
        Args:
            user_input: 用户的自然语言输入
            
        Returns:
            str: 格式化的提示
        """
        return f"""
        你是一个文件管理助手, 需要将用户的自然语言指令解析为结构化的JSON格式。

        支持的操作类型包括:
        - create_file: 创建文件
        - create_directory: 创建目录
        - delete_file: 删除文件
        - delete_directory: 删除目录
        - move_file: 移动文件
        - move_directory: 移动目录
        - rename_file: 重命名文件
        - rename_directory: 重命名目录
        - list_files: 列出文件夹内容
        - read_file: 读取文件内容
        - write_file: 写入文件内容

        请分析以下用户输入, 并将其转换为包含operation和parameters字段的JSON结构:

        用户输入: "{user_input}"

        只返回JSON, 不要包含任何额外的文本或解释。如果无法确定操作类型或参数, 请在JSON中包含error字段说明原因。
        """

    def _call_llm_with_prompt(self, prompt: str) -> str:
        """
        调用LLM处理提示并获取响应
        
        Args:
            prompt: 提示内容
            
        Returns:
            str: LLM的响应
        """        
        try:
            response = self.llm_client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一个专业的文件操作解析助手, 擅长将自然语言指令转换为结构化JSON。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            # 处理不同API可能返回的不同响应格式
            content = self._extract_content_from_response(response)
            # 记录原始响应内容, 用于调试
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"LLM响应原始内容: {content}")
            return content
        except Exception as e:
            # 如果API调用失败, 返回错误JSON
            error_msg = str(e)
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"LLM API调用异常: {error_msg}")
            return json.dumps({"error": f"LLM API调用失败: {error_msg}"})
    
    def _extract_content_from_response(self, response):
        """
        从不同格式的LLM响应中提取内容
        
        Args:
            response: LLM响应对象
            
        Returns:
            str: 提取的内容
        """
        # 尝试不同的响应格式
        try:
            # OpenAI格式
            if hasattr(response, 'choices') and hasattr(response.choices[0], 'message'):
                return response.choices[0].message.content
            # 兼容format 1: 可能有message.content
            elif hasattr(response, 'message') and hasattr(response.message, 'content'):
                return response.message.content
            # 兼容format 2: 可能直接有content属性
            elif hasattr(response, 'content'):
                return response.content
            # 兼容format 3: 可能是字典类型
            elif isinstance(response, dict):
                if 'choices' in response and len(response['choices']) > 0:
                    choice = response['choices'][0]
                    if 'message' in choice and 'content' in choice['message']:
                        return choice['message']['content']
                    elif 'text' in choice:
                        return choice['text']
                elif 'content' in response:
                    return response['content']
            # 兼容format 4: 如果是字符串, 直接返回
            elif isinstance(response, str):
                return response
            
            # 如果都不匹配, 尝试将整个响应转为字符串
            return str(response)
        except Exception as e:
            # 出现错误返回错误JSON
            return json.dumps({"error": f"无法从响应中提取内容: {str(e)}"})
    
    def _validate_parsed_data(self, data: Dict[str, Any]) -> bool:
        """
        验证解析结果是否符合预期格式
        
        Args:
            data: 解析后的数据
            
        Returns:
            bool: 验证结果
        """
        if "error" in data:
            return True
            
        if "operation" not in data or "parameters" not in data:
            return False
            
        try:
            # 检查操作类型是否受支持
            op = data["operation"].lower()
            return any(op == op_type.value for op_type in OperationType)
        except:
            return False
    
    def _execute_operation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行层: 执行解析后的文件操作
        
        Args:
            data: 解析后的结构化数据
            
        Returns:
            Dict: 操作结果
        """
        operation = data["operation"].lower()
        parameters = data["parameters"]
        
        # 根据操作类型分发到相应的处理函数
        handlers = {
            OperationType.CREATE_FILE.value: self._create_file,
            OperationType.CREATE_DIRECTORY.value: self._create_directory,
            OperationType.DELETE_FILE.value: self._delete_file,
            OperationType.DELETE_DIRECTORY.value: self._delete_directory,
            OperationType.MOVE_FILE.value: self._move_file,
            OperationType.MOVE_DIRECTORY.value: self._move_directory,
            OperationType.RENAME_FILE.value: self._rename_file,
            OperationType.RENAME_DIRECTORY.value: self._rename_directory,
            OperationType.LIST_FILES.value: self._list_files,
            OperationType.READ_FILE.value: self._read_file,
            OperationType.WRITE_FILE.value: self._write_file,
        }
        
        if operation not in handlers:
            result = FunctionResult(
                status="error",
                message=f"不支持的操作类型: {operation}",
                data={}
            )
            return result.to_dict()

            # return {
            #     "status": "error",
            #     "message": f"不支持的操作类型: {operation}"
            # }
        
        try:
            return handlers[operation](parameters)
        except Exception as e:
            result = FunctionResult(
                status="error",
                message=f"执行操作时出错: {str(e)}",
                data={}
            )

            return result.to_dict()
            # return {
            #     "status": "error",
            #     "message": f"执行操作时出错: {str(e)}"
            # }
    
    def _normalize_path(self, path: str) -> str:
        """标准化路径, 确保在基础目录下操作"""
        norm_path = os.path.normpath(os.path.join(self.base_dir, path))
        # 安全检查, 确保路径不超出基础目录
        if not norm_path.startswith(self.base_dir):
            raise ValueError(f"安全限制: 路径必须在 {self.base_dir} 内")
        return norm_path
        
    #------------------------------------ 以下是各种文件操作的具体实现------------------------------------#
    
    def _create_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """创建文件"""
        if "file_name" not in params or "path" not in params:
            # 设置默认文件名为 new_file.txt
            params["file_name"] = "new_file.txt"
            # 默认路径为当前目录
            params["path"] = "."
            # return {"status": "error", "message": "缺少必要参数: file_name 或 path"}
        
        try:
            file_path = self._normalize_path(os.path.join(params["path"], params["file_name"]))
            content = params.get("content", "")
            
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 检查文件是否已存在
            if os.path.exists(file_path):
                return {"status": "error", "message": f"文件已存在: {params['file_name']}"}
            
            # 创建文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            result = FunctionResult(
                status="success",
                message=f"文件创建成功: {params['file_name']}",
                data={
                    "path": os.path.relpath(file_path, self.base_dir)
                }
            ) 

            return result.to_dict()
            # return {
            #     "status": "success",
            #     "message": f"文件创建成功: {params['file_name']}",
            #     "path": os.path.relpath(file_path, self.base_dir)
            # }
        except Exception as e:
            result = FunctionResult(
                status="error",
                message=str(e),
                data={}
            )

            return result.to_dict()
            # return {"status": "error", "message": str(e)}
    
    def _create_directory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """创建目录"""
        if "directory_name" not in params or "path" not in params:
            # 设置默认目录名为 new_directory
            params["directory_name"] = "new_directory"
            # 默认路径为当前目录
            params["path"] = "."
            # return {"status": "error", "message": "缺少必要参数: directory_name 或 path"}
        
        try:
            dir_path = self._normalize_path(os.path.join(params["path"], params["directory_name"]))
            
            # 检查目录是否已存在
            if os.path.exists(dir_path):
                return {"status": "error", "message": f"目录已存在: {params['directory_name']}"}
            
            # 创建目录
            os.makedirs(dir_path, exist_ok=True)

            result = FunctionResult(
                status="success",
                message=f"目录创建成功: {params['directory_name']}",
                data={
                    "path": os.path.relpath(dir_path, self.base_dir)
                }
            )

            return result.to_dict()                
            # return {
            #     "status": "success",
            #     "message": f"目录创建成功: {params['directory_name']}",
            #     "path": os.path.relpath(dir_path, self.base_dir)
            # }
        except Exception as e:
            result = FunctionResult(
                status="error",
                message=str(e),
                data={}
            )
            return result.to_dict()
            # return {"status": "error", "message": str(e)}
    
    def _delete_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """删除文件"""
        if "file_path" not in params:
            # 默认路径为当前目录
            params["file_path"] = "."
            # return {"status": "error", "message": "缺少必要参数: file_path"}
        
        try:
            file_path = self._normalize_path(params["file_path"])
            
            # 检查文件是否存在
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                return {"status": "error", "message": f"文件不存在: {params['file_path']}"}
            
            # 删除文件
            os.remove(file_path)
                
            return {
                "status": "success",
                "message": f"文件删除成功: {params['file_path']}"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _delete_directory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """删除目录"""
        if "directory_path" not in params:
            return {"status": "error", "message": "缺少必要参数: directory_path"}
        
        try:
            dir_path = self._normalize_path(params["directory_path"])
            
            # 检查目录是否存在
            if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
                return {"status": "error", "message": f"目录不存在: {params['directory_path']}"}
            
            # 删除目录
            shutil.rmtree(dir_path)
                
            return {
                "status": "success",
                "message": f"目录删除成功: {params['directory_path']}"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _move_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """移动文件"""
        if "source_path" not in params or "destination_path" not in params:
            return {"status": "error", "message": "缺少必要参数: source_path 或 destination_path"}
        
        try:
            src_path = self._normalize_path(params["source_path"])
            dst_path = self._normalize_path(params["destination_path"])
            
            # 检查源文件是否存在
            if not os.path.exists(src_path) or not os.path.isfile(src_path):
                return {"status": "error", "message": f"源文件不存在: {params['source_path']}"}
            
            # 确保目标目录存在
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            
            # 检查目标文件是否已存在
            if os.path.exists(dst_path):
                return {"status": "error", "message": f"目标文件已存在: {params['destination_path']}"}
            
            # 移动文件
            shutil.move(src_path, dst_path)
                
            return {
                "status": "success",
                "message": f"文件移动成功: {params['source_path']} -> {params['destination_path']}",
                "new_path": os.path.relpath(dst_path, self.base_dir)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    
    def _move_directory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """移动目录"""
        if "source_path" not in params or "destination_path" not in params:
            return {"status": "error", "message": "缺少必要参数: source_path 或 destination_path"}
        
        try:
            src_path = self._normalize_path(params["source_path"])
            dst_path = self._normalize_path(params["destination_path"])
            
            # 检查源目录是否存在
            if not os.path.exists(src_path) or not os.path.isdir(src_path):
                return {"status": "error", "message": f"源目录不存在: {params['source_path']}"}
            
            # 检查目标目录是否已存在
            if os.path.exists(dst_path):
                return {"status": "error", "message": f"目标目录已存在: {params['destination_path']}"}
            
            # 确保目标父目录存在
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            
            # 移动目录
            shutil.move(src_path, dst_path)
                
            return {
                "status": "success",
                "message": f"目录移动成功: {params['source_path']} -> {params['destination_path']}",
                "new_path": os.path.relpath(dst_path, self.base_dir)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _rename_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """重命名文件"""
        if "file_path" not in params or "new_name" not in params:
            # 设置默认新文件名为 new_file.txt
            params["new_name"] = "rename_file.txt"
            # 默认路径为当前目录
            params["file_path"] = "."
            # return {"status": "error", "message": "缺少必要参数: file_path 或 new_name"}
        
        try:
            file_path = self._normalize_path(params["file_path"])
            dir_path = os.path.dirname(file_path)
            new_path = os.path.join(dir_path, params["new_name"])
            
            # 检查源文件是否存在
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                return {"status": "error", "message": f"文件不存在: {params['file_path']}"}
            
            # 检查新文件名是否已存在
            if os.path.exists(new_path):
                return {"status": "error", "message": f"文件已存在: {params['new_name']}"}
            
            # 重命名文件
            os.rename(file_path, new_path)
                
            return {
                "status": "success",
                "message": f"文件重命名成功: {params['file_path']} -> {params['new_name']}",
                "new_path": os.path.relpath(new_path, self.base_dir)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _rename_directory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """重命名目录"""
        if "directory_path" not in params or "new_name" not in params:
            # 设置默认新文件名为 new_file.txt
            params["new_name"] = "rename_dir"
            # 默认路径为当前目录
            params["directory_path"] = "."
            # return {"status": "error", "message": "缺少必要参数: directory_path 或 new_name"}
        
        try:
            dir_path = self._normalize_path(params["directory_path"])
            parent_dir = os.path.dirname(dir_path)
            new_path = os.path.join(parent_dir, params["new_name"])
            
            # 检查源目录是否存在
            if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
                return {"status": "error", "message": f"目录不存在: {params['directory_path']}"}
            
            # 检查新目录名是否已存在
            if os.path.exists(new_path):
                return {"status": "error", "message": f"目录已存在: {params['new_name']}"}
            
            # 重命名目录
            os.rename(dir_path, new_path)
                
            return {
                "status": "success",
                "message": f"目录重命名成功: {params['directory_path']} -> {params['new_name']}",
                "new_path": os.path.relpath(new_path, self.base_dir)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
            
    def _list_files(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """列出目录内容"""
        if "directory_path" not in params:
            # 默认路径为当前目录
            params["directory_path"] = "."
            # return {"status": "error", "message": "缺少必要参数: directory_path"}
        
        try:
            dir_path = self._normalize_path(params["directory_path"])
            
            # 检查目录是否存在
            if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
                return {"status": "error", "message": f"目录不存在: {params['directory_path']}"}
            
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
                "contents": {
                    "files": files,
                    "directories": directories
                }
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _read_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """读取文件内容"""
        if "file_path" not in params:
            # 默认路径为当前目录
            params["file_path"] = "."
            # return {"status": "error", "message": "缺少必要参数: file_path"}
        
        try:
            file_path = self._normalize_path(params["file_path"])
            
            # 检查文件是否存在
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                return {"status": "error", "message": f"文件不存在: {params['file_path']}"}
            
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            return {
                "status": "success",
                "message": f"成功读取文件: {params['file_path']}",
                "content": content
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
        
    def _write_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """写入文件内容"""
        if "file_path" not in params and "content" in params:
            # 如果提供了file_name但没有file_path, 将file_name作为file_path使用
            if "file_name" in params:
                params["file_path"] = params["file_name"]
            else:
                # 默认路径为当前目录
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
            mode = 'a' if append else 'w'
            with open(file_path, mode, encoding='utf-8') as f:
                f.write(content)
                
            return {
                "status": "success",
                "message": f"成功{'追加' if append else '写入'}文件: {params['file_path']}",
                "path": os.path.relpath(file_path, self.base_dir)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
