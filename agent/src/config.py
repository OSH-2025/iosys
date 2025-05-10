from typing import Dict, Any, Optional
import logging

class AgentConfig:
    """Agent 配置类"""
    
    def __init__(self, 
                 llm_api_key: Optional[str] = None,
                 llm_model: str = "deepseek-chat",
                 llm_api_base: Optional[str] = None,
                 base_dir: str = "./",
                 log_level: str = "INFO"):
        """
        初始化 Agent 配置
        
        Args:
            llm_api_key: LLM API 密钥
            llm_model: 使用的 LLM 模型名称
            llm_api_base: LLM API 基础URL
            base_dir: 文件操作的基础目录
            log_level: 日志级别
        """
        self.llm_api_key = llm_api_key
        self.llm_model = llm_model
        self.llm_api_base = llm_api_base
        self.base_dir = base_dir
        
        # 设置日志级别
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f'Invalid log level: {log_level}')
        logging.basicConfig(
            level=numeric_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典"""        
        return {
            "llm_model": self.llm_model,
            "llm_api_base": self.llm_api_base,
            "base_dir": self.base_dir,
        }
        
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'AgentConfig':
        """从字典创建配置实例"""
        return cls(
            llm_api_key=config_dict.get("llm_api_key"),
            llm_model=config_dict.get("llm_model", "deepseek-chat"),
            llm_api_base=config_dict.get("llm_api_base"),
            base_dir=config_dict.get("base_dir", "./"),
            log_level=config_dict.get("log_level", "INFO")
        )
