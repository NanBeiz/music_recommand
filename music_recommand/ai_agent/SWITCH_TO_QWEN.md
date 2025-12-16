# 🔄 从DeepSeek切换到通义千问 - 详细步骤

## 📋 需要修改的参数

只需要修改 **2个参数** 即可完成切换：

### 1. 修改 `.env` 文件

打开项目根目录下的 `.env` 文件（如果不存在，从 `env_example.txt` 复制），修改以下内容：

#### 修改前（DeepSeek配置）：
```bash
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

#### 修改后（通义千问配置）：
```bash
LLM_PROVIDER=qwen
QWEN_API_KEY=your_qwen_api_key_here
```

---

## 🔑 获取通义千问API密钥

1. 访问 [阿里云DashScope控制台](https://dashscope.console.aliyun.com/)
2. 注册/登录账号
3. 创建API密钥（API Key）
4. 复制API密钥到 `.env` 文件

---

## 📝 完整配置示例

`.env` 文件的完整配置应该是这样：

```bash
# ============================================
# LLM提供商配置
# ============================================
LLM_PROVIDER=qwen

# ============================================
# 通义千问 (Qwen) API配置
# ============================================
QWEN_API_KEY=sk-xxxxxxxxxxxxx  # 替换为你的实际API密钥
QWEN_MODEL=qwen-turbo          # 可选，默认: qwen-turbo
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# ============================================
# Flask配置
# ============================================
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
FLASK_DEBUG=True
```

---

## 🚀 切换步骤

### 步骤1: 修改 `.env` 文件

编辑 `.env` 文件，将以下两行：
```bash
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

改为：
```bash
LLM_PROVIDER=qwen
QWEN_API_KEY=sk-your-qwen-api-key-here
```

### 步骤2: 重启服务

**Windows:**
```bash
# 停止当前运行的服务（按 Ctrl+C）
# 然后重新启动
python app.py
# 或
run.bat
```

**Linux/Mac:**
```bash
# 停止当前运行的服务（按 Ctrl+C）
# 然后重新启动
python3 app.py
# 或
./run.sh
```

### 步骤3: 验证切换

访问健康检查端点：
```
http://127.0.0.1:5000/health
```

应该返回：
```json
{
  "status": "healthy",
  "llm_client": true,
  "knowledge_base": true,
  "llm_provider": "qwen"
}
```

如果 `llm_provider` 显示为 `qwen`，说明切换成功！

---

## 🎯 可选配置

### 选择不同的通义千问模型

通义千问提供多个模型，你可以根据需求选择：

```bash
# 快速响应模型（推荐，性价比高）
QWEN_MODEL=qwen-turbo

# 增强模型（更强的能力）
QWEN_MODEL=qwen-plus

# 最强模型（最佳效果）
QWEN_MODEL=qwen-max

# 长文本模型（支持更长的上下文）
QWEN_MODEL=qwen-max-longcontext
```

---

## ⚠️ 常见问题

### 1. API密钥错误

**错误信息：** `通义千问API密钥未设置` 或 `API调用失败`

**解决方法：**
- 检查 `.env` 文件中的 `QWEN_API_KEY` 是否正确
- 确认API密钥是否有效（可以在DashScope控制台测试）
- 确保 `.env` 文件在项目根目录

### 2. 模型不存在

**错误信息：** `模型不存在` 或 `404 Not Found`

**解决方法：**
- 检查 `QWEN_MODEL` 是否拼写正确
- 确认你的API密钥有权限使用该模型
- 参考 [通义千问文档](https://help.aliyun.com/zh/dashscope/) 确认可用模型

### 3. 服务启动失败

**错误信息：** `组件初始化失败`

**解决方法：**
- 检查 `.env` 文件格式是否正确（不要有多余的空格）
- 确认 `LLM_PROVIDER=qwen` 已设置
- 查看日志中的详细错误信息

---

## 🧪 测试切换

切换后，可以通过以下方式测试：

### 方式1: 使用前端界面

1. 打开 `index.html` 文件
2. 输入测试问题：`我想听点悲伤的歌`
3. 查看是否能正常返回推荐结果

### 方式2: 使用API测试

```bash
curl -X POST http://127.0.0.1:5000/recommend \
  -H "Content-Type: application/json" \
  -d '{"message": "我想听点悲伤的歌"}'
```

### 方式3: 查看日志

服务启动时，你应该看到：
```
🤖 使用LLM提供商: qwen
✅ 组件初始化成功
```

---

## 📚 参考资源

- [通义千问API文档](https://help.aliyun.com/zh/dashscope/)
- [DashScope控制台](https://dashscope.console.aliyun.com/)
- [模型切换完整指南](MODEL_SWITCHING_GUIDE.md)

---

## ✅ 检查清单

切换前请确认：
- [ ] 已获取通义千问API密钥
- [ ] 已修改 `.env` 文件中的 `LLM_PROVIDER=qwen`
- [ ] 已设置 `QWEN_API_KEY` 为你的实际API密钥
- [ ] 已重启服务
- [ ] 已验证 `/health` 端点显示 `llm_provider: qwen`
- [ ] 已测试推荐功能正常工作

---

**切换完成！现在你的项目使用的是通义千问模型了！** 🎉

