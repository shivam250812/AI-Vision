from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
import tempfile
from typing import Optional
import uuid
from datetime import datetime

from app.schemas import UploadResponse, ProcessingResultResponse
from app.models import ProcessingResult
from app.database import get_db, engine
from app.models import Base
from app.vision.enhanced_detector import EnhancedEmergencyLightingDetector
from app.vision.ocr_processor import OCRProcessor
from app.vision.enhanced_llm_classifier import EnhancedLLMClassifier
from app.utils.pdf_processor import PDFProcessor
from app.utils.text_association import TextAssociation

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Vision Emergency Lighting Detection - Simple Test",
    description="Simple version for testing PDF upload without background processing",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "AI Vision Emergency Lighting Detection API - Simple Test",
        "version": "1.0.0",
        "endpoints": {
            "upload": "/upload",
            "result": "/result",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/upload", response_model=UploadResponse)
async def upload_blueprint(
    file: UploadFile = File(...),
    project_id: Optional[str] = Query(None, description="Optional project identifier")
):
    """
    Upload a PDF blueprint and process immediately (for testing).
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400, 
            detail="Only PDF files are supported"
        )
    
    # Validate file size (max 50MB)
    if file.size and file.size > 50 * 1024 * 1024:
        raise HTTPException(
            status_code=400, 
            detail="File size must be less than 50MB"
        )
    
    try:
        # Create unique filename
        file_id = str(uuid.uuid4())
        pdf_name = f"{file_id}_{file.filename}"
        
        # Save file to temporary location
        temp_dir = "temp_uploads"
        os.makedirs(temp_dir, exist_ok=True)
        file_path = os.path.join(temp_dir, pdf_name)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process the PDF immediately
        print(f"Processing PDF: {pdf_name}")
        
        # Initialize processors
        pdf_processor = PDFProcessor()
        detector = EnhancedEmergencyLightingDetector()
        ocr_processor = OCRProcessor()
        llm_classifier = EnhancedLLMClassifier()
        text_associator = TextAssociation()
        
        # Process PDF pages
        processed_pages = pdf_processor.process_pdf_pages(file_path)
        
        if not processed_pages:
            raise Exception("No pages found in PDF")
        
        # Process each page
        all_emergency_detections = []
        all_ocr_data = []
        all_static_content = []
        
        for page_data in processed_pages:
            page_num = page_data['page_number']
            image = page_data['image']
            
            # Detect emergency lighting fixtures
            cv_detections = detector.process_image(image)
            emergency_fixtures = cv_detections.get('emergency_fixtures', [])
            
            # Process OCR
            ocr_data = ocr_processor.process_image(image)
            
            # Associate text with fixtures
            associated_fixtures = text_associator.associate_text_with_fixtures(
                emergency_fixtures, 
                ocr_data.get('all_text', [])
            )
            
            # Add page information
            for fixture in associated_fixtures:
                fixture['source_sheet'] = f"Page {page_num}"
                all_emergency_detections.append(fixture)
            
            # Collect OCR data
            all_ocr_data.append(ocr_data)
            
            # Extract static content (notes and tables)
            static_content = _extract_static_content(ocr_data, page_num)
            all_static_content.extend(static_content)
        
        # Combine all static content
        combined_static_content = {
            'rulebook': all_static_content
        }
        
        # Classify using LLM
        classification_result = llm_classifier.process_detections(
            all_emergency_detections,
            _combine_ocr_data(all_ocr_data),
            combined_static_content
        )
        
        # Initialize database record
        db = next(get_db())
        processing_result = ProcessingResult(
            pdf_name=pdf_name,
            status="complete",
            result=classification_result
        )
        db.add(processing_result)
        db.commit()
        db.refresh(processing_result)
        
        # Clean up temporary file
        if os.path.exists(file_path):
            os.remove(file_path)
        
        return UploadResponse(
            status="processed",
            pdf_name=pdf_name,
            message="PDF processed successfully. Results available immediately."
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )

@app.get("/result", response_model=ProcessingResultResponse)
async def get_processing_result(
    pdf_name: str = Query(..., description="Name of the uploaded PDF")
):
    """
    Get the processing result for a specific PDF.
    """
    try:
        db = next(get_db())
        result = db.query(ProcessingResult).filter(
            ProcessingResult.pdf_name == pdf_name
        ).first()
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"No processing result found for {pdf_name}"
            )
        
        if result.status == "complete":
            return ProcessingResultResponse(
                pdf_name=pdf_name,
                status="complete",
                result=result.result
            )
        elif result.status == "failed":
            return ProcessingResultResponse(
                pdf_name=pdf_name,
                status="failed",
                message=result.error_message or "Processing failed"
            )
        else:
            return ProcessingResultResponse(
                pdf_name=pdf_name,
                status="in_progress",
                message="Processing is still in progress. Please try again later."
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving result: {str(e)}"
        )

def _extract_static_content(ocr_data, page_num):
    """Extract static content from OCR data."""
    static_content = []
    
    # Extract general notes
    for note in ocr_data.get('general_notes', []):
        static_content.append({
            'type': 'note',
            'text': note,
            'source_sheet': f"Page {page_num}"
        })
    
    # Extract table data
    for table_row in ocr_data.get('table_data', []):
        static_content.append({
            'type': 'table_row',
            'symbol': table_row.get('symbol'),
            'description': table_row.get('description'),
            'mount': table_row.get('mount'),
            'voltage': table_row.get('voltage'),
            'lumens': table_row.get('lumens'),
            'source_sheet': f"Page {page_num}"
        })
    
    return static_content

def _combine_ocr_data(ocr_data_list):
    """Combine OCR data from multiple pages."""
    combined = {
        'all_text': [],
        'emergency_symbols': [],
        'table_data': [],
        'general_notes': []
    }
    
    for ocr_data in ocr_data_list:
        combined['all_text'].extend(ocr_data.get('all_text', []))
        combined['emergency_symbols'].extend(ocr_data.get('emergency_symbols', []))
        combined['table_data'].extend(ocr_data.get('table_data', []))
        combined['general_notes'].extend(ocr_data.get('general_notes', []))
    
    return combined

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 