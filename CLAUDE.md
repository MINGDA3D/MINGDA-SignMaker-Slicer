# CLAUDE.md - SignMaker Slicer Project Context

## Project Overview
**SignMaker Slicer** - A specialized 3D printing slicer software for illuminated sign letters (发光字).

This project aims to create a software similar to INC-S, which generates G-code for 3D printing sign letter shells with features like:
- Straight edge, beveled edge, and custom edge profiles
- Multi-color/material printing with color change layers
- Step/V-groove features for panel and base plate mounting
- Anti-warping skirts
- Connected letters (连襟字)
- Edge wrapping and outlining (包边/勾边)
- Integrated panel/base plate printing with infill patterns

## Tech Stack
- **Python**: 3.11+
- **GUI Framework**: PySide6
- **Geometry Library**: pyclipper (polygon clipping and offsetting)
- **DXF Parsing**: ezdxf
- **G-code Generation**: Custom implementation

## Directory Structure
```
SignMaker Slicer/
├── CLAUDE.md              # This file - project context
├── requirements.txt       # Python dependencies
├── main.py               # Application entry point
├── src/
│   ├── __init__.py
│   ├── core/             # Core algorithms
│   │   ├── __init__.py
│   │   ├── types.py      # Data types and structures
│   │   ├── dxf_parser.py # DXF file parsing
│   │   ├── path_offset.py # Path offset algorithms
│   │   ├── slice_engine.py # Main slicing engine
│   │   ├── bevel_generator.py # Bevel edge generation
│   │   ├── step_generator.py # Step/V-groove generation
│   │   ├── fill_generator.py # Infill pattern generation
│   │   └── gcode_writer.py # G-code generation
│   ├── ui/               # User interface
│   │   ├── __init__.py
│   │   ├── main_window.py # Main application window
│   │   ├── canvas_2d.py  # 2D preview canvas
│   │   ├── preview_3d.py # 3D preview widget
│   │   └── panels/       # Parameter panels
│   │       ├── __init__.py
│   │       ├── shell_panel.py # Shell parameters
│   │       ├── color_panel.py # Color change settings
│   │       ├── step_panel.py  # Step/V-groove settings
│   │       └── output_panel.py # Output settings
│   └── utils/            # Utility functions
│       ├── __init__.py
│       ├── geometry.py   # Geometry utilities
│       └── constants.py  # Application constants
├── tests/                # Unit tests
│   ├── __init__.py
│   ├── test_dxf_parser.py
│   ├── test_path_offset.py
│   └── test_slice_engine.py
└── INC-S/                # Reference documentation
    ├── INC-S软件完整功能详解.md
    └── INC-S软件功能思维导图.md
```

## Core Classes

### Data Types (`src/core/types.py`)
- `Point`: 2D point (x, y)
- `Path`: List of points forming a contour
- `Layer`: Single print layer with paths
- `SliceParams`: Slicing parameters
- `GCodeParams`: G-code generation parameters

### Core Engines
- `DXFParser`: Parse DXF files, extract contours with color info
- `SliceEngine`: Main slicing engine, orchestrates all operations
- `PathOffset`: Path inward/outward offset using pyclipper
- `BevelGenerator`: Generate beveled edge layers
- `StepGenerator`: Generate step/V-groove features
- `FillGenerator`: Generate infill patterns (panel, grid, base)
- `GCodeWriter`: Generate G-code from layers

## Key Features to Implement

### Phase 1: Core Framework
- [x] Project structure setup
- [ ] DXF parsing (contours + colors)
- [ ] Basic path offset
- [ ] Simple slice engine (straight edge)
- [ ] Basic G-code output

### Phase 2: Edge Types
- [ ] Straight edge (直边)
- [ ] Beveled edge (斜边)
- [ ] Custom edge profiles (异形边)

### Phase 3: Advanced Features
- [ ] Color change layers (换色层)
- [ ] Step/V-groove (台阶V槽)
- [ ] Anti-warping skirt (防翘裙边)
- [ ] Connected letters (连襟字)
- [ ] Edge wrapping/outlining (包边/勾边)

### Phase 4: Panel & Fill
- [ ] Panel infill with patterns
- [ ] Grid infill for resin pouring
- [ ] Base plate infill
- [ ] Panel pattern/decoration support

### Phase 5: UI
- [ ] Main window layout
- [ ] 2D canvas preview
- [ ] Parameter panels
- [ ] 3D preview
- [ ] File operations

## Development Guidelines

### Code Style
- Use type annotations for all functions
- Follow PEP8
- Write docstrings for public methods
- Keep files under 500 lines

### Coordinate System
- Origin at bottom-left
- X+ to the right
- Y+ upward
- Z+ upward (printing direction)
- Units: millimeters (mm)

### Key Parameters Reference (from INC-S)
- Layer height: 0.3mm default
- Wall thickness: 1.2mm (letters < 40cm), 1.3mm (letters >= 40cm)
- Bevel width: 5mm typical
- Base plate thickness: 10mm typical
- Print speed: 30-40mm/s (small), 50-80mm/s (large)
- Nozzle temp: 220-240°C based on wall thickness

## Current Progress
- [x] Project initialization
- [x] Reference documentation collected
- [ ] Core implementation started

## Commands Reference

```bash
# Install dependencies
pip install -r requirements.txt

# Run application
python main.py

# Run tests
pytest tests/
```

---
*Document created: 2026-01-06*
*Last updated: 2026-01-06*
