import feedparser
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from backend import crud, database
from backend.logging_config import setup_logging
import logging
import time

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def fetch_and_process_feed(feed_id: int, feed_url: str):
    """
    Fetches an RSS feed, parses it, and stores matching entries.
    """
    logger.info(f"Fetching RSS feed: {feed_url}")
    try:
        feed = feedparser.parse(feed_url)
        if feed.bozo:
            logger.warning(f"Error parsing feed {feed_url}: {feed.bozo_exception}")
            # Consider adding a mechanism to deactivate problematic feeds after multiple failures
            return

        active_keywords = [kw['keyword'] for kw in crud.get_all_keywords(active_only=True)]
        if not active_keywords:
            logger.info(f"No active keywords defined. Skipping processing for {feed_url}.")
            crud.update_last_fetched_time(feed_id) # Still update fetch time if successfully parsed
            return

        lower_active_keywords = [kw.lower() for kw in active_keywords]

        new_entries_count = 0
        for entry in feed.entries:
            title = entry.get('title', '')
            link = entry.get('link', '')
            summary = entry.get('summary', entry.get('description', ''))
            published_date_str = entry.get('published') or entry.get('updated')
            published_date = None
            if published_date_str:
                try:
                    if isinstance(published_date_str, datetime):
                        published_date = published_date_str
                    else:
                        # Attempt to parse common date formats
                        try:
                            published_date = datetime.strptime(published_date_str, "%a, %d %b %Y %H:%M:%S %z")
                        except ValueError:
                            try:
                                published_date = datetime.strptime(published_date_str, "%Y-%m-%dT%H:%M:%S%z")
                            except ValueError:
                                try:
                                    published_date = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                                except:
                                    logger.warning(f"Could not parse date '{published_date_str}' for entry: {link}")
                                    published_date = datetime.now() 

                except Exception as e:
                    logger.warning(f"Error parsing published date '{published_date_str}': {e}. Using current time.")
                    published_date = datetime.now()
            else:
                published_date = datetime.now() # Default to current time if no date available

            if not link:
                logger.warning(f"Skipping entry from {feed_url} due to missing link: {title}")
                continue

            # Case-insensitive, whole-word matching logic
            matched_entry_keywords = []
            content_to_check = f"{title.lower()} {summary.lower()}"

            for keyword in lower_active_keywords:
                import re
                if re.search(r'\b' + re.escape(keyword) + r'\b', content_to_check):
                    matched_entry_keywords.append(keyword)


            if matched_entry_keywords:
                if crud.add_result(feed_id, title, link, summary, published_date, matched_entry_keywords):
                    new_entries_count += 1

        crud.update_last_fetched_time(feed_id)
        logger.info(f"Finished processing feed {feed_url}. Added {new_entries_count} new entries.")

    except Exception as e:
        logger.error(f"Failed to fetch or process feed {feed_url}: {e}", exc_info=True)


def schedule_feed_monitoring():
    """
    Schedules all active RSS feeds for periodic monitoring.
    This function should be called at startup and whenever feed configurations change.
    """
    # Remove existing jobs to avoid duplicates if called multiple times
    for job in scheduler.get_jobs():
        job.remove()
    logger.info("Cleared existing scheduler jobs.")

    active_feeds = crud.get_all_rss_feeds(active_only=True)
    if not active_feeds:
        logger.info("No active RSS feeds to schedule.")
        return

    for feed in active_feeds:
        interval = feed.get('fetch_interval_minutes')
        if not interval or interval <= 0:
            interval = 5 # Fallback to default if not set or invalid

        scheduler.add_job(
            fetch_and_process_feed,
            IntervalTrigger(minutes=interval),
            args=[feed['id'], feed['url']],
            id=f"feed_{feed['id']}",
            name=f"Monitor: {feed['name'] or feed['url']}",
            replace_existing=True, # Important for re-scheduling after updates
            next_run_time=datetime.now() # Run immediately on startup/reschedule
        )
        logger.info(f"Scheduled feed '{feed['name'] or feed['url']}' (ID: {feed['id']}) to run every {interval} minutes.")
    
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started.")
    else:
        logger.info("Scheduler already running, jobs updated.")


def start_monitor_on_startup():
    """Initial call to schedule feeds when the application starts."""
    setup_logging() # Ensure logging is set up before any operations
    logger.info("Starting RSS monitor service...")
    database.create_tables()
    schedule_feed_monitoring()


def stop_monitor_on_shutdown():
    """Shuts down the scheduler cleanly."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped.")