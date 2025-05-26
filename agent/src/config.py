import os
from typing import Optional
import logging


class AgentConfig:
    """Agent 配置类"""

    def __init__(
        self,
        llm_api_key: Optional[str] = None,
        llm_model: Optional[str] = None,
        llm_api_base: Optional[str] = None,
        base_dir: str = "./",
        log_level: str = "INFO",
    ):
        """
        初始化 Agent 配置

        Args:
            llm_api_key: LLM API 密钥
            llm_model: 使用的 LLM 模型名称
            llm_api_base: LLM API 基础URL
            base_dir: 文件操作的基础目录
            log_level: 日志级别
        """

        self.llm_api_key = llm_api_key or os.environ.get("LLM_API_KEY")
        self.llm_model = llm_model or os.environ.get("LLM_MODEL_NAME")
        self.llm_api_base = llm_api_base or os.environ.get("LLM_BASE_URL")
        self.base_dir = base_dir

        # 设置日志级别
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f"Invalid log level: {log_level}")
        logging.basicConfig(
            level=numeric_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
