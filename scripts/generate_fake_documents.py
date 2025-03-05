#!/usr/bin/env python
"""
Generate fake documents for agencies in the system.
This script creates search descriptors and documents for each agency.
"""

import sys
import os
import random
import uuid
from datetime import datetime, date, timedelta
from faker import Faker
from sqlalchemy import func

# Add the parent directory to sys.path to allow imports from the app package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.agency import Agency
from app.models.search_descriptor import AgencyTitleSearchDescriptor
from app.models.document import AgencyDocument

fake = Faker()

# Configuration
DESCRIPTORS_PER_AGENCY = 20
BATCH_SIZE = 50

# Document title templates for more realistic regulation titles
DOCUMENT_TITLE_TEMPLATES = [
    "Regulation on {topic} for {sector}",
    "Guidelines for {topic} in {sector}",
    "{sector} {topic} Standards",
    "Requirements for {topic} in {sector}",
    "{topic} Compliance Framework for {sector}",
    "{sector} {topic} Procedures",
    "Rules Governing {topic} in {sector}",
    "{topic} Management for {sector}",
    "{sector} {topic} Oversight",
    "Mandatory {topic} Provisions for {sector}"
]

# Topics for regulation documents
REGULATION_TOPICS = [
    "Safety", "Environmental Protection", "Reporting", "Licensing", 
    "Certification", "Compliance", "Quality Control", "Risk Management",
    "Disclosure", "Inspection", "Enforcement", "Monitoring", "Assessment",
    "Financial Oversight", "Operational Standards", "Technical Requirements",
    "Data Protection", "Privacy", "Security", "Accessibility", "Transparency",
    "Accountability", "Performance Evaluation", "Resource Management"
]

# Sectors for regulation documents
REGULATION_SECTORS = [
    "Public Sector", "Private Industry", "Healthcare", "Education", 
    "Transportation", "Energy", "Finance", "Agriculture", "Manufacturing",
    "Technology", "Telecommunications", "Construction", "Real Estate",
    "Retail", "Hospitality", "Food and Drug", "Aviation", "Maritime",
    "Defense", "Infrastructure", "Research", "Development", "International Trade"
]

# Types for search descriptors
DESCRIPTOR_TYPES = [
    "PART", "SUBPART", "SECTION", "APPENDIX", "CHAPTER"
]

def generate_document_id():
    """Generate a realistic document ID in the format CFR-YYYY-NNNNN."""
    year = random.randint(2000, 2023)
    number = random.randint(10000, 99999)
    return f"CFR-{year}-{number}"

def create_fake_search_descriptors(db, agency, count=DESCRIPTORS_PER_AGENCY):
    """Create fake search descriptors for a specific agency."""
    descriptors = []
    
    for i in range(count):
        # Generate dates with some randomness
        starts_on = date.today() - timedelta(days=random.randint(365, 3650))  # 1-10 years ago
        ends_on = starts_on + timedelta(days=random.randint(365, 1825))  # 1-5 years later
        
        # Generate hierarchy data
        hierarchy = {
            "title": random.randint(1, 50),
            "chapter": random.randint(1, 20),
            "part": random.randint(1, 100),
            "subpart": chr(65 + random.randint(0, 25))  # A-Z
        }
        
        # Generate headings
        headings = {
            "title": f"Title {hierarchy['title']} - {fake.bs().title()}",
            "chapter": f"Chapter {hierarchy['chapter']} - {fake.catch_phrase().title()}",
            "part": f"Part {hierarchy['part']} - {fake.catch_phrase().title()}",
            "subpart": f"Subpart {hierarchy['subpart']} - {fake.bs().title()}"
        }
        
        # Create descriptor
        descriptor = AgencyTitleSearchDescriptor(
            id=uuid.uuid4(),
            agency_id=agency.id,
            starts_on=starts_on,
            ends_on=ends_on,
            type=random.choice(DESCRIPTOR_TYPES),
            structure_index=i,
            reserved=random.random() < 0.05,  # 5% chance of being reserved
            removed=random.random() < 0.1,    # 10% chance of being removed
            hierarchy=hierarchy,
            hierarchy_headings=headings,
            headings=headings,
            full_text_excerpt=fake.paragraph(nb_sentences=3),
            score=random.uniform(0.5, 1.0),
            change_types=random.sample(["ADDED", "MODIFIED", "REMOVED", "UNCHANGED"], k=random.randint(1, 3)),
            processing_status=random.randint(0, 3)  # 0=not processed, 1=processing, 2=completed, 3=error
        )
        
        descriptors.append(descriptor)
    
    return descriptors

def create_document_from_descriptor(descriptor, agency):
    """Create a document based on a search descriptor."""
    # Generate a realistic title
    topic = random.choice(REGULATION_TOPICS)
    sector = random.choice(REGULATION_SECTORS)
    title_template = random.choice(DOCUMENT_TITLE_TEMPLATES)
    title = title_template.format(topic=topic, sector=sector)
    
    # Create dates with some randomness
    created_date = datetime.now() - timedelta(days=random.randint(30, 1825))  # 1 month to 5 years ago
    updated_date = created_date + timedelta(days=random.randint(1, 365))  # 1 day to 1 year later
    
    # Extract title from descriptor headings if available
    if descriptor.headings and "title" in descriptor.headings:
        title_prefix = descriptor.headings["title"].split(" - ")[1] if " - " in descriptor.headings["title"] else ""
        if title_prefix:
            title = f"{title_prefix}: {title}"
    
    # Create document
    document = AgencyDocument(
        id=uuid.uuid4(),
        title=title,
        document_id=generate_document_id(),
        content=fake.text(max_nb_chars=2000),  # Sample content
        agency_metadata={
            "type": random.choice(["Rule", "Regulation", "Guidance", "Advisory", "Standard"]),
            "status": random.choice(["Active", "Proposed", "Under Review", "Archived"]),
            "priority": random.choice(["High", "Medium", "Low"]),
            "category": random.choice(["Administrative", "Technical", "Procedural", "Financial", "Operational"]),
            "descriptor_type": descriptor.type,
            "hierarchy": descriptor.hierarchy
        },
        created_at=created_date,
        updated_at=updated_date,
        agency_id=agency.id
    )
    
    return document

def main():
    """Main function to generate fake documents."""
    db = SessionLocal()
    try:
        # Get all agencies
        agencies = db.query(Agency).all()
        print(f"Found {len(agencies)} agencies")
        
        if not agencies:
            print("No agencies found. Please create agencies first.")
            return
        
        total_descriptors = 0
        total_documents = 0
        
        # Process each agency
        for agency in agencies:
            print(f"Processing agency: {agency.name}")
            
            # Check if descriptors already exist for this agency
            existing_descriptor_count = db.query(func.count(AgencyTitleSearchDescriptor.id))\
                .filter(AgencyTitleSearchDescriptor.agency_id == agency.id)\
                .scalar()
            
            if existing_descriptor_count >= DESCRIPTORS_PER_AGENCY:
                print(f"  Agency {agency.name} already has {existing_descriptor_count} descriptors, skipping")
                continue
            
            # Create fake search descriptors
            descriptors = create_fake_search_descriptors(db, agency)
            
            # Add descriptors to database
            db.add_all(descriptors)
            db.commit()
            total_descriptors += len(descriptors)
            print(f"  Created {len(descriptors)} search descriptors")
            
            # Create documents from descriptors
            documents = []
            for descriptor in descriptors:
                document = create_document_from_descriptor(descriptor, agency)
                documents.append(document)
                
                # Insert in batches to avoid memory issues
                if len(documents) >= BATCH_SIZE:
                    db.add_all(documents)
                    db.commit()
                    print(f"  Inserted batch of {len(documents)} documents")
                    total_documents += len(documents)
                    documents = []
            
            # Insert any remaining documents
            if documents:
                db.add_all(documents)
                db.commit()
                print(f"  Inserted final batch of {len(documents)} documents")
                total_documents += len(documents)
            
            print(f"  Completed processing for agency: {agency.name}")
        
        print(f"Successfully created {total_descriptors} search descriptors and {total_documents} documents across {len(agencies)} agencies")
    
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting fake document generation...")
    main()
    print("Fake document generation completed!") 