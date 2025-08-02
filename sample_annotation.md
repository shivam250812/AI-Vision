# Sample Annotation Screenshot

## Emergency Lighting Detection Example

The system detects emergency lighting fixtures by identifying **shaded rectangular areas** and associating them with nearby symbols and text.

### Visual Representation

```
┌─────────────────────────────────────────────────┐
│  ELECTRICAL BLUEPRINT - EMERGENCY LIGHTING    │
│                                               │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐      │
│  │   A1    │  │   A1E   │  │    W    │      │
│  │  [███]  │  │  [███]  │  │  [███]  │      │
│  │ EMERG   │  │ EXIT    │  │ WALL    │      │
│  └─────────┘  └─────────┘  └─────────┘      │
│                                               │
│  ┌─────────┐  ┌─────────┐                    │
│  │  EL501  │  │  EL502  │                    │
│  │  [███]  │  │  [███]  │                    │
│  │ EMERG   │  │ EMERG   │                    │
│  └─────────┘  └─────────┘                    │
│                                               │
│  Legend:                                      │
│  [███] = Shaded rectangular area             │
│  A1 = 2x4 LED Emergency Fixture              │
│  A1E = Exit/Emergency Combo Unit             │
│  W = Wall-Mounted Emergency LED              │
│  EL501/EL502 = Emergency Lighting Fixtures   │
└─────────────────────────────────────────────────┘
```

### Detection Output

```json
{
  "emergency_fixtures": [
    {
      "symbol": "A1",
      "bounding_box": [100, 150, 200, 200],
      "text_nearby": ["EM", "Exit", "Unswitched"],
      "source_sheet": "E2.4",
      "confidence": 0.95,
      "type": "recessed_led",
      "description": "2' X 4' RECESSED LED LUMINAIRE"
    },
    {
      "symbol": "A1E", 
      "bounding_box": [300, 180, 400, 230],
      "text_nearby": ["EXIT", "Emergency"],
      "source_sheet": "E2.4",
      "confidence": 0.92,
      "type": "emergency_exit",
      "description": "Exit/Emergency Combo Unit"
    },
    {
      "symbol": "W",
      "bounding_box": [500, 150, 600, 200],
      "text_nearby": ["WALLPACK", "PHOTOCELL"],
      "source_sheet": "E2.4",
      "confidence": 0.88,
      "type": "wallpack",
      "description": "WALLPACK WITH BUILT IN PHOTOCELL"
    },
    {
      "symbol": "EL501",
      "bounding_box": [100, 350, 200, 400],
      "text_nearby": ["EMERGENCY", "LIGHTING"],
      "source_sheet": "E2.4",
      "confidence": 0.85,
      "type": "emergency_light",
      "description": "Emergency Lighting Fixture"
    },
    {
      "symbol": "EL502",
      "bounding_box": [300, 350, 400, 400],
      "text_nearby": ["EMERGENCY", "LIGHTING"],
      "source_sheet": "E2.4",
      "confidence": 0.87,
      "type": "emergency_light",
      "description": "Emergency Lighting Fixture"
    }
  ]
}
```

### Grouped Summary Output

```json
{
  "summary": {
    "Lights01": { 
      "count": 1, 
      "description": "2' X 4' RECESSED LED LUMINAIRE",
      "symbols": ["A1"]
    },
    "Lights02": { 
      "count": 1, 
      "description": "Exit/Emergency Combo Unit",
      "symbols": ["A1E"]
    },
    "Lights03": { 
      "count": 1, 
      "description": "WALLPACK WITH BUILT IN PHOTOCELL",
      "symbols": ["W"]
    },
    "Lights04": { 
      "count": 2, 
      "description": "Emergency Lighting Fixture",
      "symbols": ["EL501", "EL502"]
    }
  }
}
```

### Key Detection Features

1. **Shaded Area Detection**: Identifies rectangular shaded regions representing emergency lighting fixtures
2. **Symbol Association**: Links fixtures with nearby symbols (A1, A1E, W, EL501, etc.)
3. **Text Proximity**: Associates text within spatial thresholds (150 pixels)
4. **Confidence Scoring**: Provides confidence scores for each detection
5. **Type Classification**: Classifies fixtures into categories (recessed_led, wallpack, emergency_exit, etc.)

### Detection Methods

- **Adaptive Thresholding**: Detects shaded areas using adaptive thresholding
- **Otsu Thresholding**: Alternative method for area detection
- **Edge Detection**: Uses Canny edge detection for boundary identification
- **OCR Processing**: Extracts text and symbols using Tesseract
- **LLM Classification**: Groups and classifies using AI

### Spatial Relationship Analysis

The system calculates spatial relationships between:
- Detected fixtures and nearby text
- Text density around fixtures
- Symbol distribution patterns
- Confidence validation metrics 