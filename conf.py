import os
from pathlib import Path
import json

from dotenv import load_dotenv

try: 
    load_dotenv()

    # Каталог с данными и конфигами
    DATA_FOLDER = os.getenv("DATA_FOLDER", ".agentura")
    DATA_FOLDER = Path.home() / DATA_FOLDER
    DATA_FOLDER.mkdir(parents=True, exist_ok=True)

    # Порт API-сервера
    API_PORT = int(os.getenv("API_PORT", 8888))

    # Директория для сессий
    SESSIONS_DIR = DATA_FOLDER / "sessions"
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    #
    PROVIDER_SRC = DATA_FOLDER / "providers.json"
    with PROVIDER_SRC.open(encoding='utf-8') as f:
        PROVIDERS = json.load(f)
    
except Exception as e:
    print("Ошибка при инициализации конфига (conf.py):", e)
    exit()