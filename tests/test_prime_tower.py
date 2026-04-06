import pytest
import trimesh
import shutil
import uuid
from pathlib import Path as FsPath

from src.core.gcode_writer import GCodeWriter
from src.core.prime_tower import PrimeTowerValidationError
from src.core.slice_engine import SliceEngine
from src.core.stl_writer import STLWriter
from src.core.types import (
    ColorChangePoint,
    Contour,
    Path,
    PathRole,
    Point,
    PrinterProfile,
    SliceParams,
)
from src.ui.preview_3d import Preview3DWidget


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def workspace_tmp_dir():
    tmpdir = FsPath.cwd() / f".tmp_prime_tower_{uuid.uuid4().hex}"
    tmpdir.mkdir(parents=True, exist_ok=True)
    try:
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _rect_contour(x1: float, y1: float, x2: float, y2: float) -> Contour:
    return Contour(
        outer=Path(
            points=[
                Point(x1, y1),
                Point(x2, y1),
                Point(x2, y2),
                Point(x1, y2),
            ],
            is_closed=True,
        )
    )


def _rect_contour_with_hole(
    outer_x1: float,
    outer_y1: float,
    outer_x2: float,
    outer_y2: float,
    hole_x1: float,
    hole_y1: float,
    hole_x2: float,
    hole_y2: float,
) -> Contour:
    return Contour(
        outer=Path(
            points=[
                Point(outer_x1, outer_y1),
                Point(outer_x2, outer_y1),
                Point(outer_x2, outer_y2),
                Point(outer_x1, outer_y2),
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
    )


def _base_params() -> SliceParams:
    params = SliceParams()
    params.machine.bed_width = 200.0
    params.machine.bed_depth = 200.0
    params.shell.height = 1.0
    params.shell.layer_height = 0.5
    params.prime_tower.enabled = True
    params.prime_tower.center_x = 150.0
    params.prime_tower.center_y = 150.0
    params.prime_tower.width = 20.0
    params.prime_tower.depth = 20.0
    params.prime_tower.infill_density_percent = 20
    return params


def test_slice_adds_prime_tower_paths_before_model_paths_on_each_layer():
    contour = _rect_contour(10.0, 10.0, 40.0, 40.0)
    params = _base_params()

    result = SliceEngine().slice([contour], params)

    assert len(result.layers) == 2
    for layer in result.layers:
        prime_paths = [path for path in layer.paths if path.role == PathRole.PRIME_TOWER]
        assert prime_paths
        assert layer.paths[0].role == PathRole.PRIME_TOWER
        assert any(path.role == PathRole.WALL for path in layer.paths)


def test_higher_prime_tower_density_generates_more_infill_paths():
    contour = _rect_contour(10.0, 10.0, 40.0, 40.0)
    low_density = _base_params()
    high_density = _base_params()
    high_density.prime_tower.infill_density_percent = 60

    low_result = SliceEngine().slice([contour], low_density)
    high_result = SliceEngine().slice([contour], high_density)

    def _path_length(path) -> float:
        return sum(
            ((path.points[index].x - path.points[index - 1].x) ** 2 +
             (path.points[index].y - path.points[index - 1].y) ** 2) ** 0.5
            for index in range(1, len(path.points))
        )

    low_infill_length = sum(
        _path_length(path)
        for path in low_result.layers[0].paths
        if path.role == PathRole.PRIME_TOWER and not path.is_closed
    )
    high_infill_length = sum(
        _path_length(path)
        for path in high_result.layers[0].paths
        if path.role == PathRole.PRIME_TOWER and not path.is_closed
    )

    assert high_infill_length > low_infill_length


def test_prime_tower_validation_rejects_overlap_with_model_geometry():
    contour = _rect_contour(10.0, 10.0, 40.0, 40.0)
    params = _base_params()
    params.prime_tower.center_x = 25.0
    params.prime_tower.center_y = 25.0
    params.prime_tower.width = 40.0
    params.prime_tower.depth = 40.0

    with pytest.raises(PrimeTowerValidationError, match="overlaps existing printable geometry"):
        SliceEngine().validate_prime_tower_placement([contour], params)


def test_prime_tower_2d_validation_allows_prime_tower_inside_contour_hole():
    contour = _rect_contour_with_hole(0.0, 0.0, 100.0, 100.0, 30.0, 30.0, 70.0, 70.0)
    params = _base_params()
    params.prime_tower.center_x = 50.0
    params.prime_tower.center_y = 50.0
    params.prime_tower.width = 20.0
    params.prime_tower.depth = 20.0

    SliceEngine().validate_prime_tower_2d_placement([contour], params)


def test_prime_tower_2d_validation_rejects_touching_model_boundary():
    contour = _rect_contour(0.0, 0.0, 40.0, 40.0)
    params = _base_params()
    params.prime_tower.center_x = 50.0
    params.prime_tower.center_y = 20.0
    params.prime_tower.width = 20.0
    params.prime_tower.depth = 20.0

    with pytest.raises(PrimeTowerValidationError, match="overlaps existing printable geometry"):
        SliceEngine().validate_prime_tower_2d_placement([contour], params)


def test_gcode_prints_prime_tower_before_model_after_color_change():
    contour = _rect_contour(10.0, 10.0, 40.0, 40.0)
    params = _base_params()
    params.color.enabled = True
    params.color.change_points = [ColorChangePoint(height_mm=0.5, macro_index=1)]
    profile = PrinterProfile(
        start_gcode="G28",
        end_gcode="M400",
        color_change_command_template="T{index}",
    )

    result = SliceEngine().slice([contour], params)
    lines = GCodeWriter(params.gcode).generate(
        result,
        slice_params=params,
        printer_profile=profile,
    )

    change_index = lines.index("; --- Color change at 0.50mm ---")
    prime_index = next(
        index
        for index, line in enumerate(lines[change_index + 1 :], start=change_index + 1)
        if line.startswith("; PRIME_TOWER path")
    )
    wall_index = next(
        index
        for index, line in enumerate(lines[change_index + 1 :], start=change_index + 1)
        if line.startswith("; WALL path")
    )

    assert prime_index < wall_index


def test_preview_builds_prime_tower_mesh_part(qapp):
    contour = _rect_contour(10.0, 10.0, 40.0, 40.0)
    params = _base_params()
    result = SliceEngine().slice([contour], params)

    parts = Preview3DWidget.build_mesh_parts_for_result(result, [contour], params)
    part_map = {part.name: part for part in parts}

    assert "prime_tower" in part_map
    tower_vertices = part_map["prime_tower"].vertices
    assert tower_vertices[:, 0].min() == pytest.approx(140.0, abs=1e-6)
    assert tower_vertices[:, 0].max() == pytest.approx(160.0, abs=1e-6)
    assert tower_vertices[:, 1].min() == pytest.approx(140.0, abs=1e-6)
    assert tower_vertices[:, 1].max() == pytest.approx(160.0, abs=1e-6)
    assert tower_vertices[:, 2].min() == pytest.approx(0.0, abs=1e-6)
    assert tower_vertices[:, 2].max() == pytest.approx(1.0, abs=1e-6)


def test_stl_export_includes_prime_tower_geometry(workspace_tmp_dir):
    contour = _rect_contour(10.0, 10.0, 40.0, 40.0)
    params_without_tower = _base_params()
    params_without_tower.prime_tower.enabled = False
    params_with_tower = _base_params()
    engine = SliceEngine()
    writer = STLWriter(wall_thickness=0.6)

    without_tower_result = engine.slice([contour], params_without_tower)
    with_tower_result = engine.slice([contour], params_with_tower)

    without_tower_path = workspace_tmp_dir / "without_prime_tower.stl"
    with_tower_path = workspace_tmp_dir / "with_prime_tower.stl"
    writer.write(without_tower_result, str(without_tower_path), True, [contour], params_without_tower)
    writer.write(with_tower_result, str(with_tower_path), True, [contour], params_with_tower)

    without_tower_mesh = trimesh.load(str(without_tower_path), force="mesh")
    with_tower_mesh = trimesh.load(str(with_tower_path), force="mesh")

    assert with_tower_mesh.bounds[1][0] > without_tower_mesh.bounds[1][0] + 50.0
    assert with_tower_mesh.bounds[1][1] > without_tower_mesh.bounds[1][1] + 50.0
