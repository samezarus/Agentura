# SESSION MANAGEMENT

from typing import List

from conf import *
from models import *


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