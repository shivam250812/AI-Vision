from sqlalchemy import Column, Integer, String, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class ProcessingResult(Base):
    __tablename__ = "processing_results"
    
    id = Column(Integer, primary_key=True, index=True)
    pdf_name = Column(String(255), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="pending")
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class EmergencyLighting(Base):
    __tablename__ = "emergency_lighting"
    
    id = Column(Integer, primary_key=True, index=True)
    pdf_name = Column(String(255), nullable=False, index=True)
    symbol = Column(String(50), nullable=True)
    bounding_box = Column(JSON, nullable=True)  # [x1, y1, x2, y2]
    text_nearby = Column(JSON, nullable=True)  # List of nearby text
    source_sheet = Column(String(50), nullable=True)
    confidence = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class StaticContent(Base):
    __tablename__ = "static_content"
    
    id = Column(Integer, primary_key=True, index=True)
    pdf_name = Column(String(255), nullable=False, index=True)
    content_type = Column(String(50), nullable=False)  # 'note', 'table_row'
    text = Column(Text, nullable=True)
    symbol = Column(String(50), nullable=True)
    description = Column(String(255), nullable=True)
    mount = Column(String(100), nullable=True)
    voltage = Column(String(50), nullable=True)
    lumens = Column(String(50), nullable=True)
    source_sheet = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow) 