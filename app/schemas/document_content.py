from pydantic import BaseModel
from typing import Optional
from datetime import date
import uuid

class DocumentContentResponse(BaseModel):
    id: uuid.UUID
    descriptor_id: uuid.UUID
    agency_id: int
    version_date: date
    raw_xml: str
    processed_text: Optional[str] = None
    
    class Config:
        orm_mode = True 