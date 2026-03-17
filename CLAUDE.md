# CLAUDE.md - MINGDA SignMaker Project Context

## Project Overview
**MINGDA SignMaker** - A specialized 3D printing slicer software for illuminated sign letters (发光字).

This project aims to create a software similar to INC-S and SASM3D, which generates G-code for 3D printing sign letter shells with features like:
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
- **UI Mockup Generation**: PIL/Pillow
- **G-code Generation**: Custom implementation

## Directory Structure
```
MINGDA SignMaker/
├── CLAUDE.md              # This file - project context
├── requirements.txt       # Python dependencies
├── main.py               # Application entry point (planned)
├── scripts/              # UI mockup generation scripts
│   ├── generate_ui_home.py        # Home page mockup
│   ├── generate_ui_modern.py      # Project page 2D view mockup
│   ├── generate_ui_project_3d.py  # Project page 3D view mockup
│   ├── generate_ui_params.py      # Parameter panel mockups
│   └── generate_ui_slice_preview.py # Slice preview mockup
├── src/
│   ├── __init__.py
│   ├── core/             # Core algorithms (planned)
│   │   ├── types.py      # Data types and structures
│   │   ├── dxf_parser.py # DXF file parsing
│   │   ├── path_offset.py # Path offset algorithms
│   │   ├── slice_engine.py # Main slicing engine
│   │   ├── bevel_generator.py # Bevel edge generation
│   │   ├── step_generator.py # Step/V-groove generation
│   │   ├── fill_generator.py # Infill pattern generation
│   │   └── gcode_writer.py # G-code generation
│   ├── ui/               # User interface
│   │   ├── theme.py      # Qt stylesheet and color definitions
│   │   ├── main_window.py # Main application window (planned)
│   │   ├── canvas_2d.py  # 2D preview canvas (planned)
│   │   └── preview_3d.py # 3D preview widget (planned)
│   ├── i18n/             # Internationalization (i18n)
│   │   ├── __init__.py   # i18n module exports
│   │   └── translation_manager.py # Translation manager
│   ├── business/         # Business logic layer
│   │   ├── project_manager.py  # Project management
│   │   ├── project_format.py   # .smp file format (ZIP + binary)
│   │   ├── undo_manager.py     # Undo/Redo system
│   │   └── settings_manager.py # Settings persistence
│   └── utils/            # Utility functions (planned)
├── translations/         # Qt translation files (.ts/.qm)
│   ├── signmaker_zh_CN.ts  # Chinese translations
│   ├── signmaker_en_US.ts  # English translations
│   └── signmaker_*.ts      # Other languages (ru, uk, de, fr, es, pt, it, he, ar, ja, ko, tr)
├── tools/                # Development tools
│   ├── generate_ui_mockup.py
│   ├── add_preset_to_ui.py
│   └── update_translations.py  # Translation file management tool
├── docs/                 # Documentation and assets
│   ├── 功能需求清单.md    # Feature requirements (comprehensive)
│   ├── 功能清单.md        # Feature list
│   ├── UI设计规范.md      # UI design specifications
│   ├── 01-需求分析/       # Requirements analysis
│   │   ├── 竞品分析报告.md
│   │   └── 产品需求文档(PRD).md
│   ├── 02-架构设计/       # Architecture design
│   │   ├── 系统架构设计.md
│   │   ├── 核心模块详细设计.md
│   │   ├── 数据流与接口设计.md
│   │   ├── UI架构设计.md
│   │   └── 技术选型说明.md
│   ├── UI/               # Generated UI mockups
│   │   └── *.png
│   └── images/           # Icons and assets
│       ├── MINGDA_logo.png
│       ├── 撤销.png, 重做.png    # Undo/Redo icons
│       ├── 交集.png, 差集.png    # Boolean operation icons
│       ├── move.png, rotate.png, scale.png
│       ├── mirror_x.png, mirror_y.png
│       ├── 组合.png, split_objects_dark.png
│       └── ... (other toolbar icons)
├── tests/                # Unit tests (planned)
└── INC-S/                # Reference documentation
    ├── INC-S软件完整功能详解.md
    └── INC-S软件功能思维导图.md
```

## UI Generation Scripts

The `scripts/` directory contains Python scripts that generate UI mockup images using PIL/Pillow:

| Script | Output | Description |
|--------|--------|-------------|
| `generate_ui_home.py` | `UI_Home.png` | Home page with recent projects and featured cases |
| `generate_ui_modern.py` | `UI_Modern.png` | Project page with 2D view (main editing interface) |
| `generate_ui_project_3d.py` | `UI_Modern_3D.png` | Project page with 3D preview |
| `generate_ui_params.py` | `UI_Params_Part1.png`, `UI_Params_Part2.png` | Parameter panel details |
| `generate_ui_slice_preview.py` | `UI_Slice_Preview.png` | Slice preview mode |

### Running UI Scripts
```bash
cd scripts
python generate_ui_modern.py      # Generate 2D project page
python generate_ui_project_3d.py  # Generate 3D project page
python generate_ui_params.py      # Generate parameter panels
python generate_ui_home.py        # Generate home page
```

## UI Theme System

The theme is defined in `src/ui/theme.py`:
- Dark blue color scheme (深蓝科技风)
- Colors: `bg_primary=#0D1117`, `accent_primary=#58A6FF`
- Fonts: Microsoft YaHei UI, Consolas
- Complete Qt stylesheet for PySide6

## Internationalization (i18n)

The application supports 14 languages using Qt's translation system:

### Supported Languages
| Code | Language |
|------|----------|
| zh_CN | 中文 (Chinese) |
| en_US | English |
| ru_RU | Русский (Russian) |
| uk_UA | Українська (Ukrainian) |
| de_DE | Deutsch (German) |
| fr_FR | Français (French) |
| es_ES | Español (Spanish) |
| pt_BR | Português (Portuguese) |
| it_IT | Italiano (Italian) |
| he_IL | עברית (Hebrew) |
| ar_SA | العربية (Arabic) |
| ja_JP | 日本語 (Japanese) |
| ko_KR | 한국어 (Korean) |
| tr_TR | Türkçe (Turkish) |

### Translation Workflow
```bash
# 1. Initialize empty .ts files
python tools/update_translations.py init

# 2. Extract translatable strings from source code
python tools/update_translations.py extract

# 3. Edit translations using Qt Linguist
python tools/update_translations.py edit en_US

# 4. Compile .ts files to .qm binary files
python tools/update_translations.py compile
```

### Using Translations in Code
```python
# In QWidget subclasses, use self.tr():
self.setWindowTitle(self.tr("MINGDA SignMaker"))
button.setText(self.tr("Save"))

# With format placeholders:
self.tr("Loaded: {file}, {count} contours").format(file=name, count=5)
```

## Version Number Update

发布新版本时，需要更新以下位置的版本号：

| 文件 | 说明 |
|------|------|
| `src/ui/main_window.py` | 关于对话框中的版本显示 (`Version: x.x.x (Development)`) |
| `CHANGELOG.md` | 更新日志，添加新版本条目 |
| `translations/signmaker_*.ts` | 14 个翻译文件中的 source 和 translation 版本字符串 |

### 快速更新步骤
```bash
# 1. 更新 main_window.py 中的版本号（手动修改）
# 2. 更新 CHANGELOG.md（手动添加新版本条目）
# 3. 批量更新所有翻译文件的版本号
sed -i 's/0\.1\.X/0.1.Y/g' translations/signmaker_*.ts
```

## Key Features (from 功能需求清单.md)

### File Operations
- DXF, SVG file import
- Project save/load (.smp format - ZIP container with binary geometry)
- G-code export (.gcode)
- STL, PLT, DXF export (planned)

### Project File Format (.smp)
项目文件使用 ZIP 容器格式，包含：
```
project.smp (ZIP)
├── manifest.json    # 项目元数据（JSON）
├── params.json      # 切片参数（JSON）
└── contours.bin     # 轮廓几何数据（二进制）
```

设计参考：
- [3MF 格式](https://github.com/3MFConsortium/spec_core) - ZIP + XML 容器
- [PrusaSlicer 二进制 G-code](https://help.prusa3d.com/article/binary-g-code_646763)

优点：
- 几何数据使用二进制格式，文件体积小、精度高
- 参数使用 JSON 格式，便于调试和扩展
- ZIP 压缩进一步减小文件大小

### Editing Operations
- Undo/Redo
- Move, Rotate, Scale
- Mirror (X/Y)
- Group/Ungroup (组合/打散)
- Boolean operations: Intersection (交集), Difference (差集)
- Start point editing

### Shell Parameters (字壳工艺)
- Shell height, layer height, wall thickness
- Top parameters (台阶高度, 台阶宽度)
- Bottom parameters (底边高度, 凹槽高度)
- Bevel parameters (斜边宽度, 斜边角度)
- Multi-layer wall settings
- Skirt settings

### Parameter Sections
1. 字壳工艺 - Shell technology
2. 换色层设置 - Color change layers
3. 台阶/V槽 - Steps/V-groove
4. 防翘裙边 - Anti-warping skirt
5. 连襟字 - Connected letters
6. 包边勾边 - Edge wrapping/outlining
7. 面板设置 - Panel settings
8. 底板设置 - Base plate settings
9. 排版设置 - Layout settings
10. 速度设置 - Speed settings
11. 填充 - Infill
12. 机器设置 - Machine settings
13. 输出设置 - Output settings

## Core Classes (Planned)

### Data Types (`src/core/types.py`)
- `Point`: 2D point (x, y)
- `Path`: List of points forming a contour
- `Layer`: Single print layer with paths
- `SliceParams`: Slicing parameters
- `GCodeParams`: G-code generation parameters

### Core Engines
- `DXFParser`: Parse DXF files, extract contours with color info
- `SVGParser`: Parse SVG files using svgpathtools library
- `SliceEngine`: Main slicing engine, orchestrates all operations
- `PathOffset`: Path inward/outward offset using pyclipper
- `BevelGenerator`: Generate beveled edge layers
- `StepGenerator`: Generate step/V-groove features
- `FillGenerator`: Generate infill patterns (panel, grid, base)
- `GCodeWriter`: Generate G-code from layers

## Development Phases

### Phase 1: Core Framework (MVP)
- [x] Project structure setup
- [x] UI mockup generation scripts
- [x] Theme system
- [ ] DXF parsing (contours + colors)
- [ ] Basic path offset
- [ ] Simple slice engine (straight edge)
- [ ] Basic G-code output

### Phase 2: Edge Types
- [x] Straight edge (直边) - 已实现
- [x] Beveled edge (斜边) - 已实现
- [ ] Custom edge profiles (异形边)

### Phase 3: Advanced Features
- [ ] Color change layers (换色层) - 参数已定义
- [ ] Step/V-groove (台阶V槽) - 参数已定义
- [x] Anti-warping skirt (防翘裙边) - 已实现
- [ ] Connected letters (连襟字)
- [ ] Edge wrapping/outlining (包边/勾边)
- [ ] Boolean operations (交集/差集) - PathOffset已支持

### Phase 4: Panel & Fill
- [ ] Panel infill with patterns
- [ ] Grid infill for resin pouring
- [ ] Base plate infill
- [ ] Panel pattern/decoration support
- [x] Bottom face (底面封闭) - 已实现
- [x] Export baseplate DXF (导出底板) - 已实现
- [x] Export panel DXF (导出面板) - 已实现

### Phase 5: UI Implementation
- [x] Main window layout (PySide6)
- [x] 2D canvas preview
- [x] Parameter panels
- [ ] 3D preview
- [x] File operations (DXF导入/G-code导出)
- [x] Internationalization (i18n) - 14 languages supported

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

### Key Parameters Reference
- Layer height: 0.3mm default
- Wall thickness: 1.2mm (letters < 40cm), 1.3mm (letters >= 40cm)
- Bevel width: 5mm typical
- Bevel angle: 75° (from SASM3D)
- Base plate thickness: 10mm typical
- Print speed: 30-40mm/s (small), 50-80mm/s (large)
- Nozzle temp: 220-240°C based on wall thickness

## Current Progress

### Completed (Phase 1 MVP)
- [x] Project structure setup
- [x] Reference documentation collected
- [x] UI mockup generation scripts (home, project 2D/3D, params, preview)
- [x] Theme system (src/ui/theme.py)
- [x] Feature requirements document (功能需求清单.md)
- [x] Architecture design documents
- [x] Core data types (src/core/types.py)
- [x] DXF parsing (src/core/dxf_parser.py)
- [x] SVG parsing (src/core/svg_parser.py) - using svgpathtools library
- [x] Path offset algorithms (src/core/path_offset.py)
- [x] Slice engine - straight/beveled edge (src/core/slice_engine.py)
- [x] G-code generation (src/core/gcode_writer.py)
- [x] DXF export for baseplate/panel (src/core/dxf_writer.py)
- [x] Unit tests (tests/test_core.py) - 42 tests passing
- [x] PySide6 main window (src/ui/main_window.py)
- [x] 2D canvas preview (src/ui/canvas_2d.py)
- [x] Parameter panel (src/ui/param_panel.py)
- [x] Project panel (src/ui/project_panel.py)
- [x] Undo/Redo system (src/business/undo_manager.py) - 21 tests passing
- [x] Project save/load (src/business/project_manager.py) - .smp format, 12 tests passing

### In Progress
- [ ] 3D preview widget
- [ ] Custom edge profiles (异形边)

### Planned
- [ ] Color change layer logic
- [ ] Step/V-groove generation
- [ ] Connected letters (连襟字)
- [ ] Panel/baseplate infill patterns

## Commands Reference

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Generate UI mockups
python scripts/generate_ui_modern.py
python scripts/generate_ui_project_3d.py
python scripts/generate_ui_params.py

# Run application
python main.py

# Run tests
pytest tests/

# Build standalone exe (MUST use virtual environment Python)
.venv\Scripts\python -m PyInstaller --clean --noconfirm "SignMaker Slicer.spec"
# Output: dist/MINGDA SignMaker.exe (single-file executable)
```

## Icon Naming Convention

Icons are stored in `docs/images/` with Chinese names:
- 撤销.png / 重做.png - Undo/Redo
- 交集.png / 差集.png - Intersection/Difference
- 组合.png - Group
- 起始点.png - Start point
- 顺序.png - Print order
- 画面中心.png - Center on canvas

## Known Issues & Solutions

### Issue 1: Step Generation for Internal Holes (2026-03-13)

**Problem:** Internal holes (like the triangle in letter "A") were not generating steps, or steps were misaligned with walls.

**Root Causes:**
1. **Signed Area Loss**: `Path.area` property used `abs()`, losing winding order information needed to distinguish outer contours from holes
2. **Wall Path Extraction Failure**: Attempting to extract wall positions from slice results using centroid distance was unreliable when contours were close together
3. **Edge Transform Mismatch**: Steps used original contours while walls used edge-transformed contours, causing misalignment in beveled/custom edge shells

**Solution:**
1. **Remove `abs()` from area calculation** (`src/core/types.py`):
   ```python
   @property
   def area(self) -> float:
       # Return signed area (CCW=positive, CW=negative)
       return area / 2  # Removed abs()
   ```

2. **Use transformed contours for step generation** (`src/core/stl_writer.py`):
   ```python
   # Calculate transformed contours at step heights
   temp_engine = SliceEngine()
   panel_contours = [temp_engine._apply_edge_profile(c, panel_z, params.shell) for c in contours]
   baseplate_contours = [temp_engine._apply_edge_profile(c, baseplate_z, params.shell) for c in contours]

   # Pass to step builder
   step_mesh = self.step_builder.build(contours, result, params,
                                        panel_contours=panel_contours,
                                        baseplate_contours=baseplate_contours)
   ```

3. **Correct wall inner edge calculation** (`src/core/stl/step_mesh.py`):
   - **Outer contour**: `wall_inner_edge = transformed_contour.outer + offset(-wall_thickness)`
   - **Inner hole**: `wall_inner_edge = transformed_hole` (no offset needed, as offset(-wall_thickness/2) and offset(+wall_thickness/2) cancel out)

**Key Insight:**
- Wall generation: `transformed_contour + offset(-wall_thickness/2) = wall_center_line`
- Wall inner edge (outer): `wall_center_line + offset(-wall_thickness/2) = transformed_contour + offset(-wall_thickness)`
- Wall inner edge (hole): `wall_center_line + offset(+wall_thickness/2) = transformed_hole + offset(0) = transformed_hole`

**Lesson Learned:** When generating features (steps, skirts, etc.) that must align with walls, always use the same edge-transformed contours that the slice engine uses, not the original contours.

### Issue 2: Bottom Face Gap with Internal Holes (2026-03-17)

**Problem:** When generating STL with "Enable Bottom Face" for letters with internal holes (like "R"), there was a visible gap between the outer wall and inner hole wall in the bottom face.

**Root Cause:** Same as Issue 1 - the bottom face builder used original contours while walls were generated from edge-transformed contours (after `_apply_edge_profile()`), causing misalignment.

**Solution:** Pass transformed contours at z=0 to the bottom face builder (`src/core/stl_writer.py`):
```python
# Calculate transformed contours at z=0 (bottom)
bottom_contours = []
for c in contours:
    bc = temp_engine._apply_edge_profile(c, 0, params.shell)
    if bc:
        bottom_contours.append(bc)

bottom_face_mesh = self.bottom_face_builder.build(
    bottom_contours if bottom_contours else contours, params
)
```

**Lesson Learned:** All STL mesh features (walls, steps, bottom face, etc.) must use the same edge-transformed contours to ensure proper alignment.

---
*Document created: 2026-01-06*
*Last updated: 2026-03-17*
*Based on INC-S and SASM3D software analysis*
