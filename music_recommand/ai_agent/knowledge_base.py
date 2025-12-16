"""
知识库管理模块
用于加载和搜索JSON格式的音乐数据
"""
import json
import os
import random
from typing import List, Dict, Optional, Any

class KnowledgeBase:
    """JSON知识库管理类"""

    # 允许保留的核心字段白名单
    ALLOWED_KEYS = {"id", "title", "artist", "genre", "mood", "language", "source_type"}
    
    def __init__(self, json_file_path: str = "music_data.json"):
        """
        初始化知识库
        
        Args:
            json_file_path: JSON文件路径
        """
        self.json_file_path = json_file_path
        self.data: List[Dict[str, Any]] = []
        self.load()
    
    def load(self) -> None:
        """从JSON文件加载数据"""
        if not os.path.exists(self.json_file_path):
            print(f"警告: 文件 {self.json_file_path} 不存在，将创建空数据")
            self.data = []
            return
        
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)

            # 确保data是列表
            if not isinstance(raw_data, list):
                raw_data = [raw_data] if raw_data else []

            # 对已有数据做“瘦身”：只保留白名单字段
            self.data = []
            for song in raw_data:
                if not isinstance(song, dict):
                    continue
                cleaned = {k: v for k, v in song.items() if k in self.ALLOWED_KEYS}
                # 保证至少有title/artist再收录
                if cleaned.get("title") and cleaned.get("artist"):
                    self.data.append(cleaned)
            
            print(f"成功加载 {len(self.data)} 条音乐数据")
        except json.JSONDecodeError as e:
            print(f"错误: JSON文件格式错误 - {e}")
            self.data = []
        except Exception as e:
            print(f"错误: 加载文件失败 - {e}")
            self.data = []
    
    def reload(self) -> None:
        """重新加载数据"""
        self.load()

    def save(self) -> None:
        """保存当前数据到JSON文件"""
        try:
            with open(self.json_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            print(f"✅ 知识库已保存，共 {len(self.data)} 首歌曲")
        except Exception as e:
            print(f"保存知识库失败: {e}")

    def search_by_conditions(
        self,
        genre: Optional[str] = None,
        mood: Optional[str] = None,
        artist: Optional[str] = None,
        title: Optional[str] = None,
        limit: int = 10,
        exclude_titles: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        使用条件直接搜索（安全方法，不使用eval）
        
        Args:
            genre: 流派（不区分大小写精确匹配）
            mood: 情绪（不区分大小写精确匹配）
            artist: 歌手（不区分大小写模糊匹配，substring）
            title: 歌曲标题（不区分大小写模糊匹配，substring）
            limit: 返回结果数量限制
            exclude_titles: 要排除的歌曲标题列表（全局历史推荐去重）
        
        Returns:
            匹配的歌曲列表（从所有候选中随机抽取，保证多样性）
        """
        candidates: List[Dict[str, Any]] = []

        # 安全地转换为小写，处理 None 值
        genre_lower = genre.lower().strip() if genre else None
        mood_lower = mood.lower().strip() if mood else None
        artist_lower = artist.lower().strip() if artist else None
        title_lower = title.lower().strip() if title else None

        # 构建需要排除的标题集合（小写去空格），用于全局历史推荐去重
        exclude_set = {
            str(t).lower().strip()
            for t in (exclude_titles or [])
            if t
        }
        
        for song in self.data:
            # 使用 .get() 安全地获取字典值，防止 KeyError
            # 如果字段不存在，返回空字符串，然后转换为小写
            song_genre = str(song.get('genre', '')).lower().strip()
            song_mood = str(song.get('mood', '')).lower().strip()
            song_artist = str(song.get('artist', '')).lower().strip()
            song_title = str(song.get('title', '')).lower().strip()

            # 如果该歌曲标题在排除列表中，直接跳过（全局去重）
            if exclude_set and song_title in exclude_set:
                continue

            match = True
            
            # 流派：精确匹配（不区分大小写）
            if genre_lower and song_genre != genre_lower:
                match = False
            
            # 情绪：精确匹配（不区分大小写）
            if mood_lower and song_mood != mood_lower:
                match = False
            
            # 歌手：模糊匹配（不区分大小写）
            if artist_lower and artist_lower not in song_artist:
                match = False
            
            # 歌曲标题：模糊匹配（不区分大小写）
            if title_lower and title_lower not in song_title:
                match = False
            
            if match:
                candidates.append(song)

        # 为了避免每次都返回相同的前几首，在返回前先随机打乱候选列表
        if not candidates:
            return []

        random.shuffle(candidates)
        return candidates[:limit]

    def add_new_songs(self, new_songs: List[Dict[str, Any]]) -> int:
        """
        从外部（例如LLM推荐）添加新歌曲到知识库，并持久化保存。
        会自动去重（按 title+artist）并生成连续ID。

        Args:
            new_songs: 新歌列表，每项为包含至少 title/artist 的字典

        Returns:
            实际新增的歌曲数量
        """
        if not new_songs:
            return 0

        # 计算当前最大ID（若缺失则按0处理）
        max_id = 0
        if self.data:
            try:
                max_id = max(int(song.get("id", 0)) for song in self.data)
            except (TypeError, ValueError):
                max_id = 0

        added_count = 0

        for song in new_songs:
            title = str(song.get("title", "")).strip()
            artist = str(song.get("artist", "")).strip()
            if not title or not artist:
                # 没有基本信息的歌曲，跳过
                continue

            title_lower = title.lower()
            artist_lower = artist.lower()

            # 简单去重：根据 title + artist 判断是否已存在
            is_exist = any(
                str(s.get("title", "")).strip().lower() == title_lower
                and str(s.get("artist", "")).strip().lower() == artist_lower
                for s in self.data
            )
            if is_exist:
                continue

            max_id += 1

            # 字段补全：仅保留核心字段，其余使用固定默认值
            new_entry: Dict[str, Any] = {
                "id": max_id,
                "title": title,
                "artist": artist,
                "genre": song.get("genre", "Unknown"),
                "mood": song.get("mood", "Unknown"),
                "year": None,
                "duration": 0,
                "language": song.get("language", "Unknown"),
                # 标记来源为大模型自学习生成的数据
                "source_type": "llm_generated",
            }

            self.data.append(new_entry)
            added_count += 1

        if added_count > 0:
            self.save()
            print(f"📚 知识库已更新，学习了 {added_count} 首新歌！")

        return added_count

    def delete_song(self, song_id: int) -> bool:
        """
        根据ID删除歌曲并保存

        Args:
            song_id: 要删除的歌曲ID

        Returns:
            True 删除成功；False 未找到
        """
        if not self.data:
            return False

        initial_len = len(self.data)
        self.data = [song for song in self.data if song.get("id") != song_id]

        if len(self.data) == initial_len:
            return False

        # 删除成功，保存更新
        self.save()
        print(f"🗑️ 已删除ID为 {song_id} 的歌曲，并更新知识库")
        return True
    
    def get_available_fields(self) -> List[str]:
        """
        获取数据中可用的字段列表
        
        Returns:
            字段名列表
        """
        if not self.data:
            return []
        
        # 从所有记录中收集字段
        fields = set()
        for song in self.data:
            fields.update(song.keys())
        
        return sorted(list(fields))
    
    def get_all_songs(self) -> List[Dict[str, Any]]:
        """获取所有歌曲"""
        return self.data
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        if not self.data:
            return {
                "total_songs": 0,
                "genres": [],
                "moods": [],
                "artists": []
            }
        
        genres = set()
        moods = set()
        artists = set()
        
        for song in self.data:
            if 'genre' in song:
                genres.add(song['genre'])
            if 'mood' in song:
                moods.add(song['mood'])
            if 'artist' in song:
                artists.add(song['artist'])
        
        return {
            "total_songs": len(self.data),
            "genres": sorted(list(genres)),
            "moods": sorted(list(moods)),
            "artists": sorted(list(artists))[:20]  # 限制艺术家数量
        }

