"""
通用LLM客户端模块
支持多种LLM提供商：通义千问（默认）、OpenAI、智谱、Moonshot 等
"""
import json
import os
import re
import requests
from typing import Dict, List, Optional, Set
from dotenv import load_dotenv
from abc import ABC, abstractmethod
from verifier import SongVerifier

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
    
    支持的提供商：
    - qwen: 通义千问（默认）
    - openai: OpenAI / Azure OpenAI
    - zhipu: 智谱AI
    - moonshot: 月之暗面
    """
    provider = provider or os.getenv("LLM_PROVIDER", "qwen").lower()
    
    if provider == "openai":
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
        raise ValueError(f"不支持的LLM提供商: {provider}. 支持的提供商: qwen, openai, zhipu, moonshot")


class MusicRecommendationClient:
    """音乐推荐客户端（使用任意LLM提供商）"""
    
    def __init__(self, llm_client: LLMClient):
        """
        初始化音乐推荐客户端
        
        Args:
            llm_client: LLM客户端实例
        """
        self.llm_client = llm_client
        # 用于对LLM推荐歌曲做真实性核查
        self.song_verifier = SongVerifier(llm_client)
    
    def generate_search_query(self, intent_data: Dict, available_fields: List[str]) -> Dict[str, Optional[str]]:
        """
        将用户意图转换为结构化的搜索参数（取代旧的 eval 代码生成，避免RCE）
        
        Args:
            intent_data: 意图识别结果字典
            available_fields: 知识库可用字段列表
        
        Returns:
            dict: 结构化搜索参数，如 {"genre": "rock", "mood": "sad"}
        """
        # 允许的字段（与知识库搜索维度保持一致）
        allowed_fields = {"genre", "mood", "artist", "title"}
        available_allowed = [f for f in available_fields if f in allowed_fields]

        # 如果知识库没有这些字段，直接回落到intent_data
        if not available_allowed:
            return {
                "genre": intent_data.get("genre"),
                "mood": intent_data.get("mood"),
                "artist": intent_data.get("artist"),
                "title": intent_data.get("song") or intent_data.get("title"),
            }

        system_prompt = f"""你是一个音乐推荐系统的查询生成助手。
请根据用户意图(JSON)和可用字段列表，返回一个JSON字典（不包含多余文本、代码或markdown）。
规则：
1) 仅使用可用字段：{available_allowed}
2) 如果字段缺失或无法确定，填 null
3) 只返回 JSON 对象本身，如: {{"genre": "rock", "mood": "sad"}}
4) 绝不要返回代码、函数或自然语言解释
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"用户意图: {intent_data}\n请返回JSON对象："
            }
        ]

        response = self.llm_client.chat_completion(messages, temperature=0.2, max_tokens=400)
        content = response["choices"][0]["message"]["content"]

        # 使用正则提取第一个JSON对象，兼容可能的markdown包裹
        json_text = None
        match = re.search(r"\{.*\}", content, re.S)
        if match:
            json_text = match.group(0)
        else:
            json_text = content.strip()

        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError:
            # 解析失败时，回退到 intent_data
            parsed = {}

        # 标准化字段名，并过滤只保留允许的字段
        result: Dict[str, Optional[str]] = {}
        for key, value in parsed.items():
            lower_key = str(key).lower().strip()
            if lower_key in allowed_fields:
                result[lower_key] = value

        # 兜底：用 intent_data 填充缺失字段，保持业务一致性
        result.setdefault("genre", intent_data.get("genre"))
        result.setdefault("mood", intent_data.get("mood"))
        result.setdefault("artist", intent_data.get("artist"))
        result.setdefault("title", intent_data.get("song") or intent_data.get("title"))

        return result
    
    def extract_intent(self, user_input: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, any]:
        """
        从用户输入中提取意图和实体

        Args:
            user_input: 当前用户输入
            history: 对话历史（用于理解上下文），列表元素形如 {"role": "user"/"assistant", "content": "..."}
        """
        system_prompt = """你是一个音乐推荐系统的意图识别助手。
分析用户的输入，提取以下信息：
1. 意图 (intent): "find_music", "play_song", "get_info" 等
2. 情绪 (mood): "happy", "sad", "energetic", "calm" 等，如果没有则返回null
3. 流派 (genre): "rock", "pop", "jazz" 等，如果没有则返回null
4. 歌手 (artist): 歌手名称，如果没有则返回null
5. 歌曲名 (song): 歌曲名称，如果没有则返回null

请以JSON格式返回，只返回JSON，不要其他文字。"""

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt},
        ]

        # 将历史对话插入到当前请求之前，帮助模型理解上下文
        if history:
            for item in history:
                role = item.get("role")
                content = item.get("content")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_input})
        
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
    
    def generate_recommendation(
        self, 
        user_input: str, 
        matched_songs: List[Dict], 
        intent_data: Dict,
        conversation_history: Optional[List[Dict]] = None
    ) -> str:
        """
        根据匹配的歌曲生成推荐回复
        
        Args:
            user_input: 用户输入
            matched_songs: 匹配的歌曲列表
            intent_data: 意图数据
            conversation_history: 对话历史记录（用于提供多样性）
        """
        import random
        
        # 多样化的系统提示词模板
        prompt_templates = [
            """你是一个友好的音乐推荐助手。
根据用户的请求和匹配到的歌曲，生成一个自然、友好的推荐回复。
回复应该：
1. 简洁明了
2. 提到推荐的歌曲和歌手
3. 解释为什么推荐这些歌曲
4. 使用中文回复
5. 如果有多首歌曲，可以列出2-3首最相关的""",
            
            """你是一个热情的音乐推荐专家。
请根据用户的请求和匹配到的歌曲，用生动有趣的方式推荐音乐。
回复要求：
1. 语气轻松友好
2. 突出推荐歌曲的特色
3. 可以适当表达你对这些歌曲的喜爱
4. 使用中文回复
5. 如果有多首歌曲，可以列出2-3首最相关的""",
            
            """你是一个专业的音乐推荐顾问。
请根据用户的请求和匹配到的歌曲，提供专业的音乐推荐。
回复要求：
1. 专业但不过于正式
2. 详细说明推荐理由
3. 可以提及歌曲的风格特点
4. 使用中文回复
5. 如果有多首歌曲，可以列出2-3首最相关的"""
        ]
        
        # 随机选择一个提示词模板，增加多样性
        system_prompt = random.choice(prompt_templates)
        
        # 如果有对话历史，添加到上下文中
        history_context = ""
        if conversation_history:
            recent_convs = conversation_history[-3:]  # 只使用最近3条对话
            history_context = "\n\n之前的对话记录（用于参考，避免重复）：\n"
            for conv in recent_convs:
                history_context += f"- 用户：{conv.get('user_input', '')}\n"
                history_context += f"  助手：{conv.get('response', '')[:100]}...\n"
            history_context += "\n请确保这次的回复与之前的回复有所不同，提供新的视角或信息。\n"

        songs_info = "\n".join([
            f"- {song.get('title', '未知')} by {song.get('artist', '未知')} ({song.get('genre', '未知')}, {song.get('mood', '未知')})"
            for song in matched_songs[:5]
        ])
        
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"用户说：{user_input}{history_context}\n\n匹配到的歌曲：\n{songs_info}\n\n请生成推荐回复："
            }
        ]
        
        # 增加温度值以提供更多多样性（0.8-1.0之间随机）
        temperature = random.uniform(0.8, 1.0)
        response = self.llm_client.chat_completion(messages, temperature=temperature, max_tokens=500)
        return response["choices"][0]["message"]["content"]
    
    def generate_recommendation_without_matches(
        self, 
        user_input: str, 
        intent_data: Dict,
        conversation_history: Optional[List[Dict]] = None,
        recommended_song_ids: Optional[Set[str]] = None,
        exclude_titles: Optional[List[str]] = None,
    ) -> Dict[str, any]:
        """
        当知识库中没有匹配歌曲时，让大模型推荐通用歌曲
        
        Args:
            user_input: 用户原始输入
            intent_data: 意图识别结果
            conversation_history: 对话历史记录（用于提供多样性）
            recommended_song_ids: 已推荐过的歌曲ID集合（避免重复推荐）
        
        Returns:
            包含推荐回复和推荐歌曲列表的字典
        """
        import random
        
        # 多样化的系统提示词模板，并明确要求不要总是重复最著名的几首歌，且只返回核心字段
        prompt_templates = [
            """你是一个专业的音乐推荐助手。当知识库中没有匹配的歌曲时，你需要基于用户的需求推荐一些符合要求的歌曲。

重要要求：
1. 请尽量挖掘多样化的歌曲，不要总是推荐最著名的那几首（例如《Bohemian Rhapsody》等），除非用户明确点名这些歌曲。
2. 在保证质量的前提下，可以适当推荐一些相对冷门但评价较高的作品，以增加多样性。
3. 根据用户的情绪、流派、歌手偏好等需求，推荐3-5首真实存在的歌曲。
4. 每首歌曲只需要提供以下5个字段：歌曲名(title)、歌手(artist)、流派(genre)、情绪(mood)、语言(language)，不需要返回年份(year)或时长(duration)等其他信息。
5. 生成一个友好的推荐回复，解释为什么推荐这些歌曲。
6. 使用中文回复。""",
            
            """你是一个热情的音乐推荐专家。当知识库中没有匹配的歌曲时，请基于用户的需求推荐一些有趣的好歌。

重要要求：
1. 不要总是推荐同一批全球最著名的经典歌曲，除非用户明确点名这些歌曲。
2. 在推荐中加入一定随机性，可以混合一些冷门但口碑很好的歌曲，让用户有新鲜感。
3. 推荐3-5首符合用户需求的歌曲，每首都必须是真实存在的。
4. 每首歌曲只需要返回：歌曲名(title)、歌手(artist)、流派(genre)、情绪(mood)、语言(language)，不要返回年份(year)和时长(duration)。
5. 用生动有趣的方式推荐，表达你对这些歌曲的喜爱。
6. 使用中文回复。"""
        ]
        
        system_prompt = random.choice(prompt_templates)
        
        # 如果有对话历史，添加到上下文中
        history_context = ""
        if conversation_history:
            recent_convs = conversation_history[-3:]
            history_context = "\n\n之前的对话记录（用于参考，避免重复）：\n"
            for conv in recent_convs:
                history_context += f"- 用户：{conv.get('user_input', '')}\n"
                history_context += f"  助手：{conv.get('response', '')[:100]}...\n"
            history_context += "\n请确保这次的推荐与之前的推荐有所不同。\n"
        
        # 如果已推荐过歌曲，提醒避免重复（基于歌曲ID集合）
        avoid_repeat_hint = ""
        if recommended_song_ids:
            avoid_repeat_hint = f"\n\n注意：用户已经听过一些歌曲，请避免重复推荐这些已推荐过的歌曲。\n"

        # 如果有需要显式排除的歌曲标题列表，直接告诉模型绝对不要再推荐这些歌
        exclude_hint = ""
        if exclude_titles:
            # 只展示前若干首，避免提示过长
            preview = ", ".join(exclude_titles[:10])
            exclude_hint = f"\n\n请绝对不要推荐以下这些已经推荐过的歌曲：{preview}\n"

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
        
        system_prompt_with_format = f"""{system_prompt}

在返回的 JSON 中，请务必包含歌曲的语言字段，并尽量准确识别语言，例如：
- "Mandarin"（国语 / 普通话）
- "Cantonese"（粤语）
- "English"（英语）
- "Japanese"（日语）
- "Korean"（韩语）
- "Spanish"（西班牙语）
等常见语言标签。

请以JSON格式返回，格式如下：
{{
    "recommendation": "推荐回复文本",
    "recommended_songs": [
        {{
            "title": "歌曲名",
            "artist": "歌手名",
            "genre": "流派",
            "mood": "情绪",
            "language": "语言（例如 'Mandarin' 或 'English'）"
        }},
        ...
    ]
}}"""
        
        messages = [
            {"role": "system", "content": system_prompt_with_format},
            {
                "role": "user",
                "content": (
                    f"用户说：{user_input}"
                    f"{history_context}"
                    f"{avoid_repeat_hint}"
                    f"{exclude_hint}"
                    f"\n\n用户需求：{requirements_text}\n\n请基于这些需求推荐合适的歌曲："
                )
            }
        ]
        
        # 增加温度值以提供更多多样性
        temperature = random.uniform(0.8, 1.0)
        response = self.llm_client.chat_completion(messages, temperature=temperature, max_tokens=1000)
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

    def verify_songs(self, songs: List[Dict]) -> List[Dict]:
        """
        对LLM推荐的歌曲列表进行真实性核查，仅保留通过验证的歌曲。

        Args:
            songs: 初步推荐的歌曲列表

        Returns:
            通过验证的歌曲列表
        """
        return self.song_verifier.verify_songs(songs)


