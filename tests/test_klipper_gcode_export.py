import shutil
import uuid
from pathlib import Path as FsPath

import pytest

from src.business.project_format import load_project, save_project
from src.core.gcode_writer import GCodeValidationError, GCodeWriter
from src.core.slice_engine import SliceEngine
from src.core.types import (
    ColorChangePoint,
    Contour,
    ExtruderType,
    Layer,
    LayerPath,
    Path,
    PathRole,
    Point,
    PrinterProfile,
    Project,
    ProjectMeta,
    SliceParams,
    SliceResult,
)


@pytest.fixture
def workspace_tmp_dir():
    tmpdir = FsPath.cwd() / f".tmp_pytest_klipper_export_{uuid.uuid4().hex}"
    tmpdir.mkdir(parents=True, exist_ok=True)
    try:
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _square_path() -> LayerPath:
    return LayerPath(
        points=[
            Point(0.0, 0.0),
            Point(10.0, 0.0),
            Point(10.0, 10.0),
            Point(0.0, 10.0),
        ],
        role=PathRole.WALL,
        extruder=ExtruderType.EXTRUDER_1,
        line_width=0.6,
        is_closed=True,
    )


def _build_result(layer_z_values: list[float], layer_height: float = 10.0) -> SliceResult:
    layers = [
        Layer(
            z_height=z_value,
            layer_height=layer_height,
            extruder=ExtruderType.EXTRUDER_1,
            color_index=0,
            paths=[_square_path()],
        )
        for z_value in layer_z_values
    ]
    return SliceResult(
        layers=layers,
        total_layers=len(layers),
        total_height=len(layers) * layer_height,
        estimated_time=120.0,
        estimated_filament=1.2,
    )


def _rect_contour(x1: float, y1: float, x2: float, y2: float, **kwargs) -> Contour:
    return Contour(
        outer=Path(
            points=[
                Point(x1, y1),
                Point(x2, y1),
                Point(x2, y2),
                Point(x1, y2),
            ],
            is_closed=True,
        ),
        **kwargs,
    )


def test_single_color_gcode_uses_relative_extrusion_without_tool_macros():
    params = SliceParams()
    profile = PrinterProfile(start_gcode="G28", end_gcode="M400")

    lines = GCodeWriter(params.gcode).generate(
        _build_result([0.0], layer_height=0.3),
        slice_params=params,
        printer_profile=profile,
    )

    macro_lines = [
        line.strip()
        for line in lines
        if line.strip().startswith("T") and line.strip()[1:].isdigit()
    ]

    assert any(line.startswith("M83") for line in lines)
    assert any("Start sequence" in line for line in lines)
    assert any(line.strip() == "G28" for line in lines)
    assert macro_lines == []


def test_manual_color_change_macros_follow_selected_order_and_restore_state():
    params = SliceParams()
    params.shell.height = 40.0
    params.color.enabled = True
    params.color.change_points = [
        ColorChangePoint(height_mm=10.0, macro_index=3),
        ColorChangePoint(height_mm=20.0, macro_index=1),
        ColorChangePoint(height_mm=30.0, macro_index=4),
    ]
    profile = PrinterProfile(
        start_gcode="G28",
        end_gcode="M400",
        color_change_command_template="T{index}",
    )

    lines = GCodeWriter(params.gcode).generate(
        _build_result([0.0, 10.0, 20.0, 30.0]),
        slice_params=params,
        printer_profile=profile,
    )

    macro_indices = [
        index
        for index, line in enumerate(lines)
        if line.strip().startswith("T") and line.strip()[1:].isdigit()
    ]
    macro_lines = [lines[index].strip() for index in macro_indices]

    assert macro_lines == ["T3", "T1", "T4"]
    assert "T0" not in macro_lines
    for index in macro_indices:
        assert lines[index + 1:index + 4] == [
            "G90 ; Absolute positioning",
            "M83 ; Relative extrusion",
            "G92 E0 ; Reset extruder",
        ]


def test_color_change_command_template_expands_selected_macro_index():
    params = SliceParams()
    params.shell.height = 20.0
    params.color.enabled = True
    params.color.change_points = [ColorChangePoint(height_mm=10.0, macro_index=7)]
    profile = PrinterProfile(color_change_command_template="CHANGE_{index}")

    lines = GCodeWriter(params.gcode).generate(
        _build_result([0.0, 10.0]),
        slice_params=params,
        printer_profile=profile,
    )

    assert "CHANGE_7" in lines


@pytest.mark.parametrize(
    ("change_points", "template", "message"),
    [
        (
            [],
            "T{index}",
            "no change points",
        ),
        (
            [ColorChangePoint(height_mm=20.0, macro_index=1), ColorChangePoint(height_mm=10.0, macro_index=3)],
            "T{index}",
            "strictly increasing",
        ),
        (
            [ColorChangePoint(height_mm=40.0, macro_index=1)],
            "T{index}",
            "shell height range",
        ),
        (
            [ColorChangePoint(height_mm=10.0, macro_index=-1)],
            "T{index}",
            "non-negative integer",
        ),
        (
            [ColorChangePoint(height_mm=10.0, macro_index=1)],
            "T_INDEX",
            "{index}",
        ),
    ],
)
def test_validate_rejects_invalid_manual_color_change_configuration(change_points, template, message):
    params = SliceParams()
    params.shell.height = 40.0
    params.color.enabled = True
    params.color.change_points = change_points
    profile = PrinterProfile(color_change_command_template=template)

    with pytest.raises(GCodeValidationError, match=message):
        GCodeWriter.validate(_build_result([0.0], layer_height=0.3), params, profile)


def test_project_roundtrip_preserves_printer_profile_snapshot(workspace_tmp_dir):
    file_path = workspace_tmp_dir / "klipper_profile_roundtrip.smp"
    snapshot = PrinterProfile(
        id="profile-123",
        name="Klipper Snapshot",
        bed_width=920.0,
        bed_depth=1280.0,
        start_gcode="G28\nT0",
        end_gcode="M400",
        color_change_command_template="MACRO_{index}",
    )
    project = Project(
        meta=ProjectMeta(name="Klipper Project"),
        params=SliceParams(),
        active_printer_profile_id="profile-123",
        printer_profile_snapshot=snapshot,
    )

    save_project(project, str(file_path))
    loaded = load_project(str(file_path))

    assert loaded.active_printer_profile_id == "profile-123"
    assert loaded.printer_profile_snapshot is not None
    assert loaded.printer_profile_snapshot.name == "Klipper Snapshot"
    assert loaded.printer_profile_snapshot.bed_width == pytest.approx(920.0)
    assert loaded.printer_profile_snapshot.start_gcode == "G28\nT0"
    assert loaded.printer_profile_snapshot.color_change_command_template == "MACRO_{index}"


def test_slice_engine_respects_print_order_and_user_selected_start_point():
    params = SliceParams()
    params.shell.height = 0.3
    params.shell.layer_height = 0.3
    params.shell.wall_count = 1

    later_contour = _rect_contour(0.0, 0.0, 20.0, 20.0, name="later", print_order=10)
    first_contour = _rect_contour(
        100.0,
        100.0,
        120.0,
        120.0,
        name="first",
        print_order=1,
        start_point_index=2,
    )

    result = SliceEngine().slice([later_contour, first_contour], params)
    wall_paths = [path for path in result.layers[0].paths if path.role == PathRole.WALL]

    assert len(wall_paths) >= 2
    assert wall_paths[0].points[0].x > 110.0
    assert wall_paths[0].points[0].y > 110.0
    assert wall_paths[1].points[0].x < 20.0
