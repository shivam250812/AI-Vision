import numpy as np
from typing import List, Dict, Any, Tuple
import re

class TextAssociation:
    def __init__(self, distance_threshold: int = 150):
        """
        Text association utility for linking detected fixtures with nearby text.
        
        Args:
            distance_threshold: Maximum distance to consider text as "nearby"
        """
        self.distance_threshold = distance_threshold
        
        # Emergency lighting patterns
        self.emergency_patterns = {
            'recessed_led': r'(2\s*[\'"]?\s*[xX]\s*4\s*[\'"]?\s*RECESSED\s*LED|LED\s*LUMINAIRE)',
            'wallpack': r'(WALLPACK|WALL\s*PACK|WALL\s*MOUNTED)',
            'emergency_exit': r'(EXIT|EMERGENCY\s*EXIT|A1E|A\d+E)',
            'emergency_light': r'(EMERGENCY|EM|EL\d+|E\d+)',
            'photocell': r'(PHOTOCELL|PHOTO\s*CELL)'
        }
    
    def associate_text_with_fixtures(self, 
                                   fixtures: List[Dict[str, Any]], 
                                   text_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Associate text blocks with detected fixtures based on spatial proximity.
        
        Args:
            fixtures: List of detected emergency lighting fixtures
            text_blocks: List of text blocks with bounding boxes
            
        Returns:
            List of fixtures with associated text and symbols
        """
        associated_fixtures = []
        
        for fixture in fixtures:
            fixture_bbox = fixture.get('bounding_box', [])
            if not fixture_bbox or len(fixture_bbox) != 4:
                continue
            
            # Find nearby text
            nearby_text = self._find_nearby_text(fixture_bbox, text_blocks)
            
            # Extract symbols from nearby text
            symbols = self._extract_symbols_from_text(nearby_text)
            
            # Classify fixture type based on nearby text
            fixture_type = self._classify_fixture_type(nearby_text)
            
            # Create associated fixture
            associated_fixture = fixture.copy()
            associated_fixture.update({
                'text_nearby': nearby_text,
                'symbols': symbols,
                'fixture_type': fixture_type,
                'primary_symbol': symbols[0] if symbols else None
            })
            
            associated_fixtures.append(associated_fixture)
        
        return associated_fixtures
    
    def _find_nearby_text(self, 
                          target_bbox: List[int], 
                          text_blocks: List[Dict[str, Any]]) -> List[str]:
        """
        Find text blocks that are near the target bounding box.
        
        Args:
            target_bbox: Target bounding box [x1, y1, x2, y2]
            text_blocks: List of text blocks with bounding boxes
            
        Returns:
            List of nearby text strings
        """
        nearby_text = []
        target_center = [
            (target_bbox[0] + target_bbox[2]) // 2,
            (target_bbox[1] + target_bbox[3]) // 2
        ]
        
        for text_block in text_blocks:
            text_bbox = text_block.get('bounding_box', [])
            if not text_bbox or len(text_bbox) != 4:
                continue
            
            text_center = [
                (text_bbox[0] + text_bbox[2]) // 2,
                (text_bbox[1] + text_bbox[3]) // 2
            ]
            
            # Calculate distance
            distance = np.sqrt(
                (target_center[0] - text_center[0])**2 + 
                (target_center[1] - text_center[1])**2
            )
            
            if distance <= self.distance_threshold:
                text = text_block.get('text', '').strip()
                if text:
                    nearby_text.append(text)
        
        return nearby_text
    
    def _extract_symbols_from_text(self, text_list: List[str]) -> List[str]:
        """
        Extract emergency lighting symbols from text.
        
        Args:
            text_list: List of text strings
            
        Returns:
            List of extracted symbols
        """
        symbols = []
        
        # Common emergency lighting symbols
        symbol_patterns = [
            r'EL\d+',  # EL501, EL502, etc.
            r'A\d+E?',  # A1, A1E, A2, etc.
            r'E\d+',   # E1, E2, etc.
            r'[A-Z]\d+',  # General symbol patterns
            r'EXIT',
            r'EMERGENCY',
            r'EM'
        ]
        
        for text in text_list:
            text_upper = text.upper()
            
            # Check for exact symbol matches
            for pattern in symbol_patterns:
                matches = re.findall(pattern, text_upper)
                symbols.extend(matches)
            
            # Check for specific emergency patterns
            for fixture_type, pattern in self.emergency_patterns.items():
                if re.search(pattern, text_upper, re.IGNORECASE):
                    # Extract the matched text as a symbol
                    match = re.search(pattern, text_upper, re.IGNORECASE)
                    if match:
                        symbols.append(match.group())
        
        # Remove duplicates and sort
        symbols = list(set(symbols))
        symbols.sort()
        
        return symbols
    
    def _classify_fixture_type(self, text_list: List[str]) -> str:
        """
        Classify the type of emergency lighting fixture based on nearby text.
        
        Args:
            text_list: List of nearby text strings
            
        Returns:
            Classified fixture type
        """
        combined_text = ' '.join(text_list).upper()
        
        # Check for specific patterns
        for fixture_type, pattern in self.emergency_patterns.items():
            if re.search(pattern, combined_text, re.IGNORECASE):
                return fixture_type
        
        # Default classification
        if any('EXIT' in text.upper() for text in text_list):
            return 'emergency_exit'
        elif any('EMERGENCY' in text.upper() for text in text_list):
            return 'emergency_light'
        else:
            return 'unknown'
    
    def get_fixture_description(self, fixture_type: str, symbols: List[str]) -> str:
        """
        Get a description for the fixture based on type and symbols.
        
        Args:
            fixture_type: Type of the fixture
            symbols: List of associated symbols
            
        Returns:
            Description string
        """
        descriptions = {
            'recessed_led': "2' X 4' RECESSED LED LUMINAIRE",
            'wallpack': "WALLPACK WITH BUILT IN PHOTOCELL",
            'emergency_exit': "Exit/Emergency Combo Unit",
            'emergency_light': "Emergency Lighting Fixture",
            'unknown': "Emergency Lighting Fixture"
        }
        
        description = descriptions.get(fixture_type, "Emergency Lighting Fixture")
        
        # Add symbol information if available
        if symbols:
            symbol_str = ', '.join(symbols)
            description += f" ({symbol_str})"
        
        return description
    
    def calculate_spatial_relationships(self, 
                                     fixtures: List[Dict[str, Any]], 
                                     text_blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate spatial relationships between fixtures and text.
        
        Args:
            fixtures: List of detected fixtures
            text_blocks: List of text blocks
            
        Returns:
            Dictionary containing spatial relationship analysis
        """
        relationships = {
            'fixture_text_pairs': [],
            'text_density': {},
            'symbol_distribution': {}
        }
        
        for fixture in fixtures:
            fixture_bbox = fixture.get('bounding_box', [])
            if not fixture_bbox:
                continue
            
            # Find all text within range
            nearby_text = self._find_nearby_text(fixture_bbox, text_blocks)
            
            # Calculate text density around fixture
            text_density = len(nearby_text) / max(1, len(text_blocks))
            
            relationships['fixture_text_pairs'].append({
                'fixture_id': fixture.get('id', 'unknown'),
                'fixture_bbox': fixture_bbox,
                'nearby_text': nearby_text,
                'text_density': text_density
            })
            
            # Track text density
            fixture_type = fixture.get('type', 'unknown')
            if fixture_type not in relationships['text_density']:
                relationships['text_density'][fixture_type] = []
            relationships['text_density'][fixture_type].append(text_density)
        
        # Calculate average text density by fixture type
        for fixture_type, densities in relationships['text_density'].items():
            relationships['text_density'][fixture_type] = {
                'average': np.mean(densities),
                'count': len(densities)
            }
        
        return relationships
    
    def validate_associations(self, 
                            fixtures: List[Dict[str, Any]], 
                            text_blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate the quality of text-fixture associations.
        
        Args:
            fixtures: List of fixtures with associations
            text_blocks: List of all text blocks
            
        Returns:
            Validation results
        """
        validation = {
            'total_fixtures': len(fixtures),
            'fixtures_with_text': 0,
            'fixtures_with_symbols': 0,
            'average_text_per_fixture': 0,
            'symbol_coverage': 0
        }
        
        total_text_count = 0
        fixtures_with_symbols = 0
        
        for fixture in fixtures:
            nearby_text = fixture.get('text_nearby', [])
            symbols = fixture.get('symbols', [])
            
            if nearby_text:
                validation['fixtures_with_text'] += 1
                total_text_count += len(nearby_text)
            
            if symbols:
                validation['fixtures_with_symbols'] += 1
                fixtures_with_symbols += 1
        
        if validation['total_fixtures'] > 0:
            validation['average_text_per_fixture'] = total_text_count / validation['total_fixtures']
            validation['symbol_coverage'] = fixtures_with_symbols / validation['total_fixtures']
        
        return validation 