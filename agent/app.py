import logging
from typing import Dict, Any
import json

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
        self.agent = FileAgent(config=self.config)

    async def process_command(self, user_input: str) -> Dict[str, Any]:
        """
        处理用户命令

        Args:
            user_input: 用户的自然语言输入

        Returns:
            Dict: 处理结果
        """
        logger.info(f"接收到用户输入: {user_input}")
        result = await self.agent.process(user_input)
        logger.info(f"处理结果: {json.dumps(result, ensure_ascii=False)}")
        return dict(result)
