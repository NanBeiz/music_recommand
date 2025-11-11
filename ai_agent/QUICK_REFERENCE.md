# 🚀 模型切换快速参考

## 📋 需要修改的参数

### 1. 环境变量配置文件 (`.env`)

只需要修改 **2个核心参数**：

#### 参数1: 选择LLM提供商
```bash
LLM_PROVIDER=deepseek  # 改为: openai, qwen, zhipu, moonshot
```

#### 参数2: 配置对应提供商的API密钥

**DeepSeek:**
```bash
DEEPSEEK_API_KEY=your_key_here
DEEPSEEK_MODEL=deepseek-chat  # 可选
```

**OpenAI:**
```bash
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-3.5-turbo  # 可选，默认: gpt-3.5-turbo
```

**通义千问:**
```bash
QWEN_API_KEY=your_key_here
QWEN_MODEL=qwen-turbo  # 可选
```

**智谱AI:**
```bash
ZHIPU_API_KEY=your_key_here
ZHIPU_MODEL=glm-4  # 可选
```

**月之暗面:**
```bash
MOONSHOT_API_KEY=your_key_here
MOONSHOT_MODEL=moonshot-v1-8k  # 可选
```

---

## 🔄 切换步骤

### 步骤1: 修改 `.env` 文件
```bash
# 示例：从DeepSeek切换到OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxxxxxxxxxxxx
```

### 步骤2: 重启服务
```bash
python app.py
# 或
./run.sh  # Linux/Mac
run.bat   # Windows
```

### 步骤3: 验证切换
访问 `http://127.0.0.1:5000/health` 查看当前使用的提供商

---

## 📊 参数对照表

| 参数 | DeepSeek | OpenAI | 通义千问 | 智谱AI | 月之暗面 |
|------|----------|--------|----------|--------|----------|
| **LLM_PROVIDER** | `deepseek` | `openai` | `qwen` | `zhipu` | `moonshot` |
| **API密钥** | `DEEPSEEK_API_KEY` | `OPENAI_API_KEY` | `QWEN_API_KEY` | `ZHIPU_API_KEY` | `MOONSHOT_API_KEY` |
| **模型名称** | `DEEPSEEK_MODEL` | `OPENAI_MODEL` | `QWEN_MODEL` | `ZHIPU_MODEL` | `MOONSHOT_MODEL` |
| **默认模型** | `deepseek-chat` | `gpt-3.5-turbo` | `qwen-turbo` | `glm-4` | `moonshot-v1-8k` |

---

## 💡 常用模型名称

### DeepSeek
- `deepseek-chat`
- `deepseek-coder`

### OpenAI
- `gpt-4`
- `gpt-4-turbo`
- `gpt-3.5-turbo`
- `gpt-4o`
- `gpt-4o-mini`

### 通义千问
- `qwen-turbo`
- `qwen-plus`
- `qwen-max`
- `qwen-max-longcontext`

### 智谱AI
- `glm-4`
- `glm-4-flash`
- `glm-3-turbo`

### 月之暗面
- `moonshot-v1-8k`
- `moonshot-v1-32k`
- `moonshot-v1-128k`

---

## ⚠️ 注意事项

1. **API密钥**: 必须设置对应提供商的API密钥
2. **模型名称**: 如果不设置，会使用默认模型
3. **Azure OpenAI**: 如需使用Azure OpenAI，需要额外设置 `OPENAI_BASE_URL` 和 `AZURE_OPENAI_API_VERSION`
4. **重启服务**: 修改配置后必须重启服务才能生效

---

## 📖 详细文档

- 完整切换指南: [MODEL_SWITCHING_GUIDE.md](MODEL_SWITCHING_GUIDE.md)
- 项目文档: [README.md](README.md)

---

**一句话总结：只需修改 `LLM_PROVIDER` 和对应的 `API_KEY`，然后重启服务即可！** 🎯

