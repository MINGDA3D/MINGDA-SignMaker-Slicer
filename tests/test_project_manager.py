"""
项目管理器和项目格式单元测试
"""

import pytest
import tempfile
import os
import zipfile
import json

from src.business.project_manager import ProjectManager
from src.business.project_format import (
    save_project, load_project, get_project_info,
    FORMAT_VERSION, MANIFEST_FILE, PARAMS_FILE, CONTOURS_FILE,
    ProjectFormatError
)
from src.core.types import (
    Contour, Path, Point, PathType, SliceParams,
    Project, ProjectMeta, EdgeType, BevelDirection
)


class TestProjectFormat:
    """项目格式测试"""

    def test_save_and_load_empty_project(self):
        """测试保存和加载空项目"""
        project = Project(
            meta=ProjectMeta(name="测试项目", version=FORMAT_VERSION)
        )

        with tempfile.TemporaryDirectory() as tmpdir:
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
            start_point_index=2,
            print_order=5
        )

        project = Project(
            meta=ProjectMeta(name="带轮廓项目"),
            contours=[contour]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.smp")
            save_project(project, file_path)
            loaded = load_project(file_path)

            assert len(loaded.contours) == 1
            c = loaded.contours[0]
            assert c.name == "测试轮廓"
            assert c.start_point_index == 2
            assert c.print_order == 5
            assert len(c.outer.points) == 4
            assert c.outer.color == (255, 128, 0)
            assert len(c.holes) == 1

    def test_save_and_load_with_params(self):
        """测试保存和加载包含参数的项目"""
        project = Project(meta=ProjectMeta(name="参数测试"))
        project.params.shell.height = 45.5
        project.params.shell.layer_height = 0.25
        project.params.shell.edge_type = EdgeType.BEVELED
        project.params.skirt.enabled = True
        project.params.skirt.width = 6.0

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.smp")
            save_project(project, file_path)
            loaded = load_project(file_path)

            assert loaded.params.shell.height == 45.5
            assert loaded.params.shell.layer_height == 0.25
            assert loaded.params.shell.edge_type == EdgeType.BEVELED
            assert loaded.params.skirt.enabled is True
            assert loaded.params.skirt.width == 6.0

    def test_file_size_comparison(self):
        """测试文件大小（二进制应该更小）"""
        # 创建一个有较多点的轮廓
        points = [Point(i * 0.1, i * 0.2) for i in range(1000)]
        contour = Contour(outer=Path(points=points, path_type=PathType.OUTER))
        project = Project(
            meta=ProjectMeta(name="大项目"),
            contours=[contour]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
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

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.smp")
            save_project(project, file_path)

            info = get_project_info(file_path)
            assert info["name"] == "信息测试"
            assert info["contour_count"] == 5
            assert info["version"] == FORMAT_VERSION

    def test_invalid_file_raises_error(self):
        """测试无效文件抛出错误"""
        with tempfile.TemporaryDirectory() as tmpdir:
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

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.smp")
            save_project(project, file_path)
            loaded = load_project(file_path)

            p = loaded.contours[0].outer.points[0]
            # float64 应该保持足够的精度
            assert abs(p.x - 0.123456789012345) < 1e-14
            assert abs(p.y - 0.987654321098765) < 1e-14


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

        with tempfile.TemporaryDirectory() as tmpdir:
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

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.smp")
            pm.save_project(file_path)
            assert pm.is_modified is False
