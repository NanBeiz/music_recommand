"""
通用LLM客户端模块
支持多种LLM提供商：DeepSeek、OpenAI、Claude、通义千问等
"""
import os
import requests
from typing import Dict, List, Optional
from dotenv import load_dotenv
from abc import ABC, abstractmethod

load_dotenv()


class LLMClient(ABC):
    """LLM客户端抽象基类"""
    
    @abstractmethod
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict:
        """调用LLM聊天完成API"""
        pass


class DeepSeekClient(LLMClient):
    """DeepSeek API客户端"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.deepseek.com", model: str = "deepseek-chat"):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DeepSeek API密钥未设置，请设置环境变量 DEEPSEEK_API_KEY")
        
        self.base_url = base_url
        self.default_model = model
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict:
        url = f"{self.base_url}/v1/chat/completions"
        
        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"DeepSeek API调用失败: {str(e)}")


class OpenAIClient(LLMClient):
    """OpenAI API客户端（兼容Azure OpenAI）"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API密钥未设置，请设置环境变量 OPENAI_API_KEY")
        
        # 支持Azure OpenAI（如果提供了base_url）
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.default_model = model or os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict:
        # Azure OpenAI使用不同的端点格式
        if "openai.azure.com" in self.base_url or "azure.com" in self.base_url:
            # Azure OpenAI格式: https://{resource}.openai.azure.com/openai/deployments/{deployment}/chat/completions?api-version=2024-02-15-preview
            # 如果URL已经包含完整路径，直接使用；否则构建标准路径
            if "/chat/completions" in self.base_url:
                url = self.base_url
            else:
                deployment = model or self.default_model
                url = f"{self.base_url.rstrip('/')}/openai/deployments/{deployment}/chat/completions"
            # Azure需要api-version参数
            params = {"api-version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")}
            payload = {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        else:
            # 标准OpenAI API
            url = f"{self.base_url.rstrip('/')}/chat/completions"
            params = None
            payload = {
                "model": model or self.default_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"OpenAI API调用失败: {str(e)}")


class QwenClient(LLMClient):
    """通义千问（Qwen）API客户端"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1", model: str = "qwen-turbo"):
        self.api_key = api_key or os.getenv("QWEN_API_KEY")
        if not self.api_key:
            raise ValueError("通义千问API密钥未设置，请设置环境变量 QWEN_API_KEY")
        
        self.base_url = base_url
        self.default_model = model or os.getenv("QWEN_MODEL", "qwen-turbo")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict:
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"通义千问API调用失败: {str(e)}")


class ZhipuClient(LLMClient):
    """智谱AI（GLM）API客户端"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "glm-4"):
        self.api_key = api_key or os.getenv("ZHIPU_API_KEY")
        if not self.api_key:
            raise ValueError("智谱AI API密钥未设置，请设置环境变量 ZHIPU_API_KEY")
        
        self.base_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        self.default_model = model or os.getenv("ZHIPU_MODEL", "glm-4")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict:
        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(self.base_url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"智谱AI API调用失败: {str(e)}")


class MoonshotClient(LLMClient):
    """月之暗面（Moonshot）API客户端"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "moonshot-v1-8k"):
        self.api_key = api_key or os.getenv("MOONSHOT_API_KEY")
        if not self.api_key:
            raise ValueError("月之暗面API密钥未设置，请设置环境变量 MOONSHOT_API_KEY")
        
        self.base_url = "https://api.moonshot.cn/v1/chat/completions"
        self.default_model = model or os.getenv("MOONSHOT_MODEL", "moonshot-v1-8k")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict:
        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(self.base_url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"月之暗面API调用失败: {str(e)}")


def create_llm_client(provider: Optional[str] = None) -> LLMClient:
    """
    工厂函数：根据配置创建LLM客户端
    
    Args:
        provider: 提供商名称，如果为None则从环境变量读取
    
    Returns:
        LLM客户端实例
    
    支持的表提供商：
    - deepseek: DeepSeek
    - openai: OpenAI / Azure OpenAI
    - qwen: 通义千问
    - zhipu: 智谱AI
    - moonshot: 月之暗面
    """
    provider = provider or os.getenv("LLM_PROVIDER", "deepseek").lower()
    
    if provider == "deepseek":
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        return DeepSeekClient(model=model, base_url=base_url)
    
    elif provider == "openai":
        model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        return OpenAIClient(model=model, base_url=base_url)
    
    elif provider == "qwen":
        model = os.getenv("QWEN_MODEL", "qwen-turbo")
        base_url = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        return QwenClient(model=model, base_url=base_url)
    
    elif provider == "zhipu":
        model = os.getenv("ZHIPU_MODEL", "glm-4")
        return ZhipuClient(model=model)
    
    elif provider == "moonshot":
        model = os.getenv("MOONSHOT_MODEL", "moonshot-v1-8k")
        return MoonshotClient(model=model)
    
    else:
        raise ValueError(f"不支持的LLM提供商: {provider}. 支持的提供商: deepseek, openai, qwen, zhipu, moonshot")


# 为了保持向后兼容，保留原来的DeepSeekClient导入
# 但现在使用新的通用客户端
class MusicRecommendationClient:
    """音乐推荐客户端（使用任意LLM提供商）"""
    
    def __init__(self, llm_client: LLMClient):
        """
        初始化音乐推荐客户端
        
        Args:
            llm_client: LLM客户端实例
        """
        self.llm_client = llm_client
    
    def extract_intent(self, user_input: str) -> Dict[str, any]:
        """从用户输入中提取意图和实体"""
        system_prompt = """你是一个音乐推荐系统的意图识别助手。
分析用户的输入，提取以下信息：
1. 意图 (intent): "find_music", "play_song", "get_info" 等
2. 情绪 (mood): "happy", "sad", "energetic", "calm" 等，如果没有则返回null
3. 流派 (genre): "rock", "pop", "jazz" 等，如果没有则返回null
4. 歌手 (artist): 歌手名称，如果没有则返回null
5. 歌曲名 (song): 歌曲名称，如果没有则返回null

请以JSON格式返回，只返回JSON，不要其他文字。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        
        response = self.llm_client.chat_completion(messages, temperature=0.3, max_tokens=500)
        content = response["choices"][0]["message"]["content"]
        
        # 尝试解析JSON
        import json
        try:
            # 提取JSON部分（处理可能的markdown代码块）
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            return json.loads(content)
        except json.JSONDecodeError:
            # 如果解析失败，返回默认值
            return {
                "intent": "find_music",
                "mood": None,
                "genre": None,
                "artist": None,
                "song": None
            }
    
    def generate_search_query(self, intent_data: Dict[str, any], available_fields: List[str]) -> str:
        """根据意图数据生成Python搜索查询"""
        system_prompt = f"""你是一个代码生成助手。
根据用户意图，生成一个Python列表推导式或filter表达式，用于从音乐数据列表中搜索匹配的歌曲。

可用字段: {', '.join(available_fields)}
意图数据: {intent_data}

要求：
1. 生成的代码应该是一个可执行的Python表达式
2. 假设数据存储在名为 'songs' 的列表中，每个元素是一个字典
3. 只返回代码，不要其他解释
4. 如果某个条件为None，则忽略该条件
5. 使用不区分大小写的匹配（使用.lower()）

示例：
如果意图是查找mood为"sad"的歌曲：
    [song for song in songs if song.get('mood', '').lower() == 'sad']

如果意图是查找genre为"rock"且mood为"energetic"的歌曲：
    [song for song in songs if song.get('genre', '').lower() == 'rock' and song.get('mood', '').lower() == 'energetic']"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请为以下意图生成搜索查询：{intent_data}"}
        ]
        
        response = self.llm_client.chat_completion(messages, temperature=0.2, max_tokens=300)
        query = response["choices"][0]["message"]["content"].strip()
        
        # 清理可能的代码块标记
        if "```python" in query:
            query = query.split("```python")[1].split("```")[0].strip()
        elif "```" in query:
            query = query.split("```")[1].split("```")[0].strip()
        
        return query
    
    def generate_recommendation(self, user_input: str, matched_songs: List[Dict], intent_data: Dict) -> str:
        """根据匹配的歌曲生成推荐回复"""
        system_prompt = """你是一个友好的音乐推荐助手。
根据用户的请求和匹配到的歌曲，生成一个自然、友好的推荐回复。
回复应该：
1. 简洁明了
2. 提到推荐的歌曲和歌手
3. 解释为什么推荐这些歌曲
4. 使用中文回复
5. 如果有多首歌曲，可以列出2-3首最相关的"""

        songs_info = "\n".join([
            f"- {song.get('title', '未知')} by {song.get('artist', '未知')} ({song.get('genre', '未知')}, {song.get('mood', '未知')})"
            for song in matched_songs[:5]
        ])
        
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"用户说：{user_input}\n\n匹配到的歌曲：\n{songs_info}\n\n请生成推荐回复："
            }
        ]
        
        response = self.llm_client.chat_completion(messages, temperature=0.8, max_tokens=500)
        return response["choices"][0]["message"]["content"]
    
    def generate_recommendation_without_matches(self, user_input: str, intent_data: Dict) -> Dict[str, any]:
        """
        当知识库中没有匹配歌曲时，让大模型推荐通用歌曲
        
        Args:
            user_input: 用户原始输入
            intent_data: 意图识别结果
        
        Returns:
            包含推荐回复和推荐歌曲列表的字典
        """
        system_prompt = """你是一个专业的音乐推荐助手。当知识库中没有匹配的歌曲时，你需要基于用户的需求推荐一些知名的、符合要求的歌曲。

要求：
1. 根据用户的情绪、流派、歌手偏好等需求，推荐3-5首知名的、符合要求的歌曲
2. 推荐的歌曲应该是真实存在的、广为人知的经典歌曲
3. 每首歌曲需要包含：歌曲名、歌手名、流派、情绪标签
4. 生成一个友好的推荐回复，解释为什么推荐这些歌曲
5. 使用中文回复

请以JSON格式返回，格式如下：
{
    "recommendation": "推荐回复文本",
    "recommended_songs": [
        {
            "title": "歌曲名",
            "artist": "歌手名",
            "genre": "流派",
            "mood": "情绪"
        },
        ...
    ]
}"""

        # 构建用户需求描述
        requirements = []
        if intent_data.get('mood'):
            requirements.append(f"情绪：{intent_data['mood']}")
        if intent_data.get('genre'):
            requirements.append(f"流派：{intent_data['genre']}")
        if intent_data.get('artist'):
            requirements.append(f"歌手：{intent_data['artist']}")
        if intent_data.get('song'):
            requirements.append(f"歌曲：{intent_data['song']}")
        
        requirements_text = "、".join(requirements) if requirements else "通用推荐"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"用户说：{user_input}\n\n用户需求：{requirements_text}\n\n请基于这些需求推荐合适的歌曲："
            }
        ]
        
        response = self.llm_client.chat_completion(messages, temperature=0.8, max_tokens=1000)
        content = response["choices"][0]["message"]["content"]
        
        # 尝试解析JSON
        import json
        try:
            # 提取JSON部分（处理可能的markdown代码块）
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            result = json.loads(content)
            
            # 验证返回格式
            if "recommendation" not in result:
                result["recommendation"] = content
            if "recommended_songs" not in result:
                result["recommended_songs"] = []
            
            return result
        except json.JSONDecodeError:
            # 如果解析失败，返回一个友好的回复
            return {
                "recommendation": content if content else "抱歉，我暂时无法为您推荐具体的歌曲。建议您尝试搜索特定的歌手、流派或情绪关键词。",
                "recommended_songs": []
            }

