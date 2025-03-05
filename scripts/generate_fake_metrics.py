#!/usr/bin/env python
"""
Generate fake historical metrics data for all agencies and documents in the system.
This script creates 20 years of historical data (one entry per year) for each document.
"""

import sys
import os
import random
from datetime import datetime, date, timedelta
import uuid
from faker import Faker
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func

# Add the parent directory to sys.path to allow imports from the app package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app.models.agency import Agency
from app.models.document import AgencyDocument
from app.models.metrics import AgencyRegulationDocumentHistoricalMetrics

fake = Faker()

# Configuration
START_YEAR = 2003  # 20 years ago
END_YEAR = 2023    # Current year
METRICS_DAY = 31   # Day of month for metrics (31 for end of year)
METRICS_MONTH = 12 # Month for metrics (12 for December)
BATCH_SIZE = 100   # Number of metrics to insert at once

# Ranges for random data generation
WORD_COUNT_RANGE = (1000, 50000)
PARAGRAPH_COUNT_RANGE = (20, 500)
SENTENCE_COUNT_RANGE = (100, 2000)
SECTION_COUNT_RANGE = (5, 50)
SUBPART_COUNT_RANGE = (2, 20)
COMPLEXITY_SCORE_RANGE = (0.1, 1.0)
READABILITY_SCORE_RANGE = (30, 100)  # Higher is more readable
SENTENCE_LENGTH_RANGE = (10, 40)
WORD_LENGTH_RANGE = (4, 8)
AUTHOR_COUNT_RANGE = (1, 20)
REVISION_AUTHOR_RANGE = (1, 5)
SIMPLICITY_SCORE_RANGE = (0.1, 1.0)

def generate_trending_value(base_value, year_index, trend_factor=0.02, volatility=0.1):
    """Generate a value that follows a trend over time with some volatility."""
    # Apply trend (documents tend to get more complex over time)
    trend = base_value * (1 + trend_factor * year_index)
    # Add random volatility
    volatility_factor = random.uniform(-volatility, volatility)
    return trend * (1 + volatility_factor)

def create_metrics_for_document(db: Session, document, years):
    """Create historical metrics for a single document across multiple years."""
    metrics_list = []
    
    # Base values for this document
    base_word_count = random.randint(*WORD_COUNT_RANGE)
    base_paragraph_count = random.randint(*PARAGRAPH_COUNT_RANGE)
    base_sentence_count = random.randint(*SENTENCE_COUNT_RANGE)
    base_section_count = random.randint(*SECTION_COUNT_RANGE)
    base_subpart_count = random.randint(*SUBPART_COUNT_RANGE)
    base_complexity = random.uniform(*COMPLEXITY_SCORE_RANGE)
    base_readability = random.uniform(*READABILITY_SCORE_RANGE)
    base_sentence_length = random.uniform(*SENTENCE_LENGTH_RANGE)
    base_word_length = random.uniform(*WORD_LENGTH_RANGE)
    base_simplicity = random.uniform(*SIMPLICITY_SCORE_RANGE)
    
    # Generate metrics for each year
    for i, year in enumerate(years):
        # Create a date for the metrics (end of year)
        metrics_date = date(year, METRICS_MONTH, METRICS_DAY)
        
        # Generate trending values (documents tend to get longer and more complex over time)
        word_count = int(generate_trending_value(base_word_count, i, 0.03, 0.1))
        paragraph_count = int(generate_trending_value(base_paragraph_count, i, 0.02, 0.08))
        sentence_count = int(generate_trending_value(base_sentence_count, i, 0.025, 0.09))
        section_count = int(generate_trending_value(base_section_count, i, 0.01, 0.05))
        subpart_count = int(generate_trending_value(base_subpart_count, i, 0.005, 0.03))
        
        # Complexity tends to increase, readability tends to decrease
        complexity_score = min(1.0, generate_trending_value(base_complexity, i, 0.02, 0.07))
        readability_score = max(30, base_readability * (1 - 0.01 * i) * (1 + random.uniform(-0.05, 0.05)))
        
        # Other metrics
        avg_sentence_length = generate_trending_value(base_sentence_length, i, 0.01, 0.06)
        avg_word_length = generate_trending_value(base_word_length, i, 0.005, 0.03)
        
        # Fix for the total_authors calculation to ensure it's at least 1
        total_authors = max(1, min(50, int(base_word_count / 5000) + i))  # More authors over time, at least 1
        
        # Fix for the revision_authors calculation to avoid random.randint with equal arguments
        if total_authors <= 1:
            revision_authors = 1
        else:
            # Ensure we have a valid range for randint
            max_revision = min(5, total_authors)
            if max_revision == 1:
                revision_authors = 1
            else:
                revision_authors = random.randint(1, max_revision)
        
        # Simplicity score (inverse of complexity)
        simplicity_score = max(0.1, min(1.0, base_simplicity * (1 - 0.015 * i) * (1 + random.uniform(-0.05, 0.05))))
        
        # Create a metrics object
        metrics = AgencyRegulationDocumentHistoricalMetrics(
            id=uuid.uuid4(),
            metrics_date=metrics_date,
            word_count=word_count,
            paragraph_count=paragraph_count,
            sentence_count=sentence_count,
            section_count=section_count,
            subpart_count=subpart_count,
            language_complexity_score=complexity_score,
            readability_score=readability_score,
            average_sentence_length=avg_sentence_length,
            average_word_length=avg_word_length,
            total_authors=total_authors,
            revision_authors=revision_authors,
            simplicity_score=simplicity_score,
            content_snapshot=fake.text(max_nb_chars=500),  # Just a sample, not the full content
            agency_id=document.agency_id,
            document_id=document.id
        )
        
        metrics_list.append(metrics)
    
    return metrics_list

def main():
    """Main function to generate fake metrics data."""
    db = SessionLocal()
    try:
        # Get all agencies
        agencies = db.query(Agency).all()
        print(f"Found {len(agencies)} agencies")
        
        # Years to generate data for
        years = list(range(START_YEAR, END_YEAR + 1))
        
        # Process each agency
        for agency in agencies:
            print(f"Processing agency: {agency.name}")
            
            # Get all documents for this agency
            documents = db.query(AgencyDocument).filter(AgencyDocument.agency_id == agency.id).all()
            print(f"  Found {len(documents)} documents")
            
            if not documents:
                print(f"  No documents found for agency {agency.name}, skipping")
                continue
            
            # Check if metrics already exist for this agency
            existing_metrics_count = db.query(func.count(AgencyRegulationDocumentHistoricalMetrics.id))\
                .filter(AgencyRegulationDocumentHistoricalMetrics.agency_id == agency.id)\
                .scalar()
            
            if existing_metrics_count > 0:
                print(f"  Agency {agency.name} already has {existing_metrics_count} metrics, skipping")
                continue
            
            # Process documents in batches
            all_metrics = []
            for i, document in enumerate(documents):
                try:
                    metrics_list = create_metrics_for_document(db, document, years)
                    all_metrics.extend(metrics_list)
                    
                    # Insert in batches to avoid memory issues
                    if len(all_metrics) >= BATCH_SIZE:
                        db.add_all(all_metrics)
                        db.commit()
                        print(f"  Inserted batch of {len(all_metrics)} metrics")
                        all_metrics = []
                    
                    # Print progress
                    if (i + 1) % 10 == 0:
                        print(f"  Processed {i + 1}/{len(documents)} documents")
                except Exception as e:
                    print(f"  Error processing document {document.id}: {e}")
                    continue
            
            # Insert any remaining metrics
            if all_metrics:
                db.add_all(all_metrics)
                db.commit()
                print(f"  Inserted final batch of {len(all_metrics)} metrics")
            
            print(f"  Completed processing for agency: {agency.name}")
    
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting fake metrics generation...")
    main()
    print("Fake metrics generation completed!") 