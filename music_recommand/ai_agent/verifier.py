"""
歌曲真实性验证模块

通过低温度的大模型调用，对推荐歌曲进行二次核查，尽量过滤掉不存在或歌手/歌名不匹配的“幻觉”数据。
"""
import json
from typing import List, Dict, Any, Optional


class SongVerifier:
    """使用LLM对歌曲列表进行真实性验证的工具类"""

    def __init__(self, llm_client: Any):
        """
        Args:
            llm_client: 任意实现了 chat_completion(messages, model, temperature, max_tokens) 接口的客户端
        """
        self.llm_client = llm_client

    def verify_songs(self, songs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        使用大模型对歌曲列表做真实性核查，只返回验证通过的歌曲。

        Args:
            songs: 待验证的歌曲列表

        Returns:
            通过验证的歌曲列表
        """
        if not songs:
            return []

        # 将待验证的歌曲列表序列化为JSON，便于大模型理解
        songs_json = json.dumps(songs, ensure_ascii=False, indent=2)

        system_prompt = """你是一个冷酷无情的音乐版权审核员。你的唯一工作是剔除不存在的虚构歌曲。"""

        user_prompt = f"""待核查列表（由AI生成，可能包含虚构内容）：

{songs_json}

请对每一首歌执行严格的“存在性测试”（有罪推定，除非给出充分证据，否则视为假歌）：
1. 必须能说出它收录在哪张具体的正式专辑或EP中；仅仅说“单曲”是不够的，除非是广为人知的单曲。
2. 必须能确认其发行年份。
3. 歌手和歌名必须完全对应，例如不能把《海阔天空》安给刘德华（应是Beyond或信乐团）。
4. 像《夜行船》这种听起来像赵雷风格但实际上并不存在的歌，必须无情剔除。
5. 如果对某首歌有任何不确定，或者无法给出上面的关键信息，请视为不存在并剔除。

返回：
仅返回那些你敢用职业生涯担保真实存在的歌曲 JSON 列表。对于每一首保留下来的歌，你内部可以自行确认专辑名称、发行年份和流媒体链接，但在最终返回的 JSON 中，只需要包含以下字段：
[
  {{
    "title": "歌曲名",
    "artist": "歌手名",
    "genre": "流派",
    "mood": "情绪",
    "language": "语言"
  }},
  ...
]

只返回上述 JSON 列表本身，不要任何多余说明文字。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # 低温度，倾向于保守和事实性回答
        response = self.llm_client.chat_completion(
            messages, temperature=0.1, max_tokens=1000
        )
        content = response["choices"][0]["message"]["content"]

        # 提取JSON部分（处理可能的markdown代码块）
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result = json.loads(content)
        except Exception:
            # 解析失败则放弃写入，返回空列表，避免将幻觉数据入库
            return []

        # 支持两种返回格式：直接列表 或 {"verified_songs": [...]} 包裹
        if isinstance(result, list):
            verified = result
        else:
            verified = result.get("verified_songs")
            if not isinstance(verified, list):
                return []

        # 只保留字典项，且至少包含 title 与 artist
        cleaned: List[Dict[str, Any]] = []
        for item in verified:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            artist = str(item.get("artist", "")).strip()
            if not title or not artist:
                continue
            cleaned.append(item)

        return cleaned


