# 🔄 模型切换指南

本指南将帮助您将项目从DeepSeek切换到其他LLM模型（OpenAI、通义千问、智谱AI、月之暗面等）。

## 📋 快速切换步骤

### 1. 修改环境变量配置

编辑 `.env` 文件，修改以下参数：

```bash
# 选择LLM提供商
LLM_PROVIDER=deepseek  # 改为: openai, qwen, zhipu, moonshot

# 配置对应提供商的API密钥
# 例如切换到OpenAI:
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-3.5-turbo
```

### 2. 重启服务

```bash
# Windows
run.bat

# Linux/Mac
./run.sh
```

## 🔧 详细配置说明

### 支持的模型提供商

| 提供商 | LLM_PROVIDER值 | 需要设置的环境变量 | 获取API密钥 |
|--------|---------------|------------------|------------|
| **DeepSeek** | `deepseek` | `DEEPSEEK_API_KEY` | [DeepSeek平台](https://platform.deepseek.com/) |
| **OpenAI** | `openai` | `OPENAI_API_KEY` | [OpenAI平台](https://platform.openai.com/) |
| **通义千问 (Qwen)** | `qwen` | `QWEN_API_KEY` | [阿里云DashScope](https://dashscope.console.aliyun.com/) |
| **智谱AI (Zhipu)** | `zhipu` | `ZHIPU_API_KEY` | [智谱AI平台](https://open.bigmodel.cn/) |
| **月之暗面 (Moonshot)** | `moonshot` | `MOONSHOT_API_KEY` | [Moonshot平台](https://platform.moonshot.cn/) |

---

## 📝 各模型详细配置

### 1. DeepSeek

**配置文件示例：**
```bash
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxx
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

**可用模型：**
- `deepseek-chat` (默认)
- `deepseek-coder`

---

### 2. OpenAI

**配置文件示例：**
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxxxxxxxxxxxx
OPENAI_MODEL=gpt-3.5-turbo
# 可选: Azure OpenAI
# OPENAI_BASE_URL=https://your-resource.openai.azure.com/
```

**可用模型：**
- `gpt-4`
- `gpt-4-turbo`
- `gpt-3.5-turbo` (默认)
- `gpt-4o`
- `gpt-4o-mini`

**Azure OpenAI配置：**
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=your_azure_key
OPENAI_BASE_URL=https://your-resource.openai.azure.com/
OPENAI_MODEL=your-deployment-name
```

---

### 3. 通义千问 (Qwen)

**配置文件示例：**
```bash
LLM_PROVIDER=qwen
QWEN_API_KEY=sk-xxxxxxxxxxxxx
QWEN_MODEL=qwen-turbo
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

**可用模型：**
- `qwen-turbo` (默认)
- `qwen-plus`
- `qwen-max`
- `qwen-max-longcontext`

---

### 4. 智谱AI (Zhipu)

**配置文件示例：**
```bash
LLM_PROVIDER=zhipu
ZHIPU_API_KEY=your_zhipu_api_key_here
ZHIPU_MODEL=glm-4
```

**可用模型：**
- `glm-4` (默认)
- `glm-4-flash`
- `glm-3-turbo`

---

### 5. 月之暗面 (Moonshot)

**配置文件示例：**
```bash
LLM_PROVIDER=moonshot
MOONSHOT_API_KEY=sk-xxxxxxxxxxxxx
MOONSHOT_MODEL=moonshot-v1-8k
```

**可用模型：**
- `moonshot-v1-8k` (默认)
- `moonshot-v1-32k`
- `moonshot-v1-128k`

---

## 🎯 切换示例

### 示例1: 从DeepSeek切换到OpenAI

**步骤：**
1. 编辑 `.env` 文件：
```bash
# 修改LLM提供商
LLM_PROVIDER=openai

# 配置OpenAI API密钥
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-3.5-turbo
```

2. 重启服务：
```bash
python app.py
```

3. 验证切换：
访问 `http://127.0.0.1:5000/health`，查看 `llm_provider` 字段。

---

### 示例2: 从DeepSeek切换到通义千问

**步骤：**
1. 编辑 `.env` 文件：
```bash
# 修改LLM提供商
LLM_PROVIDER=qwen

# 配置通义千问API密钥
QWEN_API_KEY=sk-your-qwen-api-key-here
QWEN_MODEL=qwen-turbo
```

2. 重启服务

---

## 🔍 验证配置

### 1. 检查健康状态

访问 `http://127.0.0.1:5000/health`，应该返回：
```json
{
  "status": "healthy",
  "llm_client": true,
  "knowledge_base": true,
  "llm_provider": "openai"
}
```

### 2. 测试推荐功能

发送测试请求：
```bash
curl -X POST http://127.0.0.1:5000/recommend \
  -H "Content-Type: application/json" \
  -d '{"message": "我想听点悲伤的歌"}'
```

---

## ⚠️ 常见问题

### 1. API密钥错误

**错误信息：** `API密钥未设置` 或 `API调用失败`

**解决方法：**
- 检查 `.env` 文件中的API密钥是否正确
- 确保环境变量名称与提供商匹配
- 验证API密钥是否有效

### 2. 模型不存在

**错误信息：** `模型不存在` 或 `404 Not Found`

**解决方法：**
- 检查模型名称是否正确
- 确认您的API密钥有权限使用该模型
- 参考各提供商的文档确认可用模型列表

### 3. 响应格式不同

**问题：** 某些模型的响应格式可能与预期不同

**解决方法：**
- 所有提供商都遵循OpenAI兼容的API格式
- 如果遇到问题，检查 `llm_client.py` 中的响应解析逻辑

---

## 🔧 高级配置

### 自定义模型参数

可以在代码中自定义温度、最大token数等参数。编辑 `llm_client.py` 中的 `MusicRecommendationClient` 类方法：

```python
# 修改意图识别的温度
response = self.llm_client.chat_completion(
    messages, 
    temperature=0.3,  # 调整此值
    max_tokens=500
)
```

### 添加新的LLM提供商

如果需要添加新的LLM提供商：

1. 在 `llm_client.py` 中创建新的客户端类（继承 `LLMClient`）
2. 实现 `chat_completion` 方法
3. 在 `create_llm_client` 函数中添加新的提供商分支

---

## 📚 参考资源

- [DeepSeek API文档](https://platform.deepseek.com/api-docs/)
- [OpenAI API文档](https://platform.openai.com/docs/)
- [通义千问API文档](https://help.aliyun.com/zh/dashscope/)
- [智谱AI API文档](https://open.bigmodel.cn/dev/api)
- [月之暗面API文档](https://platform.moonshot.cn/docs)

---

## 💡 提示

1. **成本考虑：** 不同模型的定价不同，选择适合您需求的模型
2. **性能优化：** 可以根据任务选择不同的模型（例如，意图识别使用小模型，生成回复使用大模型）
3. **备用方案：** 建议配置多个提供商的API密钥，以便在一个服务不可用时切换

---

**享受多模型支持的灵活性！** 🚀

