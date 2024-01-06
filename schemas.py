from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ItemCreate(BaseModel):
    name: str
    comment: Optional[str] = None
    label_id: Optional[int] = None
    parent_item_id: Optional[int] = None
    image_lg_path: Optional[str] = None
    image_sm_path: Optional[str] = None

class ItemUpdate(BaseModel):
    name: Optional[str] = None
    comment: Optional[str] = None
    label_id: Optional[int] = None
    parent_item_id: Optional[int] = None
    image_path: Optional[str] = None

class ItemResponse(BaseModel):
    item_id: int
    name: str
    comment: Optional[str]
    label_id: Optional[int]
    parent_item_id: Optional[int]
    image_lg_path: Optional[str]
    image_sm_path: Optional[str]
    creation_date: datetime
    last_update: Optional[datetime]
    children_count: Optional[int]
    tags: Optional[list]
