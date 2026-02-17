# Personal Rest/UI AI Agent

REST/UI персональный AI-агент на Python + FastAPI с использованием Ollama и системой Tools.

## Возможности

- Общение с AI через REST API
- **Система Tools** — агент сам выбирает и использует инструменты
- Автоматическое сохранение истории диалога по сессиям
- Доступные tools:
  - **shell** — выполнение команд в консоли сервера
  - **file_system** — чтение файлов на сервере
  - **web_search** — поиск информации в интернете (заглушка)

## Установка

Создайте виртуальное окружение и установите зависимости:
```bash
python3 -m venv .venv && source .venv/bin/activate && pip install --upgrade pip
pip install -r requirements.txt
```

```bash
cp .env.example .env
# Отредактируйте .env при необходимости
```

## Запуск

### Back

```bash
source .venv/bin/activate
python main.py
```

Или через uvicorn:
```bash
source .venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 88888
```

### Front

``` url
http://localhost:8888
```

## Архитектура Tools

### Как это работает

**Двухэтапный процесс:**

1. **Этап 1 — Выбор Tool**
   - AI анализирует запрос пользователя
   - Выбирает нужную tool или решает что tool не нужна
   - Возвращает JSON: `{"use_tool": true/false, "tool_name": "...", "parameters": {...}}`

2. **Этап 2 — Выполнение и Ответ**
   - Если tool выбрана — выполняется с параметрами
   - Результат tool передаётся в AI для генерации финального ответа
   - Пользователь получает текстовый ответ с объяснением

### Структура Tool

```python
class Tool(ABC):
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
```

### Доступные Tools

| Tool | Описание | Параметры |
|------|-----------|------------|
| **shell** | Выполнение shell команд | `command` (str) |
| **file_system** | Чтение файлов | `action` (read), `path` (str) |
| **web_search** | Поиск в интернете | `query` (str), `limit` (int, опц.) |

### Добавление новой Tool

```python
class MyCustomTool(Tool):
    @property
    def name(self) -> str:
        return "my_tool"

    @property
    def description(self) -> str:
        return "Описание для AI"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "..."}
            },
            "required": ["param1"]
        }

    async def execute(self, param1: str) -> str:
        # Логика выполнения
        return "Результат выполнения"

# Регистрация в main.py
tool_manager.register(MyCustomTool())
```

## Структура проекта

```
agentura/
├── main.py              # Основное приложение FastAPI + Tools система
├── requirements.txt     # Зависимости Python
├── .env.example        # Пример переменных окружения
├── sessions/           # Автоматически создается для хранения историй
│   └── {session_id}.json  # Файлы с историями сессий
└── README.md           # Документация
```

## Как работает история

- Каждая сессия сохраняется в `sessions/{session_id}.json`
- История накапливается автоматически: user → assistant → user → assistant...
- Новые сессии начинаются с пустой историей
- Агент "помнит" весь контекст внутри одной сессии
- Пары user/assistant скрыты под капотом — вы просто отправляете промпты
