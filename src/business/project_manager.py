"""
项目管理器模块

负责项目的创建、打开、保存和导入导出。
使用 .smp (SignMaker Project) 格式：ZIP 容器 + 二进制几何 + JSON 参数
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, List

from PySide6.QtCore import QObject, Signal

from src.core.asset_utils import assign_contours_to_asset
from src.core.types import Project, ProjectMeta, Contour, SliceParams
from src.core.dxf_parser import DXFParser
from src.business.project_format import (
    save_project as _save_project,
    load_project as _load_project,
    FORMAT_VERSION
)


class ProjectManager(QObject):
    """项目管理器

    负责项目的创建、打开、保存和导入导出。

    项目文件格式 (.smp)：
    - ZIP 容器，包含：
      - manifest.json: 项目元数据
      - params.json: 切片参数
      - contours.bin: 二进制几何数据
    """

    # 信号
    project_loaded = Signal(object)  # Project
    project_saved = Signal(str)  # 保存路径
    project_modified = Signal()

    PROJECT_VERSION = FORMAT_VERSION
    FILE_EXTENSION = ".smp"

    def __init__(self):
        super().__init__()
        self.current_project: Optional[Project] = None
        self.current_path: Optional[str] = None
        self.is_modified = False
        self._parser = DXFParser()

    def new_project(self) -> Project:
        """创建新项目"""
        meta = ProjectMeta(
            name="未命名项目",
            created_at=datetime.now().isoformat(),
            modified_at=datetime.now().isoformat(),
            version=self.PROJECT_VERSION
        )

        self.current_project = Project(meta=meta)
        self.current_path = None
        self.is_modified = False

        self.project_loaded.emit(self.current_project)
        return self.current_project

    def open_project(self, file_path: str) -> Project:
        """打开项目文件

        Args:
            file_path: 项目文件路径

        Returns:
            加载的项目对象

        Raises:
            ProjectFormatError: 文件格式错误
        """
        project = _load_project(file_path)

        self.current_project = project
        self.current_path = file_path
        self.is_modified = False

        self.project_loaded.emit(project)
        return project

    def save_project(
        self,
        file_path: Optional[str] = None,
        preview_png: Optional[bytes] = None,
    ) -> None:
        """保存项目

        Args:
            file_path: 保存路径，None 则使用当前路径
        """
        if file_path is None:
            file_path = self.current_path

        if file_path is None:
            raise ValueError("未指定保存路径")

        if self.current_project is None:
            raise ValueError("没有可保存的项目")

        # 更新修改时间
        self.current_project.meta.modified_at = datetime.now().isoformat()

        # 保存
        _save_project(self.current_project, file_path, preview_png=preview_png)

        self.current_path = file_path
        self.is_modified = False

        self.project_saved.emit(file_path)

    def import_dxf(self, file_path: str) -> None:
        """导入DXF到当前项目"""
        if self.current_project is None:
            self.new_project()

        contours = self._parser.parse(file_path)
        assign_contours_to_asset(contours, Path(file_path).name)
        self.current_project.contours.extend(contours)

        self.is_modified = True
        self.project_modified.emit()

    def mark_modified(self):
        """标记项目已修改"""
        self.is_modified = True
        self.project_modified.emit()
