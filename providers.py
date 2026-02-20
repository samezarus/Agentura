# PROVIDERS

from abc import ABC, abstractmethod
from typing import List, Dict

import ollama
from openai import OpenAI

from conf import *

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

    def __init__(self, base_url: str, model: str, headers: dict = {}):
        if headers:
            self._client = ollama.Client(
                host=base_url, 
                headers=headers
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
    
    _default_provider_name = PROVIDERS["default"]
    _default_provider      = PROVIDERS["items"][_default_provider_name]
    _engine                = _default_provider["engine"]

    _base_url      = _default_provider["base_url"]
    _default_model = _default_provider["default_model"]

    if _engine == "openai":
        _api_key = _default_provider["api_key"]
        if not _api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI provider")
        
        return OpenAICompatibleProvider(
            api_key=_api_key,
            model=_default_model,
            base_url=_base_url
        )
    else:  # ollama по умолчанию
        _ollama_provider = OllamaProvider(
            base_url=_base_url,
            model=_default_model,
            headers=_default_provider["headers"]
        )

        return _ollama_provider