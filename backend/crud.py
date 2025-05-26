import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime
from backend.database import get_db_connection
from backend.models import KeywordCreate, KeywordUpdate, RSSFeedCreate, RSSFeedUpdate
from backend.config import settings
import logging

logger = logging.getLogger(__name__)

def create_keyword(keyword: KeywordCreate) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO keywords (keyword) VALUES (?)", (keyword.keyword.lower(),))
        conn.commit()
        keyword_id = cursor.lastrowid
        return get_keyword(keyword_id)
    except sqlite3.IntegrityError:
        logger.warning(f"Keyword '{keyword.keyword}' already exists.")
        return None # Indicate that it already exists
    except Exception as e:
        logger.error(f"Error creating keyword: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def get_keyword(keyword_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, keyword, is_active FROM keywords WHERE id = ?", (keyword_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_keywords(active_only: bool = False) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT id, keyword, is_active FROM keywords"
    params = []
    if active_only:
        query += " WHERE is_active = 1"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_keyword(keyword_id: int, keyword: KeywordUpdate) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    update_fields = []
    params = []

    if keyword.keyword is not None:
        update_fields.append("keyword = ?")
        params.append(keyword.keyword.lower())
    if keyword.is_active is not None:
        update_fields.append("is_active = ?")
        params.append(1 if keyword.is_active else 0)

    if not update_fields:
        conn.close()
        return get_keyword(keyword_id) # No fields to update

    query = f"UPDATE keywords SET {', '.join(update_fields)} WHERE id = ?"
    params.append(keyword_id)

    try:
        cursor.execute(query, tuple(params))
        conn.commit()
        return get_keyword(keyword_id)
    except Exception as e:
        logger.error(f"Error updating keyword {keyword_id}: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def delete_keyword(keyword_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM keywords WHERE id = ?", (keyword_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error deleting keyword {keyword_id}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

#  RSS Feed CRUD Operations 
def create_rss_feed(feed: RSSFeedCreate) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO rss_feeds (url, name, fetch_interval_minutes) VALUES (?, ?, ?)",
            (str(feed.url), feed.name, settings.DEFAULT_FETCH_INTERVAL_MINUTES)
        )
        conn.commit()
        feed_id = cursor.lastrowid
        return get_rss_feed(feed_id)
    except sqlite3.IntegrityError:
        logger.warning(f"RSS Feed URL '{feed.url}' already exists.")
        return None
    except Exception as e:
        logger.error(f"Error creating RSS feed: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def get_rss_feed(feed_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, url, name, last_fetched, fetch_interval_minutes, is_active FROM rss_feeds WHERE id = ?",
        (feed_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_rss_feeds(active_only: bool = False) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT id, url, name, last_fetched, fetch_interval_minutes, is_active FROM rss_feeds"
    params = []
    if active_only:
        query += " WHERE is_active = 1"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_rss_feed(feed_id: int, feed: RSSFeedUpdate) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    update_fields = []
    params = []

    if feed.url is not None:
        update_fields.append("url = ?")
        params.append(str(feed.url))
    if feed.name is not None:
        update_fields.append("name = ?")
        params.append(feed.name)
    if feed.fetch_interval_minutes is not None:
        update_fields.append("fetch_interval_minutes = ?")
        params.append(feed.fetch_interval_minutes)
    if feed.is_active is not None:
        update_fields.append("is_active = ?")
        params.append(1 if feed.is_active else 0)

    if not update_fields:
        conn.close()
        return get_rss_feed(feed_id)

    query = f"UPDATE rss_feeds SET {', '.join(update_fields)} WHERE id = ?"
    params.append(feed_id)

    try:
        cursor.execute(query, tuple(params))
        conn.commit()
        return get_rss_feed(feed_id)
    except Exception as e:
        logger.error(f"Error updating RSS feed {feed_id}: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def delete_rss_feed(feed_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Also delete associated results to maintain data integrity
        cursor.execute("DELETE FROM results WHERE feed_id = ?", (feed_id,))
        cursor.execute("DELETE FROM rss_feeds WHERE id = ?", (feed_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error deleting RSS feed {feed_id}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def update_last_fetched_time(feed_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE rss_feeds SET last_fetched = ? WHERE id = ?",
            (datetime.now().isoformat(), feed_id)
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Error updating last fetched time for feed {feed_id}: {e}")
        conn.rollback()
    finally:
        conn.close()

#  Results Operations 
def add_result(feed_id: int, title: str, link: str, summary: str, published_date: Optional[datetime], matched_keywords: List[str]) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Truncate summary if too long
        if summary and len(summary) > settings.SUMMARY_MAX_LENGTH:
            summary = summary[:settings.SUMMARY_MAX_LENGTH] + "..."

        published_date_str = published_date.isoformat() if published_date else None
        matched_keywords_str = ",".join(matched_keywords)

        cursor.execute(
            "INSERT INTO results (feed_id, title, link, summary, published_date, matched_keywords) VALUES (?, ?, ?, ?, ?, ?)",
            (feed_id, title, link, summary, published_date_str, matched_keywords_str)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # logger.warning(f"Result with link '{link}' already exists. Skipping.")
        return False
    except Exception as e:
        logger.error(f"Error adding result for link '{link}': {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_results(
    page: int = 1,
    page_size: int = 12,
    keyword_filters: Optional[List[str]] = None
) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()

    base_query = "SELECT id, feed_id, title, link, summary, published_date, matched_keywords, processed_at FROM results"
    count_query = "SELECT COUNT(*) FROM results"
    conditions = []
    params = []

    if keyword_filters:
        # Using OR for keyword filtering
        keyword_clauses = []
        for kw in keyword_filters:
            # Case-insensitive search for keywords within the comma-separated string
            keyword_clauses.append("LOWER(matched_keywords) LIKE ?")
            params.append(f"%{kw.lower()}%") 

        if keyword_clauses:
            conditions.append(f"({' OR '.join(keyword_clauses)})")

    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)
        count_query += " WHERE " + " AND ".join(conditions)

    # Get total count
    cursor.execute(count_query, params)
    total_items = cursor.fetchone()[0]

    # Add order by and limit/offset for pagination
    base_query += " ORDER BY published_date DESC, processed_at DESC LIMIT ? OFFSET ?"
    params.append(page_size)
    params.append((page - 1) * page_size)

    cursor.execute(base_query, params)
    rows = cursor.fetchall()
    conn.close()

    results = [dict(row) for row in rows]
    total_pages = (total_items + page_size - 1) // page_size

    return {
        "items": results,
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page,
        "page_size": page_size,
    }