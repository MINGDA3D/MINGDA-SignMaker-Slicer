"""
项目文件格式模块

.smp (SignMaker Project) 文件格式：
- ZIP 容器，包含：
  - manifest.json: 项目元数据
  - params.json: 切片参数
  - contours.bin: 轮廓几何数据（二进制）

设计参考：
- 3MF 格式 (ZIP + XML)
- PrusaSlicer 项目格式
"""

import json
import struct
import zipfile
import io
from datetime import datetime
from typing import Optional, List, BinaryIO
from pathlib import Path

from src.core.contour_classifier import repair_contours
from src.core.types import (
    Project, ProjectMeta, Contour, SliceParams,
    Point, Path as ContourPath, PathType,
    deserialize_params,
    migrate_legacy_contour_start_point_index,
    serialize_params,
)
from src.business.printer_profile_manager import (
    serialize_printer_profile,
    deserialize_printer_profile,
)


# 格式常量
FORMAT_VERSION = "4.4"
MANIFEST_FILE = "manifest.json"
PARAMS_FILE = "params.json"
CONTOURS_FILE = "contours.bin"
PREVIEW_FILE = "preview.png"
PRINTER_PROFILE_FILE = "printer_profile.json"

# 二进制格式
BINARY_MAGIC = b'SMPC'  # SignMaker Project Contours
BINARY_VERSION = 4


class ProjectFormatError(Exception):
    """项目文件格式错误"""
    pass


def save_project(
    project: Project,
    file_path: str,
    preview_png: Optional[bytes] = None,
) -> None:
    """保存项目到 .smp 文件

    Args:
        project: 项目对象
        file_path: 保存路径
    """
    with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. manifest.json - 元数据
        manifest = {
            "format_version": FORMAT_VERSION,
            "application": "MINGDA SignMaker",
            "created_at": project.meta.created_at or datetime.now().isoformat(),
            "modified_at": datetime.now().isoformat(),
            "project": {
                "name": project.meta.name,
                "author": project.meta.author,
                "description": project.meta.description
            },
            "statistics": {
                "contour_count": len(project.contours),
                "total_points": sum(
                    len(c.outer.points) + sum(len(h.points) for h in c.holes)
                    for c in project.contours
                )
            }
        }
        zf.writestr(MANIFEST_FILE, json.dumps(manifest, ensure_ascii=False, indent=2))

        # 2. params.json - 切片参数
        params_data = serialize_params(project.params)
        zf.writestr(PARAMS_FILE, json.dumps(params_data, ensure_ascii=False, indent=2))

        # 3. contours.bin - 几何数据（二进制）
        contours_bin = _serialize_contours(project.contours)
        zf.writestr(CONTOURS_FILE, contours_bin)

        if project.active_printer_profile_id or project.printer_profile_snapshot is not None:
            profile_payload = {
                "active_profile_id": project.active_printer_profile_id,
                "profile": (
                    serialize_printer_profile(project.printer_profile_snapshot)
                    if project.printer_profile_snapshot is not None
                    else None
                ),
            }
            zf.writestr(
                PRINTER_PROFILE_FILE,
                json.dumps(profile_payload, ensure_ascii=False, indent=2),
            )

        if preview_png:
            zf.writestr(PREVIEW_FILE, preview_png)


def load_project(file_path: str) -> Project:
    """从 .smp 文件加载项目

    Args:
        file_path: 文件路径

    Returns:
        项目对象

    Raises:
        ProjectFormatError: 文件格式错误
    """
    if not zipfile.is_zipfile(file_path):
        raise ProjectFormatError(f"Not a valid .smp file: {file_path}")

    with zipfile.ZipFile(file_path, 'r') as zf:
        # 检查必需文件
        names = zf.namelist()
        if MANIFEST_FILE not in names:
            raise ProjectFormatError(f"Missing {MANIFEST_FILE}")
        if CONTOURS_FILE not in names:
            raise ProjectFormatError(f"Missing {CONTOURS_FILE}")

        # 1. 读取 manifest
        manifest = json.loads(zf.read(MANIFEST_FILE).decode('utf-8'))

        # 2. 读取参数
        params = SliceParams()
        if PARAMS_FILE in names:
            params_data = json.loads(zf.read(PARAMS_FILE).decode('utf-8'))
            params = deserialize_params(params_data)

        active_printer_profile_id = ""
        printer_profile_snapshot = None
        if PRINTER_PROFILE_FILE in names:
            profile_payload = json.loads(zf.read(PRINTER_PROFILE_FILE).decode("utf-8"))
            active_printer_profile_id = profile_payload.get("active_profile_id", "")
            profile_data = profile_payload.get("profile")
            if profile_data:
                printer_profile_snapshot = deserialize_printer_profile(profile_data)

        # 3. 读取轮廓
        project_format_version = manifest.get("format_version", FORMAT_VERSION)
        contours_bin = zf.read(CONTOURS_FILE)
        contours = repair_contours(_deserialize_contours(contours_bin))
        _migrate_legacy_contour_start_points(contours, project_format_version)

        # 构建项目
        project_info = manifest.get('project', {})
        meta = ProjectMeta(
            name=project_info.get('name', ''),
            author=project_info.get('author', ''),
            description=project_info.get('description', ''),
            created_at=manifest.get('created_at', ''),
            modified_at=manifest.get('modified_at', ''),
            version=manifest.get('format_version', FORMAT_VERSION)
        )

        return Project(
            meta=meta,
            contours=contours,
            params=params,
            active_printer_profile_id=active_printer_profile_id,
            printer_profile_snapshot=printer_profile_snapshot,
        )


def _serialize_contours(contours: List[Contour]) -> bytes:
    """序列化轮廓为二进制

    格式:
        Header: magic(4) + version(4) + count(4)
        Each Contour:
            name_len(2) + name(var) + start_idx(4) + print_order(4)
            asset_id_len(2) + asset_id(var) + asset_name_len(2) + asset_name(var)
            group_len(2) + group(var)
            outer_path + hole_count(4) + holes[]
            cf_count(4) + connected_frames[]
            pattern_count(4) + patterns[]
        Each Path:
            type(1) + color(3) + closed(1) + start_idx(4) + point_count(4)
            points[] as (x: f64, y: f64)
    """
    buf = io.BytesIO()

    # Header
    buf.write(BINARY_MAGIC)
    buf.write(struct.pack('<II', BINARY_VERSION, len(contours)))

    for contour in contours:
        # Name (UTF-8)
        name_bytes = contour.name.encode('utf-8')
        buf.write(struct.pack('<H', len(name_bytes)))
        buf.write(name_bytes)

        # Properties
        buf.write(struct.pack('<ii', contour.start_point_index, contour.print_order))
        asset_id_bytes = contour.asset_id.encode('utf-8')
        buf.write(struct.pack('<H', len(asset_id_bytes)))
        buf.write(asset_id_bytes)
        asset_name_bytes = contour.asset_name.encode('utf-8')
        buf.write(struct.pack('<H', len(asset_name_bytes)))
        buf.write(asset_name_bytes)
        group_bytes = contour.group_id.encode('utf-8')
        buf.write(struct.pack('<H', len(group_bytes)))
        buf.write(group_bytes)

        # Outer path
        _write_path(buf, contour.outer)

        # Holes
        buf.write(struct.pack('<I', len(contour.holes)))
        for hole in contour.holes:
            _write_path(buf, hole)

        # Connected frames
        buf.write(struct.pack('<I', len(contour.connected_frames)))
        for cf in contour.connected_frames:
            _write_path(buf, cf)

        # Patterns
        buf.write(struct.pack('<I', len(contour.patterns)))
        for pattern in contour.patterns:
            _write_path(buf, pattern)

    return buf.getvalue()


def _write_path(buf: BinaryIO, path: ContourPath) -> None:
    """写入路径"""
    # Type mapping
    type_map = {
        PathType.OUTER: 0, PathType.INNER: 1, PathType.CONNECTED: 2,
        PathType.HOLE: 3, PathType.PATTERN: 4
    }
    buf.write(struct.pack('<B', type_map.get(path.path_type, 0)))

    # Color RGB
    buf.write(struct.pack('<BBB', *path.color[:3]))

    # Is closed
    buf.write(struct.pack('<?', path.is_closed))

    # Start point token
    buf.write(struct.pack('<i', path.start_point_index))

    # Points (float64 for precision)
    buf.write(struct.pack('<I', len(path.points)))
    for p in path.points:
        buf.write(struct.pack('<dd', p.x, p.y))


def _deserialize_contours(data: bytes) -> List[Contour]:
    """反序列化轮廓"""
    buf = io.BytesIO(data)

    # Header
    magic = buf.read(4)
    if magic != BINARY_MAGIC:
        raise ProjectFormatError(f"Invalid magic: {magic}")

    version, count = struct.unpack('<II', buf.read(8))
    if version > BINARY_VERSION:
        raise ProjectFormatError(f"Unsupported version: {version}")

    contours = []
    for _ in range(count):
        # Name
        name_len = struct.unpack('<H', buf.read(2))[0]
        name = buf.read(name_len).decode('utf-8')

        # Properties
        start_idx, print_order = struct.unpack('<ii', buf.read(8))
        asset_id = ""
        asset_name = ""
        if version >= 3:
            asset_id_len = struct.unpack('<H', buf.read(2))[0]
            asset_id = buf.read(asset_id_len).decode('utf-8')
            asset_name_len = struct.unpack('<H', buf.read(2))[0]
            asset_name = buf.read(asset_name_len).decode('utf-8')
        group_id = ""
        if version >= 2:
            group_len = struct.unpack('<H', buf.read(2))[0]
            group_id = buf.read(group_len).decode('utf-8')

        # Outer
        outer = _read_path(buf, version)

        # Holes
        hole_count = struct.unpack('<I', buf.read(4))[0]
        holes = [_read_path(buf, version) for _ in range(hole_count)]

        # Connected frames
        cf_count = struct.unpack('<I', buf.read(4))[0]
        connected_frames = [_read_path(buf, version) for _ in range(cf_count)]

        # Patterns
        pattern_count = struct.unpack('<I', buf.read(4))[0]
        patterns = [_read_path(buf, version) for _ in range(pattern_count)]

        contours.append(Contour(
            outer=outer, holes=holes,
            connected_frames=connected_frames, patterns=patterns,
            name=name, asset_id=asset_id, asset_name=asset_name, group_id=group_id,
            start_point_index=start_idx, print_order=print_order
        ))

    return contours


def _parse_format_version(version: str) -> tuple[int, ...]:
    parts = []
    for raw_part in str(version or "").split("."):
        try:
            parts.append(int(raw_part))
        except ValueError:
            break
    return tuple(parts) if parts else (0,)


def _migrate_legacy_contour_start_points(
    contours: List[Contour],
    project_format_version: str,
) -> None:
    """Upgrade raw start-point storage used before 4.3."""
    if _parse_format_version(project_format_version) >= _parse_format_version("4.3"):
        return

    for contour in contours:
        migrate_legacy_contour_start_point_index(contour)


def _read_path(buf: BinaryIO, version: int) -> ContourPath:
    """读取路径"""
    type_map = {
        0: PathType.OUTER, 1: PathType.INNER, 2: PathType.CONNECTED,
        3: PathType.HOLE, 4: PathType.PATTERN
    }

    path_type = type_map.get(struct.unpack('<B', buf.read(1))[0], PathType.OUTER)
    color = struct.unpack('<BBB', buf.read(3))
    is_closed = struct.unpack('<?', buf.read(1))[0]
    start_point_index = struct.unpack('<i', buf.read(4))[0] if version >= 4 else 0

    point_count = struct.unpack('<I', buf.read(4))[0]
    points = []
    for _ in range(point_count):
        x, y = struct.unpack('<dd', buf.read(16))
        points.append(Point(x, y))

    return ContourPath(
        points=points,
        path_type=path_type,
        color=color,
        is_closed=is_closed,
        start_point_index=start_point_index,
    )


def get_project_info(file_path: str) -> dict:
    """快速获取项目信息（不加载几何数据）"""
    info = {"path": file_path, "size": Path(file_path).stat().st_size}

    with zipfile.ZipFile(file_path, 'r') as zf:
        manifest = json.loads(zf.read(MANIFEST_FILE).decode('utf-8'))
        info["version"] = manifest.get("format_version")
        info["name"] = manifest.get("project", {}).get("name", "")
        info["contour_count"] = manifest.get("statistics", {}).get("contour_count", 0)
        info["created_at"] = manifest.get("created_at")
        info["modified_at"] = manifest.get("modified_at")

    return info


def load_project_preview_png(file_path: str) -> Optional[bytes]:
    """Load the embedded preview PNG from a project file if it exists."""
    with zipfile.ZipFile(file_path, 'r') as zf:
        if PREVIEW_FILE not in zf.namelist():
            return None
        return zf.read(PREVIEW_FILE)


def load_project_contours(file_path: str) -> List[Contour]:
    """Load only contour geometry from a project file."""
    with zipfile.ZipFile(file_path, 'r') as zf:
        names = zf.namelist()
        if MANIFEST_FILE not in names:
            raise ProjectFormatError(f"Missing {MANIFEST_FILE}")
        if CONTOURS_FILE not in names:
            raise ProjectFormatError(f"Missing {CONTOURS_FILE}")
        manifest = json.loads(zf.read(MANIFEST_FILE).decode("utf-8"))
        contours_bin = zf.read(CONTOURS_FILE)
        contours = repair_contours(_deserialize_contours(contours_bin))
        _migrate_legacy_contour_start_points(
            contours,
            manifest.get("format_version", FORMAT_VERSION),
        )
        return contours
