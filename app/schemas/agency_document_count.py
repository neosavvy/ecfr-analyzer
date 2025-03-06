from pydantic import BaseModel
from typing import Optional
from datetime import date
import uuid

class AgencyDocumentCountResponse(BaseModel):
    id: uuid.UUID
    agency_id: int
    query_date: date
    reference_date: date
    total_count: int
    current_page: int
    per_page: int
    is_complete: int
    
    class Config:
        orm_mode = True 