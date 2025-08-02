import cv2
import numpy as np
from typing import List, Dict, Any
from .enhanced_detector import EnhancedEmergencyLightingDetector

class EmergencyLightingDetector:
    def __init__(self, model_path: str = None):
        """
        Basic emergency lighting detector that wraps the enhanced detector.
        """
        self.enhanced_detector = EnhancedEmergencyLightingDetector(model_path)
    
    def process_image(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Process an image to detect emergency lighting fixtures.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Dictionary containing detection results
        """
        return self.enhanced_detector.process_image(image)
    
    def detect_shaded_rectangular_areas(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detect shaded rectangular areas representing emergency lighting fixtures.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            List of detected areas with bounding boxes
        """
        return self.enhanced_detector.detect_shaded_rectangular_areas(image)
    
    def classify_emergency_fixture_type(self, text_nearby: List[str]) -> Dict[str, Any]:
        """
        Classify the type of emergency lighting fixture based on nearby text.
        
        Args:
            text_nearby: List of nearby text strings
            
        Returns:
            Classification result with type and confidence
        """
        return self.enhanced_detector.classify_emergency_fixture_type(text_nearby) 