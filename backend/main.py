from fastapi import FastAPI, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from typing import List, Optional
from datetime import datetime

from backend import crud, monitor
from backend.models import (
    KeywordCreate, KeywordUpdate, KeywordInDB,
    RSSFeedCreate, RSSFeedUpdate, RSSFeedInDB,
    ResultInDB, PaginatedResults
)
from backend.logging_config import setup_logging
import logging

# Set up logging early
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RSS Monitor Service",
    description="Monitors RSS feeds for keywords and stores matching results.",
    version="1.0.0"
)

# Configure CORS for frontend access
origins = [
    "http://localhost",
    "http://localhost:8000", # FastAPI's default port
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
    "http://localhost:8080", # Common for frontend dev servers
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (frontend)
app.mount("/frontend", StaticFiles(directory="frontend"), name="static")

@app.on_event("startup")
async def startup_event():
    monitor.start_monitor_on_startup()
    logger.info("FastAPI application startup completed.")

@app.on_event("shutdown")
async def shutdown_event():
    monitor.stop_monitor_on_shutdown()
    logger.info("FastAPI application shutdown completed.")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serves the main HTML page."""
    with open(os.path.join("frontend", "index.html"), "r") as f:
        return f.read()

#  Keyword Endpoints 

@app.post("/keywords/", response_model=KeywordInDB, status_code=status.HTTP_201_CREATED)
async def create_new_keyword(keyword: KeywordCreate):
    db_keyword = crud.create_keyword(keyword)
    if db_keyword is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Keyword already exists."
        )
    return db_keyword

@app.get("/keywords/", response_model=List[KeywordInDB])
async def get_all_keywords(active_only: bool = False):
    return crud.get_all_keywords(active_only=active_only)

@app.get("/keywords/{keyword_id}", response_model=KeywordInDB)
async def get_keyword_by_id(keyword_id: int):
    keyword = crud.get_keyword(keyword_id)
    if keyword is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Keyword not found")
    return keyword

@app.put("/keywords/{keyword_id}", response_model=KeywordInDB)
async def update_existing_keyword(keyword_id: int, keyword: KeywordUpdate):
    updated_keyword = crud.update_keyword(keyword_id, keyword)
    if updated_keyword is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Keyword not found or no changes made")
    return updated_keyword

@app.delete("/keywords/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_keyword(keyword_id: int):
    if not crud.delete_keyword(keyword_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Keyword not found")
    return

#  RSS Feed Endpoints 

@app.post("/rss-feeds/", response_model=RSSFeedInDB, status_code=status.HTTP_201_CREATED)
async def create_new_rss_feed(feed: RSSFeedCreate):
    db_feed = crud.create_rss_feed(feed)
    if db_feed is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="RSS Feed URL already exists."
        )
    # Re-schedule monitoring jobs after adding/updating a feed
    monitor.schedule_feed_monitoring()
    return db_feed

@app.get("/rss-feeds/", response_model=List[RSSFeedInDB])
async def get_all_rss_feeds(active_only: bool = False):
    return crud.get_all_rss_feeds(active_only=active_only)

@app.get("/rss-feeds/{feed_id}", response_model=RSSFeedInDB)
async def get_rss_feed_by_id(feed_id: int):
    feed = crud.get_rss_feed(feed_id)
    if feed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RSS Feed not found")
    return feed

@app.put("/rss-feeds/{feed_id}", response_model=RSSFeedInDB)
async def update_existing_rss_feed(feed_id: int, feed: RSSFeedUpdate):
    updated_feed = crud.update_rss_feed(feed_id, feed)
    if updated_feed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RSS Feed not found or no changes made")
    # Re-schedule monitoring jobs after adding/updating a feed
    monitor.schedule_feed_monitoring()
    return updated_feed

@app.delete("/rss-feeds/{feed_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_rss_feed(feed_id: int):
    if not crud.delete_rss_feed(feed_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RSS Feed not found")
    # Re-schedule monitoring jobs after deleting a feed
    monitor.schedule_feed_monitoring()
    return

@app.post("/rss-feeds/{feed_id}/refetch", status_code=status.HTTP_202_ACCEPTED)
async def refetch_rss_feed_manually(feed_id: int, background_tasks: BackgroundTasks):
    feed_data = crud.get_rss_feed(feed_id)
    if not feed_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RSS Feed not found")

    feed_url = feed_data['url']
    background_tasks.add_task(monitor.fetch_and_process_feed, feed_id, feed_url)
    logger.info(f"Manually triggered re-fetch for feed ID {feed_id} ({feed_url}).")
    return {"message": "Re-fetch task initiated successfully. Check logs for progress."}

#  Results Endpoints 

@app.get("/results/", response_model=PaginatedResults)
async def get_results_paginated(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    keywords: Optional[str] = Query(None, description="Comma-separated keywords to filter by (OR logic)"),
):
    keyword_filters = [k.strip() for k in keywords.split(',')] if keywords else None
    
    results = crud.get_results(
        page=page,
        page_size=page_size,
        keyword_filters=keyword_filters
    )
    # Convert datetime objects to ISO format strings for JSON serialization
    for item in results['items']:
        if item.get('published_date'):
            item['published_date'] = datetime.fromisoformat(item['published_date'])
        if item.get('processed_at'):
            item['processed_at'] = datetime.fromisoformat(item['processed_at'])

    return results