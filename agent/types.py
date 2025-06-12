from typing import Dict, Any, NotRequired, TypedDict


class ToolCallResult(TypedDict):
    """工具调用结果类型"""

    status: str  # "success" 或 "error"
    message: str  # 操作结果消息
    data: NotRequired[Dict[str, Any]]  # 附加数据，例如文件路径等
