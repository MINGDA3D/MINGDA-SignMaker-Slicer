"""Regression coverage for V-groove layers at decimal Z boundaries."""

from __future__ import annotations

import math

import pytest

from src.core.path_offset import PathOffset
from src.core.slice_engine import SliceEngine
from src.core.step_generator import StepGenerator
from src.core.stl.step_mesh import StepMeshBuilder
from src.core.types import (
    Contour,
    Path,
    PathRole,
    Point,
    SliceParams,
    StepConfig,
    StepParams,
)


def _contour() -> Contour:
    """Return a roomy profile so layer selection is independent of offsets."""
    return Contour(outer=Path(points=[
        Point(0.0, 0.0), Point(100.0, 0.0),
        Point(100.0, 100.0), Point(0.0, 100.0),
    ]))


@pytest.mark.parametrize(
    "target, layer_height, shell_height, end, width, start, count",
    [
        ("baseplate", 0.6, 48.0, 3.6, 4.0, 0.0, 6),
        ("baseplate", 0.3, 48.0, 3.6, 1.8, 0.6, 10),
        ("baseplate", 0.3, 48.0, 3.0, 1.8, 0.0, 10),
        ("panel", 0.3, 40.2, 34.2, 1.6, 31.2, 10),
        ("panel", 0.6, 48.0, 38.4, 3.0, 32.4, 10),
        ("baseplate", 0.3, 48.0, 3.6, 1.0, 0.6, 10),
    ],
)
def test_v_groove_ends_at_configured_height_without_extra_layer(
    target: str,
    layer_height: float,
    shell_height: float,
    end: float,
    width: float,
    start: float,
    count: int,
) -> None:
    """Actual slice paths and mesh must stop at the selected upper boundary."""
    contour = _contour()
    params = SliceParams()
    params.shell.height = shell_height
    params.shell.layer_height = layer_height
    params.shell.line_width = 2 * layer_height
    params.shell.wall_count = 3 if layer_height == 0.3 else 2
    params.shell.wall_thickness = params.shell.line_width * params.shell.wall_count
    params.machine.nozzle_diameter = params.shell.line_width
    setattr(params.step, f"{target}_step_enabled", True)
    setattr(params.step, f"{target}_step_is_v_groove", True)
    setattr(params.step, f"{target}_step_height", end)
    setattr(params.step, f"{target}_step_width", width)

    result = SliceEngine().slice([contour], params)
    layers = [layer for layer in result.layers
              if any(path.role == PathRole.V_GROOVE for path in layer.paths)]
    widths = [next(path.line_width for path in layer.paths
                   if path.role == PathRole.V_GROOVE) for layer in layers]

    assert len(layers) == count
    assert [layer.z_height for layer in layers] == pytest.approx(
        [start + index * layer_height for index in range(count)]
    )
    assert widths == pytest.approx([width * (index + 1) / count
                                   for index in range(count)])
    assert layers[-1].z_height + layers[-1].layer_height == pytest.approx(end)

    mesh = StepMeshBuilder(PathOffset()).build([contour], result, params)
    assert mesh is not None
    assert mesh.bounds[:, 2] == pytest.approx([start, end])


@pytest.mark.parametrize("full_width_at_end", [True, False])
def test_custom_v_groove_rejects_neighbor_layers_touching_boundaries(
    full_width_at_end: bool,
) -> None:
    """Either slope orientation must treat its start/end as half-open bounds."""
    generator = StepGenerator()
    config = StepConfig(position=3.6, height=1.2, width=1.8, is_v_groove=True)
    for z in (math.nextafter(3.0, math.inf), math.nextafter(4.8, -math.inf)):
        paths = generator.generate_step_for_layer(
            _contour(), z, 0.6, config, StepParams(),
            full_width_at_end=full_width_at_end,
        )
        assert paths == []


def test_custom_step_planning_and_query_agree_at_rounded_boundaries() -> None:
    """Planning must not select the layer below a nearly rounded start."""
    generator = StepGenerator()
    config = StepConfig(
        position=math.nextafter(3.6, -math.inf), height=1.2,
        width=1.8, is_v_groove=True,
    )
    params = StepParams(enabled=True, steps=[config])
    layer_map = generator.get_step_layers(params, 12.0, 0.6)

    assert sorted(layer_map) == pytest.approx([3.6, 4.2])
    assert not generator.is_step_layer(3.0, 0.6, params)[0]
    assert generator.is_step_layer(6 * 0.6, 0.6, params)[0]
    assert not generator.is_step_layer(4.8, 0.6, params)[0]


@pytest.mark.parametrize(
    "start, height, bottom, top, full_width_at_end",
    [
        (0.0, 3.6, 0.3, math.nextafter(0.6, math.inf), True),
        (3.6, 6.0, math.nextafter(6.6, -math.inf), 6.9, False),
    ],
)
def test_width_ramp_excludes_floating_point_slivers(
    start: float,
    height: float,
    bottom: float,
    top: float,
    full_width_at_end: bool,
) -> None:
    """No virtual extra layer should appear outside the ten-layer ramp."""
    width = StepGenerator()._compute_v_step_width(
        step_width=1.8, step_height=height, step_start=start,
        layer_bottom=bottom, layer_top=top, layer_height=0.3,
        full_width_at_end=full_width_at_end,
    )
    assert width == 0.0


def test_v_groove_still_omits_widths_smaller_than_printable_cutoff() -> None:
    """Tolerance retains an exact 0.1 mm pass without creating a 0.05 mm pass."""
    generator = StepGenerator()
    config = StepConfig(position=0.0, height=3.6, width=0.5, is_v_groove=True)
    paths = generator.generate_step_for_layer(
        _contour(), 0.6, 0.3, config, StepParams(),
    )
    assert paths == []


def test_legacy_bottom_groove_excludes_the_layer_at_its_upper_boundary() -> None:
    """The retained legacy entry point must follow the same Z boundary rule."""
    params = StepParams(bottom_groove_enabled=True, bottom_groove_height=3.6)
    generator = StepGenerator()
    assert generator.generate_bottom_groove(_contour(), 3.0, 0.6, params)
    assert generator.generate_bottom_groove(_contour(), 6 * 0.6, 0.6, params) == []
