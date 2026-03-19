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
