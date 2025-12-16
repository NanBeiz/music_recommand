# 🎵 AI音乐推荐智能体

一个基于LLM的智能音乐推荐系统，支持多种大语言模型（DeepSeek、OpenAI、通义千问、智谱AI、月之暗面等），结合了自然语言处理、知识库检索和生成式AI技术。

## ✨ 功能特点

- 🤖 **智能意图识别**: 使用LLM理解用户的自然语言输入
- 🧠 **智能推理**: 根据用户需求生成精确的搜索查询
- 📚 **知识库检索**: 从JSON格式的音乐数据库中快速检索匹配歌曲
- 💬 **自然回复**: 生成友好、个性化的音乐推荐回复
- 🌐 **Web界面**: 美观易用的前端界面
- 🔄 **多模型支持**: 支持DeepSeek、OpenAI、通义千问、智谱AI、月之暗面等多种LLM

## 🏗️ 项目架构

```
ai_agent/
├── app.py                    # Flask后端主应用
├── llm_client.py            # 通用LLM客户端（支持多模型）
├── deepseek_client.py       # DeepSeek客户端（向后兼容）
├── knowledge_base.py        # 知识库管理模块
├── music_data.json          # 音乐数据（JSON格式）
├── index.html               # 前端Web界面
├── requirements.txt         # Python依赖
├── env_example.txt          # 环境变量示例
├── MODEL_SWITCHING_GUIDE.md # 模型切换指南
└── README.md                # 项目文档
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置API密钥

创建 `.env` 文件，并填入你的DeepSeek API密钥：

**Windows:**
```bash
copy env_example.txt .env
```

**Linux/Mac:**
```bash
cp env_example.txt .env
```

编辑 `.env` 文件，配置您选择的LLM提供商：

**使用DeepSeek（默认）：**
```
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

**使用OpenAI：**
```
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-3.5-turbo
```

**使用通义千问：**
```
LLM_PROVIDER=qwen
QWEN_API_KEY=your_qwen_api_key_here
```

> 💡 获取API密钥:
> - DeepSeek: [DeepSeek平台](https://platform.deepseek.com/)
> - OpenAI: [OpenAI平台](https://platform.openai.com/)
> - 通义千问: [阿里云DashScope](https://dashscope.console.aliyun.com/)
> - 智谱AI: [智谱AI平台](https://open.bigmodel.cn/)
> - 月之暗面: [Moonshot平台](https://platform.moonshot.cn/)
> 
> 📖 详细的模型切换指南请参考 [MODEL_SWITCHING_GUIDE.md](MODEL_SWITCHING_GUIDE.md)

### 3. 启动后端服务

**方式1: 使用启动脚本（推荐）**

Windows:
```bash
run.bat
```

Linux/Mac:
```bash
chmod +x run.sh
./run.sh
```

**方式2: 直接运行Python**

```bash
python app.py
```

服务将在 `http://127.0.0.1:5000` 启动

### 4. 打开前端界面

在浏览器中打开 `index.html` 文件，或者使用以下命令启动一个简单的HTTP服务器：

```bash
# Python 3
python -m http.server 8000

# 然后访问 http://localhost:8000/index.html
```

## 📖 API文档

### POST /recommend

获取音乐推荐

**请求体:**
```json
{
  "message": "我想听点悲伤的歌"
}
```

**响应:**
```json
{
  "success": true,
  "recommendation": "根据你的需求，我为你推荐以下悲伤的歌曲...",
  "matched_songs": [
    {
      "id": 5,
      "title": "Someone Like You",
      "artist": "Adele",
      "genre": "Pop",
      "mood": "sad",
      "year": 2011,
      "duration": 285
    }
  ],
  "intent": {
    "intent": "find_music",
    "mood": "sad",
    "genre": null,
    "artist": null
  }
}
```

### GET /health

健康检查端点

### GET /stats

获取知识库统计信息

## 🔧 核心模块说明

### 1. LLMClient (`llm_client.py`)

通用的LLM客户端，支持多种模型提供商：
- `DeepSeekClient`: DeepSeek API客户端
- `OpenAIClient`: OpenAI/Azure OpenAI客户端
- `QwenClient`: 通义千问API客户端
- `ZhipuClient`: 智谱AI客户端
- `MoonshotClient`: 月之暗面客户端
- `MusicRecommendationClient`: 音乐推荐业务逻辑封装
  - `extract_intent()`: 从用户输入中提取意图和实体
  - `generate_search_query()`: 生成Python搜索查询代码
  - `generate_recommendation()`: 生成推荐回复

### 2. KnowledgeBase (`knowledge_base.py`)

管理JSON知识库：
- `load()`: 加载JSON数据
- `search()`: 执行搜索查询
- `search_by_conditions()`: 基于条件搜索（备用方法）

### 3. Flask App (`app.py`)

Web服务主应用：
- `/recommend`: 主要的推荐端点
- `/health`: 健康检查
- `/stats`: 统计信息

## 🎯 使用示例

### 示例1: 基于情绪的推荐
```
用户: "我想听点悲伤的歌"
系统: 推荐包含 "Someone Like You", "Yesterday", "Hallelujah" 等
```

### 示例2: 基于流派的推荐
```
用户: "推荐一些摇滚音乐"
系统: 推荐包含 "Bohemian Rhapsody", "Hotel California", "Stairway to Heaven" 等
```

### 示例3: 基于歌手的推荐
```
用户: "推荐Adele的歌"
系统: 推荐 Adele 的歌曲
```

## 🛠️ 技术栈

- **后端**: Flask (Python Web框架)
- **AI模型**: 支持多种LLM（DeepSeek、OpenAI、通义千问、智谱AI、月之暗面等）
- **知识库**: JSON格式数据存储
- **前端**: HTML + CSS + JavaScript (原生)
- **API通信**: RESTful API

## 🔄 切换LLM模型

项目支持多种LLM提供商，只需修改 `.env` 文件中的配置即可切换：

```bash
# 切换到OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key_here

# 切换到通义千问
LLM_PROVIDER=qwen
QWEN_API_KEY=your_key_here
```

详细的切换指南和配置说明请参考：[MODEL_SWITCHING_GUIDE.md](MODEL_SWITCHING_GUIDE.md)

## 📝 扩展建议

1. **添加更多音乐数据**: 扩展 `music_data.json` 文件
2. **支持音频播放**: 集成音乐播放API
3. **用户历史记录**: 添加数据库存储用户交互历史
4. **个性化推荐**: 基于用户历史偏好进行推荐
5. **多语言支持**: 支持更多语言的音乐推荐

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 🙏 致谢

- [DeepSeek](https://www.deepseek.com/) - 提供强大的LLM API
- [Flask](https://flask.palletsprojects.com/) - 优秀的Python Web框架

---

**享受音乐，享受AI！** 🎵✨

