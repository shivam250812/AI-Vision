import cv2
import numpy as np
import pytesseract
from typing import List, Dict, Any, Tuple
import re
import json

class OCRProcessor:
    def __init__(self):
        """
        OCR processor for extracting text, symbols, and tables from blueprint images.
        """
        self.emergency_symbols = [
            'EL', 'A1', 'A1E', 'A2', 'A2E', 'W', 'E1', 'E2', 'EM', 'EXIT'
        ]
        
        # Configure Tesseract for better text recognition
        self.tesseract_config = '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,()-/ '
    
    def process_image(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Process an image to extract text, symbols, and tables.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Dictionary containing extracted text, symbols, and table data
        """
        try:
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Extract all text
            all_text = self._extract_all_text(gray)
            
            # Extract emergency symbols
            emergency_symbols = self._extract_emergency_symbols(gray, all_text)
            
            # Extract table data
            table_data = self._extract_table_data(gray, all_text)
            
            # Extract general notes
            general_notes = self._extract_general_notes(gray, all_text)
            
            return {
                'all_text': all_text,
                'emergency_symbols': emergency_symbols,
                'table_data': table_data,
                'general_notes': general_notes
            }
            
        except Exception as e:
            print(f"Error in OCR processing: {e}")
            return {
                'all_text': [],
                'emergency_symbols': [],
                'table_data': [],
                'general_notes': []
            }
    
    def _extract_all_text(self, gray: np.ndarray) -> List[Dict[str, Any]]:
        """
        Extract all text from the image with bounding boxes.
        """
        try:
            # Use Tesseract to get text with bounding boxes
            data = pytesseract.image_to_data(gray, config=self.tesseract_config, output_type=pytesseract.Output.DICT)
            
            text_blocks = []
            n_boxes = len(data['text'])
            
            for i in range(n_boxes):
                # Filter out empty text and low confidence
                if int(data['conf'][i]) > 30 and data['text'][i].strip():
                    text_blocks.append({
                        'text': data['text'][i].strip(),
                        'bounding_box': [
                            data['left'][i],
                            data['top'][i],
                            data['left'][i] + data['width'][i],
                            data['top'][i] + data['height'][i]
                        ],
                        'confidence': int(data['conf'][i]) / 100.0
                    })
            
            return text_blocks
            
        except Exception as e:
            print(f"Error extracting text: {e}")
            return []
    
    def _extract_emergency_symbols(self, gray: np.ndarray, all_text: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract emergency lighting symbols from text.
        """
        emergency_symbols = []
        
        for text_block in all_text:
            text = text_block['text'].upper()
            
            # Check for emergency symbols
            for symbol in self.emergency_symbols:
                if symbol in text:
                    emergency_symbols.append({
                        'symbol': symbol,
                        'text': text_block['text'],
                        'bounding_box': text_block['bounding_box'],
                        'confidence': text_block['confidence']
                    })
                    break
            
            # Check for patterns like EL501, EL502, etc.
            el_pattern = re.search(r'EL\d+', text)
            if el_pattern:
                emergency_symbols.append({
                    'symbol': el_pattern.group(),
                    'text': text_block['text'],
                    'bounding_box': text_block['bounding_box'],
                    'confidence': text_block['confidence']
                })
        
        return emergency_symbols
    
    def _extract_table_data(self, gray: np.ndarray, all_text: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract table data from the image.
        """
        table_data = []
        
        # Look for table-like structures
        # This is a simplified approach - in production, you'd want more sophisticated table detection
        
        # Group text by vertical alignment (potential table rows)
        y_coords = [block['bounding_box'][1] for block in all_text]
        y_coords.sort()
        
        # Find rows (text blocks with similar y-coordinates)
        rows = []
        current_row = []
        row_threshold = 20  # pixels
        
        for i, text_block in enumerate(all_text):
            if not current_row:
                current_row.append(text_block)
            else:
                # Check if this text is in the same row
                y_diff = abs(text_block['bounding_box'][1] - current_row[0]['bounding_box'][1])
                if y_diff <= row_threshold:
                    current_row.append(text_block)
                else:
                    # New row
                    if current_row:
                        rows.append(current_row)
                    current_row = [text_block]
        
        if current_row:
            rows.append(current_row)
        
        # Process rows to extract table data
        for row in rows:
            # Sort by x-coordinate
            row.sort(key=lambda x: x['bounding_box'][0])
            
            # Look for table-like patterns
            row_text = ' '.join([block['text'] for block in row])
            
            # Check for lighting schedule patterns
            if any(keyword in row_text.upper() for keyword in ['LUMINAIRE', 'MOUNT', 'VOLTAGE', 'LUMENS']):
                # This might be a table header or data row
                table_row = self._parse_table_row(row)
                if table_row:
                    table_data.append(table_row)
        
        return table_data
    
    def _parse_table_row(self, row: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Parse a row of text into table data.
        """
        if len(row) < 2:
            return None
        
        # Simple parsing - look for common patterns
        row_text = ' '.join([block['text'] for block in row])
        
        # Extract symbol (usually first column)
        symbol = row[0]['text'] if row else ''
        
        # Look for description keywords
        description_keywords = ['LUMINAIRE', 'FIXTURE', 'LIGHT', 'EMERGENCY']
        description = ''
        for block in row:
            if any(keyword in block['text'].upper() for keyword in description_keywords):
                description = block['text']
                break
        
        # Look for mount information
        mount_keywords = ['CEILING', 'WALL', 'RECESSED', 'SURFACE']
        mount = ''
        for block in row:
            if any(keyword in block['text'].upper() for keyword in mount_keywords):
                mount = block['text']
                break
        
        # Look for voltage information
        voltage_pattern = re.search(r'\d+V', row_text)
        voltage = voltage_pattern.group() if voltage_pattern else ''
        
        # Look for lumens information
        lumens_pattern = re.search(r'\d+lm', row_text)
        lumens = lumens_pattern.group() if lumens_pattern else ''
        
        return {
            'symbol': symbol,
            'description': description,
            'mount': mount,
            'voltage': voltage,
            'lumens': lumens,
            'raw_text': row_text
        }
    
    def _extract_general_notes(self, gray: np.ndarray, all_text: List[Dict[str, Any]]) -> List[str]:
        """
        Extract general notes from the image.
        """
        notes = []
        
        # Look for text blocks that might be notes
        for text_block in all_text:
            text = text_block['text']
            
            # Check for note-like patterns
            if any(keyword in text.upper() for keyword in ['NOTE:', 'GENERAL', 'SPECIFICATION', 'REQUIREMENT']):
                notes.append(text)
            
            # Check for longer text blocks (likely notes)
            if len(text) > 50 and text_block['confidence'] > 0.7:
                notes.append(text)
        
        return notes
    
    def get_text_near_bounding_box(self, target_bbox: List[int], all_text: List[Dict[str, Any]], 
                                  distance_threshold: int = 100) -> List[str]:
        """
        Get text near a specific bounding box.
        
        Args:
            target_bbox: Target bounding box [x1, y1, x2, y2]
            all_text: All extracted text blocks
            distance_threshold: Maximum distance to consider "nearby"
            
        Returns:
            List of nearby text strings
        """
        nearby_text = []
        target_center = [
            (target_bbox[0] + target_bbox[2]) // 2,
            (target_bbox[1] + target_bbox[3]) // 2
        ]
        
        for text_block in all_text:
            text_bbox = text_block['bounding_box']
            text_center = [
                (text_bbox[0] + text_bbox[2]) // 2,
                (text_bbox[1] + text_bbox[3]) // 2
            ]
            
            # Calculate distance
            distance = np.sqrt(
                (target_center[0] - text_center[0])**2 + 
                (target_center[1] - text_center[1])**2
            )
            
            if distance <= distance_threshold:
                nearby_text.append(text_block['text'])
        
        return nearby_text 