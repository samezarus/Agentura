import os
import sys
from datetime import datetime
import time
from pathlib import Path
import json

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

from conf import *
from models import *
from sessions import *
from tools import *
from ai import *
from providers import *


app = FastAPI(title="AI Agent API")

# Монтируем статические файлы
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Создаём провайдер моделей
model_provider = get_model_provider()

# Создаём и регистриуем tools
tool_manager = ToolManager()
tool_manager.register(ShellTool())
tool_manager.register(FileSystemTool())
tool_manager.register(WebSearchTool())

# ==================== API ENDPOINTS ====================

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Основной endpoint для общения с агентом"""

    # Загружаем историю сессии
    history = load_session(request.session_id)

    # Timestamp для сообщения пользователя
    user_timestamp = datetime.now().isoformat()

    # Проверяем - нужно ли использовать tool
    use_tool, tool_name, params = await should_use_tool(request.prompt, tool_manager, model_provider)

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
    response = generate_response(request.prompt, history, model_provider, tool_context)
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
