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

        # 修改点1：增强 System Prompt，强调版权审核员的严厉程度
        system_prompt = """你是一个极其严苛的音乐版权数据库管理员。你的任务是清洗脏数据，剔除一切虚构、张冠李戴或无法验证来源的歌曲。宁可错杀，绝不放过一个假歌。"""

        # 修改点2：在 User Prompt 中强制要求输出专辑和年份作为“证据”
        user_prompt = f"""待核查列表（由AI生成，可能包含虚构内容）：

{songs_json}

请对每一首歌执行严格的“存在性验证”。
规则如下：
1. **证据确凿**：必须能明确指出该歌曲收录在哪张**正式专辑**（Album）或**EP**中，以及具体的**发行年份**。
2. **拒绝模糊**：如果只能说是“单曲”且无法提供具体发行年份，或者你对它是否存在有一丝怀疑，请直接**剔除**。
3. **拒绝张冠李戴**：歌手和歌名必须严格对应（例如《海阔天空》不能是刘德华唱的）。
4. **拒绝拼凑**：像《夜行船》这种听起来像赵雷但实际不存在的歌，必须剔除。

**输出要求**：
请返回一个 JSON 列表，只包含那些你**100%确定真实存在**的歌曲。
**重要**：为了证明你没有瞎编，每一首歌**必须**包含 `album` (收录专辑) 和 `year` (发行年份) 字段。如果无法提供这两个字段，请不要将该歌曲放入返回列表中。

返回格式示例：
[
  {{
    "title": "歌曲名",
    "artist": "歌手名",
    "album": "确切的专辑名", 
    "year": "发行年份(如 2013)",
    "genre": "流派",
    "mood": "情绪",
    "language": "语言"
  }}
]

只返回 JSON 列表本身，不要包含任何 markdown 标记或额外解释。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # 低温度，倾向于保守和事实性回答
        response = self.llm_client.chat_completion(
            messages, temperature=0.1, max_tokens=1500  # 稍微增加 max_tokens 以容纳专辑信息
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

            # 修改点3：简单的后处理检查，如果专辑名看起来像“未知”或“单曲”，可以考虑二次过滤（可选）
            # 这里暂时只做基础判空
            if not title or not artist:
                continue

            # 可以在这里把 album 和 year 字段保留，也可以为了保持数据结构一致性而剔除
            # 建议保留，反正 knowledge_base.py 那边通常只取它需要的字段，或者会把多余字段存入 extra
            cleaned.append(item)

        return cleaned