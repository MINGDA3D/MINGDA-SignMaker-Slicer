"""Step meshes must depict the same material paths that G-code exports."""

from __future__ import annotations

import math
import re

import pytest
from shapely.geometry import LineString, Point as ShapelyPoint, box
from shapely.ops import unary_union

from src.core.gcode_writer import GCodeWriter
from src.core.path_offset import PathOffset
from src.core.slice_engine import SliceEngine
from src.core.stl.step_mesh import StepMeshBuilder
from src.core.toolpath_geometry import path_footprint, union_path_footprints
from src.core.types import (
    Contour, Layer, LayerPath, Path, PathRole, Point,
    SliceParams, SliceResult, StepConfig,
)


def _rectangle(x: float = 10.0, y: float = 10.0) -> Contour:
    return Contour(outer=Path(points=[
        Point(x, y), Point(x + 40, y), Point(x + 40, y + 40), Point(x, y + 40),
    ]))


def _params() -> SliceParams:
    params = SliceParams()
    params.shell.height = 6.0
    params.shell.layer_height = 0.3
    params.shell.line_width = 0.6
    params.shell.wall_count = 1
    params.shell.wall_thickness = 0.6
    params.skirt.enabled = False
    return params


@pytest.mark.parametrize("role", [PathRole.STEP, PathRole.V_GROOVE])
def test_mesh_uses_actual_layer_and_paths_even_without_feature_flags(role: PathRole) -> None:
    """Custom or precomputed paths need neither contour reconstruction nor extra Z."""
    path = LayerPath(points=[Point(10, 10), Point(20, 10)], role=role,
                     line_width=1.2, is_closed=False)
    result = SliceResult(layers=[Layer(z_height=2.1, layer_height=0.3, paths=[path])])
    params = _params()
    mesh = StepMeshBuilder(PathOffset()).build([_rectangle(100, 100)], result, params)

    assert mesh is not None
    assert mesh.bounds[0] == pytest.approx((10.0, 9.4, 2.1))
    assert mesh.bounds[1] == pytest.approx((20.0, 10.6, 2.4))
    assert abs(mesh.volume) == pytest.approx(10 * 1.2 * 0.3)


def test_enabled_parameters_do_not_invent_steps_absent_from_slice_result() -> None:
    """A collapsed or omitted path must remain absent in exported geometry."""
    params = _params()
    params.step.panel_step_enabled = True
    params.step.panel_step_height = 3.0
    params.step.panel_step_width = 2.0
    mesh = StepMeshBuilder(PathOffset()).build([_rectangle()], SliceResult(), params)
    assert mesh is None


def test_step_and_v_groove_overlap_is_unioned_once_in_the_same_layer() -> None:
    """Mixed custom/platform structures must not create duplicate overlapping solids."""
    paths = [
        LayerPath(points=[Point(10, y), Point(20, y)], role=role,
                  line_width=2.0, is_closed=False)
        for y, role in ((10.0, PathRole.STEP), (11.0, PathRole.V_GROOVE))
    ]
    layer = Layer(z_height=1.0, layer_height=0.3, paths=paths)
    mesh = StepMeshBuilder(PathOffset()).build([], SliceResult(layers=[layer]), _params())
    assert mesh is not None
    assert abs(mesh.volume) == pytest.approx(10 * 3 * 0.3)


def test_custom_flat_step_uses_its_single_print_layer() -> None:
    """Custom steps were omitted when mesh generation only read panel/baseplate flags."""
    params = _params()
    params.step.enabled = True
    params.step.steps = [StepConfig(enabled=True, position=1.2, width=1.4, height=0.0)]
    contour = _rectangle()
    result = SliceEngine().slice([contour], params)
    step_layers = [layer for layer in result.layers if any(path.role == PathRole.STEP for path in layer.paths)]
    assert len(step_layers) == 1
    layer = step_layers[0]
    mesh = StepMeshBuilder(PathOffset()).build([contour], result, params)
    assert mesh is not None
    assert mesh.bounds[0][2] == pytest.approx(layer.z_height)
    assert mesh.bounds[1][2] == pytest.approx(layer.z_height + layer.layer_height)


def test_split_v_groove_does_not_fill_a_bridge_without_a_print_path() -> None:
    """A narrow dumbbell neck disappears from the groove centerline before the wall."""
    contour = Contour(outer=Path(points=[Point(x, y) for x, y in [
        (0, 0), (20, 0), (20, 9), (40, 9), (40, 0), (60, 0),
        (60, 20), (40, 20), (40, 11), (20, 11), (20, 20), (0, 20),
    ]]))
    params = _params()
    params.step.baseplate_step_enabled = True
    params.step.baseplate_step_is_v_groove = True
    params.step.baseplate_step_height = 3.0
    params.step.baseplate_step_width = 1.6
    result = SliceEngine().slice([contour], params)
    layers = [layer for layer in result.layers if any(path.role == PathRole.V_GROOVE for path in layer.paths)]
    layer = layers[-1]
    grooves = [path for path in layer.paths if path.role == PathRole.V_GROOVE]
    assert len(grooves) == 2
    builder = StepMeshBuilder(PathOffset())
    geometry = builder._build_v_groove_layer_geometry(layer, params)
    assert geometry is not None
    assert not geometry.intersects(box(29, 9.5, 31, 10.5))
    assert not geometry.covers(ShapelyPoint(30, 10))
    mesh = builder.build([contour], SliceResult(layers=[layer]), params)
    assert mesh is not None
    assert abs(mesh.volume) == pytest.approx(geometry.area * layer.layer_height, abs=1e-6)


def _gcode_regions(lines: list[str]) -> list[object]:
    """Parse actual exported XY and WIDTH values into independent swept regions."""
    regions = []
    coordinates: list[tuple[float, float]] = []
    width = 0.0

    def finish() -> None:
        if len(coordinates) >= 2:
            regions.append(LineString(coordinates).buffer(
                width / 2.0, cap_style=2, join_style=2, mitre_limit=2.0,
            ))

    for line in lines:
        if line.startswith(";TYPE:"):
            finish()
            coordinates = []
        elif line.startswith(";WIDTH:"):
            width = float(line.split(":", 1)[1])
        elif line.startswith(("G0 X", "G1 X")):
            values = dict(re.findall(r"([XY])(-?[0-9.]+)", line))
            coordinates.append((float(values["X"]), float(values["Y"])))
    finish()
    return regions


def test_mesh_matches_serialized_gcode_with_coordinate_and_width_rounding() -> None:
    """Compare exports at actual 0.001 mm precision, including a non-grid width."""
    paths = [
        LayerPath(points=[Point(10.00049, 10.00049), Point(35.00049, 10.00049),
                          Point(35.00049, 28.00049), Point(10.00049, 28.00049)],
                  role=PathRole.STEP, line_width=0.5818181818),
        LayerPath(points=[Point(45.00049, 10.00049), Point(65.00049, 10.00049),
                          Point(65.00049, 28.00049), Point(45.00049, 28.00049)],
                  role=PathRole.V_GROOVE, line_width=1.60049),
    ]
    layer = Layer(z_height=2.1, layer_height=0.3, paths=paths)
    result = SliceResult(layers=[layer], total_layers=1, total_height=2.4)
    lines = GCodeWriter().generate(result, slice_params=_params())
    exported = unary_union(_gcode_regions(lines))
    expected = union_path_footprints(paths)
    assert expected is not None
    # XY rounds by <=0.0005 per axis; WIDTH by <=0.0005. Allow the
    # resulting corner displacement and its perimeter-scaled area difference.
    tolerance = 0.002
    assert exported.boundary.hausdorff_distance(expected.boundary) < tolerance
    assert exported.symmetric_difference(expected).area < expected.length * tolerance
    mesh = StepMeshBuilder(PathOffset()).build([], result, _params())
    assert mesh is not None
    assert abs(mesh.volume) == pytest.approx(expected.area * layer.layer_height, abs=1e-6)
    assert any(line.startswith("G0 Z2.400 ") for line in lines)
    assert mesh.bounds[1][2] == pytest.approx(2.4)


def test_footprints_skip_invalid_paths_and_preserve_open_endpoints() -> None:
    """Malformed paths must not create long stray bands or phantom end caps."""
    invalid = [
        LayerPath(points=[Point(0, 0), Point(1, 0)], line_width=0.0, is_closed=False),
        LayerPath(points=[Point(0, 0), Point(math.nan, 0)], is_closed=False),
        LayerPath(points=[Point(1, 1)] * 4),
    ]
    assert union_path_footprints(invalid) is None
    valid = LayerPath(points=[Point(1, 1), Point(1, 1), Point(5, 1)],
                      line_width=2.0, is_closed=False)
    region = path_footprint(valid)
    assert region is not None
    assert region.equals(box(1, 0, 5, 2))
