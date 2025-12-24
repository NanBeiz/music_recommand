# 🎵 AI 音乐推荐智能体 (WeChat Edition)

> 一个具备**自我核查**、**知识库自学习**与**长期记忆**能力的 AI 音乐助手，专为微信公众号环境打造。

本项目是一个基于大语言模型（LLM）的智能 Agent，能够理解用户的自然语言需求，从本地知识库或外部生成推荐。它集成了**反幻觉机制 (Anti-Hallucination)**，确保推荐的歌曲真实存在，并支持通过微信接口进行异步交互。

## ✨ 核心特性

- **🧠 多模型驱动**: 支持通义千问 (Qwen)、OpenAI、智谱 AI (Zhipu)、月之暗面 (Moonshot) 等多种 LLM 切换。
- **🛡️ 幻觉校验机制 (Verifier)**: 内置“版权审核员”Agent，对 LLM 生成的推荐结果进行二次核查，剔除不存在的虚假歌曲（拒绝“张冠李戴”）。
- **📚 RAG 与自学习**: 优先检索本地 JSON 知识库；若本地无匹配，则利用 LLM 生成并验证，验证通过的歌曲会自动**写入知识库**，实现越用越聪明。
- **💬 智能上下文记忆**: 基于滑动窗口机制维护对话历史，支持多轮对话，并能根据用户历史偏好进行去重推荐。
- **⚡ 微信异步响应**: 针对微信服务器 5 秒超时限制，采用**异步线程池**处理推荐任务，并通过中转服务器主动推送客服消息。
- **📊 数据持久化**: 使用 SQLite + SQLAlchemy 记录所有用户交互 (`User`) 和对话日志 (`ChatLog`)，并提供管理后台接口。
- **🐳 Docker 开箱即用**: 提供完整的 Docker 和 Docker Compose 配置，集成 Ngrok 内网穿透。

## 🏗️ 项目架构

```
WeChat/
├── wechat_service.py       # [核心] Flask 主服务，包含路由、业务编排与后台任务管理
├── llm_client.py           # [核心] LLM 客户端工厂，封装各家大模型 API
├── knowledge_base.py       # [数据] JSON 知识库管理，支持模糊搜索与持久化
├── verifier.py             # [组件] 歌曲真实性校验器 (Anti-Hallucination)
├── memory_manager.py       # [组件] 会话记忆与去重逻辑
├── music_data.json         # [数据] 本地音乐元数据文件
├── wechat_data.db          # [数据] SQLite 数据库 (用户与日志)
├── docker-compose.yml      # Docker 编排文件
└── requirements.txt        # Python 依赖
```

## 🚀 快速开始

### 1. 环境准备

确保已安装 Python 3.8+ 或 Docker。

### 2. 配置环境变量

复制 `.env` 文件并填入你的 API Key：

```
# Linux/Mac
cp env_example.txt .env
# Windows
copy env_example.txt .env
```

编辑 `.env` 文件，关键配置如下：

```
# LLM 提供商: qwen, openai, zhipu, moonshot
LLM_PROVIDER=qwen
# 对应的 API Key
QWEN_API_KEY=sk-xxxxxxxxxxxx
# OPENAI_API_KEY=sk-xxxxxxxx (如果使用 OpenAI)

# 服务端口
FLASK_PORT=5000

# 微信消息中转服务器地址 (用于发送客服消息)
MAIN_SERVER=[http://your-relay-server.com](http://your-relay-server.com)
```

### 3. 运行方式

#### 方式 A: Docker Compose (推荐)

一键启动服务和 Ngrok 隧道：

```
docker-compose up -d --build
```

启动后，访问 `http://localhost:4040` 查看 Ngrok 的公网 URL，将其配置到你的微信公众号后台。

#### 方式 B: 本地 Python 运行

```
# 安装依赖
pip install -r requirements.txt

# 启动服务
python wechat_service.py
```

服务将在 `http://0.0.0.0:5000` 启动。

## 📖 API 接口说明

### 1. 微信消息入口 (Webhook)

- **URL**: `POST /message`
- **描述**: 接收微信（或中转服务）转发的用户消息。
- **机制**: 立即返回文本 "正在为您生成音乐推荐..."，随后在后台线程处理并通过客服接口回调。
- **参数**: `from_user` (OpenID), `content` (消息内容), `type` (text)。

### 2. 标准推荐接口 (RESTful)

- **URL**: `POST /recommend`

- **描述**: 供 Web 前端或调试使用的同步接口。

- **请求示例**:

  ```
  {
    "message": "推荐几首适合下雨天听的周杰伦的歌",
    "session_id": "test_user_001"
  }
  ```

### 3. 管理后台统计

- **URL**: `GET /admin/stats`
- **描述**: 获取总用户数、今日活跃用户、热门意图分布及最近对话日志。

### 4. 用户列表

- **URL**: `GET /admin/users?page=1&page_size=20`
- **描述**: 分页查看与系统交互过的微信用户。

## 🛡️ 幻觉校验工作流

这是本系统区别于普通 ChatBot 的核心逻辑：

1. **意图提取**: LLM 分析用户输入（例如："我想听伤感的粤语歌"）。
2. **本地检索**: 在 `music_data.json` 中查找。
   - *命中*: 直接返回结果。
   - *未命中*: 进入生成模式。
3. **LLM 生成**: 模型尝试生成 5 首符合条件的歌曲。
4. **Verifier 介入**: `verifier.py` 扮演严苛的版权管理员，要求 LLM 为每一首歌提供**专辑名**和**发行年份**作为证据。
5. **过滤与入库**:
   - 无法提供确凿证据的歌曲被剔除。
   - 验证通过的歌曲被作为推荐结果返回。
   - 系统**异步**将新歌写入 `music_data.json`，完成自学习。

## 🛠️ 技术栈

- **Web 框架**: Flask 3.0
- **数据库**: SQLite + SQLAlchemy (ORM)
- **LLM 客户端**: Requests (支持 OpenAI 协议及各家私有协议)
- **部署**: Docker + Docker Compose
- **内网穿透**: Ngrok

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License