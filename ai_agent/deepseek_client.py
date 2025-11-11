"""
DeepSeek API客户端模块（向后兼容）
为了保持向后兼容，保留此文件
新项目建议直接使用 llm_client.py 中的通用客户端
"""
from llm_client import DeepSeekClient, MusicRecommendationClient

# 导出以保持向后兼容
__all__ = ['DeepSeekClient', 'MusicRecommendationClient']
