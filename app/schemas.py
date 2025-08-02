from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class UploadResponse(BaseModel):
    status: str
    pdf_name: str
    message: str

class ProcessingResultResponse(BaseModel):
    pdf_name: str
    status: str
    result: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

class EmergencyLightingDetection(BaseModel):
    symbol: Optional[str] = None
    bounding_box: List[int]  # [x1, y1, x2, y2]
    text_nearby: List[str]
    source_sheet: str
    confidence: float

class StaticContentItem(BaseModel):
    type: str  # 'note' or 'table_row'
    text: Optional[str] = None
    symbol: Optional[str] = None
    description: Optional[str] = None
    mount: Optional[str] = None
    voltage: Optional[str] = None
    lumens: Optional[str] = None
    source_sheet: str

class RulebookContent(BaseModel):
    rulebook: List[StaticContentItem]

class LightingSummary(BaseModel):
    count: int
    description: str

class ProcessingSummary(BaseModel):
    summary: Dict[str, LightingSummary]

class ErrorResponse(BaseModel):
    error: str
    message: str 