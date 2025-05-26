from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime

class KeywordBase(BaseModel):
    keyword: str

class KeywordCreate(KeywordBase):
    pass

class KeywordUpdate(KeywordBase):
    is_active: Optional[bool] = None

class KeywordInDB(KeywordBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True # updated from orm_mode=True for Pydantic v2

class RSSFeedBase(BaseModel):
    url: HttpUrl
    name: Optional[str] = None

class RSSFeedCreate(RSSFeedBase):
    pass

class RSSFeedUpdate(RSSFeedBase):
    name: Optional[str] = None
    fetch_interval_minutes: Optional[int] = None
    is_active: Optional[bool] = None

class RSSFeedInDB(RSSFeedBase):
    id: int
    name: Optional[str] = None
    last_fetched: Optional[datetime] = None
    fetch_interval_minutes: int
    is_active: bool

    class Config:
        from_attributes = True

class ResultInDB(BaseModel):
    id: int
    feed_id: int
    title: Optional[str]
    link: str
    summary: Optional[str]
    published_date: Optional[datetime]
    matched_keywords: Optional[str]
    processed_at: datetime

    class Config:
        from_attributes = True

class PaginatedResults(BaseModel):
    items: List[ResultInDB]
    total_items: int
    total_pages: int
    current_page: int
    page_size: int