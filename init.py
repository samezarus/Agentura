from pathlib import Path
import json

from conf import *


def _init_providers():
    """ Инициализация дефолтных AI-поставщиков """
    _providers = {
        "default": "ollama",
        "items": dict()
    }
    
    _providers["items"]["ollama"] = {
        "active": True,
        "engine": "ollama",
        "base_url": "http://localhost:11434",
        "model": "gpt-oss:120b",
        "headers": dict()
    }

    _providers["items"]["ollama_nginx"] = {
        "active": False,
        "engine": "ollama",
        "base_url": "https://my-ollama.com",
        "model": "gpt-oss:120b",
        "headers": {"Authorization": "Bearer <key_in_nginx_rule>"}
    }

    _providers["items"]["z.ai"] = {
        "active": True,
        "engine": "openai",
        "base_url": "https://api.z.ai/api/coding/paas/v4",
        "model": "glm-5",
        "api_key": "..."
    }

    return _providers


def _init():
    """ Инициализация проекта """

    try:        
        # Инициализация дефолтных AI-поставщиков
        with open(DATA_FOLDER / "providers.json", "w", encoding="utf-8") as file:
            json.dump(_init_providers(), file, indent=4, ensure_ascii=False)

    except Exception as e: 
        print("Ошибка инициализации (agentura.py init)", e)
        raise


if __name__ == "__main__":
    _init()