#!/usr/bin/env python3
"""
AI GitHub Assistant - 基于Deepseek AI的智能GitHub助手
集成Deepseek AI模型，支持自然语言查询GitHub仓库
使用MCP协议实现工具调用机制
"""

import sys
import json
import re
from pathlib import Path
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import uvicorn
import aiohttp

# 添加src目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from src.github_client import GitHubClient
from src.config import config

app = FastAPI(title="AI GitHub Assistant - 智能GitHub助手")


class MCPGitHubAssistant:
    def __init__(self):
        self.github_client = GitHubClient()
        
        # MCP工具定义
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_github_repositories",
                    "description": "Search GitHub repositories using query keywords. Returns popular repositories matching the search criteria.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search keywords (in English) to find repositories, e.g. 'python web framework', 'machine learning', 'face detection'"
                            },
                            "language": {
                                "type": "string",
                                "description": "Optional programming language filter (python, javascript, java, etc.)"
                            },
                            "sort": {
                                "type": "string",
                                "enum": ["stars", "forks", "updated"],
                                "description": "Sort results by stars, forks, or last updated"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Number of results to return (1-20)",
                                "minimum": 1,
                                "maximum": 20
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_repository_info",
                    "description": "Get detailed information about a specific GitHub repository",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "owner": {
                                "type": "string",
                                "description": "Repository owner/organization name"
                            },
                            "repo": {
                                "type": "string",
                                "description": "Repository name"
                            }
                        },
                        "required": ["owner", "repo"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_github_users",
                    "description": "Search GitHub users and organizations",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Username or organization name to search"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
    
    def process_markdown(self, text):
        """在Python端处理Markdown格式"""
        result = text
        
        # 处理标题
        result = re.sub(r'^### (.+)$', r'<h3><strong>\1</strong></h3>', result, flags=re.MULTILINE)
        result = re.sub(r'^## (.+)$', r'<h2><strong>\1</strong></h2>', result, flags=re.MULTILINE)
        result = re.sub(r'^# (.+)$', r'<h1><strong>\1</strong></h1>', result, flags=re.MULTILINE)
        
        # 处理粗体链接 **[text](url)**
        result = re.sub(r'\*\*\[([^\]]+)\]\(([^)]+)\)\*\*', r'<strong><a href="\2" target="_blank">\1</a></strong>', result)
        
        # 处理普通链接 [text](url)
        result = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', result)
        
        # 处理粗体文本 **text**
        result = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', result)
        
        # 处理换行
        result = result.replace('\n', '<br>')
        
        return result

    async def call_deepseek_with_tools(self, messages):
        """调用Deepseek API，包含工具定义"""
        headers = config.get_deepseek_headers()

        data = {
            "model": "deepseek-chat",
            "messages": messages,
            "tools": self.tools,
            "tool_choice": "auto",
            "max_tokens": 2000,
            "temperature": 0.7
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(config.DEEPSEEK_API_URL, headers=headers, json=data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"Deepseek API调用失败: {response.status} - {error_text}")

    async def execute_tool_call(self, tool_call):
        """执行工具调用"""
        function_name = tool_call["function"]["name"]
        arguments = json.loads(tool_call["function"]["arguments"])

        print(f"🔧 执行工具: {function_name}")
        print(f"📝 参数: {arguments}")

        try:
            if function_name == "search_github_repositories":
                repositories = await self.github_client.search_repositories(
                    query=arguments["query"],
                    language=arguments.get("language"),
                    sort=arguments.get("sort", "stars"),
                    per_page=arguments.get("limit", 8)
                )

                return {
                    "success": True,
                    "data": {
                        "query": arguments["query"],
                        "count": len(repositories),
                        "repositories": repositories[:arguments.get("limit", 8)]
                    }
                }

            elif function_name == "get_repository_info":
                repo_info = await self.github_client.get_repository_info(
                    arguments["owner"], arguments["repo"]
                )

                return {
                    "success": True,
                    "data": repo_info
                }

            elif function_name == "search_github_users":
                users = await self.github_client.search_users(
                    query=arguments["query"]
                )

                return {
                    "success": True,
                    "data": {
                        "query": arguments["query"],
                        "count": len(users),
                        "users": users[:10]
                    }
                }

        except Exception as e:
            print(f"❌ 工具执行失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def chat(self, user_message):
        """处理聊天请求 - 标准MCP流程"""
        # 初始消息
        messages = [
            {
                "role": "system",
                "content": """你是一个GitHub搜索助手。你有以下工具可以使用：

1. search_github_repositories - 搜索GitHub仓库
2. get_repository_info - 获取仓库详细信息（需要用户名和仓库名）
3. search_github_users - 搜索用户和组织

处理用户查询的策略：
- 如果用户询问特定用户的特定项目，优先使用get_repository_info工具
- 如果用户询问某类项目的推荐，使用search_github_repositories
- 如果用户询问某个用户的信息，使用search_github_users

重要提示：
- 搜索时使用英文关键词效果更好
- 可以根据用户需求调用多个工具获得更全面的结果
- 必须先获取数据，再基于实际数据回答用户问题
- 如果没有找到结果，要明确告知用户"""
            },
            {"role": "user", "content": user_message}
        ]

        # 第一次API调用
        print(f"💬 用户消息: {user_message}")
        response = await self.call_deepseek_with_tools(messages)
        assistant_message = response["choices"][0]["message"]

        # 检查是否有工具调用
        tool_calls = assistant_message.get("tool_calls", [])
        messages.append(assistant_message)

        # 执行工具调用
        if tool_calls:
            print(f"🔧 检测到 {len(tool_calls)} 个工具调用")
            
            for tool_call in tool_calls:
                print(f"🔨 执行工具: {tool_call['function']['name']}")
                tool_result = await self.execute_tool_call(tool_call)
                print(f"✅ 工具执行完成，结果长度: {len(str(tool_result))}")
                
                # 添加工具结果到消息历史
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": json.dumps(tool_result, ensure_ascii=False)
                })

            # 再次调用API获取最终回答
            print("🤖 正在生成最终回答...")
            try:
                final_response = await self.call_deepseek_with_tools(messages)
                final_message = final_response["choices"][0]["message"]["content"]
                print(f"✅ 最终回答生成成功，长度: {len(final_message)}")
                
                if not final_message or final_message.strip() == "":
                    print("❌ 警告：最终回答为空")
                    final_message = "抱歉，我无法生成回答。请稍后重试。"

                return {
                    "message": self.process_markdown(final_message),
                    "tool_calls": tool_calls,
                    "conversation": messages
                }
            except Exception as e:
                print(f"❌ 生成最终回答时出错: {str(e)}")
                return {
                    "message": f"工具调用成功，但生成最终回答时出错: {str(e)}",
                    "tool_calls": tool_calls,
                    "conversation": messages
                }
        else:
            return {
                "message": self.process_markdown(assistant_message["content"]),
                "tool_calls": None,
                "conversation": messages
            }


# 全局助手实例
assistant = MCPGitHubAssistant()


def get_web_interface():
    """生成Web界面HTML"""
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI GitHub Assistant - 智能GitHub助手</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            * { 
                margin: 0; 
                padding: 0; 
                box-sizing: border-box; 
            }
            
            body {
                font-family: 'Segoe UI', 'Microsoft YaHei', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                line-height: 1.6;
            }
            
            .container {
                max-width: 900px;
                margin: 0 auto;
                padding: 20px;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
            }
            
            .header {
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                padding: 12px 20px;
                border-radius: 15px;
                text-align: center;
                margin-bottom: 15px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.18);
            }
            
            .header h1 {
                color: #2d3748;
                font-size: 1.5em;
                margin: 0;
                font-weight: 700;
                background: linear-gradient(135deg, #667eea, #764ba2);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            
            .chat-container {
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 20px;
                flex: 1;
                display: flex;
                flex-direction: column;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.18);
            }
            
            .messages {
                flex: 1;
                overflow-y: auto;
                overflow-x: hidden;
                padding: 15px;
                margin-bottom: 15px;
                background: rgba(248, 250, 252, 0.5);
                border-radius: 15px;
                border: 1px solid rgba(226, 232, 240, 0.5);
                height: calc(100vh - 280px);
                min-height: 400px;
                max-height: calc(100vh - 280px);
                scroll-behavior: smooth;
            }
            
            .message {
                margin-bottom: 15px;
                padding: 15px 20px;
                border-radius: 15px;
                max-width: 85%;
                word-wrap: break-word;
                position: relative;
                animation: messageSlide 0.3s ease-out;
            }
            
            @keyframes messageSlide {
                from {
                    opacity: 0;
                    transform: translateY(10px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            .user-message {
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                margin-left: auto;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
                border-bottom-right-radius: 5px;
            }
            
            .assistant-message {
                background: linear-gradient(135deg, #f8fafc, #e2e8f0);
                color: #2d3748;
                margin-right: auto;
                border-left: 4px solid #667eea;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
                border-bottom-left-radius: 5px;
            }
            
                         .tools-used {
                 background: rgba(102, 126, 234, 0.05);
                 margin-top: 10px;
                 border-radius: 10px;
                 font-size: 0.9em;
                 border: 1px solid rgba(102, 126, 234, 0.2);
                 overflow: hidden;
             }
             
             .tools-header {
                 background: rgba(102, 126, 234, 0.1);
                 padding: 10px 12px;
                 cursor: pointer;
                 display: flex;
                 align-items: center;
                 justify-content: space-between;
                 font-weight: 600;
                 color: #667eea;
                 transition: all 0.3s ease;
             }
             
             .tools-header:hover {
                 background: rgba(102, 126, 234, 0.15);
             }
             
             .tools-toggle {
                 font-size: 0.9em;
                 transition: all 0.3s ease;
                 font-weight: bold;
             }
             
             .tools-content {
                 padding: 12px;
                 display: none;
                 border-top: 1px solid rgba(102, 126, 234, 0.1);
             }
             
             .tools-content.show {
                 display: block;
             }
            
            .input-form {
                display: flex;
                gap: 12px;
                align-items: flex-end;
                background: linear-gradient(135deg, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9));
                padding: 15px;
                border-radius: 15px;
                border: 1px solid rgba(102, 126, 234, 0.2);
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
                backdrop-filter: blur(10px);
            }
            
            .message-input {
                flex: 1;
                padding: 12px 16px;
                border: 2px solid transparent;
                border-radius: 12px;
                background: white;
                font-size: 0.95em;
                resize: none;
                min-height: 44px;
                max-height: 120px;
                transition: all 0.3s ease;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                font-family: inherit;
                line-height: 1.4;
            }
            
            .message-input:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.15), 0 4px 15px rgba(0, 0, 0, 0.15);
                transform: translateY(-1px);
            }
            
            .message-input::placeholder {
                color: #9ca3af;
                font-style: italic;
            }
            
            .send-button {
                width: 44px;
                height: 44px;
                background: linear-gradient(135deg, #667eea, #764ba2);
                border: none;
                border-radius: 50%;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
                display: flex;
                align-items: center;
                justify-content: center;
                flex-shrink: 0;
                position: relative;
            }
            
            .send-button i {
                color: white;
                font-size: 16px;
            }
            
            .send-button:hover:not(:disabled) {
                transform: translateY(-2px);
                box-shadow: 0 6px 25px rgba(102, 126, 234, 0.4);
                background: linear-gradient(135deg, #5a67d8, #6b46c1);
            }
            
            .send-button:active:not(:disabled) {
                transform: translateY(0px);
                box-shadow: 0 2px 10px rgba(102, 126, 234, 0.3);
            }
            
            .send-button:disabled {
                opacity: 0.5;
                cursor: not-allowed;
                transform: none;
                box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
                background: linear-gradient(135deg, #9ca3af, #6b7280);
            }
            
                         /* 增强的加载状态样式 */
             .loading {
                 display: none;
                 text-align: center;
                 padding: 25px;
                 margin: 15px 0;
                 background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
                 border-radius: 15px;
                 border: 1px solid rgba(102, 126, 234, 0.2);
             }
             
             .loading.show { 
                 display: block; 
             }
             
             .loading-content {
                 display: flex;
                 flex-direction: column;
                 align-items: center;
                 gap: 15px;
             }
             
             .loading-text {
                 color: #667eea;
                 font-weight: 600;
                 font-size: 1.2em;
                 display: flex;
                 align-items: center;
                 gap: 12px;
             }
             

             
             /* 转圈圈加载图标 */
             .loading-spinner {
                 width: 24px;
                 height: 24px;
                 border: 3px solid rgba(102, 126, 234, 0.2);
                 border-top: 3px solid #667eea;
                 border-radius: 50%;
                 animation: spin 1s linear infinite;
             }
             
             @keyframes spin {
                 from { transform: rotate(0deg); }
                 to { transform: rotate(360deg); }
             }
            
            .example-questions {
                background: linear-gradient(135deg, rgba(248, 250, 252, 0.8), rgba(241, 245, 249, 0.8));
                border-radius: 15px;
                padding: 20px;
                margin-bottom: 15px;
                border: 1px solid rgba(226, 232, 240, 0.5);
                backdrop-filter: blur(5px);
            }
            
            .welcome-message {
                color: #4a5568;
                margin-bottom: 15px;
                font-size: 1em;
                line-height: 1.5;
                text-align: center;
                padding: 15px;
                background: rgba(255, 255, 255, 0.6);
                border-radius: 12px;
                border-left: 4px solid #667eea;
            }
            
            .example-questions h3 {
                color: #2d3748;
                margin-bottom: 15px;
                font-size: 1em;
                text-align: center;
                font-weight: 600;
            }
            
            .examples-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 12px;
            }
            
            .example-item {
                background: linear-gradient(135deg, rgba(255, 255, 255, 0.9), rgba(248, 250, 252, 0.9));
                border-radius: 10px;
                padding: 12px 16px;
                cursor: pointer;
                transition: all 0.3s ease;
                border-left: 3px solid #667eea;
                font-size: 0.9em;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
                border: 1px solid rgba(226, 232, 240, 0.3);
                text-align: center;
            }
            
            .example-item:hover {
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                transform: translateY(-2px) scale(1.02);
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            }
            
            .assistant-message h1 {
                font-size: 1.4em;
                color: #2d3748;
                margin: 15px 0 10px 0;
                font-weight: 700;
            }
            
            .assistant-message h2 {
                font-size: 1.2em;
                color: #2d3748;
                margin: 12px 0 8px 0;
                font-weight: 600;
            }
            
            .assistant-message h3 {
                font-size: 1.1em;
                color: #2d3748;
                margin: 10px 0 6px 0;
                font-weight: 600;
            }
            
            /* 响应式设计 */
            @media (max-width: 768px) {
                .container {
                    padding: 10px;
                }
                
                .header h1 {
                    font-size: 1.5em;
                }
                
                .message {
                    max-width: 95%;
                    padding: 12px 15px;
                }
                
                .examples-grid {
                    grid-template-columns: 1fr;
                    gap: 8px;
                }
                
                .input-form {
                    flex-direction: column;
                    gap: 12px;
                    padding: 12px;
                }
                
                .message-input {
                    min-height: 40px;
                }
                
                .send-button {
                    width: 100%;
                    height: 44px;
                }
                
                .messages {
                    height: calc(100vh - 320px);
                }
            }
            
            /* 滚动条美化 */
            .messages::-webkit-scrollbar {
                width: 6px;
            }
            
            .messages::-webkit-scrollbar-track {
                background: rgba(226, 232, 240, 0.3);
                border-radius: 3px;
            }
            
            .messages::-webkit-scrollbar-thumb {
                background: linear-gradient(135deg, #667eea, #764ba2);
                border-radius: 3px;
            }
            
            .messages::-webkit-scrollbar-thumb:hover {
                background: linear-gradient(135deg, #5a67d8, #6b46c1);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 AI GitHub Assistant</h1>
            </div>
            
            <div class="chat-container">
                <div class="messages" id="messages">
                    <div class="example-questions">
                        <div class="welcome-message">
                            👋 欢迎使用GitHub智能助手！我可以帮你搜索仓库、查看项目详情、分析用户信息。
                        </div>
                        <h3>💡 试试这些问题：</h3>
                        <div class="examples-grid">
                            <div class="example-item" onclick="askExample('搜索人脸识别相关的Python项目')">
                                🔍 搜索人脸识别项目
                            </div>
                            <div class="example-item" onclick="askExample('找一些机器学习库')">
                                🤖 查找机器学习库
                            </div>
                            <div class="example-item" onclick="askExample('查看microsoft/vscode仓库详情')">
                                📦 查看仓库详情
                            </div>
                            <div class="example-item" onclick="askExample('推荐一些优秀的Go语言框架')">
                                🚀 Go语言框架推荐
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="loading" id="loading">
                    <div class="loading-content">
                        <div class="loading-text">
                            <div class="loading-spinner"></div>
                            <span>生成回答中...</span>
                        </div>
                    </div>
                </div>
                
                <form class="input-form" onsubmit="return submitForm(event)">
                    <textarea 
                        id="messageInput" 
                        class="message-input" 
                        placeholder="问我任何GitHub相关问题，我会使用MCP工具来帮你搜索..."
                        rows="2"
                        onkeydown="handleKeyPress(event)"
                    ></textarea>
                    <button type="submit" class="send-button" id="sendButton">
                        <i class="fas fa-paper-plane"></i>
                    </button>
                </form>
            </div>
        </div>

<script>
function askExample(text) {
    document.getElementById('messageInput').value = text;
    submitMessage();
}

function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        submitMessage();
    }
}

function submitForm(event) {
    event.preventDefault();
    submitMessage();
    return false;
}

async function submitMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    if (!message) return;

    addMessage(message, 'user');
    input.value = '';
    showLoading(true);

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: 'message=' + encodeURIComponent(message)
        });

        if (response.ok) {
            const result = await response.json();
            addMessage(result.message, 'assistant', result.tool_calls);
        } else {
            addMessage('抱歉，发生了错误，请稍后重试。', 'assistant');
        }
    } catch (error) {
        console.error('Error:', error);
        addMessage('网络连接错误，请检查网络后重试。', 'assistant');
    } finally {
        showLoading(false);
    }
}

function addMessage(content, sender, toolCalls) {
    const messages = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    
    let html = `<div>${content}</div>`;
    
    if (toolCalls && toolCalls.length > 0) {
        const toolsId = 'tools-' + Date.now();
        html += `
            <div class="tools-used">
                <div class="tools-header" onclick="toggleTools('${toolsId}')">
                    <span>🔧 使用的MCP工具 (${toolCalls.length}个)</span>
                    <span class="tools-toggle" id="toggle-${toolsId}">▼</span>
                </div>
                <div class="tools-content" id="${toolsId}">`;
        
        for (let i = 0; i < toolCalls.length; i++) {
            const tool = toolCalls[i];
            const args = JSON.parse(tool.function.arguments);
            let argStr = '';
            for (const k in args) {
                if (argStr) argStr += ', ';
                argStr += `${k}: "${args[k]}"`;
            }
            html += `<div>• <strong>${tool.function.name}</strong>(${argStr})</div>`;
        }
        
        html += `
                </div>
            </div>`;
    }
    
    messageDiv.innerHTML = html;
    messages.appendChild(messageDiv);
    messages.scrollTop = messages.scrollHeight;
}

function toggleTools(toolsId) {
    const content = document.getElementById(toolsId);
    const toggle = document.getElementById('toggle-' + toolsId);
    
    if (content.classList.contains('show')) {
        content.classList.remove('show');
        toggle.classList.remove('expanded');
        toggle.textContent = '▼';
    } else {
        content.classList.add('show');
        toggle.classList.add('expanded');
        toggle.textContent = '▲';
    }
}

function showLoading(show) {
    const loading = document.getElementById('loading');
    const sendButton = document.getElementById('sendButton');
    
    if (show) {
        loading.classList.add('show');
        sendButton.disabled = true;
    } else {
        loading.classList.remove('show');
        sendButton.disabled = false;
    }
}
</script>
    </body>
    </html>
    """
    return html_content


@app.get("/", response_class=HTMLResponse)
async def index():
    """主页面"""
    return get_web_interface()


@app.post("/chat")
async def chat(message: str = Form(...)):
    """处理聊天请求"""
    try:
        result = await assistant.chat(message)
        return {
            "success": True,
            "message": result["message"],
            "tool_calls": result["tool_calls"]
        }
    except Exception as e:
        print(f"❌ 聊天处理失败: {str(e)}")
        return {
            "success": False,
            "message": f"抱歉，处理您的请求时出现错误: {str(e)}",
            "tool_calls": None
        }


# 创建全局助手实例
assistant = MCPGitHubAssistant()

if __name__ == "__main__":
    print("🔧 启动AI GitHub Assistant...")
    print("🌐 访问地址: http://localhost:3000")
    print("🛠️  集成标准MCP工具调用协议")
    print()
    
    # 验证配置
    if not config.validate():
        print("❌ 配置验证失败，请检查环境变量设置")
        print("📋 请确保 .env 文件包含以下必要配置：")
        print("   - GITHUB_TOKEN=your_github_token")
        print("   - DEEPSEEK_API_KEY=your_deepseek_api_key")
        exit(1)
    
    print("✅ 配置验证通过")
    print("⏹️  按 Ctrl+C 停止服务")
    print()

    uvicorn.run(app, host="localhost", port=3000)