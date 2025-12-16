"""
Flask Web应用主文件
实现AI音乐推荐智能体的HTTP API接口
"""
import os
import logging
import uuid
from typing import Dict, Set
from flask import Flask, request, jsonify
from flask_cors import CORS
from llm_client import create_llm_client, MusicRecommendationClient
from knowledge_base import KnowledgeBase

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局推荐历史：记录最近若干轮推荐过的歌曲标题列表
# 结构示例：[['song1', 'song2'], ['song3'], ...]
RECOMMENDATION_HISTORY = []

# 全局对话上下文（滑动窗口，仅保留最近 10 轮对话，共 20 条消息）
# 结构示例：[{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]
CHAT_CONTEXT = []

# 会话级推荐去重（仅内存，不落盘）：session_id -> set(song_id)
SESSION_RECOMMENDED_IDS: Dict[str, Set[str]] = {}


def _song_id(song: Dict) -> str:
    """生成歌曲唯一标识（标题+歌手，小写去空格）"""
    title = str(song.get("title", "")).lower().strip()
    artist = str(song.get("artist", "")).lower().strip()
    return f"{title}||{artist}"

# 创建Flask应用
app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 初始化组件
try:
    # 从环境变量读取LLM提供商配置（默认使用通义千问）
    llm_provider = os.getenv("LLM_PROVIDER", "qwen")
    logger.info(f"🤖 使用LLM提供商: {llm_provider}")
    
    # 创建LLM客户端
    llm_client = create_llm_client(llm_provider)
    
    # 创建音乐推荐客户端（封装了业务逻辑）
    music_client = MusicRecommendationClient(llm_client)
    
    # 初始化知识库
    knowledge_base = KnowledgeBase()

    # 可选脏数据清理：移除已知错误的幻觉歌曲，如把《夜行船》安给赵雷
    try:
        to_delete_ids = [
            song.get("id")
            for song in knowledge_base.data
            if str(song.get("title", "")).strip() == "夜行船"
            and str(song.get("artist", "")).strip() == "赵雷"
        ]
        for sid in to_delete_ids:
            if sid is not None:
                knowledge_base.delete_song(sid)
                logger.info(f"🧹 启动清理：已删除疑似幻觉歌曲 ID={sid}（夜行船 / 赵雷）")
    except Exception as e:
        logger.error(f"启动时清理脏数据失败: {e}", exc_info=True)
    
    logger.info("✅ 组件初始化成功")
except Exception as e:
    logger.error(f"❌ 组件初始化失败: {e}")
    music_client = None
    knowledge_base = None
    SESSION_RECOMMENDED_IDS = {}


@app.route('/', methods=['GET'])
def index():
    """根路径，返回API信息"""
    return jsonify({
        "message": "AI音乐推荐智能体 API",
        "version": "2.0.0",
        "features": [
            "记忆管理：避免重复推荐",
            "多样性回复：相同问题不同回答",
            "会话管理：支持多用户会话"
        ],
        "endpoints": {
            "/": "API信息",
            "/recommend": "POST - 获取音乐推荐（支持 session_id）",
            "/health": "GET - 健康检查",
            "/stats": "GET - 知识库统计信息",
            "/reset": "POST - 清空对话上下文（滑动窗口）"
        }
    })


@app.route('/admin/delete_song', methods=['POST'])
def admin_delete_song():
    """
    删除指定ID的歌曲（管理接口）
    请求体示例: {"id": 123}
    """
    if not knowledge_base:
        return jsonify({"success": False, "error": "知识库未初始化"}), 500

    data = request.get_json() or {}
    song_id = data.get("id")

    try:
        song_id_int = int(song_id)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "请提供有效的歌曲ID"}), 400

    deleted = knowledge_base.delete_song(song_id_int)
    if deleted:
        return jsonify({"success": True, "message": f"已删除ID为 {song_id_int} 的歌曲"}), 200
    else:
        return jsonify({"success": False, "message": f"未找到ID为 {song_id_int} 的歌曲"}), 404


@app.route('/health', methods=['GET'])
def health():
    """健康检查端点"""
    status = {
        "status": "healthy",
        "llm_client": music_client is not None,
        "knowledge_base": knowledge_base is not None and len(knowledge_base.data) > 0,
        "llm_provider": os.getenv("LLM_PROVIDER", "deepseek")
    }
    return jsonify(status)


@app.route('/stats', methods=['GET'])
def stats():
    """获取知识库统计信息"""
    if not knowledge_base:
        return jsonify({"error": "知识库未初始化"}), 500
    
    stats_data = knowledge_base.get_statistics()
    
    return jsonify(stats_data)


@app.route('/reset', methods=['POST'])
def reset_chat_context():
    """
    清空全局对话上下文（滑动窗口）和会话推荐去重集合（仅内存）
    """
    global CHAT_CONTEXT, SESSION_RECOMMENDED_IDS
    CHAT_CONTEXT = []
    SESSION_RECOMMENDED_IDS = {}
    logger.info("🧹 已清空全局对话上下文 CHAT_CONTEXT 以及会话推荐去重缓存")
    return jsonify({"success": True, "message": "聊天上下文与推荐去重缓存已清空"})


@app.route('/recommend', methods=['POST'])
def recommend():
    """
    音乐推荐主端点
    
    请求体格式:
    {
        "message": "我想听点悲伤的歌",
        "session_id": "optional_session_id"  # 可选，用于记忆管理
    }
    
    返回格式:
    {
        "success": true,
        "recommendation": "推荐回复文本",
        "matched_songs": [...],
        "intent": {...},
        "session_id": "..."
    }
    """
    try:
        # 检查组件是否初始化
        if not music_client or not knowledge_base:
            return jsonify({
                "success": False,
                "error": "服务未正确初始化，请检查配置"
            }), 500
        
        # 获取用户输入
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({
                "success": False,
                "error": "请提供 'message' 字段"
            }), 400
        
        user_input = data['message'].strip()
        if not user_input:
            return jsonify({
                "success": False,
                "error": "消息不能为空"
            }), 400
        
        # 获取或生成会话ID
        session_id = data.get('session_id') or str(uuid.uuid4())
        
        logger.info(f"📩 收到用户请求 (会话: {session_id[:8]}...): {user_input}")
        
        # 获取已推荐过的歌曲ID（内存）
        recommended_song_ids = SESSION_RECOMMENDED_IDS.get(session_id, set())
        
        # 步骤1: 意图识别
        logger.info("🔍 步骤1: 意图识别...")
        intent_data = music_client.extract_intent(user_input, history=CHAT_CONTEXT)
        logger.info(f"   识别结果: {intent_data}")

        # 步骤2: 基于意图生成结构化搜索参数（不生成代码，避免RCE）
        available_fields = knowledge_base.get_available_fields()
        search_params = music_client.generate_search_query(intent_data, available_fields)
        logger.info(f"   搜索参数: {search_params}")
        
        # 构建全局排除列表：最近 10 轮推荐过的歌曲标题
        exclude_titles: list[str] = []
        recent_history = RECOMMENDATION_HISTORY[-10:]
        for turn_songs in recent_history:
            # turn_songs 是一轮中的多个歌曲标题
            for title in turn_songs:
                if title:
                    exclude_titles.append(title)

        # 步骤3: 使用结构化参数执行搜索（核心搜索逻辑）
        logger.info("🔎 步骤3: 执行搜索...")
        matched_songs = knowledge_base.search_by_conditions(
            genre=search_params.get('genre'),
            mood=search_params.get('mood'),
            artist=search_params.get('artist'),
            title=search_params.get('title'),
            limit=10,  # 增加搜索数量，以便过滤后仍有足够结果
            exclude_titles=exclude_titles,
        )
        logger.info(f"   找到 {len(matched_songs)} 首匹配的歌曲")
        
        # 步骤3: 过滤已推荐过的歌曲
        if matched_songs:
            original_count = len(matched_songs)
            filtered = []
            for song in matched_songs:
                song_id = _song_id(song)
                if song_id not in recommended_song_ids:
                    filtered.append(song)
            matched_songs = filtered
            filtered_count = len(matched_songs)
            if original_count > filtered_count:
                logger.info(f"   过滤掉 {original_count - filtered_count} 首已推荐过的歌曲，剩余 {filtered_count} 首")
        
        # 如果仍然没有找到匹配的歌曲，让大模型推荐通用歌曲（兜底）
        source = "knowledge_base"
        if not matched_songs:
            logger.info("   未找到匹配歌曲，使用大模型推荐通用歌曲...")
            llm_recommendation = music_client.generate_recommendation_without_matches(
                user_input,
                intent_data,
                conversation_history=CHAT_CONTEXT,
                recommended_song_ids=recommended_song_ids,
                # 将全局历史标题列表传给大模型，强制其避免重复这些歌曲
                exclude_titles=[t for turn in RECOMMENDATION_HISTORY for t in turn]
            )
            
            recommendation = llm_recommendation.get("recommendation", "抱歉，我暂时无法为您推荐具体的歌曲。")
            matched_songs = llm_recommendation.get("recommended_songs", [])
            source = "llm_recommendation"
            
            logger.info(f"   大模型初步推荐了 {len(matched_songs)} 首歌曲，开始进行真实性核查...")

            # 第二步：使用低温度LLM进行真实性核查，仅保留真实存在的歌曲
            verified_songs = music_client.verify_songs(matched_songs)
            logger.info(f"🛡️ 经过核查，从 {len(matched_songs)} 首中保留了 {len(verified_songs)} 首真实歌曲")

            # 将通过验证的歌曲用于后续展示与自学习；如果全部不通过，则保留原始列表仅用于回复文案
            if verified_songs:
                matched_songs = verified_songs

            # 自学习：仅将通过验证的歌曲写入知识库
            if verified_songs:
                try:
                    added = knowledge_base.add_new_songs(verified_songs)
                    logger.info(f"📚 自学习：已将 {added} 首经核查的大模型推荐新歌写入知识库")
                except Exception as e:
                    logger.error(f"自学习写入知识库时出错: {e}", exc_info=True)
        else:
            # 步骤4: 生成推荐回复（有匹配歌曲时）
            logger.info("💬 步骤4: 生成推荐回复...")
            recommendation = music_client.generate_recommendation(
                user_input,
                matched_songs[:5],  # 限制传递给LLM的歌曲数量
                intent_data,
                conversation_history=CHAT_CONTEXT
            )
        
        # 记录推荐的歌曲到内存（用于推荐去重）
        if matched_songs:
            session_set = SESSION_RECOMMENDED_IDS.setdefault(session_id, set())
            for song in matched_songs:
                song_id = _song_id(song)
                session_set.add(song_id)

            # 记录到全局推荐历史（只记录标题，用于跨会话的去重）
            current_titles = [s.get("title") for s in matched_songs if s.get("title")]
            if current_titles:
                RECOMMENDATION_HISTORY.append(current_titles)
                # 可选：限制历史长度，避免无限增长
                if len(RECOMMENDATION_HISTORY) > 100:
                    del RECOMMENDATION_HISTORY[:-100]

        # 使用全局滑动窗口记录对话历史（仅保留最近 10 轮）
        CHAT_CONTEXT.append({"role": "user", "content": user_input})
        CHAT_CONTEXT.append({"role": "assistant", "content": recommendation})
        if len(CHAT_CONTEXT) > 20:
            # 只保留最后 20 条消息（10 轮问答）
            del CHAT_CONTEXT[:-20]
        
        # 返回结果
        return jsonify({
            "success": True,
            "recommendation": recommendation,
            "matched_songs": matched_songs[:5],  # 限制返回数量
            "intent": intent_data,
            "source": source,
            "session_id": session_id
        })
    
    except Exception as e:
        logger.error(f"❌ 处理请求时出错: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"服务器错误: {str(e)}"
        }), 500


if __name__ == '__main__':
    # 从环境变量读取配置
    host = os.getenv('FLASK_HOST', '127.0.0.1')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"🚀 启动Flask应用: http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)

