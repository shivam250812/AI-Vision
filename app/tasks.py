from celery import shared_task
from sqlalchemy.orm import Session
import os
import json
from typing import Dict, Any, List
import traceback

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import ProcessingResult, EmergencyLighting, StaticContent
from app.vision.detector import EmergencyLightingDetector
from app.vision.ocr_processor import OCRProcessor
from app.vision.llm_classifier import LLMClassifier
from app.utils.pdf_processor import PDFProcessor
from app.utils.text_association import TextAssociation

@celery_app.task(bind=True)
def process_blueprint_task(self, file_path: str, pdf_name: str, project_id: str = None):
    """
    Background task to process a PDF blueprint.
    
    Args:
        file_path: Path to the uploaded PDF file
        pdf_name: Name of the PDF file
        project_id: Optional project identifier
        
    Returns:
        Processing result dictionary
    """
    db = SessionLocal()
    
    try:
        # Update task status to processing
        self.update_state(state='PROCESSING', meta={'current': 0, 'total': 100})
        
        # Update database status
        result_record = db.query(ProcessingResult).filter(
            ProcessingResult.pdf_name == pdf_name
        ).first()
        
        if result_record:
            result_record.status = "processing"
            db.commit()
        
        # Initialize processors
        pdf_processor = PDFProcessor()
        detector = EmergencyLightingDetector()
        ocr_processor = OCRProcessor()
        llm_classifier = LLMClassifier()
        text_associator = TextAssociation()
        
        # Step 1: Process PDF pages (20%)
        self.update_state(state='PROCESSING', meta={'current': 20, 'total': 100})
        
        processed_pages = pdf_processor.process_pdf_pages(file_path)
        
        if not processed_pages:
            raise Exception("No pages found in PDF")
        
        # Step 2: Detect emergency lighting fixtures (40%)
        self.update_state(state='PROCESSING', meta={'current': 40, 'total': 100})
        
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
        
        # Step 3: LLM Classification (60%)
        self.update_state(state='PROCESSING', meta={'current': 60, 'total': 100})
        
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
        
        # Step 4: Save results to database (80%)
        self.update_state(state='PROCESSING', meta={'current': 80, 'total': 100})
        
        # Save emergency lighting detections
        for detection in all_emergency_detections:
            emergency_record = EmergencyLighting(
                pdf_name=pdf_name,
                symbol=detection.get('symbol'),
                bounding_box=detection.get('bounding_box'),
                text_nearby=detection.get('text_nearby'),
                source_sheet=detection.get('source_sheet'),
                confidence=detection.get('confidence')
            )
            db.add(emergency_record)
        
        # Save static content
        for content in all_static_content:
            static_record = StaticContent(
                pdf_name=pdf_name,
                content_type=content.get('type'),
                text=content.get('text'),
                symbol=content.get('symbol'),
                description=content.get('description'),
                mount=content.get('mount'),
                voltage=content.get('voltage'),
                lumens=content.get('lumens'),
                source_sheet=content.get('source_sheet')
            )
            db.add(static_record)
        
        # Update processing result
        if result_record:
            result_record.status = "complete"
            result_record.result = classification_result
            db.commit()
        
        # Step 5: Cleanup (100%)
        self.update_state(state='PROCESSING', meta={'current': 100, 'total': 100})
        
        # Clean up temporary file
        if os.path.exists(file_path):
            os.remove(file_path)
        
        return {
            "status": "success",
            "pdf_name": pdf_name,
            "detections_count": len(all_emergency_detections),
            "classification": classification_result
        }
        
    except Exception as e:
        # Update database with error
        if result_record:
            result_record.status = "failed"
            result_record.error_message = str(e)
            db.commit()
        
        # Clean up temporary file
        if os.path.exists(file_path):
            os.remove(file_path)
        
        error_msg = f"Error processing blueprint: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        
        raise Exception(error_msg)
        
    finally:
        db.close()

def _extract_static_content(ocr_data: Dict[str, Any], page_num: int) -> List[Dict[str, Any]]:
    """
    Extract static content (notes and table data) from OCR data.
    """
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

def _combine_ocr_data(ocr_data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Combine OCR data from multiple pages.
    """
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