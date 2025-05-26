import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "rss_monitor.sqlite3")
    DEFAULT_FETCH_INTERVAL_MINUTES: int = int(os.getenv("DEFAULT_FETCH_INTERVAL_MINUTES", 5))
    LOG_FILE_PATH: str = os.getenv("LOG_FILE_PATH", "logs/app.log")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    SUMMARY_MAX_LENGTH: int = int(os.getenv("SUMMARY_MAX_LENGTH", 1000)) # Max length for summary field

settings = Settings()