"""
记忆管理模块
用于存储用户的历史推荐记录和对话历史，避免重复推荐并提供多样性回复
"""
import json
import os
from typing import List, Dict, Optional, Set
from datetime import datetime
from collections import defaultdict


class MemoryManager:
    """记忆管理器，用于存储和检索用户历史记录"""
    
    def __init__(self, storage_file: str = "user_memory.json"):
        """
        初始化记忆管理器
        
        Args:
            storage_file: 存储文件路径
        """
        self.storage_file = storage_file
        self.memory: Dict[str, Dict] = {}  # {session_id: {recommended_songs: [], conversations: []}}
        self.load()
    
    def load(self) -> None:
        """从文件加载记忆数据"""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    self.memory = json.load(f)
                print(f"✅ 成功加载 {len(self.memory)} 个会话的记忆数据")
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️ 加载记忆数据失败: {e}，将使用空记忆")
                self.memory = {}
        else:
            self.memory = {}
    
    def save(self) -> None:
        """保存记忆数据到文件"""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self.memory, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"⚠️ 保存记忆数据失败: {e}")
    
    def get_session_memory(self, session_id: str) -> Dict:
        """获取指定会话的记忆数据"""
        if session_id not in self.memory:
            self.memory[session_id] = {
                "recommended_songs": [],
                "conversations": [],
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            }
        return self.memory[session_id]
    
    def add_recommended_songs(self, session_id: str, songs: List[Dict]) -> None:
        """
        记录推荐的歌曲
        
        Args:
            session_id: 会话ID
            songs: 推荐的歌曲列表
        """
        session_memory = self.get_session_memory(session_id)
        
        # 提取歌曲的唯一标识（title + artist）
        for song in songs:
            song_id = self._get_song_id(song)
            if song_id not in session_memory["recommended_songs"]:
                session_memory["recommended_songs"].append(song_id)
        
        session_memory["last_updated"] = datetime.now().isoformat()
        self.save()
    
    def get_recommended_song_ids(self, session_id: str) -> Set[str]:
        """
        获取已推荐过的歌曲ID集合
        
        Args:
            session_id: 会话ID
        
        Returns:
            已推荐歌曲ID的集合
        """
        session_memory = self.get_session_memory(session_id)
        return set(session_memory["recommended_songs"])
    
    def add_conversation(self, session_id: str, user_input: str, response: str, intent_data: Dict) -> None:
        """
        记录对话历史
        
        Args:
            session_id: 会话ID
            user_input: 用户输入
            response: AI回复
            intent_data: 意图数据
        """
        session_memory = self.get_session_memory(session_id)
        
        conversation = {
            "user_input": user_input,
            "response": response,
            "intent": intent_data,
            "timestamp": datetime.now().isoformat()
        }
        
        session_memory["conversations"].append(conversation)
        
        # 限制对话历史数量，只保留最近50条
        if len(session_memory["conversations"]) > 50:
            session_memory["conversations"] = session_memory["conversations"][-50:]
        
        session_memory["last_updated"] = datetime.now().isoformat()
        self.save()
    
    def get_recent_conversations(self, session_id: str, limit: int = 5) -> List[Dict]:
        """
        获取最近的对话记录
        
        Args:
            session_id: 会话ID
            limit: 返回的记录数量
        
        Returns:
            最近的对话记录列表
        """
        session_memory = self.get_session_memory(session_id)
        return session_memory["conversations"][-limit:]
    
    def get_similar_conversations(self, session_id: str, user_input: str, limit: int = 3) -> List[Dict]:
        """
        获取相似的历史对话（基于用户输入的相似性）
        
        Args:
            session_id: 会话ID
            user_input: 当前用户输入
            limit: 返回的记录数量
        
        Returns:
            相似的对话记录列表
        """
        session_memory = self.get_session_memory(session_id)
        conversations = session_memory["conversations"]
        
        if not conversations:
            return []
        
        # 简单的相似度匹配：检查关键词重叠
        user_input_lower = user_input.lower()
        user_keywords = set(user_input_lower.split())
        
        scored_conversations = []
        for conv in conversations:
            conv_input_lower = conv["user_input"].lower()
            conv_keywords = set(conv_input_lower.split())
            
            # 计算关键词重叠度
            if user_keywords:
                overlap = len(user_keywords & conv_keywords) / len(user_keywords)
                if overlap > 0.3:  # 至少30%的关键词重叠
                    scored_conversations.append((overlap, conv))
        
        # 按相似度排序，返回最相似的几条
        scored_conversations.sort(key=lambda x: x[0], reverse=True)
        return [conv for _, conv in scored_conversations[:limit]]
    
    def filter_recommended_songs(self, session_id: str, songs: List[Dict]) -> List[Dict]:
        """
        过滤掉已经推荐过的歌曲
        
        Args:
            session_id: 会话ID
            songs: 待过滤的歌曲列表
        
        Returns:
            过滤后的歌曲列表
        """
        recommended_ids = self.get_recommended_song_ids(session_id)
        filtered_songs = []
        
        for song in songs:
            song_id = self._get_song_id(song)
            if song_id not in recommended_ids:
                filtered_songs.append(song)
        
        return filtered_songs
    
    def _get_song_id(self, song: Dict) -> str:
        """
        生成歌曲的唯一标识
        
        Args:
            song: 歌曲字典
        
        Returns:
            歌曲的唯一标识字符串
        """
        title = str(song.get('title', '')).lower().strip()
        artist = str(song.get('artist', '')).lower().strip()
        return f"{title}||{artist}"
    
    def clear_session(self, session_id: str) -> None:
        """清除指定会话的记忆"""
        if session_id in self.memory:
            del self.memory[session_id]
            self.save()
    
    def get_statistics(self, session_id: Optional[str] = None) -> Dict:
        """
        获取统计信息
        
        Args:
            session_id: 会话ID，如果为None则返回全局统计
        
        Returns:
            统计信息字典
        """
        if session_id:
            session_memory = self.get_session_memory(session_id)
            return {
                "session_id": session_id,
                "recommended_count": len(session_memory["recommended_songs"]),
                "conversation_count": len(session_memory["conversations"]),
                "created_at": session_memory.get("created_at"),
                "last_updated": session_memory.get("last_updated")
            }
        else:
            return {
                "total_sessions": len(self.memory),
                "total_recommended_songs": sum(
                    len(mem.get("recommended_songs", [])) 
                    for mem in self.memory.values()
                ),
                "total_conversations": sum(
                    len(mem.get("conversations", [])) 
                    for mem in self.memory.values()
                )
            }

