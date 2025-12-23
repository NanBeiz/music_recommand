"""
wechat_service.py (Flask 版)

统一服务：
- 保留 app.py 中完整的音乐推荐与会话管理逻辑（推荐去重、多轮上下文、自学习）
- 新增：用户管理、对话日志（SQLite + SQLAlchemy）
- 新增：后台管理接口（用户列表、统计）
- 新增：微信公众号接入（/message，通过中转服务器客服接口回复）

运行方式：
    python wechat_service.py
"""

import os
import uuid
import json
import threading
import logging
from datetime import datetime, date
from typing import Dict, Set, List, Optional, Any

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import requests

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    func,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session

from llm_client import create_llm_client, MusicRecommendationClient
from knowledge_base import KnowledgeBase

# ---------------------- 环境与日志 ----------------------

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 中转服务器地址（给微信发客服消息）
MAIN_SERVER = os.getenv("MAIN_SERVER", "http://1.95.125.201")

# ---------------------- Flask 应用 ----------------------

app = Flask(__name__)
CORS(app)

# ---------------------- SQLite / SQLAlchemy ----------------------

Base = declarative_base()


class User(Base):
    """用户表：基于 openid 管理公众号用户"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    openid = Column(String(128), unique=True, index=True, nullable=False)
    first_seen = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_active = Column(DateTime, nullable=False, default=datetime.utcnow)
    interaction_count = Column(Integer, nullable=False, default=0)

    chat_logs = relationship("ChatLog", back_populates="user")


class ChatLog(Base):
    """对话日志：记录用户输入与 AI 回复"""

    __tablename__ = "chat_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_input = Column(Text, nullable=False)
    ai_reply = Column(Text, nullable=False)
    intent_type = Column(String(64), nullable=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="chat_logs")


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "wechat_data.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """获取数据库会话（调用方负责关闭）"""
    return SessionLocal()


# ---------------------- 内存级会话管理（从 app.py 平移） ----------------------

# 按 session_id 存储每个用户的推荐历史与对话上下文，保证多用户隔离
USER_REC_HISTORY: Dict[str, List[List[str]]] = {}
USER_CHAT_CONTEXTS: Dict[str, List[Dict[str, str]]] = {}
SESSION_RECOMMENDED_IDS: Dict[str, Set[str]] = {}
# 记录每个会话的最后活跃时间（用于超时自动重置）
SESSION_LAST_ACTIVE: Dict[str, datetime] = {}


def _song_id(song: Dict) -> str:
    """生成歌曲唯一标识（标题+歌手，小写去空格）"""
    title = str(song.get("title", "")).lower().strip()
    artist = str(song.get("artist", "")).lower().strip()
    return f"{title}||{artist}"


# ---------------------- LLM / 知识库 初始化（与 app.py 保持一致） ----------------------

music_client: Optional[MusicRecommendationClient] = None
knowledge_base: Optional[KnowledgeBase] = None


def init_components():
    """启动时初始化组件"""
    global music_client, knowledge_base, SESSION_RECOMMENDED_IDS
    try:
        llm_provider = os.getenv("LLM_PROVIDER", "qwen")
        logger.info(f"🤖 使用LLM提供商: {llm_provider}")

        llm_client = create_llm_client(llm_provider)
        music_client = MusicRecommendationClient(llm_client)

        music_data_path = os.getenv("MUSIC_DATA_PATH", "music_data.json")
        knowledge_base = KnowledgeBase(json_file_path=music_data_path)

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
                    logger.info(
                        f"🧹 启动清理：已删除疑似幻觉歌曲 ID={sid}（夜行船 / 赵雷）"
                    )
        except Exception as e:
            logger.error(f"启动时清理脏数据失败: {e}", exc_info=True)

        logger.info("✅ 组件初始化成功")
    except Exception as e:
        logger.error(f"❌ 组件初始化失败: {e}")
        music_client = None
        knowledge_base = None
        SESSION_RECOMMENDED_IDS = {}


# ---------------------- 微信客服消息中转 ----------------------


def send_custom_message(openid: str, content: str) -> Dict[str, Any]:
    """通过中转服务器发送微信客服消息"""
    url = f"{MAIN_SERVER}/send_custom_message"
    data = {
        "openid": openid,
        "message_type": "text",
        "content": content,
    }
    try:
        resp = requests.post(
            url,
            data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        return resp.json()
    except Exception as e:
        logger.error(f"发送客服消息失败: {e}")
        return {"errcode": -1, "errmsg": str(e)}


# ---------------------- 推荐主逻辑（从 app.py 平移成函数） ----------------------


def recommend_core(user_input: str, session_id: Optional[str]) -> Dict[str, Any]:
    """
    复用 app.py 的推荐主流程，返回结果字典。
    不负责 HTTP 序列化，可被 REST 接口和微信后台任务复用。
    """
    global music_client, knowledge_base, SESSION_LAST_ACTIVE

    if not music_client or not knowledge_base:
        return {
            "success": False,
            "error": "服务未正确初始化，请检查配置",
        }

    session_id = session_id or str(uuid.uuid4())
    logger.info(f"📩 收到用户请求 (会话: {session_id[:8]}...): {user_input}")

    # 获取已推荐过的歌曲ID（内存）
    recommended_song_ids = SESSION_RECOMMENDED_IDS.get(session_id, set())

    # --- 初始化该 session 的上下文与历史（保证隔离） ---
    user_chat = USER_CHAT_CONTEXTS.setdefault(session_id, [])
    rec_history = USER_REC_HISTORY.setdefault(session_id, [])

    # --- 支持用户命令：刷新数据（清除该会话全部记忆） ---
    try:
        now = datetime.utcnow()
        normalized = str(user_input).strip()
        if normalized == "刷新数据":
            # 仅清除该会话的数据，保证多用户隔离
            SESSION_RECOMMENDED_IDS.pop(session_id, None)
            USER_CHAT_CONTEXTS.pop(session_id, None)
            USER_REC_HISTORY.pop(session_id, None)
            SESSION_LAST_ACTIVE[session_id] = now
            return {
                "success": True,
                "recommendation": "已为您清除所有历史记忆，推荐与上下文已重置。",
                "matched_songs": [],
                "intent": {"intent": "reset_memory"},
                "source": "system_command",
                "session_id": session_id,
            }

        # 超时自动重置：如果距上次活跃超过 10 分钟，则清除已推荐缓存（仅该会话）
        last_active = SESSION_LAST_ACTIVE.get(session_id)
        if last_active is not None:
            try:
                if (now - last_active).total_seconds() > 600:
                    SESSION_RECOMMENDED_IDS.pop(session_id, None)
            except Exception:
                # 忽略时间计算异常，继续正常推荐流程
                pass
        # 始终更新最后活跃时间为当前
        SESSION_LAST_ACTIVE[session_id] = now
    except Exception as e:
        logger.debug(f"处理会话刷新/超时逻辑时出错: {e}")

    # 步骤1: 意图识别
    logger.info("🔍 步骤1: 意图识别...")
    intent_data = music_client.extract_intent(user_input, history=CHAT_CONTEXT)
    logger.info(f"   识别结果: {intent_data}")

    # 步骤2: 基于意图生成结构化搜索参数
    available_fields = knowledge_base.get_available_fields()
    search_params = music_client.generate_search_query(intent_data, available_fields)
    logger.info(f"   搜索参数: {search_params}")

    # 构建全局排除列表：最近 10 轮推荐过的歌曲标题
    exclude_titles: List[str] = []
    recent_history = RECOMMENDATION_HISTORY[-10:]
    for turn_songs in recent_history:
        for title in turn_songs:
            if title:
                exclude_titles.append(title)

    # 步骤3: 使用结构化参数执行搜索
    logger.info("🔎 步骤3: 执行搜索...")
    matched_songs = knowledge_base.search_by_conditions(
        genre=search_params.get("genre"),
        mood=search_params.get("mood"),
        artist=search_params.get("artist"),
        title=search_params.get("title"),
        limit=10,
        exclude_titles=exclude_titles,
    )
    logger.info(f"   找到 {len(matched_songs)} 首匹配的歌曲")

    # 过滤已推荐过的歌曲
    if matched_songs:
        original_count = len(matched_songs)
        filtered = []
        for song in matched_songs:
            sid = _song_id(song)
            if sid not in recommended_song_ids:
                filtered.append(song)
        matched_songs = filtered
        filtered_count = len(matched_songs)
        if original_count > filtered_count:
            logger.info(
                f"   过滤掉 {original_count - filtered_count} 首已推荐过的歌曲，剩余 {filtered_count} 首"
            )

    # 如果仍然没有找到匹配的歌曲，让大模型推荐通用歌曲（兜底）
    source = "knowledge_base"
    if not matched_songs:
        logger.info("   未找到匹配歌曲，使用大模型推荐通用歌曲...")
        llm_recommendation = music_client.generate_recommendation_without_matches(
            user_input,
            intent_data,
            conversation_history=CHAT_CONTEXT,
            recommended_song_ids=recommended_song_ids,
            exclude_titles=[t for turn in RECOMMENDATION_HISTORY for t in turn],
        )

        recommendation = llm_recommendation.get(
            "recommendation", "抱歉，我暂时无法为您推荐具体的歌曲。"
        )
        matched_songs = llm_recommendation.get("recommended_songs", [])
        source = "llm_recommendation"

        logger.info(f"   大模型初步推荐了 {len(matched_songs)} 首歌曲，开始进行真实性核查...")

        # 第二步：使用低温度LLM进行真实性核查，仅保留真实存在的歌曲
        verified_songs = music_client.verify_songs(matched_songs)
        logger.info(
            f"🛡️ 经过核查，从 {len(matched_songs)} 首中保留了 {len(verified_songs)} 首真实歌曲"
        )

        # 将通过验证的歌曲用于后续展示；如果全部不通过，则保留原始列表仅用于回复文案
        if verified_songs:
            matched_songs = verified_songs
        # 注意：不在此处直接写入知识库以避免阻塞/耽误对用户的回复。
        #      会将经核查的歌曲通过返回值传回调用方，由调用方在发送回复后异步执行自学习写入。
        # 确保 recommendation 中包含经核查的歌曲列表，避免调用方未展示歌名的情况
        try:
            if matched_songs:
                lines = []
                lines.append("")  # 与主推荐文本空行分隔
                lines.append("🎵 推荐歌曲列表：")
                for idx, song in enumerate(matched_songs, start=1):
                    title = song.get("title") or song.get("name") or ""
                    artist = song.get("artist") or song.get("singer") or ""
                    title = str(title).strip()
                    artist = str(artist).strip()
                    if title or artist:
                        if artist:
                            lines.append(f"{idx}. {title} - {artist}")
                        else:
                            lines.append(f"{idx}. {title}")
                if len(lines) > 2:
                    songs_str = "\n".join(lines)
                    recommendation = f"{recommendation}\n{songs_str}"
        except Exception as e:
            logger.error(f"附加 matched_songs 到 recommendation 时出错: {e}", exc_info=True)
    else:
        # 有匹配歌曲时，生成推荐回复
        logger.info("💬 步骤4: 生成推荐回复...")
        recommendation = music_client.generate_recommendation(
            user_input,
            matched_songs[:5],
            intent_data,
            conversation_history=CHAT_CONTEXT,
        )

    # 记录推荐的歌曲到内存（用于推荐去重）
    if matched_songs:
        session_set = SESSION_RECOMMENDED_IDS.setdefault(session_id, set())
        for song in matched_songs:
            sid = _song_id(song)
            session_set.add(sid)

        # 记录到全局推荐历史（只记录标题，用于跨会话的去重）
        current_titles = [s.get("title") for s in matched_songs if s.get("title")]
        if current_titles:
            RECOMMENDATION_HISTORY.append(current_titles)
            if len(RECOMMENDATION_HISTORY) > 100:
                del RECOMMENDATION_HISTORY[:-100]

    # 使用全局滑动窗口记录对话历史（仅保留最近 10 轮）
    CHAT_CONTEXT.append({"role": "user", "content": user_input})
    CHAT_CONTEXT.append({"role": "assistant", "content": recommendation})
    if len(CHAT_CONTEXT) > 20:
        del CHAT_CONTEXT[:-20]

    return {
        "success": True,
        "recommendation": recommendation,
        "matched_songs": matched_songs[:5],
        "intent": intent_data,
        "source": source,
        "session_id": session_id,
    }


# ---------------------- 通用 HTTP 接口（兼容 app.py 功能） ----------------------


@app.route("/", methods=["GET"])
def index():
    """根路径，返回API信息"""
    return jsonify(
        {
            "message": "AI音乐推荐智能体 API（Flask + 微信接入版）",
            "version": "2.0.0",
            "features": [
                "记忆管理：避免重复推荐",
                "多样性回复：相同问题不同回答",
                "会话管理：支持多用户会话",
                "用户管理：基于 openid 的活跃统计",
                "对话日志：SQLite 持久化",
                "微信接入：/message + 客服消息",
            ],
            "endpoints": {
                "/": "API信息",
                "/recommend": "POST - 获取音乐推荐（支持 session_id）",
                "/health": "GET - 健康检查",
                "/stats": "GET - 知识库统计信息",
                "/reset": "POST - 清空对话上下文（滑动窗口）",
                "/admin/delete_song": "POST - 删除知识库歌曲",
                "/admin/users": "GET - 分页获取用户列表",
                "/admin/stats": "GET - 获取用户与对话统计",
                "/message": "POST - 微信消息入口（中转服务器调用）",
            },
        }
    )


@app.route("/recommend", methods=["POST"])
def recommend():
    """音乐推荐主端点（与 app.py 对齐，供普通前端或测试调用）"""
    data = request.get_json(silent=True) or {}
    if "message" not in data:
        return jsonify({"success": False, "error": "请提供 'message' 字段"}), 400

    user_input = str(data.get("message", "")).strip()
    if not user_input:
        return jsonify({"success": False, "error": "消息不能为空"}), 400

    session_id = data.get("session_id")
    result = recommend_core(user_input, session_id)
    status_code = 200 if result.get("success") else 500
    return jsonify(result), status_code


@app.route("/health", methods=["GET"])
def health():
    """健康检查端点"""
    status = {
        "status": "healthy",
        "llm_client": music_client is not None,
        "knowledge_base": knowledge_base is not None
        and knowledge_base.data is not None
        and len(knowledge_base.data) > 0,
        "llm_provider": os.getenv("LLM_PROVIDER", "qwen"),
    }
    return jsonify(status)


@app.route("/stats", methods=["GET"])
def stats():
    """获取知识库统计信息"""
    if not knowledge_base:
        return jsonify({"error": "知识库未初始化"}), 500
    return jsonify(knowledge_base.get_statistics())


@app.route("/reset", methods=["POST"])
def reset_chat_context():
    """清空全局对话上下文和会话推荐去重集合"""
    global CHAT_CONTEXT, SESSION_RECOMMENDED_IDS
    CHAT_CONTEXT = []
    SESSION_RECOMMENDED_IDS = {}
    logger.info("🧹 已清空全局对话上下文 CHAT_CONTEXT 以及会话推荐去重缓存")
    return jsonify({"success": True, "message": "聊天上下文与推荐去重缓存已清空"})


@app.route("/admin/delete_song", methods=["POST"])
def admin_delete_song():
    """删除指定ID的歌曲（管理接口）"""
    if not knowledge_base:
        return jsonify({"success": False, "error": "知识库未初始化"}), 500

    data = request.get_json(silent=True) or {}
    song_id = data.get("id")
    try:
        song_id_int = int(song_id)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "请提供有效的歌曲ID"}), 400

    deleted = knowledge_base.delete_song(song_id_int)
    if deleted:
        return jsonify({"success": True, "message": f"已删除ID为 {song_id_int} 的歌曲"})
    return jsonify({"success": False, "message": f"未找到ID为 {song_id_int} 的歌曲"}), 404


# ---------------------- 后台管理：用户与统计 ----------------------


@app.route("/admin/users", methods=["GET"])
def list_users():
    """分页获取用户列表"""
    page = int(request.args.get("page", 1))
    page_size = min(int(request.args.get("page_size", 20)), 100)
    if page < 1:
        page = 1

    db = get_db()
    try:
        total = db.query(func.count(User.id)).scalar() or 0
        offset = (page - 1) * page_size
        users = (
            db.query(User)
            .order_by(User.last_active.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )
        return jsonify(
            {
                "total": total,
                "page": page,
                "page_size": page_size,
                "users": [
                    {
                        "id": u.id,
                        "openid": u.openid,
                        "first_seen": u.first_seen,
                        "last_active": u.last_active,
                        "interaction_count": u.interaction_count,
                    }
                    for u in users
                ],
            }
        )
    except Exception as e:
        logger.error(f"/admin/users 查询失败: {e}")
        return jsonify({"total": 0, "page": page, "page_size": page_size, "users": []})
    finally:
        db.close()


@app.route("/admin/stats", methods=["GET"])
def admin_stats():
    """后台统计：总用户数、今日活跃、最近100条日志、热门意图"""
    db = get_db()
    try:
        total_users = db.query(func.count(User.id)).scalar() or 0
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_active_users = (
            db.query(func.count(User.id))
            .filter(User.last_active >= today_start)
            .scalar()
            or 0
        )

        recent_logs = (
            db.query(ChatLog)
            .order_by(ChatLog.timestamp.desc())
            .limit(100)
            .all()
        )

        intent_rows = (
            db.query(ChatLog.intent_type, func.count(ChatLog.id))
            .group_by(ChatLog.intent_type)
            .order_by(func.count(ChatLog.id).desc())
            .all()
        )

        popular_intents = [
            {"intent_type": row[0], "count": row[1]} for row in intent_rows
        ]

        return jsonify(
            {
                "total_users": total_users,
                "today_active_users": today_active_users,
                "recent_logs": [
                    {
                        "id": log.id,
                        "user_id": log.user_id,
                        "user_input": log.user_input,
                        "ai_reply": log.ai_reply,
                        "intent_type": log.intent_type,
                        "timestamp": log.timestamp,
                    }
                    for log in recent_logs
                ],
                "popular_intents": popular_intents,
            }
        )
    except Exception as e:
        logger.error(f"/admin/stats 查询失败: {e}")
        return jsonify(
            {
                "total_users": 0,
                "today_active_users": 0,
                "recent_logs": [],
                "popular_intents": [],
            }
        )
    finally:
        db.close()


# ---------------------- 微信消息处理：/message 接口 ----------------------


def process_wechat_request(from_user: str, content: str, msg_type: str) -> None:
    """
    后台任务：
    - 更新/创建 User
    - 调用推荐核心逻辑（用 openid 作为 session_id）
    - 记录 ChatLog
    - 通过客服接口把结果发回微信
    """
    db = get_db()
    try:
        now = datetime.utcnow()

        # 1. 更新或创建用户记录
        user = db.query(User).filter(User.openid == from_user).first()
        if user is None:
            user = User(
                openid=from_user,
                first_seen=now,
                last_active=now,
                interaction_count=1,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            user.last_active = now
            user.interaction_count = (user.interaction_count or 0) + 1
            db.commit()

        # 2. 生成 AI 回复（仅处理文本消息）
        if msg_type == "text":
            result = recommend_core(content, session_id=from_user)
            ai_reply = result.get(
                "recommendation", "抱歉，我暂时无法为您推荐具体的歌曲。"
            )
            intent_type = (result.get("intent") or {}).get("intent") or result.get(
                "source"
            )

            # matched_songs 的展示已在 recommend_core 内整合入 recommendation 字段，
            # 此处无需再次追加以避免重复显示。
        else:
            ai_reply = f"暂时只支持文本消息进行音乐推荐，您发送的是 {msg_type} 类型消息。"
            intent_type = "unsupported_type"

        # 3. 写入 ChatLog
        chat_log = ChatLog(
            user_id=user.id,
            user_input=content,
            ai_reply=ai_reply,
            intent_type=intent_type,
            timestamp=datetime.utcnow(),
        )
        db.add(chat_log)
        db.commit()

        # 4. 发送客服消息到微信
        resp = send_custom_message(from_user, ai_reply)
        logger.info(f"客服消息发送结果: {resp}")
    except Exception as e:
        logger.error(f"process_wechat_request 出错: {e}", exc_info=True)
    finally:
        db.close()


@app.route("/message", methods=["POST"])
def wechat_message():
    """
    微信服务器（或中间服务器）转发过来的消息入口：
    1. 立即返回“正在为您生成音乐推荐...”，防止超时
    2. 用后台线程处理推荐与客服发送
    """
    from_user = request.form.get("from_user")
    content = request.form.get("content")
    msg_type = request.form.get("type")

    if not from_user or content is None or not msg_type:
        return "缺少必要参数", 400

    logger.info(f"收到微信消息: from_user={from_user}, type={msg_type}, content={content}")

    threading.Thread(
        target=process_wechat_request, args=(from_user, content, msg_type), daemon=True
    ).start()

    return "正在为您生成音乐推荐..."


# ---------------------- 启动 ----------------------


if __name__ == "__main__":
    init_components()
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "8080"))
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    # 强制监听所有网络接口，不管环境变量怎么设
    app.run(host="0.0.0.0", port=port, debug=debug)


