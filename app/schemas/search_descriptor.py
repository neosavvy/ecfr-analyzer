from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import date
import uuid

class HierarchyData(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    chapter: Optional[str] = None
    subchapter: Optional[str] = None
    part: Optional[str] = None
    subpart: Optional[str] = None
    subject_group: Optional[str] = None
    section: Optional[str] = None
    appendix: Optional[str] = None
    
    class Config:
        extra = "allow"

class AgencyTitleSearchDescriptorResponse(BaseModel):
    id: uuid.UUID
    agency_id: int
    starts_on: Optional[date] = None
    ends_on: Optional[date] = None
    type: Optional[str] = None
    structure_index: Optional[int] = None
    reserved: bool = False
    removed: bool = False
    hierarchy: HierarchyData = {}
    hierarchy_headings: HierarchyData = {}
    headings: HierarchyData = {}
    full_text_excerpt: Optional[str] = None
    score: Optional[float] = None
    change_types: List[str] = []
    
    class Config:
        orm_mode = True
        extra = "allow" 