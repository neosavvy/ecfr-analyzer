#!/usr/bin/env python
"""
Clean metrics data from the database.
This script removes all historical metrics data, allowing you to start fresh with real data.
"""

import sys
import os
from sqlalchemy import text

# Add the parent directory to sys.path to allow imports from the app package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app.models.metrics import AgencyRegulationDocumentHistoricalMetrics

def clean_metrics_data():
    """Remove all metrics data from the database."""
    db = SessionLocal()
    try:
        # Count metrics before deletion
        count = db.query(AgencyRegulationDocumentHistoricalMetrics).count()
        print(f"Found {count} metrics records to delete")
        
        if count == 0:
            print("No metrics data to clean. Database is already empty.")
            return
        
        # Confirm deletion
        confirm = input(f"Are you sure you want to delete all {count} metrics records? (y/n): ")
        if confirm.lower() != 'y':
            print("Operation cancelled.")
            return
        
        # Delete all metrics
        db.query(AgencyRegulationDocumentHistoricalMetrics).delete()
        db.commit()
        print(f"Successfully deleted {count} metrics records")
        
        # Reset the sequence if needed (for PostgreSQL)
        try:
            with engine.connect() as connection:
                connection.execute(text("ALTER SEQUENCE agency_regulation_document_historical_metrics_id_seq RESTART WITH 1"))
                print("Reset ID sequence")
        except Exception as e:
            print(f"Note: Could not reset sequence: {e}")
    
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting metrics data cleanup...")
    clean_metrics_data()
    print("Metrics data cleanup completed!") 