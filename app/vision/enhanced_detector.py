import cv2
import numpy as np
from typing import List, Tuple, Dict, Any
import torch
from ultralytics import YOLO
import os
import re

class EnhancedEmergencyLightingDetector:
    def __init__(self, model_path: str = None):
        """
        Enhanced emergency lighting detector with specific fixture type detection.
        """
        self.model = None
        self.confidence_threshold = 0.5
        
        # Emergency lighting fixture patterns
        self.emergency_patterns = {
            'recessed_led': r'(2\s*[\'"]?\s*[xX]\s*4\s*[\'"]?\s*RECESSED\s*LED|LED\s*LUMINAIRE)',
            'wallpack': r'(WALLPACK|WALL\s*PACK|WALL\s*MOUNTED)',
            'emergency_exit': r'(EXIT|EMERGENCY\s*EXIT|A1E|A\d+E)',
            'emergency_light': r'(EMERGENCY|EM|EL\d+|E\d+)',
            'photocell': r'(PHOTOCELL|PHOTO\s*CELL)'
        }
        
        # Try to load custom model if provided
        if model_path and os.path.exists(model_path):
            try:
                self.model = YOLO(model_path)
                print(f"Loaded custom model from {model_path}")
            except Exception as e:
                print(f"Failed to load custom model: {e}")
        
        # If no custom model, use default YOLO model for object detection
        if self.model is None:
            try:
                self.model = YOLO('yolov8n.pt')
                print("Using default YOLO model")
            except Exception as e:
                print(f"Failed to load YOLO model: {e}")
                self.model = None
    
    def detect_shaded_rectangular_areas(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Enhanced detection of shaded rectangular areas representing emergency lighting fixtures.
        """
        detections = []
        
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply multiple detection methods
            methods = [
                self._detect_by_adaptive_threshold,
                self._detect_by_otsu_threshold,
                self._detect_by_edge_detection
            ]
            
            for method in methods:
                method_detections = method(gray)
                detections.extend(method_detections)
            
            # Remove duplicates and merge overlapping detections
            detections = self._merge_overlapping_detections(detections)
            
            return detections
            
        except Exception as e:
            print(f"Error in enhanced detection: {e}")
            return []
    
    def _detect_by_adaptive_threshold(self, gray: np.ndarray) -> List[Dict[str, Any]]:
        """Detect using adaptive thresholding."""
        detections = []
        
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if 500 < area < 50000:  # Filter by area
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h
                
                # Look for rectangular shapes
                if 0.3 <= aspect_ratio <= 3.0:
                    confidence = min(area / 10000, 0.9)
                    detections.append({
                        "bounding_box": [x, y, x + w, y + h],
                        "confidence": confidence,
                        "method": "adaptive_threshold",
                        "area": area
                    })
        
        return detections
    
    def _detect_by_otsu_threshold(self, gray: np.ndarray) -> List[Dict[str, Any]]:
        """Detect using Otsu thresholding."""
        detections = []
        
        # Apply Otsu thresholding
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if 1000 < area < 30000:  # Different area range
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h
                
                if 0.5 <= aspect_ratio <= 2.5:
                    confidence = min(area / 8000, 0.85)
                    detections.append({
                        "bounding_box": [x, y, x + w, y + h],
                        "confidence": confidence,
                        "method": "otsu_threshold",
                        "area": area
                    })
        
        return detections
    
    def _detect_by_edge_detection(self, gray: np.ndarray) -> List[Dict[str, Any]]:
        """Detect using edge detection."""
        detections = []
        
        # Apply edge detection
        edges = cv2.Canny(gray, 50, 150)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if 800 < area < 40000:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h
                
                if 0.4 <= aspect_ratio <= 2.8:
                    confidence = min(area / 12000, 0.8)
                    detections.append({
                        "bounding_box": [x, y, x + w, y + h],
                        "confidence": confidence,
                        "method": "edge_detection",
                        "area": area
                    })
        
        return detections
    
    def _merge_overlapping_detections(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge overlapping detections to avoid duplicates."""
        if not detections:
            return []
        
        # Sort by confidence
        detections.sort(key=lambda x: x['confidence'], reverse=True)
        
        merged = []
        used = set()
        
        for i, detection in enumerate(detections):
            if i in used:
                continue
            
            current_bbox = detection['bounding_box']
            merged_group = [detection]
            used.add(i)
            
            # Check for overlaps with other detections
            for j, other_detection in enumerate(detections[i+1:], i+1):
                if j in used:
                    continue
                
                other_bbox = other_detection['bounding_box']
                if self._calculate_iou(current_bbox, other_bbox) > 0.3:
                    merged_group.append(other_detection)
                    used.add(j)
            
            # Merge the group
            if len(merged_group) > 1:
                # Take the highest confidence detection
                best_detection = max(merged_group, key=lambda x: x['confidence'])
                merged.append(best_detection)
            else:
                merged.append(detection)
        
        return merged
    
    def _calculate_iou(self, bbox1: List[int], bbox2: List[int]) -> float:
        """Calculate Intersection over Union between two bounding boxes."""
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        # Calculate intersection
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i <= x1_i or y2_i <= y1_i:
            return 0.0
        
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        
        # Calculate union
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def classify_emergency_fixture_type(self, text_nearby: List[str]) -> Dict[str, Any]:
        """
        Classify the type of emergency lighting fixture based on nearby text.
        """
        classification = {
            'type': 'unknown',
            'confidence': 0.0,
            'description': '',
            'symbol': ''
        }
        
        # Combine all nearby text
        combined_text = ' '.join(text_nearby).upper()
        
        # Check for specific patterns
        for fixture_type, pattern in self.emergency_patterns.items():
            if re.search(pattern, combined_text, re.IGNORECASE):
                classification['type'] = fixture_type
                classification['confidence'] = 0.8
                
                if fixture_type == 'recessed_led':
                    classification['description'] = "2' X 4' RECESSED LED LUMINAIRE"
                elif fixture_type == 'wallpack':
                    classification['description'] = "WALLPACK WITH BUILT IN PHOTOCELL"
                elif fixture_type == 'emergency_exit':
                    classification['description'] = "Exit/Emergency Combo Unit"
                elif fixture_type == 'emergency_light':
                    classification['description'] = "Emergency Lighting Fixture"
                
                break
        
        # Extract symbol from text
        symbol_patterns = [r'EL\d+', r'A\d+E?', r'E\d+', r'[A-Z]\d+']
        for pattern in symbol_patterns:
            match = re.search(pattern, combined_text)
            if match:
                classification['symbol'] = match.group()
                break
        
        return classification
    
    def process_image(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Process an image to detect emergency lighting fixtures with enhanced classification.
        """
        # Detect shaded rectangular areas
        emergency_detections = self.detect_shaded_rectangular_areas(image)
        
        # Classify each detection
        classified_detections = []
        for detection in emergency_detections:
            # This would normally be populated by text association
            # For now, we'll use a placeholder
            text_nearby = []  # Would be populated by text association
            
            classification = self.classify_emergency_fixture_type(text_nearby)
            
            classified_detection = detection.copy()
            classified_detection.update(classification)
            classified_detections.append(classified_detection)
        
        return {
            "emergency_fixtures": classified_detections,
            "total_detections": len(classified_detections),
            "detection_methods": list(set(d['method'] for d in emergency_detections))
        } 