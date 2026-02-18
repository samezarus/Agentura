import os
from pathlib import Path

from dotenv import load_dotenv

try: 
    load_dotenv()

    # Базовые спеки проекта
    #   Каталог с данными и конфигами
    DATA_FOLDER = os.getenv("DATA_FOLDER", ".agentura")
    DATA_FOLDER = Path.home() / DATA_FOLDER
    DATA_FOLDER.mkdir(parents=True, exist_ok=True)
    #   Порт API-сервера
    API_PORT = int(os.getenv("API_PORT", 8888))
except Exception as e:
    print("Ошибка при инициализации конфига (conf.py):", e)
    exit()