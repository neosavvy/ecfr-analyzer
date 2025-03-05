#!/usr/bin/env python
"""
Analyze metrics data in the database.
This script provides statistics about the historical metrics data.
"""

import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sqlalchemy import func, extract

# Add the parent directory to sys.path to allow imports from the app package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.agency import Agency
from app.models.document import AgencyDocument
from app.models.metrics import AgencyRegulationDocumentHistoricalMetrics

def analyze_metrics_data():
    """Analyze metrics data and print statistics."""
    db = SessionLocal()
    try:
        # Count total metrics
        total_metrics = db.query(func.count(AgencyRegulationDocumentHistoricalMetrics.id)).scalar()
        print(f"Total metrics records: {total_metrics}")
        
        if total_metrics == 0:
            print("No metrics data found. Run the generate_fake_metrics.py script first.")
            return
        
        # Count metrics by year
        metrics_by_year = db.query(
            extract('year', AgencyRegulationDocumentHistoricalMetrics.metrics_date).label('year'),
            func.count(AgencyRegulationDocumentHistoricalMetrics.id).label('count')
        ).group_by('year').order_by('year').all()
        
        print("\nMetrics by year:")
        for year, count in metrics_by_year:
            print(f"  {int(year)}: {count} records")
        
        # Count metrics by agency
        metrics_by_agency = db.query(
            Agency.name,
            func.count(AgencyRegulationDocumentHistoricalMetrics.id).label('count')
        ).join(Agency, Agency.id == AgencyRegulationDocumentHistoricalMetrics.agency_id)\
         .group_by(Agency.name)\
         .order_by(func.count(AgencyRegulationDocumentHistoricalMetrics.id).desc())\
         .limit(10)\
         .all()
        
        print("\nTop 10 agencies by metrics count:")
        for agency_name, count in metrics_by_agency:
            print(f"  {agency_name}: {count} records")
        
        # Get average metrics values
        avg_metrics = db.query(
            func.avg(AgencyRegulationDocumentHistoricalMetrics.word_count).label('avg_word_count'),
            func.avg(AgencyRegulationDocumentHistoricalMetrics.paragraph_count).label('avg_paragraph_count'),
            func.avg(AgencyRegulationDocumentHistoricalMetrics.sentence_count).label('avg_sentence_count'),
            func.avg(AgencyRegulationDocumentHistoricalMetrics.language_complexity_score).label('avg_complexity'),
            func.avg(AgencyRegulationDocumentHistoricalMetrics.readability_score).label('avg_readability'),
            func.avg(AgencyRegulationDocumentHistoricalMetrics.simplicity_score).label('avg_simplicity')
        ).first()
        
        print("\nAverage metrics values:")
        print(f"  Word count: {avg_metrics.avg_word_count:.2f}")
        print(f"  Paragraph count: {avg_metrics.avg_paragraph_count:.2f}")
        print(f"  Sentence count: {avg_metrics.avg_sentence_count:.2f}")
        print(f"  Complexity score: {avg_metrics.avg_complexity:.2f}")
        print(f"  Readability score: {avg_metrics.avg_readability:.2f}")
        print(f"  Simplicity score: {avg_metrics.avg_simplicity:.2f}")
        
        # Get metrics trends over time
        metrics_trends = db.query(
            extract('year', AgencyRegulationDocumentHistoricalMetrics.metrics_date).label('year'),
            func.avg(AgencyRegulationDocumentHistoricalMetrics.word_count).label('avg_word_count'),
            func.avg(AgencyRegulationDocumentHistoricalMetrics.language_complexity_score).label('avg_complexity'),
            func.avg(AgencyRegulationDocumentHistoricalMetrics.readability_score).label('avg_readability'),
            func.avg(AgencyRegulationDocumentHistoricalMetrics.simplicity_score).label('avg_simplicity')
        ).group_by('year').order_by('year').all()
        
        print("\nMetrics trends over time:")
        print("  Year | Word Count | Complexity | Readability | Simplicity")
        print("  ------------------------------------------------")
        for trend in metrics_trends:
            print(f"  {int(trend.year)} | {trend.avg_word_count:.0f} | {trend.avg_complexity:.2f} | {trend.avg_readability:.2f} | {trend.avg_simplicity:.2f}")
        
        # Get document with most metrics
        doc_with_most_metrics = db.query(
            AgencyDocument.title,
            func.count(AgencyRegulationDocumentHistoricalMetrics.id).label('metrics_count')
        ).join(AgencyRegulationDocumentHistoricalMetrics, 
               AgencyRegulationDocumentHistoricalMetrics.document_id == AgencyDocument.id)\
         .group_by(AgencyDocument.title)\
         .order_by(func.count(AgencyRegulationDocumentHistoricalMetrics.id).desc())\
         .first()
        
        if doc_with_most_metrics:
            print(f"\nDocument with most metrics: {doc_with_most_metrics.title} ({doc_with_most_metrics.metrics_count} records)")
        
        # Get document with highest complexity
        doc_with_highest_complexity = db.query(
            AgencyDocument.title,
            func.avg(AgencyRegulationDocumentHistoricalMetrics.language_complexity_score).label('avg_complexity')
        ).join(AgencyRegulationDocumentHistoricalMetrics, 
               AgencyRegulationDocumentHistoricalMetrics.document_id == AgencyDocument.id)\
         .group_by(AgencyDocument.title)\
         .order_by(func.avg(AgencyRegulationDocumentHistoricalMetrics.language_complexity_score).desc())\
         .first()
        
        if doc_with_highest_complexity:
            print(f"Document with highest complexity: {doc_with_highest_complexity.title} (score: {doc_with_highest_complexity.avg_complexity:.2f})")
        
        # Get document with highest readability
        doc_with_highest_readability = db.query(
            AgencyDocument.title,
            func.avg(AgencyRegulationDocumentHistoricalMetrics.readability_score).label('avg_readability')
        ).join(AgencyRegulationDocumentHistoricalMetrics, 
               AgencyRegulationDocumentHistoricalMetrics.document_id == AgencyDocument.id)\
         .group_by(AgencyDocument.title)\
         .order_by(func.avg(AgencyRegulationDocumentHistoricalMetrics.readability_score).desc())\
         .first()
        
        if doc_with_highest_readability:
            print(f"Document with highest readability: {doc_with_highest_readability.title} (score: {doc_with_highest_readability.avg_readability:.2f})")
    
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("Analyzing metrics data...")
    analyze_metrics_data()
    print("\nAnalysis completed!") 