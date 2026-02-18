from typing import List, Optional, Dict, Any
import os
import sys
from datetime import datetime
import time
from pathlib import Path
import subprocess
import json
from abc import ABC, abstractmethod

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, Field, field_validator
import ollama
from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()

app = FastAPI(title="AI Agent API")

# Монтируем статические файлы
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Настройки
DATA_FOLDER = os.getenv("DATA_FOLDER", "~/.agentura")
API_PORT = os.getenv("API_PORT", 8888)

MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "ollama").lower()
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
SESSIONS_DIR = Path("sessions")

# Создаём директорию для сессий если нет
SESSIONS_DIR.mkdir(exist_ok=True)


# ==================== MODEL PROVIDERS ====================

class ModelProvider(ABC):
    """Абстрактный класс для провайдеров моделей"""

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Отправить сообщение модели и получить ответ"""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Название используемой модели"""
        pass


class OllamaProvider(ModelProvider):
    """Провайдер для Ollama"""

    def __init__(self, api_key: str, base_url: str, model: str):
        if api_key:
            self._client = ollama.Client(
                host=base_url, 
                headers={"Authorization": f"Bearer {api_key}"}
            )
        else: 
            self._client = ollama.Client(host=base_url)
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        response = self._client.chat(
            model=self._model,
            messages=messages,
            **kwargs
        )
        return response['message']['content']


class OpenAICompatibleProvider(ModelProvider):
    """Провайдер для OpenAI-совместимых API (OpenAI, Azure, vLLM, LM Studio и т.д.)"""

    def __init__(self, api_key: str, model: str, base_url: str, headers: dict = None):
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            default_headers=headers
        )
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            **kwargs
        )
        return response.choices[0].message.content


def get_model_provider() -> ModelProvider:
    """Фабрика для создания провайдера на основе конфигурации"""
    if MODEL_PROVIDER == "openai":
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required for OpenAI provider")
        return OpenAICompatibleProvider(
            api_key=OPENAI_API_KEY,
            model=OPENAI_MODEL,
            base_url=OPENAI_BASE_URL
        )
    else:  # ollama по умолчанию
        return OllamaProvider(
            api_key=OLLAMA_API_KEY,
            base_url=OLLAMA_BASE_URL,
            model=OLLAMA_MODEL,
        )


# Создаём провайдер моделей
model_provider = get_model_provider()


# ==================== TOOLS SYSTEM ====================

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


# Создаём и регистриуем tools
tool_manager = ToolManager()
tool_manager.register(ShellTool())
tool_manager.register(FileSystemTool())
tool_manager.register(WebSearchTool())


# ==================== MODELS & HANDLERS ====================

class HistoryItem(BaseModel):
    from_: str = Field(alias="from")
    message: str
    timestamp: Optional[str] = None
    model: Optional[str] = None

    model_config = {"populate_by_name": True}


class ChatRequest(BaseModel):
    session_id: str
    prompt: str


class ChatResponse(BaseModel):
    response: str
    tool_used: Optional[str] = None
    tool_result: Optional[str] = None
    response_time: Optional[float] = None  # Время генерации в секундах


class ToolDetectionRequest(BaseModel):
    prompt: str


class ToolDetectionResponse(BaseModel):
    use_tool: bool
    tool_name: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


# ==================== SESSION MANAGEMENT ====================

def load_session(session_id: str) -> List[HistoryItem]:
    """Загружает историю сессии из файла"""
    session_file = SESSIONS_DIR / f"{session_id}.json"
    if session_file.exists():
        with open(session_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Поддержка старого формата: from_ -> from
            for item in data:
                if "from_" in item and "from" not in item:
                    item["from"] = item.pop("from_")
            return [HistoryItem(**item) for item in data]
    return []


def save_session(session_id: str, history: List[HistoryItem]):
    """Сохраняет историю сессии в файл"""
    session_file = SESSIONS_DIR / f"{session_id}.json"
    with open(session_file, 'w', encoding='utf-8') as f:
        json.dump([item.model_dump(by_alias=True) for item in history], f, ensure_ascii=False, indent=2)


# ==================== AI FUNCTIONS ====================

async def should_use_tool(prompt: str) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """AI решает - нужно ли использовать tool и какую"""

    tools_description = tool_manager.get_tools_for_prompt()

    system_prompt = f"""You are a tool selection system. Decide if the user's request requires using a tool.

AVAILABLE TOOLS:
{tools_description}

RULES:
- Use "shell" for commands like: ls, pwd, cat, grep, find, mkdir, etc.
- Use "file_system" for reading files: "read file X", "show me X", "what's in X"
- Use "web_search" for searching internet: "search for X", "find info about X"
- DO NOT use tools for: greetings, general questions, math, explanations, chat

RESPOND WITH ONLY THIS JSON (no other text):
{{"use_tool": true, "tool_name": "shell", "parameters": {{"command": "ls -la"}}}}
or
{{"use_tool": false, "tool_name": null, "parameters": null}}

EXAMPLES:
User: "show me main.py"
{{"use_tool": true, "tool_name": "file_system", "parameters": {{"action": "read", "path": "main.py"}}}}

User: "run ls"
{{"use_tool": true, "tool_name": "shell", "parameters": {{"command": "ls"}}}}

User: "hello"
{{"use_tool": false, "tool_name": null, "parameters": null}}

User: "what is Python?"
{{"use_tool": false, "tool_name": null, "parameters": null}}"""

    try:
        raw_content = model_provider.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        ).strip()
        print(f"[DEBUG] Raw tool response: {raw_content[:500]}")

        # Пытаемся извлечь JSON из ответа
        import re
        json_match = re.search(r'\{[\s\S]*\}', raw_content)
        if json_match:
            result = json.loads(json_match.group())
        else:
            print(f"[DEBUG] No JSON found in response")
            result = {}

        return result.get('use_tool', False), result.get('tool_name'), result.get('parameters')
    except Exception as e:
        print(f"Error detecting tool: {e}")
        return False, None, None


def generate_response(prompt: str, history: List[HistoryItem],
                      tool_context: Optional[str] = None) -> str:
    """Генерирует ответ с помощью AI"""

    messages = []

    # Системный промпт
    system_prompt = "You are a helpful AI assistant with access to various tools."
    if tool_context:
        system_prompt += f"\n\n{tool_context}\n\nExplain the tool result to the user in a helpful way."

    messages.append({"role": "system", "content": system_prompt})

    # История диалога
    for item in history:
        role = "user" if item.from_ == "user" else "assistant"
        messages.append({"role": role, "content": item.message})

    # Текущий промпт
    messages.append({"role": "user", "content": prompt})

    try:
        print(f"[DEBUG] Sending to model with context: {tool_context[:200] if tool_context else 'None'}...")
        result = model_provider.chat(messages=messages)
        print(f"[DEBUG] Model response: {result[:200] if result else 'EMPTY'}...")

        # Fallback: если модель вернула пустой ответ, но есть результат tool
        if not result or not result.strip():
            if tool_context:
                return tool_context
            return "No response generated"

        # Если модель ответила, добавляем результат tool
        if tool_context:
            return f"{result}\n\n---\n{tool_context}"

        return result
    except Exception as e:
        print(f"[DEBUG] Error: {e}")
        # Fallback при ошибке - возвращаем результат tool если есть
        if tool_context:
            return tool_context
        return f"Error generating response: {str(e)}"


# ==================== API ENDPOINTS ====================

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Основной endpoint для общения с агентом"""

    # Загружаем историю сессии
    history = load_session(request.session_id)

    # Timestamp для сообщения пользователя
    user_timestamp = datetime.now().isoformat()

    # Проверяем - нужно ли использовать tool
    use_tool, tool_name, params = await should_use_tool(request.prompt)

    tool_result = None

    if use_tool and tool_name:
        # Выполняем tool
        tool_result = await tool_manager.call(tool_name, **(params or {}))

    # Генерируем финальный ответ и замеряем время
    tool_context = None
    if use_tool and tool_result:
        # Красивое форматирование для разных типов tools
        tool_icons = {
            "shell": "💻",
            "file_system": "📄",
            "web_search": "🔍"
        }
        icon = tool_icons.get(tool_name, "🔧")
        tool_context = f"{icon} **{tool_name}**\n\n```\n{tool_result}\n```"

    # Замеряем время генерации ответа
    start_time = time.time()
    response = generate_response(request.prompt, history, tool_context)
    response_time = time.time() - start_time

    # Timestamp для ответа ассистента
    assistant_timestamp = datetime.now().isoformat()

    # Сохраняем историю с timestamp и model
    history.append(HistoryItem(
        from_="user",
        message=request.prompt,
        timestamp=user_timestamp,
        model=None
    ))
    history.append(HistoryItem(
        from_="assistant",
        message=response,
        timestamp=assistant_timestamp,
        model=model_provider.model_name
    ))
    save_session(request.session_id, history)

    return ChatResponse(
        response=response,
        tool_used=tool_name if use_tool else None,
        tool_result=tool_result,
        response_time=response_time
    )


@app.get("/tools")
async def list_tools():
    """Показать все доступные tools"""
    tools_info = []
    for tool in tool_manager.get_tools():
        tools_info.append({
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters
        })
    return {"tools": tools_info}


@app.delete("/sessions/{session_id}")
async def clear_session(session_id: str):
    """Удалить историю конкретной сессии"""
    session_file = SESSIONS_DIR / f"{session_id}.json"
    if session_file.exists():
        session_file.unlink()
        return {"message": f"Session '{session_id}' cleared"}
    return {"message": f"Session '{session_id}' not found"}


@app.delete("/sessions")
async def clear_all_sessions():
    """Удалить истории всех сессий"""
    deleted = 0
    for session_file in SESSIONS_DIR.glob("*.json"):
        session_file.unlink()
        deleted += 1
    return {"message": f"Cleared {deleted} session(s)"}


@app.get("/api/sessions")
async def list_sessions():
    """Получить список всех сессий"""
    sessions = []
    for session_file in SESSIONS_DIR.glob("*.json"):
        session_id = session_file.stem
        with open(session_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Возьмём первое сообщение как заголовок
            first_msg = data[0].get('message', 'Empty')[:30] if data else 'Empty'
            sessions.append({
                "id": session_id,
                "title": first_msg
            })
    return {"sessions": sessions}


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Получить историю конкретной сессии"""
    history = load_session(session_id)
    return {
        "id": session_id,
        "messages": [msg.model_dump() for msg in history]
    }


@app.delete("/api/sessions/{session_id}/messages/{message_index}")
async def delete_message_pair(session_id: str, message_index: int):
    """Удалить пару сообщений (пользователь + AI) по индексу"""
    history = load_session(session_id)

    if message_index < 0 or message_index >= len(history):
        raise HTTPException(status_code=400, detail="Invalid message index")

    # Удаляем сообщение пользователя
    history.pop(message_index)

    # Если есть ответ AI - удаляем и его
    if message_index < len(history) and history[message_index].from_ == "assistant":
        history.pop(message_index)

    save_session(session_id, history)
    return {"message": "Deleted", "remaining": len(history)}


@app.get("/")
async def root():
    """Отдаём web-chat"""
    html_path = Path(__file__).parent / "static" / "index.html"
    if html_path.exists():
        with open(html_path, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    return {
        "message": "AI Agent API is running",
        "provider": MODEL_PROVIDER,
        "model": model_provider.model_name
    }


@app.get("/api/config")
async def get_config():
    """Получить текущую конфигурацию"""
    return {
        "provider": MODEL_PROVIDER,
        "model": model_provider.model_name
    }


if __name__ == "__main__":
    args = sys.argv[1:]  # все переданные параметры кроме имени скрипта

    if "init" in args:
        from init import _init
        _init()

    if "run" in args:
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=API_PORT)
