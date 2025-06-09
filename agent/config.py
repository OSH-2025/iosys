import os
import logging

from jfs import IOSYSFileSystem
from rag import IOSYSRAG


class AgentConfig:
    """Agent 配置类"""

    fs: IOSYSFileSystem
    rag: IOSYSRAG

    def __init__(
        self,
        fs: IOSYSFileSystem,
        rag: IOSYSRAG,
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

        self.fs = fs
        self.rag = rag
        self.llm_api_key = os.environ["LLM_API_KEY"]
        self.llm_model = os.environ["LLM_MODEL_NAME"]
        self.llm_api_base = os.environ["LLM_BASE_URL"]

        # 设置日志级别
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f"Invalid log level: {log_level}")
        logging.basicConfig(
            level=numeric_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
