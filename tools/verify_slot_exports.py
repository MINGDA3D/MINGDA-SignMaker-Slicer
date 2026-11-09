"""Verify actual slot STL sections against paths parsed from exported G-code.

Run with project paths and --output. Source projects are never modified.
Exported *_slots_only.stl files are diagnostic components, not complete models.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import trimesh
from shapely.geometry import LineString, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import polygonize, unary_union
from trimesh.intersections import mesh_plane

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.business.project_format import load_project, save_project
from src.core.gcode_writer import GCodeWriter
from src.core.path_offset import PathOffset
from src.core.slice_engine import SliceEngine
from src.core.stl.step_mesh import StepMeshBuilder
from src.core.stl_writer import STLWriter
from src.core.types import EdgeType, Layer, LayerPath, PathRole, Point, Project


SLOT_ROLES = {PathRole.STEP, PathRole.V_GROOVE}
NUMBER = re.compile(r"\b([XYZE])(-?\d+(?:\.\d+)?)")
SCENARIO_NAMES = ("panel_flat", "baseplate_flat", "panel_v", "baseplate_v", "screenshot_v")


def validate_output_paths(sources: list[Path], output: Path) -> None:
    """Reject output names that would overwrite any source or another case."""
    source_names = {str(path.resolve()).casefold() for path in sources}
    output_names: set[str] = set()
    for source in sources:
        for scenario in SCENARIO_NAMES:
            destination = output / f"{source.stem}_{scenario}.smp"
            name = str(destination.resolve()).casefold()
            if name in source_names or name in output_names:
                raise ValueError(f"Verification output would overwrite a project: {destination}")
            output_names.add(name)


def digest(path: Path) -> str:
    """Return a source-project checksum."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_slot_gcode(lines: Iterable[str]) -> dict[float, Layer]:
    """Read extruded slot moves independently of the slicer's LayerPath objects."""
    layers: dict[float, Layer] = {}
    position = {"X": 0.0, "Y": 0.0, "Z": 0.0}
    role: PathRole | None = None
    width, height, print_z = 0.0, 0.0, 0.0
    points: list[Point] = []

    def flush() -> None:
        nonlocal points
        if points and role in SLOT_ROLES:
            bottom = round(print_z - height, 6)
            layer = layers.setdefault(bottom, Layer(z_height=bottom, layer_height=height))
            closed = points[0] == points[-1]
            layer.paths.append(LayerPath(
                points=points[:-1] if closed else points,
                role=role, line_width=width, is_closed=closed,
            ))
        points = []

    for line in lines:
        if line.startswith(";TYPE:"):
            flush()
            role = PathRole.__members__.get(line.split(":", 1)[1].strip())
        elif line.startswith(";WIDTH:"):
            width = float(line.split(":", 1)[1])
        elif line.startswith(";HEIGHT:"):
            height = float(line.split(":", 1)[1])
        elif line.startswith(("G0 ", "G1 ")):
            values = {key: float(value) for key, value in NUMBER.findall(line.split(";", 1)[0])}
            extrudes = line.startswith("G1 ") and values.get("E", 0) > 0
            if extrudes and ("X" in values or "Y" in values) and role in SLOT_ROLES:
                if not points:
                    points.append(Point(position["X"], position["Y"]))
                    print_z = values.get("Z", position["Z"])
                points.append(Point(values.get("X", position["X"]), values.get("Y", position["Y"])))
            position.update({key: value for key, value in values.items() if key in position})
    flush()
    return layers


def nominal_print_region(paths: Iterable[LayerPath]) -> BaseGeometry:
    """Sweep exported centerlines using their declared nominal extrusion widths."""
    regions = []
    for path in paths:
        coords = [(point.x, point.y) for point in path.points]
        if path.is_closed:
            coords.append(coords[0])
        regions.append(LineString(coords).buffer(
            path.line_width / 2, join_style=2, mitre_limit=2, cap_style=2,
        ))
    return unary_union(regions)


def section_region(mesh: trimesh.Trimesh, z: float) -> BaseGeometry:
    """Recover filled material from actual STL triangle-plane intersections."""
    segments = mesh_plane(mesh, plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if not len(segments):
        return Polygon()
    segments = np.round(segments[:, :, :2], 6)
    lines = unary_union([LineString(segment) for segment in segments])
    x1, y1 = segments[:, 0, 0], segments[:, 0, 1]
    x2, y2 = segments[:, 1, 0], segments[:, 1, 1]
    cells = []
    for polygon in polygonize(lines):
        point = polygon.representative_point()
        eligible = (y1 > point.y) != (y2 > point.y)
        crossings = x1[eligible] + (point.y - y1[eligible]) * (
            x2[eligible] - x1[eligible]
        ) / (y2[eligible] - y1[eligible])
        if np.count_nonzero(crossings > point.x) % 2:
            cells.append(polygon)
    return unary_union(cells)


def scenarios(project: Project) -> Iterable[tuple[str, Project]]:
    """Enable each slot independently and add the supplied screenshot settings."""
    for target, v_groove in (
        ("panel", False), ("baseplate", False),
        ("panel", True), ("baseplate", True), ("screenshot", True),
    ):
        variant = copy.deepcopy(project)
        params = variant.params
        params.edge_wrap.wrap_enabled = False
        params.edge_wrap.outline_enabled = False
        params.bottom_face.enabled = False
        params.light_slot.enabled = False
        params.top_face.enabled = False
        params.step.enabled = False
        params.step.panel_step_enabled = target != "baseplate"
        params.step.baseplate_step_enabled = target == "baseplate"
        actual_target = "panel" if target == "screenshot" else target
        setattr(params.step, actual_target + "_step_is_v_groove", v_groove)
        if target == "screenshot":
            params.shell.height = 40.2
            params.shell.layer_height = 0.3
            params.shell.line_width = 0.6
            params.shell.wall_count = 3
            params.shell.wall_thickness = 1.8
            params.shell.edge_type = EdgeType.STRAIGHT
            params.step.panel_step_height = 34.2
            params.step.panel_step_width = 1.6
        name = target + ("_v" if v_groove else "_flat")
        variant.meta.name = project.meta.name + "_" + name
        yield name, variant


def verify_variant(name: str, project: Project, output: Path) -> dict[str, Any]:
    """Export and compare slot material at every feature-bearing layer."""
    result = SliceEngine().slice(project.contours, project.params)
    slot_layers = [layer for layer in result.layers if any(
        path.role in SLOT_ROLES for path in layer.paths
    )]
    mesh = StepMeshBuilder(PathOffset()).build(project.contours, result, project.params)
    assert mesh is not None and slot_layers, name
    slot_path = output / f"{name}_slots_only.stl"
    mesh.export(slot_path)
    exported = trimesh.load(str(slot_path), force="mesh", process=False)
    lines = GCodeWriter().generate(result, slice_params=project.params)
    (output / f"{name}.gcode").write_text("\n".join(lines), encoding="utf-8")
    parsed = parse_slot_gcode(lines)
    expected_bottoms = {round(layer.z_height, 6) for layer in slot_layers}
    assert set(parsed) == expected_bottoms, (name, sorted(parsed), sorted(expected_bottoms))
    checks = []
    for bottom, layer in parsed.items():
        expected = nominal_print_region(layer.paths)
        actual = section_region(exported, bottom + layer.layer_height / 2)
        difference = expected.symmetric_difference(actual).area
        mean_edge_error = difference / max(expected.boundary.length, 1)
        bounds_error = max(abs(a - b) for a, b in zip(expected.bounds, actual.bounds))
        boundary_error = expected.boundary.hausdorff_distance(actual.boundary)
        # Binary STL float32 coordinates and three-decimal G-code introduce
        # small export rounding. Missing or shifted ledges exceed this bound.
        assert mean_edge_error < 0.002, (name, bottom, mean_edge_error)
        assert bounds_error < 0.003, (name, bottom, bounds_error)
        assert boundary_error < 0.003, (name, bottom, boundary_error)
        checks.append({
            "bottom_z": bottom, "height": layer.layer_height,
            "symmetric_difference_mm2": difference,
            "mean_boundary_displacement_mm": mean_edge_error,
            "bounds_difference_mm": bounds_error,
            "maximum_boundary_distance_mm": boundary_error,
        })
    expected_z = [min(parsed), max(z + layer.layer_height for z, layer in parsed.items())]
    assert np.allclose(exported.bounds[:, 2], expected_z, atol=0.0001), name
    save_project(project, str(output / f"{name}.smp"))
    if name.endswith("screenshot_v") or name.endswith("e1_baseplate_v"):
        STLWriter().write(result, str(output / f"{name}_full_model.stl"),
                          contours=project.contours, params=project.params)
    return {
        "case": name, "feature_layer_count": len(parsed),
        "slot_mesh_z_bounds": exported.bounds[:, 2].tolist(),
        "maximum_mean_boundary_displacement_mm": max(c["mean_boundary_displacement_mm"] for c in checks),
        "maximum_bounds_difference_mm": max(c["bounds_difference_mm"] for c in checks),
        "maximum_boundary_distance_mm": max(c["maximum_boundary_distance_mm"] for c in checks),
        "layers": checks,
    }


def main() -> None:
    """Verify supplied projects and write a machine-readable result manifest."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("projects", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        validate_output_paths(args.projects, args.output)
    except ValueError as exc:
        parser.error(str(exc))
    args.output.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "method": "Nominal swept STEP/V_GROOVE regions parsed from actual exported G-code versus reloaded binary STL sections, every feature layer.",
        "scenario_note": "Features enabled in copies; other bottom/top features disabled to isolate slots. Screenshot: height40.2/layer0.3/line0.6/wall1.8/top drop6/width1.6 mm.",
        "sources": [], "cases": [],
    }
    for source in args.projects:
        before = digest(source)
        project = load_project(str(source))
        for scenario, variant in scenarios(project):
            name = source.stem + "_" + scenario
            case = verify_variant(name, variant, args.output)
            report["cases"].append(case)
            print(name, "PASS", case["feature_layer_count"], "layers",
                  case["maximum_mean_boundary_displacement_mm"], "mm", flush=True)
        assert before == digest(source)
        report["sources"].append({"path": str(source), "sha256": before, "unchanged": True})
        (args.output / "verification.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8",
        )
    print("All export comparisons passed:", args.output / "verification.json", flush=True)


if __name__ == "__main__":
    main()
