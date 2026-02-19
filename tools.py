# TOOLS SYSTEM

from abc import ABC, abstractmethod
from typing import List, Dict, Any
import subprocess
from pathlib import Path
import json


class Tool(ABC):
    """Базовый класс для всех tools"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Уникальное название tool"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Описание для AI - что делает эта tool"""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """JSON Schema параметров для AI"""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """Выполнение tool и возврат результата"""
        pass


class ShellTool(Tool):
    """Выполнение shell команд на сервере"""

    @property
    def name(self) -> str:
        return "shell"

    @property
    def description(self) -> str:
        return "Execute shell commands on the server (ls, pwd, grep, etc.)"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute"
                }
            },
            "required": ["command"]
        }

    async def execute(self, command: str) -> str:
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            output = result.stdout or result.stderr
            return output if output else "Command executed with no output"
        except subprocess.TimeoutExpired:
            return "Error: Command execution timed out"
        except Exception as e:
            return f"Error executing command: {str(e)}"


class FileSystemTool(Tool):
    """Чтение и запись файлов на сервере"""

    @property
    def name(self) -> str:
        return "file_system"

    @property
    def description(self) -> str:
        return "Read files from the server filesystem. Use for viewing code, configs, logs."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["read"],
                    "description": "Action to perform"
                },
                "path": {
                    "type": "string",
                    "description": "File path to read"
                }
            },
            "required": ["action", "path"]
        }

    async def execute(self, action: str, path: str) -> str:
        if action != "read":
            return "Error: Only 'read' action is supported"

        try:
            file_path = Path(path).resolve()
            # Защита от выхода за пределы текущей директории
            if not str(file_path).startswith(str(Path.cwd().resolve())):
                return "Error: Access denied - path outside working directory"

            if not file_path.exists():
                return f"Error: File not found: {path}"

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Ограничиваем размер
            if len(content) > 10000:
                return content[:10000] + "\n\n... (file truncated, too large)"

            return content
        except Exception as e:
            return f"Error reading file: {str(e)}"


class WebSearchTool(Tool):
    """Поиск информации в интернете (упрощённая версия)"""

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Search the web for current information, news, documentation"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of results (default: 3)",
                    "default": 3
                }
            },
            "required": ["query"]
        }

    async def execute(self, query: str, limit: int = 3) -> str:
        # Упрощённая реализация - возвращает заглушку
        # Для реальной работы нужен API (например, DuckDuckGo, Google, etc.)
        return f"Web search for '{query}' would return {limit} results. (Implement actual search API)"


class ToolManager:
    """Менеджер для управления всеми tools"""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        """Регистрация новой tool"""
        self._tools[tool.name] = tool

    def get_tools(self) -> List[Tool]:
        """Получить все зарегистрированные tools"""
        return list(self._tools.values())

    def get_tools_for_prompt(self) -> str:
        """Генерирует описание tools для AI промпта"""
        descriptions = []
        for tool in self.get_tools():
            params = json.dumps(tool.parameters, ensure_ascii=False)
            descriptions.append(f"- {tool.name}: {tool.description}\n  Parameters: {params}")
        return "\n".join(descriptions)

    async def call(self, tool_name: str, **kwargs) -> str:
        """Вызывает tool по имени с параметрами"""
        if tool_name not in self._tools:
            return f"Error: Unknown tool '{tool_name}'"
        return await self._tools[tool_name].execute(**kwargs)