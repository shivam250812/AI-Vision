import os
import json
from typing import List, Dict, Any, Optional
import requests
from dotenv import load_dotenv

load_dotenv()

class EnhancedLLMClassifier:
    def __init__(self, api_key: str = None):
        """
        Enhanced LLM classifier for grouping emergency lighting fixtures with structured output.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.api_url = "https://api.openai.com/v1/chat/completions"
        
        if not self.api_key:
            print("Warning: No OpenAI API key provided. Using fallback classification.")
    
    def classify_and_group_emergency_lighting(self, 
                                            detections: List[Dict[str, Any]], 
                                            static_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced classification and grouping of emergency lighting fixtures.
        
        Args:
            detections: List of emergency lighting detections
            static_content: Extracted static content (notes, tables)
            
        Returns:
            Dictionary with structured grouped results
        """
        if not self.api_key:
            return self._fallback_grouping(detections, static_content)
        
        try:
            # Prepare prompt for LLM
            prompt = self._create_enhanced_classification_prompt(detections, static_content)
            
            # Call OpenAI API
            response = self._call_openai_api(prompt)
            
            # Parse response
            result = self._parse_llm_response(response)
            
            return result
            
        except Exception as e:
            print(f"Error in LLM classification: {e}")
            return self._fallback_grouping(detections, static_content)
    
    def _create_enhanced_classification_prompt(self, 
                                             detections: List[Dict[str, Any]], 
                                             static_content: Dict[str, Any]) -> str:
        """
        Create an enhanced prompt for the LLM to classify and group emergency lighting fixtures.
        """
        # Format detections with more detail
        detection_text = ""
        for i, detection in enumerate(detections):
            symbol = detection.get('symbol', 'Unknown')
            bounding_box = detection.get('bounding_box', [])
            text_nearby = detection.get('text_nearby', [])
            source_sheet = detection.get('source_sheet', 'Unknown')
            fixture_type = detection.get('type', 'unknown')
            description = detection.get('description', '')
            confidence = detection.get('confidence', 0.0)
            
            detection_text += f"Detection {i+1}:\n"
            detection_text += f"  Symbol: {symbol}\n"
            detection_text += f"  Type: {fixture_type}\n"
            detection_text += f"  Description: {description}\n"
            detection_text += f"  Bounding Box: {bounding_box}\n"
            detection_text += f"  Nearby Text: {text_nearby}\n"
            detection_text += f"  Source Sheet: {source_sheet}\n"
            detection_text += f"  Confidence: {confidence:.2f}\n\n"
        
        # Format static content
        rulebook_text = ""
        if 'rulebook' in static_content:
            for item in static_content['rulebook']:
                if item.get('type') == 'note':
                    rulebook_text += f"Note: {item.get('text', '')}\n"
                elif item.get('type') == 'table_row':
                    rulebook_text += f"Table Row - Symbol: {item.get('symbol', '')}, "
                    rulebook_text += f"Description: {item.get('description', '')}, "
                    rulebook_text += f"Mount: {item.get('mount', '')}, "
                    rulebook_text += f"Voltage: {item.get('voltage', '')}, "
                    rulebook_text += f"Lumens: {item.get('lumens', '')}\n"
        
        prompt = f"""
You are an expert electrical engineer specializing in emergency lighting systems. Analyze the detected emergency lighting fixtures and group them by type with accurate counts and descriptions.

DETECTED EMERGENCY LIGHTING FIXTURES:
{detection_text}

REFERENCE INFORMATION (General Notes and Lighting Schedule):
{rulebook_text}

TASK:
1. Analyze all detected emergency lighting fixtures
2. Group them by fixture type and symbol
3. Count how many of each type were detected
4. Provide accurate descriptions based on the reference information
5. Create a structured summary with counts and descriptions

OUTPUT FORMAT:
Return a JSON object with the following structure:
{{
  "summary": {{
    "Lights01": {{ "count": <number>, "description": "<description>", "symbols": ["<symbol1>", "<symbol2>"] }},
    "Lights02": {{ "count": <number>, "description": "<description>", "symbols": ["<symbol1>", "<symbol2>"] }},
    ...
  }},
  "detailed_detections": [
    {{
      "symbol": "<symbol>",
      "type": "<fixture_type>",
      "description": "<description>",
      "bounding_box": [x1, y1, x2, y2],
      "text_nearby": ["<text1>", "<text2>"],
      "source_sheet": "<sheet_name>",
      "confidence": <confidence_score>
    }}
  ]
}}

CLASSIFICATION RULES:
- Group by fixture type: Recessed LED, Wallpack, Exit/Emergency, etc.
- Count each detection separately
- Use the lighting schedule table to understand fixture specifications
- Provide clear, technical descriptions
- Include all relevant symbols in the grouping
- Ensure counts match the actual number of detections

Please provide the JSON response only, no additional text.
"""
        
        return prompt
    
    def _call_openai_api(self, prompt: str) -> str:
        """
        Call the OpenAI API with the classification prompt.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert electrical engineer specializing in emergency lighting systems. Provide accurate, technical classifications and groupings."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": 1500
        }
        
        response = requests.post(self.api_url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        return result['choices'][0]['message']['content']
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the LLM response and extract the classification results.
        """
        try:
            # Try to extract JSON from the response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx != 0:
                json_str = response[start_idx:end_idx]
                result = json.loads(json_str)
                return result
            else:
                raise ValueError("No JSON found in response")
                
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            print(f"Response: {response}")
            return {"summary": {}, "detailed_detections": []}
    
    def _fallback_grouping(self, 
                          detections: List[Dict[str, Any]], 
                          static_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback grouping when LLM is not available.
        """
        # Group detections by type and symbol
        grouped_detections = {}
        
        for detection in detections:
            fixture_type = detection.get('type', 'unknown')
            symbol = detection.get('symbol', 'Unknown')
            
            if fixture_type not in grouped_detections:
                grouped_detections[fixture_type] = {
                    'count': 0,
                    'symbols': set(),
                    'descriptions': set()
                }
            
            grouped_detections[fixture_type]['count'] += 1
            grouped_detections[fixture_type]['symbols'].add(symbol)
            
            description = detection.get('description', '')
            if description:
                grouped_detections[fixture_type]['descriptions'].add(description)
        
        # Create summary
        summary = {}
        detailed_detections = []
        
        for i, (fixture_type, group_data) in enumerate(grouped_detections.items(), 1):
            # Get the most common description or create a default
            descriptions = list(group_data['descriptions'])
            description = descriptions[0] if descriptions else f"{fixture_type.replace('_', ' ').title()} Fixture"
            
            summary[f"Lights{i:02d}"] = {
                "count": group_data['count'],
                "description": description,
                "symbols": list(group_data['symbols'])
            }
        
        # Create detailed detections
        for detection in detections:
            detailed_detection = {
                "symbol": detection.get('symbol', 'Unknown'),
                "type": detection.get('type', 'unknown'),
                "description": detection.get('description', ''),
                "bounding_box": detection.get('bounding_box', []),
                "text_nearby": detection.get('text_nearby', []),
                "source_sheet": detection.get('source_sheet', 'Unknown'),
                "confidence": detection.get('confidence', 0.0)
            }
            detailed_detections.append(detailed_detection)
        
        return {
            "summary": summary,
            "detailed_detections": detailed_detections
        }
    
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
        # Combine detections with OCR data
        combined_detections = self._combine_detections(emergency_detections, ocr_data)
        
        # Classify and group using LLM
        classification = self.classify_and_group_emergency_lighting(combined_detections, static_content)
        
        return classification
    
    def _combine_detections(self, 
                           emergency_detections: List[Dict[str, Any]], 
                           ocr_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Combine computer vision detections with OCR data.
        """
        combined = []
        
        # Add emergency detections
        for detection in emergency_detections:
            combined.append({
                "symbol": detection.get("symbol", "Unknown"),
                "type": detection.get("type", "unknown"),
                "description": detection.get("description", ""),
                "bounding_box": detection.get("bounding_box", []),
                "text_nearby": detection.get("text_nearby", []),
                "source_sheet": detection.get("source_sheet", "Unknown"),
                "confidence": detection.get("confidence", 0.0)
            })
        
        # Add OCR symbols
        if "emergency_symbols" in ocr_data:
            for symbol in ocr_data["emergency_symbols"]:
                combined.append({
                    "symbol": symbol.get("symbol", "Unknown"),
                    "type": "emergency_light",
                    "description": "Emergency Lighting Fixture",
                    "bounding_box": symbol.get("bounding_box", []),
                    "text_nearby": [symbol.get("text", "")],
                    "source_sheet": "OCR",
                    "confidence": symbol.get("confidence", 0.0)
                })
        
        return combined 