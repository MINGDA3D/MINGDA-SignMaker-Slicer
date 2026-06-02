import base64
import shutil
import uuid
from pathlib import Path as FsPath

import pytest

from src.app_info import APP_NAME, get_app_version
from src.business.project_format import load_project, save_project
from src.core.gcode_writer import GCodeValidationError, GCodeWriter
from src.core.slice_engine import SliceEngine
from src.core.types import (
    ColorChangePoint,
    Contour,
    EdgeType,
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
    U_SHAPE_FINE_LAYER_HEIGHT,
    set_contour_user_start_point_index,
    set_path_user_start_point_index,
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


def _rect_contour_with_hole(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    hole_x1: float,
    hole_y1: float,
    hole_x2: float,
    hole_y2: float,
    **kwargs,
) -> Contour:
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
        holes=[
            Path(
                points=[
                    Point(hole_x1, hole_y1),
                    Point(hole_x2, hole_y1),
                    Point(hole_x2, hole_y2),
                    Point(hole_x1, hole_y2),
                ],
                is_closed=True,
            )
        ],
        **kwargs,
    )


def _extract_thumbnail_blocks(lines: list[str]) -> list[dict[str, str | int]]:
    blocks: list[dict[str, str | int]] = []
    index = 0

    while index < len(lines):
        line = lines[index].strip()
        if not line.startswith("; thumbnail begin "):
            index += 1
            continue

        parts = line.split()
        dimensions = parts[3]
        encoded_length = int(parts[4])
        index += 1
        encoded_lines: list[str] = []

        while index < len(lines) and lines[index].strip() != "; thumbnail end":
            encoded_lines.append(lines[index].removeprefix("; ").strip())
            index += 1

        blocks.append(
            {
                "dimensions": dimensions,
                "encoded_length": encoded_length,
                "encoded": "".join(encoded_lines),
            }
        )
        index += 1

    return blocks


def _extract_config_block(lines: list[str]) -> list[str]:
    start = lines.index("; CONFIG_BLOCK_START")
    end = lines.index("; CONFIG_BLOCK_END")
    return lines[start + 1:end]


def _first_print_feedrate_for_role(lines: list[str], role: str) -> int:
    for index, line in enumerate(lines):
        if not line.startswith(f"; {role} path"):
            continue
        for move in lines[index + 1:]:
            if move.startswith("; "):
                break
            if move.startswith("G1 X") and " E" in move and " F" in move:
                return int(move.rsplit(" F", 1)[1])
    raise AssertionError(f"Could not find print move for role {role}.")


@pytest.mark.parametrize(
    ("path_role", "role_name"),
    [
        (PathRole.STEP, "STEP"),
        (PathRole.V_GROOVE, "V_GROOVE"),
    ],
)
def test_gcode_uses_dedicated_step_speed_for_step_related_paths(path_role, role_name):
    params = SliceParams()
    params.shell.layer_height = 0.3
    params.speed.first_layer_speed = 12.0
    params.speed.print_speed = 70.0
    params.step.print_speed = 34.0
    profile = PrinterProfile(start_gcode="G28", end_gcode="M400")

    step_path = _square_path()
    step_path.role = path_role
    wall_path = _square_path()
    result = SliceResult(
        layers=[
            Layer(
                z_height=0.0,
                layer_height=0.3,
                extruder=ExtruderType.EXTRUDER_1,
                color_index=0,
                paths=[step_path, wall_path],
            )
        ],
        total_layers=1,
        total_height=0.3,
        estimated_time=5.0,
        estimated_filament=0.1,
    )

    lines = GCodeWriter(params.gcode).generate(
        result,
        slice_params=params,
        printer_profile=profile,
    )

    layer0_index = lines.index("; Layer 0 at Z=0.30mm")
    layer0_lines = lines[layer0_index + 1:]

    assert _first_print_feedrate_for_role(layer0_lines, role_name) == 2040
    assert _first_print_feedrate_for_role(layer0_lines, "WALL") != 2040


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
    assert lines[0] == "; ========================================"
    assert lines[1] == f"; {APP_NAME} {get_app_version()}"
    assert any(line.startswith("; Date: ") for line in lines[:10])
    assert any(
        line.startswith(f"; generated by OrcaSlicer {APP_NAME} {get_app_version()} on ")
        for line in lines
    )
    assert "; HEADER_BLOCK_START" in lines
    assert "; HEADER_BLOCK_END" in lines
    assert "; CONFIG_BLOCK_START" in lines
    assert "; CONFIG_BLOCK_END" in lines
    assert any(line.startswith("; total layer number: 1") for line in lines)
    assert any(line.startswith("; filament_density: 1.24") for line in lines)
    assert any(line.startswith("; filament_diameter: 1.75") for line in lines)
    assert any(line.startswith("; max_z_height: 0.30") for line in lines)
    config_lines = _extract_config_block(lines)
    config_pairs = [line for line in config_lines if line.startswith("; ") and " = " in line]
    assert len(config_pairs) >= 80
    assert "; layer_height = 0.3" in config_lines
    assert "; first_layer_bed_temperature = 60" in config_lines
    assert "; gcode_flavor = klipper" in config_lines
    assert macro_lines == []


def test_orca_config_block_maps_current_machine_and_print_settings():
    params = SliceParams()
    params.shell.layer_height = 0.4
    params.shell.line_width = 1.1
    params.shell.wall_count = 3
    params.gcode.first_layer_nozzle_temp = 235
    params.gcode.other_layer_nozzle_temp = 220
    params.gcode.first_layer_bed_temp = 65
    params.speed.first_layer_speed = 18.0
    params.speed.print_speed = 54.0
    params.speed.travel_speed = 160.0
    profile = PrinterProfile(
        name="MINGDA Test",
        bed_width=900.0,
        bed_depth=1300.0,
        bed_height=120.0,
        nozzle_diameter=1.0,
        filament_diameter=2.85,
        retract_length=1.6,
        retract_speed=35.0,
        start_gcode="START_PRINT\nG28",
        end_gcode="END_PRINT",
    )

    lines = GCodeWriter(params.gcode).generate(
        _build_result([0.0], layer_height=0.4),
        slice_params=params,
        printer_profile=profile,
    )

    config_lines = _extract_config_block(lines)

    assert lines.index("; CONFIG_BLOCK_START") > lines.index("; --- Print statistics ---")
    assert "; printable_area = 0x0,900x0,900x1300,0x1300" in config_lines
    assert not any(line.startswith("; bed_exclude_area =") for line in config_lines)
    assert "; printable_height = 120" in config_lines
    assert "; layer_height = 0.4" in config_lines
    assert "; initial_layer_print_height = 0.4" in config_lines
    assert "; line_width = 1.1" in config_lines
    assert "; wall_loops = 3" in config_lines
    assert "; nozzle_diameter = 1" in config_lines
    assert "; filament_diameter = 2.85" in config_lines
    assert "; first_layer_temperature = 235" in config_lines
    assert "; first_layer_bed_temperature = 65" in config_lines
    assert "; initial_layer_speed = 18" in config_lines
    assert "; travel_speed = 160" in config_lines
    assert "; retraction_length = 1.6" in config_lines
    assert "; machine_start_gcode = START_PRINT\\nG28" in config_lines


def test_start_and_end_gcode_templates_expand_using_current_print_settings():
    params = SliceParams()
    params.gcode.first_layer_nozzle_temp = 235
    params.gcode.first_layer_bed_temp = 70
    profile = PrinterProfile(
        start_gcode=(
            "START_PRINT EXTRUDER={nozzle_temperature_initial_layer[0]} "
            "BED=[first_layer_bed_temperature] TOOL=[initial_tool]"
        ),
        end_gcode="END_PRINT",
    )

    lines = GCodeWriter(params.gcode).generate(
        _build_result([0.0], layer_height=0.3),
        slice_params=params,
        printer_profile=profile,
    )

    assert "START_PRINT EXTRUDER=235 BED=70 TOOL=0" in lines
    assert "END_PRINT" in lines


def test_temperature_settings_use_first_layer_values_then_switch_before_second_layer():
    params = SliceParams()
    params.gcode.first_layer_nozzle_temp = 230
    params.gcode.other_layer_nozzle_temp = 215
    params.gcode.first_layer_bed_temp = 65
    params.gcode.other_layer_bed_temp = 55
    profile = PrinterProfile(start_gcode="G28", end_gcode="M400")

    lines = GCodeWriter(params.gcode).generate(
        _build_result([0.0, 0.3], layer_height=0.3),
        slice_params=params,
        printer_profile=profile,
    )

    assert "M140 S65 ; Set first layer bed temperature" in lines
    assert "M104 S230 ; Set first layer nozzle temperature" in lines
    assert "M190 S65 ; Wait for first layer bed temperature" in lines
    assert "M109 S230 ; Wait for first layer nozzle temperature" in lines

    transition_index = lines.index("; --- Print settings transition after first layer ---")
    assert lines[transition_index + 1:transition_index + 5] == [
        "M140 S55 ; Set other layers bed temperature",
        "M104 S215 ; Set other layers nozzle temperature",
        "M190 S55 ; Wait for other layers bed temperature",
        "M109 S215 ; Wait for other layers nozzle temperature",
    ]


def test_cooling_settings_use_first_layer_fan_then_switch_before_second_layer():
    params = SliceParams()
    params.gcode.first_layer_fan_percent = 25
    params.gcode.other_layer_fan_percent = 60
    profile = PrinterProfile(start_gcode="G28", end_gcode="M400")

    lines = GCodeWriter(params.gcode).generate(
        _build_result([0.0, 0.3], layer_height=0.3),
        slice_params=params,
        printer_profile=profile,
    )

    start_gcode_index = lines.index("G28")
    first_layer_fan_index = lines.index("M106 S64 ; Set first layer fan speed to 25%")
    transition_index = lines.index("; --- Print settings transition after first layer ---")

    assert first_layer_fan_index > start_gcode_index
    assert lines[transition_index + 1] == "M106 S153 ; Set other layers fan speed to 60%"


def test_slice_emits_skirt_for_height_derived_layers_before_model_paths():
    contour = _rect_contour(0.0, 0.0, 40.0, 20.0)
    params = SliceParams()
    params.shell.height = 0.9
    params.shell.layer_height = 0.3
    params.skirt.enabled = True
    params.skirt.height = 0.6

    result = SliceEngine().slice([contour], params)

    assert len(result.layers) == 3
    assert result.layers[0].paths[0].role == PathRole.SKIRT
    assert result.layers[1].paths[0].role == PathRole.SKIRT
    assert any(path.role == PathRole.WALL for path in result.layers[0].paths)
    assert any(path.role == PathRole.WALL for path in result.layers[1].paths)
    assert all(path.role != PathRole.SKIRT for path in result.layers[2].paths)


def test_gcode_prints_skirt_before_model_on_all_skirt_layers():
    contour = _rect_contour(0.0, 0.0, 40.0, 20.0)
    params = SliceParams()
    params.shell.height = 0.9
    params.shell.layer_height = 0.3
    params.skirt.enabled = True
    params.skirt.height = 0.6
    profile = PrinterProfile(start_gcode="G28", end_gcode="M400")

    result = SliceEngine().slice([contour], params)
    lines = GCodeWriter(params.gcode).generate(
        result,
        slice_params=params,
        printer_profile=profile,
        contours=[contour],
    )

    layer0_index = lines.index("; Layer 0 at Z=0.30mm")
    layer1_index = lines.index("; Layer 1 at Z=0.60mm")
    layer2_index = lines.index("; Layer 2 at Z=0.90mm")

    layer0_paths = [
        line for line in lines[layer0_index + 1:layer1_index] if line.startswith("; ")
    ]
    layer1_paths = [
        line for line in lines[layer1_index + 1:layer2_index] if line.startswith("; ")
    ]
    layer2_paths = [
        line for line in lines[layer2_index + 1:] if line.startswith("; ")
    ]

    assert layer0_paths[0].startswith("; SKIRT path")
    assert layer1_paths[0].startswith("; SKIRT path")
    assert any(line.startswith("; WALL path") for line in layer0_paths)
    assert any(line.startswith("; WALL path") for line in layer1_paths)
    assert not any(line.startswith("; SKIRT path") for line in layer2_paths)


def test_gcode_uses_dedicated_skirt_speed_on_each_skirt_layer():
    contour = _rect_contour(0.0, 0.0, 40.0, 20.0)
    params = SliceParams()
    params.shell.height = 0.9
    params.shell.layer_height = 0.3
    params.speed.first_layer_speed = 12.0
    params.speed.print_speed = 70.0
    params.skirt.enabled = True
    params.skirt.height = 0.6
    params.skirt.speed = 33.0
    profile = PrinterProfile(start_gcode="G28", end_gcode="M400")

    result = SliceEngine().slice([contour], params)
    lines = GCodeWriter(params.gcode).generate(
        result,
        slice_params=params,
        printer_profile=profile,
        contours=[contour],
    )

    layer0_index = lines.index("; Layer 0 at Z=0.30mm")
    layer1_index = lines.index("; Layer 1 at Z=0.60mm")
    layer2_index = lines.index("; Layer 2 at Z=0.90mm")

    layer0_lines = lines[layer0_index + 1:layer1_index]
    layer1_lines = lines[layer1_index + 1:layer2_index]

    assert _first_print_feedrate_for_role(layer0_lines, "SKIRT") == 1980
    assert _first_print_feedrate_for_role(layer1_lines, "SKIRT") == 1980
    assert _first_print_feedrate_for_role(layer0_lines, "WALL") != 1980
    assert _first_print_feedrate_for_role(layer1_lines, "WALL") != 1980


def test_gcode_emits_per_path_width_and_height_for_u_shape_fine_layers():
    contour = _rect_contour(0.0, 0.0, 40.0, 20.0)
    params = SliceParams()
    params.shell.edge_type = EdgeType.U_SHAPED
    params.shell.height = 1.0
    params.shell.layer_height = 0.3
    params.shell.line_width = 0.6
    params.shell.wall_count = 2
    params.shell.u_bottom_layers = 1
    profile = PrinterProfile(start_gcode="G28", end_gcode="M400")

    result = SliceEngine().slice([contour], params)
    lines = GCodeWriter(params.gcode).generate(
        result,
        slice_params=params,
        printer_profile=profile,
        contours=[contour],
    )

    fine_height = U_SHAPE_FINE_LAYER_HEIGHT
    layer0_index = lines.index(f"; Layer 0 at Z={fine_height:.2f}mm")
    wall_type_index = lines.index(";TYPE:WALL", layer0_index)

    assert lines[wall_type_index + 1] == ";WIDTH:0.600"
    assert lines[wall_type_index + 2] == f";HEIGHT:{fine_height:.3f}"
    assert lines[wall_type_index + 3].startswith("; WALL path")
    assert "; layer_height = 0.3" in _extract_config_block(lines)


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


def test_generate_embeds_orca_style_png_thumbnail_blocks_when_contours_are_available():
    params = SliceParams()
    profile = PrinterProfile(start_gcode="G28", end_gcode="M400")
    contours = [_rect_contour(0.0, 0.0, 20.0, 10.0)]

    lines = GCodeWriter(params.gcode).generate(
        _build_result([0.0], layer_height=0.3),
        slice_params=params,
        printer_profile=profile,
        contours=contours,
    )

    assert "; THUMBNAIL_BLOCK_START" in lines
    assert lines[0] == "; ========================================"
    assert lines[1] == f"; {APP_NAME} {get_app_version()}"
    assert lines.index("; THUMBNAIL_BLOCK_START") > 1
    assert lines.index("; THUMBNAIL_BLOCK_START") < lines.index("; HEADER_BLOCK_START")
    assert lines.index("; HEADER_BLOCK_START") < lines.index("; --- Start sequence ---")

    blocks = _extract_thumbnail_blocks(lines)
    assert [block["dimensions"] for block in blocks] == ["32x32", "300x300"]

    for block in blocks:
        encoded = str(block["encoded"])
        assert len(encoded) == int(block["encoded_length"])
        assert base64.b64decode(encoded).startswith(b"\x89PNG\r\n\x1a\n")


def test_generate_skips_thumbnail_blocks_when_contours_are_missing():
    params = SliceParams()
    profile = PrinterProfile(start_gcode="G28", end_gcode="M400")

    lines = GCodeWriter(params.gcode).generate(
        _build_result([0.0], layer_height=0.3),
        slice_params=params,
        printer_profile=profile,
    )

    assert "; THUMBNAIL_BLOCK_START" not in lines
    assert not any("thumbnail begin" in line for line in lines)


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
    )
    set_contour_user_start_point_index(first_contour, 2)

    result = SliceEngine().slice([later_contour, first_contour], params)
    wall_paths = [path for path in result.layers[0].paths if path.role == PathRole.WALL]

    assert len(wall_paths) >= 2
    assert wall_paths[0].points[0].x > 110.0
    assert wall_paths[0].points[0].y > 110.0
    assert wall_paths[1].points[0].x < 20.0


def test_slice_engine_respects_explicit_first_vertex_start_point():
    params = SliceParams()
    params.shell.height = 0.3
    params.shell.layer_height = 0.3
    params.shell.wall_count = 1

    contour = _rect_contour(100.0, 100.0, 120.0, 120.0, name="first")
    set_contour_user_start_point_index(contour, 0)

    result = SliceEngine().slice([contour], params)
    wall_paths = [path for path in result.layers[0].paths if path.role == PathRole.WALL]

    assert wall_paths
    assert wall_paths[0].points[0].x < 110.0
    assert wall_paths[0].points[0].y < 110.0


def test_slice_engine_respects_hole_start_point():
    params = SliceParams()
    params.shell.height = 0.3
    params.shell.layer_height = 0.3
    params.shell.wall_count = 1

    contour = _rect_contour_with_hole(0.0, 0.0, 60.0, 60.0, 20.0, 20.0, 40.0, 40.0, name="hole")
    set_path_user_start_point_index(contour.holes[0], 2)

    result = SliceEngine().slice([contour], params)
    wall_paths = [path for path in result.layers[0].paths if path.role == PathRole.WALL]

    assert len(wall_paths) >= 2
    hole_wall = next(
        path
        for path in wall_paths
        if min(point.x for point in path.points) > 15.0
        and max(point.x for point in path.points) < 45.0
    )
    assert hole_wall.points[0].x > 35.0
    assert hole_wall.points[0].y > 35.0


def test_slice_engine_respects_global_loop_print_order_with_holes():
    params = SliceParams()
    params.shell.height = 0.3
    params.shell.layer_height = 0.3
    params.shell.wall_count = 1

    contour_with_hole = _rect_contour_with_hole(
        0.0,
        0.0,
        60.0,
        60.0,
        20.0,
        20.0,
        40.0,
        40.0,
        name="with-hole",
    )
    later_contour = _rect_contour(100.0, 0.0, 120.0, 20.0, name="later")

    contour_with_hole.holes[0].print_order = 1
    later_contour.outer.print_order = 2
    contour_with_hole.outer.print_order = 3

    result = SliceEngine().slice([contour_with_hole, later_contour], params)
    wall_paths = [path for path in result.layers[0].paths if path.role == PathRole.WALL]

    assert len(wall_paths) >= 3

    def bounds(path):
        xs = [point.x for point in path.points]
        ys = [point.y for point in path.points]
        return min(xs), min(ys), max(xs), max(ys)

    first_bounds = bounds(wall_paths[0])
    second_bounds = bounds(wall_paths[1])
    third_bounds = bounds(wall_paths[2])

    assert first_bounds[0] > 15.0 and first_bounds[2] < 45.0
    assert second_bounds[0] > 95.0 and second_bounds[2] < 125.0
    assert third_bounds[0] < 5.0 and third_bounds[2] > 55.0


def test_slice_engine_keeps_multi_wall_passes_grouped_per_loop():
    params = SliceParams()
    params.shell.height = 0.3
    params.shell.layer_height = 0.3
    params.shell.wall_count = 2

    contour = _rect_contour_with_hole(
        0.0,
        0.0,
        60.0,
        60.0,
        20.0,
        20.0,
        40.0,
        40.0,
        name="with-hole",
    )
    contour.holes[0].print_order = 1
    contour.outer.print_order = 2

    result = SliceEngine().slice([contour], params)
    wall_paths = [path for path in result.layers[0].paths if path.role == PathRole.WALL]

    assert len(wall_paths) == 4

    def is_hole(path) -> bool:
        xs = [point.x for point in path.points]
        return min(xs) > 15.0 and max(xs) < 45.0

    assert is_hole(wall_paths[0]) is True
    assert is_hole(wall_paths[1]) is True
    assert is_hole(wall_paths[2]) is False
    assert is_hole(wall_paths[3]) is False
