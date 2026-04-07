import pytest

from src.core.path_offset import PathOffset
from src.core.skirt_generator import SkirtGenerator
from src.core.types import Contour, Path, Point, SliceParams


def _make_contour_with_hole():
    return Contour(
        outer=Path(
            points=[
                Point(0, 0),
                Point(50, 0),
                Point(50, 50),
                Point(0, 50),
            ]
        ),
        holes=[
            Path(
                points=[
                    Point(15, 15),
                    Point(35, 15),
                    Point(35, 35),
                    Point(15, 35),
                ]
            )
        ],
    )


def _closed_bounds(paths):
    bounds = []
    for path in paths:
        if not path.is_closed:
            continue
        xs = [p.x for p in path.points]
        ys = [p.y for p in path.points]
        bounds.append((round(min(xs), 3), round(min(ys), 3), round(max(xs), 3), round(max(ys), 3)))
    return sorted(bounds)


def _distance_to_rect(point, rect):
    left, bottom, right, top = rect
    if left <= point.x <= right and bottom <= point.y <= top:
        return min(
            point.x - left,
            right - point.x,
            point.y - bottom,
            top - point.y,
        )
    dx = max(left - point.x, 0.0, point.x - right)
    dy = max(bottom - point.y, 0.0, point.y - top)
    return (dx * dx + dy * dy) ** 0.5


def _min_connector_body_gap(paths, rects):
    open_paths = [path for path in paths if not path.is_closed]
    assert open_paths

    min_gap = float("inf")
    for path in open_paths:
        endpoint_dist = min(
            min(_distance_to_rect(point, rect) for rect in rects)
            for point in (path.points[0], path.points[-1])
        )
        min_gap = min(min_gap, endpoint_dist)

    return min_gap


def test_skirt_generator_supports_outer_inner_independently():
    contour = _make_contour_with_hole()
    params = SliceParams().skirt
    params.enabled = True

    generator = SkirtGenerator()
    paths = generator.generate_skirt_clipped(
        contour=contour,
        all_contours=[contour],
        params=params,
        wall_thickness=1.2,
        path_offset=PathOffset(),
    )

    assert _closed_bounds(paths) == [
        (-5.0, -5.0, 55.0, 55.0),
        (20.0, 20.0, 30.0, 30.0),
    ]

    params.outer_enabled = False
    params.inner_enabled = True

    paths = generator.generate_skirt_clipped(
        contour=contour,
        all_contours=[contour],
        params=params,
        wall_thickness=1.2,
        path_offset=PathOffset(),
    )

    assert _closed_bounds(paths) == [
        (5.0, 5.0, 45.0, 45.0),
        (10.0, 10.0, 40.0, 40.0),
    ]

    params.outer_enabled = True
    params.inner_enabled = True

    paths = generator.generate_skirt_clipped(
        contour=contour,
        all_contours=[contour],
        params=params,
        wall_thickness=1.2,
        path_offset=PathOffset(),
    )

    assert len(_closed_bounds(paths)) == 4

    params.outer_enabled = False
    params.inner_enabled = False

    paths = generator.generate_skirt_clipped(
        contour=contour,
        all_contours=[contour],
        params=params,
        wall_thickness=1.2,
        path_offset=PathOffset(),
    )

    assert paths == []


def test_skirt_generator_keeps_ring_bounds_when_wall_gap_changes():
    contour = Contour(
        outer=Path(
            points=[
                Point(0.0, 0.0),
                Point(40.0, 0.0),
                Point(40.0, 20.0),
                Point(0.0, 20.0),
            ]
        ),
        holes=[],
    )
    params = SliceParams().skirt
    params.enabled = True
    params.offset = 1.0

    generator = SkirtGenerator()
    outer_paths = generator.generate_skirt_clipped(
        contour=contour,
        all_contours=[contour],
        params=params,
        wall_thickness=1.2,
        path_offset=PathOffset(),
    )

    assert _closed_bounds(outer_paths) == [
        (-5.0, -5.0, 45.0, 25.0),
    ]
    assert _min_connector_body_gap(outer_paths, [(0.0, 0.0, 40.0, 20.0)]) == pytest.approx(1.0)

    params.outer_enabled = False
    params.inner_enabled = True

    inner_paths = generator.generate_skirt_clipped(
        contour=contour,
        all_contours=[contour],
        params=params,
        wall_thickness=1.2,
        path_offset=PathOffset(),
    )

    assert _closed_bounds(inner_paths) == [
        (5.0, 5.0, 35.0, 15.0),
    ]
    assert _min_connector_body_gap(inner_paths, [(0.0, 0.0, 40.0, 20.0)]) == pytest.approx(1.0)


def test_skirt_generator_clamps_wall_gap_to_one_mm():
    contour = Contour(
        outer=Path(
            points=[
                Point(0.0, 0.0),
                Point(40.0, 0.0),
                Point(40.0, 20.0),
                Point(0.0, 20.0),
            ]
        ),
        holes=[],
    )
    params = SliceParams().skirt
    params.enabled = True
    params.offset = 5.0

    paths = SkirtGenerator().generate_skirt_clipped(
        contour=contour,
        all_contours=[contour],
        params=params,
        wall_thickness=1.2,
        path_offset=PathOffset(),
    )

    assert _min_connector_body_gap(paths, [(0.0, 0.0, 40.0, 20.0)]) == pytest.approx(1.0)


def test_skirt_generator_uses_explicit_path_line_width():
    contour = Contour(
        outer=Path(
            points=[
                Point(0.0, 0.0),
                Point(40.0, 0.0),
                Point(40.0, 20.0),
                Point(0.0, 20.0),
            ]
        ),
        holes=[],
    )
    params = SliceParams().skirt
    params.enabled = True
    params.height = 0.3

    paths = SkirtGenerator().generate_skirt_clipped(
        contour=contour,
        all_contours=[contour],
        params=params,
        wall_thickness=1.2,
        path_offset=PathOffset(),
        path_line_width=0.8,
    )

    assert paths
    assert all(path.line_width == pytest.approx(0.8) for path in paths)


def test_skirt_generator_connector_start_point_matches_wall_gap():
    contour = Contour(
        outer=Path(
            points=[
                Point(0.0, 0.0),
                Point(40.0, 0.0),
                Point(40.0, 20.0),
                Point(0.0, 20.0),
            ]
        ),
        holes=[],
    )
    params = SliceParams().skirt
    params.enabled = True
    params.offset = 0.1

    paths = SkirtGenerator().generate_skirt_clipped(
        contour=contour,
        all_contours=[contour],
        params=params,
        wall_thickness=1.2,
        path_offset=PathOffset(),
        path_line_width=0.8,
    )

    assert _min_connector_body_gap(paths, [(0.0, 0.0, 40.0, 20.0)]) == pytest.approx(0.1)
