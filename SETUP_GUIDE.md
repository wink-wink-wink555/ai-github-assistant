# AI GitHub Assistant 安装指南

本指南将帮助您快速安装和配置 AI GitHub Assistant 项目。

## 📋 系统要求

- **Python**: 3.8 或更高版本
- **操作系统**: Windows 10+, macOS 10.14+, Linux
- **网络**: 稳定的互联网连接
- **账户**: GitHub 和 DeepSeek 账户（用于获取 API Token）

## 🚀 快速安装

### 步骤 1: 克隆项目

   ```bash
   # 克隆项目到本地
   git clone https://github.com/wink-wink-wink555/ai-github-assistant.git
   cd ai-github-assistant
   ```

### 步骤 2: 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 或使用虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### 步骤 3: 配置环境变量

```bash
# 复制环境变量模板
cp config.env.example .env

# 编辑 .env 文件
# Windows: notepad .env
# macOS/Linux: nano .env
```

在 `.env` 文件中配置以下内容：

```env
# GitHub API Token（必需）
GITHUB_TOKEN=your_github_token_here

# Deepseek AI API Key（必需）
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_API_URL=https://api.deepseek.com/chat/completions

# 可选配置
GITHUB_BASE_URL=https://api.github.com
LOG_LEVEL=INFO
```

### 步骤 4: 获取 API 密钥

#### GitHub Personal Access Token

1. 访问 [GitHub Settings - Personal Access Tokens](https://github.com/settings/tokens)
2. 点击 **Generate new token (classic)**
3. 设置 Token 信息：
   - **Note**: 输入描述，如 "AI GitHub Assistant"
   - **Expiration**: 选择有效期（建议 90 天）
   - **Scopes**: 选择以下权限：
     - ✅ `public_repo` - 访问公共仓库
     - ✅ `read:user` - 读取用户信息
     - ✅ `read:org` - 读取组织信息
4. 点击 **Generate token**
5. **立即复制** token 并保存到 `.env` 文件

#### Deepseek API Key

1. 访问 [Deepseek AI Platform](https://platform.deepseek.com/)
2. 注册账户并登录
3. 前往 API 密钥页面
4. 创建新的 API 密钥
5. 复制密钥并保存到 `.env` 文件

### 步骤 5: 启动应用

选择其中一种启动方式：

#### 🤖 AI 智能助手版本（推荐）

```bash
python ai_github_assistant.py
```

启动后访问：`http://localhost:8000`

#### 🔍 简单搜索版本

```bash
python github_search_web.py
```

启动后访问：`http://localhost:8000`

### 步骤 6: 验证安装

打开浏览器访问 `http://localhost:8000`，如果看到界面正常显示，说明安装成功！

## 🛠️ 高级配置



### 自定义配置

#### 修改服务器端口

FastAPI默认运行在8000端口。如需修改，请在启动时指定：
```bash
uvicorn ai_github_assistant:app --host 0.0.0.0 --port 8080
```

#### 修改日志级别

```env
LOG_LEVEL=DEBUG  # 可选: DEBUG, INFO, WARNING, ERROR
```

#### 自定义 GitHub API 端点

```env
GITHUB_BASE_URL=https://github.yourdomain.com/api/v3  # 企业版 GitHub
```

## 🔧 开发环境设置

### 开发模式启动

```bash
# 启动开发服务器（自动重载）
python ai_github_assistant.py --reload

# 或使用 uvicorn
uvicorn ai_github_assistant:app --reload --host 0.0.0.0 --port 8000
```

### 代码格式化

```bash
# 安装开发依赖
pip install black isort flake8

# 格式化代码
black .
isort .

# 检查代码质量
flake8 .
```

### 运行测试

```bash
# 安装测试依赖
pip install pytest

# 运行测试
pytest tests/
```

## 🔄 MCP 协议集成

### 与 Claude Desktop 集成

1. 找到 Claude Desktop 配置文件：
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`

2. 添加 MCP 服务器配置：
   ```json
   {
     "mcpServers": {
       "github-assistant": {
         "command": "python",
         "args": ["C:/path/to/your/project/src/server.py"],
         "env": {
           "GITHUB_TOKEN": "your_github_token_here"
         }
       }
     }
   }
   ```

3. 重启 Claude Desktop

### 启动 MCP 服务器

```bash
# 启动独立的 MCP 服务器
python src/server.py
```

## 🐛 故障排除

### 常见问题解决

#### 1. 依赖安装失败

**错误**: `pip install` 失败

**解决方案**:
```bash
# 更新 pip
python -m pip install --upgrade pip

# 使用清华源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 或使用虚拟环境
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 2. GitHub API 认证失败

**错误**: `HTTP 401 Unauthorized`

**解决方案**:
- 检查 GitHub Token 是否正确
- 确认 Token 权限包含 `public_repo`
- 验证 Token 是否过期
- 重新生成 Token

#### 3. 端口被占用

**错误**: `Address already in use`

**解决方案**:
```bash
# 查看端口占用
netstat -ano | findstr :3000  # Windows
lsof -i :3000                 # macOS/Linux

# 终止进程或更改端口
SERVER_PORT=8080 python ai_github_assistant.py
```

#### 4. 导入模块失败

**错误**: `ModuleNotFoundError`

**解决方案**:
```bash
# 确保在项目根目录
cd ai-github-assistant

# 检查 Python 路径
python -c "import sys; print(sys.path)"

# 安装缺失的依赖
pip install -r requirements.txt
```

#### 5. Deepseek API 调用失败

**错误**: `API Key 无效`

**解决方案**:
- 检查 API Key 是否正确
- 确认账户余额充足
- 验证 API Key 权限
- 检查网络连接

### 日志调试

#### 查看日志文件

```bash
# 查看应用日志
tail -f logs/app.log

# 查看错误日志
tail -f logs/error.log
```

#### 启用调试模式

在 `.env` 文件中设置：
```env
LOG_LEVEL=DEBUG
```

### 性能优化

#### 提高响应速度

```env
# 增加并发数
WORKER_COUNT=4

# 启用缓存
CACHE_ENABLED=true
CACHE_TTL=300
```

#### 减少 API 调用

```env
# 限制搜索结果数量
DEFAULT_SEARCH_LIMIT=10

# 启用请求缓存
ENABLE_REQUEST_CACHE=true
```

## 📚 使用技巧

### 常用查询示例

1. **项目搜索**：
   - "推荐一些 Python 机器学习项目"
   - "查找 Vue.js 的热门组件库"
   - "搜索微软开源的 TypeScript 项目"

2. **用户查询**：
   - "查看 Facebook 的开源项目"
   - "搜索 Google 的 AI 相关仓库"

3. **特定项目**：
   - "获取 microsoft/vscode 的详细信息"
   - "查看 facebook/react 的统计数据"

### 快捷键

- **Ctrl + Enter**: 发送消息（在 AI 助手界面）
- **Ctrl + L**: 清空输入框
- **Ctrl + R**: 刷新页面

## 🔄 更新指南

### 更新到最新版本

```bash
# 拉取最新代码
git pull origin main

# 更新依赖
pip install -r requirements.txt --upgrade

# 重启应用
python ai_github_assistant.py
```

### 备份配置

```bash
# 备份配置文件
cp .env .env.backup
```

## 📞 获取帮助

如果遇到问题，请通过以下方式寻求帮助：

1. **查看文档**: [README.md](README.md)
2. **搜索 Issues**: [GitHub Issues](https://github.com/wink-wink-wink555/ai-github-assistant/issues)
3. **提交 Bug 报告**: [新建 Issue](https://github.com/wink-wink-wink555/ai-github-assistant/issues/new)
4. **加入社区**: [Discussion](https://github.com/wink-wink-wink555/ai-github-assistant/discussions)

## 🎉 安装完成！

恭喜您成功安装了 AI GitHub Assistant！

现在您可以：
- 🤖 与 AI 助手对话查询 GitHub 信息
- 🔍 使用简单搜索界面查找项目
- 📊 获取详细的仓库统计信息
- 👥 搜索用户和组织

开始享受智能的 GitHub 搜索体验吧！🚀 
