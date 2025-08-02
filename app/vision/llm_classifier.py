from typing import List, Dict, Any
from .enhanced_llm_classifier import EnhancedLLMClassifier

class LLMClassifier:
    def __init__(self, api_key: str = None):
        """
        Basic LLM classifier that wraps the enhanced classifier.
        """
        self.enhanced_classifier = EnhancedLLMClassifier(api_key)
    
    def process_detections(self, 
                          emergency_detections: List[Dict[str, Any]], 
                          ocr_data: Dict[str, Any],
                          static_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process all detections and create a comprehensive classification and grouping.
        
        Args:
            emergency_detections: Computer vision detections
            ocr_data: OCR extracted data
            static_content: Static content (notes, tables)
            
        Returns:
            Comprehensive classification and grouping result
        """
        return self.enhanced_classifier.process_detections(
            emergency_detections, ocr_data, static_content
        )
    
    def classify_and_group_emergency_lighting(self, 
                                            detections: List[Dict[str, Any]], 
                                            static_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify and group emergency lighting fixtures.
        
        Args:
            detections: List of emergency lighting detections
            static_content: Extracted static content (notes, tables)
            
        Returns:
            Dictionary with structured grouped results
        """
        return self.enhanced_classifier.classify_and_group_emergency_lighting(
            detections, static_content
        ) 