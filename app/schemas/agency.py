from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union

class CFRReference(BaseModel):
    title: int
    chapter: Optional[str] = None
    subtitle: Optional[str] = None
    
    # This validator ensures we always have either chapter or subtitle
    @classmethod
    def validate_reference(cls, values):
        if not values.get('chapter') and not values.get('subtitle'):
            values['chapter'] = 'I'  # Default chapter if neither is provided
        return values
    
    model_config = {
        "extra": "allow"  # Allow extra fields that might be in the API response
    }

class AgencyResponse(BaseModel):
    name: str
    short_name: Optional[str] = None
    display_name: Optional[str] = None
    sortable_name: Optional[str] = None
    slug: str
    children: List[Dict[str, Any]] = []
    cfr_references: List[CFRReference] = []
    
    class Config:
        orm_mode = True
        extra = "allow"  # Allow extra fields that might be in the API response 