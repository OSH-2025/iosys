import logging
from typing import Dict, Any, Optional
import json
import openai

from agent.src.file_agent import FileAgent
from agent.src.config import AgentConfig

logger = logging.getLogger(__name__)


class FileManagerApp:
    """文件管理应用"""

    def __init__(self, config: Optional[AgentConfig] = None):
        """
        初始化文件管理应用

        Args:
            config: 配置对象, 如果为None则使用默认配置
        """
        self.config = config or AgentConfig()
        self.llm_client = self._init_llm_client()
        self.agent = FileAgent(config=self.config, llm_client=self.llm_client)
        logger.info(f"文件管理应用初始化完成，基础目录: {self.config.base_dir}")

    def _init_llm_client(self):
        """
        初始化 LLM 客户端

        Returns:
            LLM 客户端实例
        """
        client_args = {"api_key": self.config.llm_api_key}
        # 如果提供了自定义API基础URL，则使用它
        if self.config.llm_api_base:
            client_args["base_url"] = self.config.llm_api_base

        client = openai.Client(**client_args)
        logger.info(f"客户端初始化成功，使用模型: {self.config.llm_model}")
        return client

    def process_command(self, user_input: str) -> Dict[str, Any]:
        """
        处理用户命令

        Args:
            user_input: 用户的自然语言输入

        Returns:
            Dict: 处理结果
        """
        try:
            logger.info(f"接收到用户输入: {user_input}")
            result = self.agent.process(user_input)
            logger.info(f"处理结果: {json.dumps(result, ensure_ascii=False)}")
            return result
        except Exception as e:
            error_msg = f"处理命令时出错: {str(e)}"
            logger.error(f"{error_msg}")
            return {"status": "error", "message": error_msg}
