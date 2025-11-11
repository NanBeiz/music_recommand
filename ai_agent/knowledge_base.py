"""
知识库管理模块
用于加载和搜索JSON格式的音乐数据
"""
import json
import os
from typing import List, Dict, Optional, Any

class KnowledgeBase:
    """JSON知识库管理类"""
    
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
                self.data = json.load(f)
            
            # 确保data是列表
            if not isinstance(self.data, list):
                self.data = [self.data] if self.data else []
            
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
    
    def search(self, query_code: str) -> List[Dict[str, Any]]:
        """
        使用生成的查询代码搜索数据
        
        Args:
            query_code: Python搜索表达式，例如：
                [song for song in songs if song.get('mood', '').lower() == 'sad']
        
        Returns:
            匹配的歌曲列表
        """
        try:
            # 创建安全的执行环境
            songs = self.data
            # 执行查询代码
            result = eval(query_code)
            return result if isinstance(result, list) else []
        except Exception as e:
            print(f"搜索执行错误: {e}")
            return []
    
    def search_by_conditions(
        self,
        genre: Optional[str] = None,
        mood: Optional[str] = None,
        artist: Optional[str] = None,
        title: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        使用条件直接搜索（备用方法）
        
        Args:
            genre: 流派
            mood: 情绪
            artist: 歌手
            title: 歌曲标题
            limit: 返回结果数量限制
        
        Returns:
            匹配的歌曲列表
        """
        results = []
        
        for song in self.data:
            match = True
            
            if genre and song.get('genre', '').lower() != genre.lower():
                match = False
            if mood and song.get('mood', '').lower() != mood.lower():
                match = False
            if artist and artist.lower() not in song.get('artist', '').lower():
                match = False
            if title and title.lower() not in song.get('title', '').lower():
                match = False
            
            if match:
                results.append(song)
                if len(results) >= limit:
                    break
        
        return results
    
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

