from sqlalchemy import Column, Integer, String, JSON, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base

class Agency(Base):
    __tablename__ = "agencies"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    short_name = Column(String)
    display_name = Column(String)
    sortable_name = Column(String)
    slug = Column(String, unique=True, nullable=False)
    children = Column(JSON, default=list)
    cfr_references = Column(JSON, default=list)
    
    # Relationship with search descriptors
    search_descriptors = relationship("AgencyTitleSearchDescriptor", back_populates="agency", cascade="all, delete-orphan")
    
    # Relationship with documents (to be implemented later)
    # documents = relationship("Document", back_populates="agency")
    
    def __repr__(self):
        return f"<Agency(name='{self.name}', short_name='{self.short_name}')>"
    
    @classmethod
    def from_api_response(cls, data):
        """Create an Agency instance from API response data"""
        # Process CFR references to ensure they have either chapter or subtitle
        cfr_references = data.get("cfr_references", [])
        for ref in cfr_references:
            if not ref.get('chapter') and 'subtitle' in ref:
                # If there's no chapter but there is a subtitle, use subtitle as chapter
                ref['chapter'] = ref['subtitle']
        
        return cls(
            name=data.get("name"),
            short_name=data.get("short_name"),
            display_name=data.get("display_name"),
            sortable_name=data.get("sortable_name"),
            slug=data.get("slug"),
            children=data.get("children", []),
            cfr_references=cfr_references
        ) 