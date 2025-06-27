from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from .types import ToolCallResult

class ConversationMemory:
    """管理与用户的对话历史"""
    
    def __init__(self, max_history: int = 10):
        """
        初始化对话历史管理器
        
        Args:
            max_history: 保存的最大对话轮数
        """
        self.max_history = max_history
        self.history: List[Dict[str, Any]] = []
    
    def add_interaction(self, user_input: str, agent_response: ToolCallResult) -> None:
        """
        添加一轮对话到历史记录
        
        Args:
            user_input: 用户的输入
            agent_response: 代理的响应
        """
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "agent_response": agent_response
        })
        
        # 如果历史记录超过最大长度，移除最旧的记录
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取历史记录
        
        Args:
            limit: 返回的最大记录数，None表示全部返回
        
        Returns:
            历史记录列表
        """
        if limit is None:
            return self.history
        return self.history[-limit:]
    
    def get_formatted_history(self, limit: Optional[int] = None) -> str:
        """
        获取格式化的历史记录，适合送给LLM
        
        Args:
            limit: 返回的最大记录数，None表示全部返回
        
        Returns:
            格式化的历史记录
        """
        history = self.get_history(limit)
        formatted = []
        
        for i, interaction in enumerate(history):
            formatted.append(f"对话 {i+1}:")
            formatted.append(f"用户: {interaction['user_input']}")
            response = interaction['agent_response']
            message = response.get('message', '')
            formatted.append(f"助手: {message}")
            formatted.append("")
        
        return "\n".join(formatted)
    
    def clear(self) -> None:
        """清空历史记录"""
        self.history = []