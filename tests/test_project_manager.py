"""
项目管理器和项目格式单元测试
"""

import json
import os
import shutil
import uuid
import zipfile
from contextlib import contextmanager
from pathlib import Path as FilePath

import pytest

from src.business.project_manager import ProjectManager
from src.business.project_format import (
    save_project, load_project, get_project_info,
    FORMAT_VERSION, MANIFEST_FILE, PARAMS_FILE, CONTOURS_FILE,
    ProjectFormatError, _serialize_contours, load_project_contours,
)
from src.core.edge_presets import EdgePresetManager
from src.core.types import (
    Contour, Path, Point, PathType, SliceParams,
    Project, ProjectMeta, EdgeType, BevelDirection,
    get_contour_user_start_point_index, get_path_user_start_point_index,
    set_contour_user_start_point_index, set_path_user_start_point_index,
)


_TEST_TMP_ROOT = FilePath(__file__).resolve().parents[1] / ".tmp_test_project_manager"


@contextmanager
def writable_tempdir():
    """Use a repo-local writable temp directory to avoid sandboxed tempfile ACL issues."""
    _TEST_TMP_ROOT.mkdir(exist_ok=True)
    tmpdir = _TEST_TMP_ROOT / uuid.uuid4().hex
    tmpdir.mkdir()
    try:
        yield str(tmpdir)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


class TestProjectFormat:
    """项目格式测试"""

    def test_save_and_load_empty_project(self):
        """测试保存和加载空项目"""
        project = Project(
            meta=ProjectMeta(name="测试项目", version=FORMAT_VERSION)
        )

        with writable_tempdir() as tmpdir:
            file_path = os.path.join(tmpdir, "test.smp")
            save_project(project, file_path)

            # 验证是 ZIP 文件
            assert zipfile.is_zipfile(file_path)

            # 验证内容
            with zipfile.ZipFile(file_path, 'r') as zf:
                assert MANIFEST_FILE in zf.namelist()
                assert PARAMS_FILE in zf.namelist()
                assert CONTOURS_FILE in zf.namelist()

            # 加载
            loaded = load_project(file_path)
            assert loaded.meta.name == "测试项目"
            assert len(loaded.contours) == 0

    def test_save_and_load_with_contours(self):
        """测试保存和加载包含轮廓的项目"""
        contour = Contour(
            outer=Path(
                points=[Point(0, 0), Point(100, 0), Point(100, 100), Point(0, 100)],
                path_type=PathType.OUTER,
                color=(255, 128, 0)
            ),
            holes=[
                Path(
                    points=[Point(20, 20), Point(80, 20), Point(80, 80), Point(20, 80)],
                    path_type=PathType.INNER,
                    color=(0, 255, 0)
                )
            ],
            name="测试轮廓",
            asset_id="asset-1",
            asset_name="logo.svg",
            group_id="group-1",
            print_order=5
        )
        set_contour_user_start_point_index(contour, 2)
        set_path_user_start_point_index(contour.holes[0], 1)
        contour.holes[0].print_order = 2
        contour.screw_hole_centers = [Point(15, 25), Point(85, 25)]

        project = Project(
            meta=ProjectMeta(name="带轮廓项目"),
            contours=[contour]
        )

        with writable_tempdir() as tmpdir:
            file_path = os.path.join(tmpdir, "test.smp")
            save_project(project, file_path)
            loaded = load_project(file_path)

            assert len(loaded.contours) == 1
            c = loaded.contours[0]
            assert c.name == "测试轮廓"
            assert c.asset_id == "asset-1"
            assert c.asset_name == "logo.svg"
            assert c.group_id == "group-1"
            assert c.start_point_index == 3
            assert get_contour_user_start_point_index(c) == 2
            assert c.print_order == 5
            assert c.outer.print_order == 5
            assert len(c.outer.points) == 4
            assert c.outer.color == (255, 128, 0)
            assert len(c.holes) == 1
            assert c.holes[0].print_order == 2
            assert c.screw_hole_centers == [Point(15, 25), Point(85, 25)]
            hole_start_index = get_path_user_start_point_index(c.holes[0])
            assert hole_start_index is not None
            assert c.holes[0].points[hole_start_index] == Point(80, 20)

    def test_save_and_load_with_params(self):
        """测试保存和加载包含参数的项目"""
        project = Project(meta=ProjectMeta(name="参数测试"))
        project.params.shell.height = 45.5
        project.params.shell.layer_height = 0.25
        project.params.shell.edge_type = EdgeType.BEVELED
        project.params.skirt.enabled = True
        project.params.skirt.width = 6.0
        project.params.skirt.speed = 26.0

        with writable_tempdir() as tmpdir:
            file_path = os.path.join(tmpdir, "test.smp")
            save_project(project, file_path)

            with zipfile.ZipFile(file_path, 'r') as zf:
                params_data = json.loads(zf.read(PARAMS_FILE).decode('utf-8'))
            assert params_data["shell"]["height_layers"] == 182
            assert "height" not in params_data["shell"]

            loaded = load_project(file_path)

            assert loaded.params.shell.height == 45.5
            assert loaded.params.shell.layer_height == 0.25
            assert loaded.params.shell.edge_type == EdgeType.BEVELED
            assert loaded.params.skirt.enabled is True
            assert loaded.params.skirt.width == 6.0
            assert loaded.params.skirt.speed == 26.0

    def test_save_and_load_with_custom_wall_preset_params(self):
        """Test that .smp params preserve the selected custom wall preset."""
        preset_name = "zigzag_2"
        project = Project(meta=ProjectMeta(name="custom-wall-preset"))
        project.params.shell.edge_type = EdgeType.CUSTOM
        project.params.shell.edge_profile = EdgePresetManager().get_preset_profile(preset_name)

        with writable_tempdir() as tmpdir:
            file_path = os.path.join(tmpdir, "custom_wall_preset.smp")
            save_project(project, file_path)

            with zipfile.ZipFile(file_path, 'r') as zf:
                params_data = json.loads(zf.read(PARAMS_FILE).decode('utf-8'))

            saved_profile = params_data["shell"]["edge_profile"]
            assert params_data["shell"]["edge_type"] == "CUSTOM"
            assert saved_profile["profile_type"] == "PRESET"
            assert saved_profile["preset_name"] == preset_name

            loaded = load_project(file_path)

            assert loaded.params.shell.edge_type == EdgeType.CUSTOM
            assert loaded.params.shell.edge_profile is not None
            assert loaded.params.shell.edge_profile.preset_name == preset_name

    def test_file_size_comparison(self):
        """测试文件大小（二进制应该更小）"""
        # 创建一个有较多点的轮廓
        points = [Point(i * 0.1, i * 0.2) for i in range(1000)]
        contour = Contour(outer=Path(points=points, path_type=PathType.OUTER))
        project = Project(
            meta=ProjectMeta(name="大项目"),
            contours=[contour]
        )

        with writable_tempdir() as tmpdir:
            file_path = os.path.join(tmpdir, "test.smp")
            save_project(project, file_path)

            # 检查文件大小（应该被压缩）
            file_size = os.path.getsize(file_path)
            # 1000 点 × 16 字节/点 = 16KB 原始数据
            # 压缩后应该明显小于这个
            assert file_size < 10000  # 应该小于 10KB

    def test_get_project_info(self):
        """测试快速获取项目信息"""
        contours = [
            Contour(outer=Path(points=[Point(0, 0), Point(1, 1)]))
            for _ in range(5)
        ]
        project = Project(
            meta=ProjectMeta(name="信息测试"),
            contours=contours
        )

        with writable_tempdir() as tmpdir:
            file_path = os.path.join(tmpdir, "test.smp")
            save_project(project, file_path)

            info = get_project_info(file_path)
            assert info["name"] == "信息测试"
            assert info["contour_count"] == 5
            assert info["version"] == FORMAT_VERSION

    def test_invalid_file_raises_error(self):
        """测试无效文件抛出错误"""
        with writable_tempdir() as tmpdir:
            file_path = os.path.join(tmpdir, "invalid.smp")

            # 创建一个无效的文件
            with open(file_path, 'w') as f:
                f.write("not a zip file")

            with pytest.raises(ProjectFormatError):
                load_project(file_path)

    def test_precision_preserved(self):
        """测试浮点精度保持"""
        # 使用高精度坐标
        precise_points = [
            Point(0.123456789012345, 0.987654321098765),
            Point(1.111111111111111, 2.222222222222222)
        ]
        contour = Contour(outer=Path(points=precise_points))
        project = Project(meta=ProjectMeta(name="精度测试"), contours=[contour])

        with writable_tempdir() as tmpdir:
            file_path = os.path.join(tmpdir, "test.smp")
            save_project(project, file_path)
            loaded = load_project(file_path)

            p = loaded.contours[0].outer.points[0]
            # float64 应该保持足够的精度
            assert abs(p.x - 0.123456789012345) < 1e-14
            assert abs(p.y - 0.987654321098765) < 1e-14

    def test_load_project_repairs_wrong_hole_assignment(self):
        """测试加载时将不被包含的 hole 提升为独立 contour"""
        contour = Contour(
            outer=Path(
                points=[Point(0, 0), Point(100, 0), Point(100, 100), Point(0, 100)],
                path_type=PathType.OUTER,
            ),
            holes=[
                Path(
                    points=[Point(150, 150), Point(180, 150), Point(180, 180), Point(150, 180)],
                    path_type=PathType.INNER,
                )
            ],
            name="修正测试",
        )

        project = Project(
            meta=ProjectMeta(name="修正测试项目"),
            contours=[contour],
        )

        with writable_tempdir() as tmpdir:
            file_path = os.path.join(tmpdir, "repair.smp")
            save_project(project, file_path)
            loaded = load_project(file_path)

            assert len(loaded.contours) == 2
            assert all(len(c.holes) == 0 for c in loaded.contours)

    def test_load_project_normalizes_loop_orientation(self):
        """测试加载时统一 outer/hole 绕向"""
        contour = Contour(
            outer=Path(
                points=[Point(0, 0), Point(0, 100), Point(100, 100), Point(100, 0)],
                path_type=PathType.OUTER,
            ),
            holes=[
                Path(
                    points=[Point(20, 20), Point(20, 80), Point(80, 80), Point(80, 20)],
                    path_type=PathType.INNER,
                )
            ],
        )

        project = Project(meta=ProjectMeta(name="方向修正"), contours=[contour])

        with writable_tempdir() as tmpdir:
            file_path = os.path.join(tmpdir, "orientation.smp")
            save_project(project, file_path)
            loaded = load_project(file_path)

            assert len(loaded.contours) == 1
            assert loaded.contours[0].outer.area > 0
            assert len(loaded.contours[0].holes) == 1
            assert loaded.contours[0].holes[0].area < 0

    def test_load_project_migrates_legacy_start_point_tokens(self):
        """测试旧格式工程中的起始点索引会迁移到新语义"""
        contour = Contour(
            outer=Path(
                points=[Point(0, 0), Point(100, 0), Point(100, 100), Point(0, 100)],
                path_type=PathType.OUTER,
            ),
            name="legacy-start-point",
            start_point_index=2,
        )
        manifest = {
            "format_version": "4.2",
            "application": "MINGDA SignMaker",
            "created_at": "2026-01-01T00:00:00",
            "modified_at": "2026-01-01T00:00:00",
            "project": {"name": "legacy-project"},
            "statistics": {"contour_count": 1, "total_points": 4},
        }

        with writable_tempdir() as tmpdir:
            file_path = os.path.join(tmpdir, "legacy-start-point.smp")
            with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(
                    MANIFEST_FILE,
                    json.dumps(manifest, ensure_ascii=False, indent=2),
                )
                zf.writestr(PARAMS_FILE, json.dumps({}, ensure_ascii=False, indent=2))
                zf.writestr(CONTOURS_FILE, _serialize_contours([contour]))

            loaded = load_project(file_path)
            assert loaded.contours[0].start_point_index == 3
            assert get_contour_user_start_point_index(loaded.contours[0]) == 2
            assert loaded.contours[0].screw_hole_centers == []

            loaded_contours = load_project_contours(file_path)
            assert loaded_contours[0].start_point_index == 3
            assert get_contour_user_start_point_index(loaded_contours[0]) == 2
            assert loaded_contours[0].screw_hole_centers == []

    def test_load_project_migrates_legacy_contour_print_order_to_loops(self):
        """测试旧格式工程中的 contour 级打印顺序会迁移到 loop 级顺序"""
        contour_a = Contour(
            outer=Path(
                points=[Point(0, 0), Point(80, 0), Point(80, 80), Point(0, 80)],
                path_type=PathType.OUTER,
            ),
            holes=[
                Path(
                    points=[Point(20, 20), Point(60, 20), Point(60, 60), Point(20, 60)],
                    path_type=PathType.INNER,
                )
            ],
            name="legacy-a",
            print_order=10,
        )
        contour_b = Contour(
            outer=Path(
                points=[Point(100, 0), Point(140, 0), Point(140, 40), Point(100, 40)],
                path_type=PathType.OUTER,
            ),
            name="legacy-b",
            print_order=1,
        )
        manifest = {
            "format_version": "4.4",
            "application": "MINGDA SignMaker",
            "created_at": "2026-01-01T00:00:00",
            "modified_at": "2026-01-01T00:00:00",
            "project": {"name": "legacy-print-order"},
            "statistics": {"contour_count": 2, "total_points": 12},
        }

        with writable_tempdir() as tmpdir:
            file_path = os.path.join(tmpdir, "legacy-print-order.smp")
            with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(
                    MANIFEST_FILE,
                    json.dumps(manifest, ensure_ascii=False, indent=2),
                )
                zf.writestr(PARAMS_FILE, json.dumps({}, ensure_ascii=False, indent=2))
                zf.writestr(CONTOURS_FILE, _serialize_contours([contour_a, contour_b]))

            loaded = load_project(file_path)
            assert loaded.contours[1].outer.print_order == 1
            assert loaded.contours[0].outer.print_order == 2
            assert loaded.contours[0].holes[0].print_order == 3

            loaded_contours = load_project_contours(file_path)
            assert loaded_contours[1].outer.print_order == 1
            assert loaded_contours[0].outer.print_order == 2
            assert loaded_contours[0].holes[0].print_order == 3


class TestProjectManager:
    """项目管理器测试"""

    def test_new_project(self):
        """测试创建新项目"""
        pm = ProjectManager()
        project = pm.new_project()

        assert project is not None
        assert project.meta.version == FORMAT_VERSION
        assert len(project.contours) == 0
        assert pm.is_modified is False

    def test_save_and_load_project(self):
        """测试通过 ProjectManager 保存和加载"""
        pm = ProjectManager()
        project = pm.new_project()
        project.meta.name = "管理器测试"

        contour = Contour(
            outer=Path(points=[Point(0, 0), Point(10, 0), Point(10, 10)]),
            name="测试"
        )
        project.contours.append(contour)

        with writable_tempdir() as tmpdir:
            file_path = os.path.join(tmpdir, "test.smp")
            pm.save_project(file_path)

            pm2 = ProjectManager()
            loaded = pm2.open_project(file_path)

            assert loaded.meta.name == "管理器测试"
            assert len(loaded.contours) == 1
            assert loaded.contours[0].name == "测试"

    def test_save_without_path_raises_error(self):
        """测试没有指定路径时保存会抛出错误"""
        pm = ProjectManager()
        pm.new_project()

        with pytest.raises(ValueError):
            pm.save_project()

    def test_save_without_project_raises_error(self):
        """测试没有项目时保存会抛出错误"""
        pm = ProjectManager()

        with pytest.raises(ValueError):
            pm.save_project("/tmp/test.smp")

    def test_modified_flag(self):
        """测试修改标记"""
        pm = ProjectManager()
        pm.new_project()

        assert pm.is_modified is False
        pm.mark_modified()
        assert pm.is_modified is True

        with writable_tempdir() as tmpdir:
            file_path = os.path.join(tmpdir, "test.smp")
            pm.save_project(file_path)
            assert pm.is_modified is False
