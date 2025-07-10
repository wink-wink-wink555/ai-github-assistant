"""
GitHub Search MCP Server
基于Model Context Protocol的GitHub仓库搜索服务器
"""

import asyncio
import json
import sys
import os
from typing import Any, Dict, List, Optional

# 添加父目录到Python路径，以便导入src模块
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from mcp.server import Server
from mcp.types import Resource, Tool, TextContent

from src.config import config
from src.utils.logger import app_logger
from src.github_client import GitHubClient

class GitHubSearchMCPServer:
    """GitHub搜索MCP服务器类"""
    
    def __init__(self):
        self.server = Server(config.MCP_SERVER_NAME)
        self.github_client = GitHubClient()
        app_logger.info("Initializing GitHub Search MCP Server")
        self._setup_handlers()
        
    def _setup_handlers(self):
        """设置MCP处理器"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """列出所有可用的工具"""
            return [
                Tool(
                    name="search_repositories",
                    description="Search GitHub repositories by keywords, language, and other filters",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search keywords for repositories"
                            },
                            "language": {
                                "type": "string",
                                "description": "Programming language filter (optional)"
                            },
                            "sort": {
                                "type": "string",
                                "enum": ["stars", "forks", "updated"],
                                "description": "Sort criteria (optional)",
                                "default": "stars"
                            },
                            "per_page": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 30,
                                "description": "Number of results (optional)",
                                "default": 10
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="get_repository_info",
                    description="Get detailed information about a specific GitHub repository",
                    inputSchema={
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
                ),
                Tool(
                    name="search_users",
                    description="Search GitHub users and organizations",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search keywords for users"
                            },
                            "type": {
                                "type": "string",
                                "enum": ["user", "org"],
                                "description": "Account type filter (optional)"
                            }
                        },
                        "required": ["query"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """调用工具"""
            app_logger.info(f"Tool called: {name} with arguments: {arguments}")
            
            try:
                if name == "search_repositories":
                    return await self._search_repositories(**arguments)
                elif name == "get_repository_info":
                    return await self._get_repository_info(**arguments)
                elif name == "search_users":
                    return await self._search_users(**arguments)
                else:
                    return [TextContent(
                        type="text",
                        text=f"Unknown tool: {name}"
                    )]
            except Exception as e:
                app_logger.error(f"Error calling tool {name}: {str(e)}")
                return [TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]
    
    async def _search_repositories(self, query: str, language: Optional[str] = None, 
                                 sort: str = "stars", per_page: int = 10) -> List[TextContent]:
        """搜索GitHub仓库"""
        try:
            repositories = await self.github_client.search_repositories(
                query=query, language=language, sort=sort, per_page=per_page
            )
            
            if not repositories:
                return [TextContent(
                    type="text",
                    text=f"No repositories found for query: {query}"
                )]
            
            # 格式化结果
            formatted_results = self._format_repository_results(repositories)
            
            return [TextContent(
                type="text",
                text=formatted_results
            )]
            
        except Exception as e:
            app_logger.error(f"Error searching repositories: {str(e)}")
            return [TextContent(
                type="text",
                text=f"Error searching repositories: {str(e)}"
            )]
    
    async def _get_repository_info(self, owner: str, repo: str) -> List[TextContent]:
        """获取仓库详细信息"""
        try:
            repo_info = await self.github_client.get_repository_info(owner, repo)
            formatted_info = self._format_repository_info(repo_info)
            
            return [TextContent(
                type="text",
                text=formatted_info
            )]
            
        except Exception as e:
            app_logger.error(f"Error getting repository info: {str(e)}")
            return [TextContent(
                type="text",
                text=f"Error getting repository info: {str(e)}"
            )]
    
    async def _search_users(self, query: str, type: Optional[str] = None) -> List[TextContent]:
        """搜索用户"""
        try:
            users = await self.github_client.search_users(query=query, type=type)
            
            if not users:
                return [TextContent(
                    type="text",
                    text=f"No users found for query: {query}"
                )]
            
            formatted_users = self._format_user_results(users)
            
            return [TextContent(
                type="text",
                text=formatted_users
            )]
            
        except Exception as e:
            app_logger.error(f"Error searching users: {str(e)}")
            return [TextContent(
                type="text",
                text=f"Error searching users: {str(e)}"
            )]
    
    def _format_repository_results(self, repositories: List[Dict]) -> str:
        """格式化仓库搜索结果"""
        results = []
        results.append(f"🔍 Found {len(repositories)} repositories:\n")
        
        for i, repo in enumerate(repositories, 1):
            stars = repo.get('stargazers_count', 0)
            forks = repo.get('forks_count', 0)
            language = repo.get('language', 'Unknown')
            description = repo.get('description', 'No description')
            
            results.append(
                f"{i}. **{repo['full_name']}** ⭐ {stars:,}\n"
                f"   📝 {description}\n"
                f"   💻 {language} | 🍴 {forks:,} forks\n"
                f"   🔗 {repo.get('html_url', '')}\n"
            )
        
        return "\n".join(results)
    
    def _format_repository_info(self, repo: Dict) -> str:
        """格式化仓库详细信息"""
        return f"""📦 **{repo['full_name']}**

📝 **Description:** {repo.get('description', 'No description')}
⭐ **Stars:** {repo.get('stargazers_count', 0):,}
🍴 **Forks:** {repo.get('forks_count', 0):,}
👀 **Watchers:** {repo.get('watchers_count', 0):,}
🐛 **Issues:** {repo.get('open_issues_count', 0):,}
💻 **Language:** {repo.get('language', 'Unknown')}
📦 **Size:** {repo.get('size', 0):,} KB
📅 **Created:** {repo.get('created_at', 'Unknown')[:10]}
📅 **Updated:** {repo.get('updated_at', 'Unknown')[:10]}
🔗 **URL:** {repo.get('html_url', '')}

📄 **License:** {repo.get('license', {}).get('name', 'No license') if repo.get('license') else 'No license'}
🏠 **Homepage:** {repo.get('homepage', 'No homepage')}"""
    
    def _format_user_results(self, users: List[Dict]) -> str:
        """格式化用户搜索结果"""
        results = []
        results.append(f"👥 Found {len(users)} users:\n")
        
        for i, user in enumerate(users, 1):
            user_type = "🏢 Organization" if user.get('type') == 'Organization' else "👤 User"
            results.append(
                f"{i}. **{user['login']}** ({user_type})\n"
                f"   🔗 {user.get('html_url', '')}\n"
            )
        
        return "\n".join(results)
    
    async def run(self):
        """运行服务器"""
        app_logger.info("Starting GitHub Search MCP Server")
        
        try:
            from mcp.server.stdio import stdio_server
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream, 
                    write_stream,
                    initialization_options={}
                )
        except Exception as e:
            app_logger.error(f"Server run error: {e}")
            raise

async def main():
    """主函数"""
    server = GitHubSearchMCPServer()
    await server.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        app_logger.info("Server stopped by user")
    except Exception as e:
        app_logger.error(f"Server error: {e}")
        import traceback
        app_logger.error(f"Traceback: {traceback.format_exc()}") 