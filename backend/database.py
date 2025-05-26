import sqlite3
from backend.config import settings
import logging
from backend.logging_config import setup_logging


logger = logging.getLogger(__name__)

DATABASE_FILE = settings.DATABASE_URL

def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row # This allows accessing columns by name
    return conn

def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rss_feeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL UNIQUE,
            name TEXT,
            last_fetched DATETIME,
            fetch_interval_minutes INTEGER DEFAULT ' + str(settings.DEFAULT_FETCH_INTERVAL_MINUTES})',
            is_active BOOLEAN DEFAULT 1
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL UNIQUE,
            is_active BOOLEAN DEFAULT 1
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feed_id INTEGER NOT NULL,
            title TEXT,
            link TEXT NOT NULL UNIQUE,
            summary TEXT,
            published_date DATETIME,
            matched_keywords TEXT,
            processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (feed_id) REFERENCES rss_feeds(id)
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("Database tables checked/created successfully.")

if __name__ == "__main__":
    setup_logging()
    create_tables()