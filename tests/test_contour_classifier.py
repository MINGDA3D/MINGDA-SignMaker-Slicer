from src.core.contour_classifier import repair_contours
from src.core.types import Contour, Path, PathType, Point


def test_repair_contours_promotes_uncontained_hole_to_contour():
    contour = Contour(
        outer=Path(
            points=[Point(0, 0), Point(100, 0), Point(100, 100), Point(0, 100)],
            path_type=PathType.OUTER,
            is_closed=True,
        ),
        holes=[
            Path(
                points=[Point(150, 150), Point(180, 150), Point(180, 180), Point(150, 180)],
                path_type=PathType.INNER,
                is_closed=True,
            )
        ],
    )

    repaired = repair_contours([contour])

    assert len(repaired) == 2
    assert all(len(item.holes) == 0 for item in repaired)


def test_repair_contours_normalizes_outer_and_hole_orientation():
    contour = Contour(
        outer=Path(
            points=[Point(0, 0), Point(0, 100), Point(100, 100), Point(100, 0)],
            path_type=PathType.OUTER,
            is_closed=True,
        ),
        holes=[
            Path(
                points=[Point(20, 20), Point(20, 80), Point(80, 80), Point(80, 20)],
                path_type=PathType.INNER,
                is_closed=True,
            )
        ],
    )

    repaired = repair_contours([contour])

    assert len(repaired) == 1
    assert repaired[0].outer.area > 0
    assert len(repaired[0].holes) == 1
    assert repaired[0].holes[0].area < 0
