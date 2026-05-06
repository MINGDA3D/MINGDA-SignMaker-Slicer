import io

import ezdxf
import pytest

from src.core.dxf_parser import DXFParser


def _to_dxf_bytes(doc) -> bytes:
    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue().encode("utf-8")


@pytest.fixture
def parser():
    return DXFParser()


def test_parse_nested_polylines_is_direction_independent(parser):
    for inner_points in (
        [(20, 20), (80, 20), (80, 80), (20, 80)],
        [(20, 20), (20, 80), (80, 80), (80, 20)],
    ):
        doc = ezdxf.new("R2010")
        msp = doc.modelspace()
        msp.add_lwpolyline([(0, 0), (100, 0), (100, 100), (0, 100)], close=True)
        msp.add_lwpolyline(inner_points, close=True)

        contours = parser.parse_from_bytes(_to_dxf_bytes(doc))

        assert len(contours) == 1
        assert len(contours[0].holes) == 1


def test_parse_three_level_nested_polylines(parser):
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (100, 0), (100, 100), (0, 100)], close=True)
    msp.add_lwpolyline([(20, 20), (80, 20), (80, 80), (20, 80)], close=True)
    msp.add_lwpolyline([(30, 30), (30, 70), (70, 70), (70, 30)], close=True)

    contours = parser.parse_from_bytes(_to_dxf_bytes(doc))

    assert len(contours) == 2
    assert [len(contour.holes) for contour in contours] == [1, 0]


def test_parse_hatch_prefers_explicit_shell_loops(parser):
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    hatch = msp.add_hatch(color=7)
    hatch.paths.add_polyline_path(
        [(0, 0), (100, 0), (100, 100), (0, 100)],
        is_closed=True,
        flags=DXFParser.HATCH_FLAG_EXTERNAL,
    )
    hatch.paths.add_polyline_path(
        [(20, 20), (80, 20), (80, 80), (20, 80)],
        is_closed=True,
        flags=0,
    )
    hatch.paths.add_polyline_path(
        [(30, 30), (30, 70), (70, 70), (70, 30)],
        is_closed=True,
        flags=DXFParser.HATCH_FLAG_OUTERMOST,
    )

    contours = parser.parse_from_bytes(_to_dxf_bytes(doc))

    assert len(contours) == 2
    assert [len(contour.holes) for contour in contours] == [1, 0]


def test_parse_connected_line_segments_as_closed_contour(parser):
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_line((0, 0), (10, 0))
    msp.add_line((10, 10), (0, 10))
    msp.add_line((10, 0), (10, 10))
    msp.add_line((0, 10), (0, 0))

    contours = parser.parse_from_bytes(_to_dxf_bytes(doc))

    assert len(contours) == 1
    assert contours[0].outer.bounds == pytest.approx((0, 0, 10, 10))


def test_parse_nested_line_segment_loops_as_hole(parser):
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    for start, end in [
        ((0, 0), (100, 0)),
        ((100, 0), (100, 100)),
        ((100, 100), (0, 100)),
        ((0, 100), (0, 0)),
        ((25, 25), (75, 25)),
        ((75, 75), (25, 75)),
        ((75, 25), (75, 75)),
        ((25, 75), (25, 25)),
    ]:
        msp.add_line(start, end)

    contours = parser.parse_from_bytes(_to_dxf_bytes(doc))

    assert len(contours) == 1
    assert len(contours[0].holes) == 1


def test_parse_open_line_segments_are_ignored(parser):
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_line((0, 0), (10, 0))
    msp.add_line((10, 0), (10, 10))
    msp.add_line((10, 10), (0, 10))

    contours = parser.parse_from_bytes(_to_dxf_bytes(doc))

    assert contours == []
