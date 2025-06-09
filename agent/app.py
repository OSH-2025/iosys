import logging
from typing import Dict, Any
import json
import openai

from .file_agent import FileAgent
from .config import AgentConfig

logger = logging.getLogger(__name__)


class FileManagerApp:
    """文件管理应用"""

    def __init__(self, config: AgentConfig):
        """
        初始化文件管理应用

        Args:
            config: 配置对象, 如果为None则使用默认配置
        """
        self.config = config
        self.llm_client = self._init_llm_client()
        self.agent = FileAgent(config=self.config, llm_client=self.llm_client)

    def _init_llm_client(self):
        """
        初始化 LLM 客户端

        Returns:
            LLM 客户端实例
        """
        client = openai.Client(
            api_key=self.config.llm_api_key,
            base_url=self.config.llm_api_base,
        )
        return client

    def process_command(self, user_input: str) -> Dict[str, Any]:
        """
        处理用户命令

        Args:
            user_input: 用户的自然语言输入

        Returns:
            Dict: 处理结果
        """
        logger.info(f"接收到用户输入: {user_input}")
        result = self.agent.process(user_input)
        logger.info(f"处理结果: {json.dumps(result, ensure_ascii=False)}")
        return result
