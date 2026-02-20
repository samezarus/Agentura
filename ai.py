# AI FUNCTIONS

from typing import List, Optional, Dict, Any
import json

from models import *
from tools import *
from providers import *


async def should_use_tool(
        prompt: str, 
        tool_manager: ToolManager, 
        model_provider: ModelProvider
    ) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
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


def generate_response(
        prompt: str, 
        history: List[HistoryItem],
        model_provider: ModelProvider,
        tool_context: Optional[str] = None
    ) -> str:
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