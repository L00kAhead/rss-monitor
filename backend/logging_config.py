import logging
from backend.config import settings

def setup_logging():
    log_level = settings.LOG_LEVEL.upper()
    numeric_level = getattr(logging, log_level, logging.INFO)

    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(settings.LOG_FILE_PATH),
            logging.StreamHandler() # Also log to console
        ]
    )
    # Silence overly chatty loggers if necessary
    logging.getLogger('apscheduler').setLevel(logging.WARNING)
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('fastapi').setLevel(logging.WARNING)
    logging.getLogger('feedparser').setLevel(logging.WARNING)