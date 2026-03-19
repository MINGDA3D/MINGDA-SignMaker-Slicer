from src.core.path_offset import PathOffset
from src.core.slice_engine import SliceEngine
from src.core.stl.skirt_mesh import SkirtMeshBuilder
from src.core.types import BevelDirection, Contour, EdgeType, Path, Point, SliceParams


def test_skirt_mesh_is_watertight_for_short_connectors():
    contour = Contour(
        outer=Path(
            points=[
                Point(0, 0),
                Point(50, 0),
                Point(50, 12),
                Point(18, 12),
                Point(18, 50),
                Point(0, 50),
            ]
        ),
        holes=[],
    )

    params = SliceParams()
    params.skirt.enabled = True
    params.skirt.height = 0.3

    mesh = SkirtMeshBuilder(PathOffset()).build([contour], params)

    assert mesh is not None
    assert len(mesh.faces) > 0
    assert mesh.is_watertight


def test_skirt_mesh_follows_bottom_contour_for_top_large_bevel():
    contour = Contour(
        outer=Path(
            points=[
                Point(0, 0),
                Point(40, 0),
                Point(40, 20),
                Point(0, 20),
            ]
        ),
        holes=[],
    )

    params = SliceParams()
    params.skirt.enabled = True
    params.skirt.height = 0.3
    params.shell.edge_type = EdgeType.BEVELED
    params.shell.bevel_direction = BevelDirection.TOP_LARGE
    params.shell.bevel_width = 2.0
    params.shell.baseplate_thickness = 1.0
    params.shell.panel_thickness = 1.0
    params.shell.height = 10.0

    bottom_contour = SliceEngine()._apply_edge_profile(contour, 0, params.shell)
    assert bottom_contour is not None

    straight_mesh = SkirtMeshBuilder(PathOffset()).build([contour], params)
    beveled_mesh = SkirtMeshBuilder(PathOffset()).build(
        [bottom_contour], params, source_contours=[bottom_contour]
    )

    assert straight_mesh is not None
    assert beveled_mesh is not None
    assert beveled_mesh.bounds[0][0] > straight_mesh.bounds[0][0]
    assert beveled_mesh.bounds[1][0] < straight_mesh.bounds[1][0]
