from fastapi import FastAPI, File, UploadFile, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
import tempfile
from typing import Optional
import uuid
from datetime import datetime

from app.schemas import UploadResponse, ProcessingResultResponse, ErrorResponse
from app.models import ProcessingResult
from app.database import get_db, engine
from app.models import Base
from app.tasks import process_blueprint_task

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Vision Emergency Lighting Detection",
    description="API for detecting and classifying emergency lighting fixtures from construction blueprints",
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
        "message": "AI Vision Emergency Lighting Detection API",
        "version": "1.0.0",
        "endpoints": {
            "upload": "/blueprints/upload",
            "result": "/blueprints/result",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/blueprints/upload", response_model=UploadResponse)
async def upload_blueprint(
    file: UploadFile = File(...),
    project_id: Optional[str] = Query(None, description="Optional project identifier"),
    background_tasks: BackgroundTasks = None
):
    """
    Upload a PDF blueprint and initiate background processing.
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
        
        # Initialize database record
        db = next(get_db())
        processing_result = ProcessingResult(
            pdf_name=pdf_name,
            status="pending"
        )
        db.add(processing_result)
        db.commit()
        db.refresh(processing_result)
        
        # Start background processing using Celery
        try:
            # Use Celery task for background processing
            task = process_blueprint_task.delay(file_path, pdf_name, project_id)
            print(f"Started background processing task: {task.id}")
        except Exception as e:
            print(f"Error starting background task: {e}")
            # Fallback: update status to failed
            processing_result.status = "failed"
            processing_result.error_message = f"Failed to start background processing: {str(e)}"
            db.commit()
            raise HTTPException(
                status_code=500,
                detail="Failed to start background processing"
            )
        
        return UploadResponse(
            status="uploaded",
            pdf_name=pdf_name,
            message="Processing started in background."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading file: {str(e)}"
        )

@app.get("/blueprints/result", response_model=ProcessingResultResponse)
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

@app.get("/test/vision")
async def test_vision():
    """Test vision processing with sample images."""
    try:
        from app.vision.enhanced_detector import EnhancedEmergencyLightingDetector
        from app.vision.enhanced_llm_classifier import EnhancedLLMClassifier
        from app.vision.ocr_processor import OCRProcessor
        import cv2
        
        # Test with different images
        test_images = [
            "AI Vision/Lighting Fixture.png",
            "AI Vision/EL - 501.png",
            "AI Vision/EL - 502.png",
            "AI Vision/EL - 503.png",
            "AI Vision/EL - 504.png"
        ]
        
        results = {}
        
        for image_path in test_images:
            if os.path.exists(image_path):
                # Load image
                image = cv2.imread(image_path)
                if image is None:
                    results[image_path] = {"error": "Could not load image"}
                    continue
                
                # Initialize processors
                detector = EnhancedEmergencyLightingDetector()
                ocr_processor = OCRProcessor()
                llm_classifier = EnhancedLLMClassifier()
                
                # Process image
                cv_result = detector.process_image(image)
                ocr_result = ocr_processor.process_image(image)
                
                # Create static content for LLM
                static_content = {
                    'rulebook': [
                        {
                            'type': 'table_row',
                            'symbol': 'EL502',
                            'description': 'Emergency Lighting Fixture',
                            'mount': 'Ceiling',
                            'voltage': '277V',
                            'lumens': '1500lm'
                        },
                        {
                            'type': 'table_row',
                            'symbol': 'EL503',
                            'description': 'Emergency Lighting Fixture',
                            'mount': 'Ceiling',
                            'voltage': '277V',
                            'lumens': '1500lm'
                        },
                        {
                            'type': 'table_row',
                            'symbol': 'EL504',
                            'description': 'Emergency Lighting Fixture',
                            'mount': 'Ceiling',
                            'voltage': '277V',
                            'lumens': '1500lm'
                        }
                    ]
                }
                
                # Classify and group using LLM
                classification_result = llm_classifier.process_detections(
                    cv_result.get('emergency_fixtures', []),
                    ocr_result,
                    static_content
                )
                
                results[image_path] = {
                    "status": "success",
                    "image_shape": image.shape,
                    "cv_detections": len(cv_result.get('emergency_fixtures', [])),
                    "ocr_text_detections": len(ocr_result.get('all_text', [])),
                    "emergency_symbols": len(ocr_result.get('emergency_symbols', [])),
                    "cv_result": cv_result,
                    "ocr_result": ocr_result,
                    "classification_result": classification_result
                }
            else:
                results[image_path] = {"error": "Image not found"}
        
        return {
            "status": "success",
            "results": results
        }
        
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 