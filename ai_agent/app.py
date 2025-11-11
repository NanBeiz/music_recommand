"""
Flask Web应用主文件
实现AI音乐推荐智能体的HTTP API接口
"""
import os
import logging
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

# 创建Flask应用
app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 初始化组件
try:
    # 从环境变量读取LLM提供商配置
    llm_provider = os.getenv("LLM_PROVIDER", "deepseek")
    logger.info(f"🤖 使用LLM提供商: {llm_provider}")
    
    # 创建LLM客户端
    llm_client = create_llm_client(llm_provider)
    
    # 创建音乐推荐客户端（封装了业务逻辑）
    music_client = MusicRecommendationClient(llm_client)
    
    # 初始化知识库
    knowledge_base = KnowledgeBase()
    logger.info("✅ 组件初始化成功")
except Exception as e:
    logger.error(f"❌ 组件初始化失败: {e}")
    music_client = None
    knowledge_base = None


@app.route('/', methods=['GET'])
def index():
    """根路径，返回API信息"""
    return jsonify({
        "message": "AI音乐推荐智能体 API",
        "version": "1.0.0",
        "endpoints": {
            "/": "API信息",
            "/recommend": "POST - 获取音乐推荐",
            "/health": "GET - 健康检查",
            "/stats": "GET - 知识库统计信息"
        }
    })


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
    
    return jsonify(knowledge_base.get_statistics())


@app.route('/recommend', methods=['POST'])
def recommend():
    """
    音乐推荐主端点
    
    请求体格式:
    {
        "message": "我想听点悲伤的歌"
    }
    
    返回格式:
    {
        "success": true,
        "recommendation": "推荐回复文本",
        "matched_songs": [...],
        "intent": {...}
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
        
        logger.info(f"📩 收到用户请求: {user_input}")
        
        # 步骤1: 意图识别
        logger.info("🔍 步骤1: 意图识别...")
        intent_data = music_client.extract_intent(user_input)
        logger.info(f"   识别结果: {intent_data}")
        
        # 步骤2: 生成搜索查询
        logger.info("🧠 步骤2: 生成搜索查询...")
        available_fields = knowledge_base.get_available_fields()
        search_query = music_client.generate_search_query(intent_data, available_fields)
        logger.info(f"   搜索查询: {search_query}")
        
        # 步骤3: 执行搜索
        logger.info("🔎 步骤3: 执行搜索...")
        matched_songs = knowledge_base.search(search_query)
        logger.info(f"   找到 {len(matched_songs)} 首匹配的歌曲")
        
        # 如果没有找到匹配的歌曲，使用备用搜索方法
        if not matched_songs:
            logger.info("   使用备用搜索方法...")
            matched_songs = knowledge_base.search_by_conditions(
                genre=intent_data.get('genre'),
                mood=intent_data.get('mood'),
                artist=intent_data.get('artist'),
                title=intent_data.get('song'),
                limit=5
            )
        
        # 如果仍然没有找到匹配的歌曲，让大模型推荐通用歌曲
        source = "knowledge_base"
        if not matched_songs:
            logger.info("   未找到匹配歌曲，使用大模型推荐通用歌曲...")
            llm_recommendation = music_client.generate_recommendation_without_matches(
                user_input,
                intent_data
            )
            
            recommendation = llm_recommendation.get("recommendation", "抱歉，我暂时无法为您推荐具体的歌曲。")
            matched_songs = llm_recommendation.get("recommended_songs", [])
            source = "llm_recommendation"
            
            logger.info(f"   大模型推荐了 {len(matched_songs)} 首歌曲")
        else:
            # 步骤4: 生成推荐回复（有匹配歌曲时）
            logger.info("💬 步骤4: 生成推荐回复...")
            recommendation = music_client.generate_recommendation(
                user_input,
                matched_songs,
                intent_data
            )
        
        # 返回结果
        return jsonify({
            "success": True,
            "recommendation": recommendation,
            "matched_songs": matched_songs[:5],  # 限制返回数量
            "intent": intent_data,
            "search_query": search_query if source == "knowledge_base" else None,
            "source": source
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
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    logger.info(f"🚀 启动Flask应用: http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)

