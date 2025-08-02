#!/usr/bin/env python3
"""
Database initialization script for the AI Vision Emergency Lighting Detection system.
"""

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import Base
from app.database import engine

def init_database():
    """
    Initialize the database by creating all tables.
    """
    try:
        print("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully!")
        
        # Test database connection
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # Test query
        from sqlalchemy import text
        result = db.execute(text("SELECT 1"))
        print("Database connection test successful!")
        
        db.close()
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        sys.exit(1)

def create_sample_data():
    """
    Create sample data for testing.
    """
    try:
        from app.database import SessionLocal
        from app.models import ProcessingResult
        
        print("Creating sample data...")
        
        db = SessionLocal()
        
        # Create sample processing result
        sample_result = ProcessingResult(
            pdf_name="sample_blueprint.pdf",
            status="complete",
            result={
                "summary": {
                    "Lights01": {"count": 5, "description": "2x4 LED Emergency Fixture"},
                    "Lights02": {"count": 3, "description": "Exit/Emergency Combo Unit"}
                }
            }
        )
        
        db.add(sample_result)
        db.commit()
        
        print("Sample data created successfully!")
        db.close()
        
    except Exception as e:
        print(f"Error creating sample data: {e}")

if __name__ == "__main__":
    load_dotenv()
    
    print("Initializing AI Vision Emergency Lighting Detection Database...")
    
    # Initialize database
    init_database()
    
    # Create sample data (optional)
    create_sample_data()
    
    print("Database initialization completed!") 