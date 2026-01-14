"""
项目管理器模块

负责项目的创建、打开、保存和导入导出。
"""

import json
import os
from datetime import datetime
from typing import Optional, List
from dataclasses import asdict

from PySide6.QtCore import QObject, Signal

from src.core.types import (
    Project, ProjectMeta, Contour, SliceParams, GCodeParams,
    Point, Path, PathType
)
from src.core.dxf_parser import DXFParser


class ProjectManager(QObject):
    """项目管理器"""

    # 信号
    project_loaded = Signal(object)  # Project
    project_saved = Signal(str)  # 保存路径
    project_modified = Signal()

    PROJECT_VERSION = "1.0"

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
        """打开项目文件（.dada格式）"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        project = self._deserialize_project(data)

        self.current_project = project
        self.current_path = file_path
        self.is_modified = False

        self.project_loaded.emit(project)
        return project

    def save_project(self, file_path: Optional[str] = None) -> None:
        """保存项目"""
        if file_path is None:
            file_path = self.current_path

        if file_path is None:
            raise ValueError("未指定保存路径")

        if self.current_project is None:
            raise ValueError("没有可保存的项目")

        # 更新修改时间
        self.current_project.meta.modified_at = datetime.now().isoformat()

        # 序列化并保存
        data = self._serialize_project(self.current_project)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self.current_path = file_path
        self.is_modified = False

        self.project_saved.emit(file_path)

    def import_dxf(self, file_path: str) -> None:
        """导入DXF到当前项目"""
        if self.current_project is None:
            self.new_project()

        contours = self._parser.parse(file_path)
        self.current_project.contours.extend(contours)

        self.is_modified = True
        self.project_modified.emit()

    def mark_modified(self):
        """标记项目已修改"""
        self.is_modified = True
        self.project_modified.emit()

    def _serialize_project(self, project: Project) -> dict:
        """序列化项目为字典"""
        return {
            'version': project.meta.version,
            'meta': {
                'name': project.meta.name,
                'created_at': project.meta.created_at,
                'modified_at': project.meta.modified_at
            },
            'contours': [self._serialize_contour(c) for c in project.contours],
            'slice_params': self._serialize_params(project.slice_params),
            'gcode_params': self._serialize_params(project.gcode_params)
        }

    def _serialize_contour(self, contour: Contour) -> dict:
        """序列化轮廓"""
        return {
            'name': contour.name,
            'outer': {
                'points': [[p.x, p.y] for p in contour.outer.points],
                'start_index': contour.outer.start_index
            },
            'holes': [
                {
                    'points': [[p.x, p.y] for p in h.points],
                    'start_index': h.start_index
                }
                for h in contour.holes
            ],
            'connected_frames': [
                {'points': [[p.x, p.y] for p in cf.points]}
                for cf in contour.connected_frames
            ],
            'patterns': [
                {'points': [[p.x, p.y] for p in pt.points]}
                for pt in contour.patterns
            ]
        }

    def _serialize_params(self, params) -> dict:
        """序列化参数对象"""
        try:
            return asdict(params)
        except:
            return {}

    def _deserialize_project(self, data: dict) -> Project:
        """反序列化项目"""
        meta = ProjectMeta(
            name=data['meta']['name'],
            created_at=data['meta']['created_at'],
            modified_at=data['meta']['modified_at'],
            version=data.get('version', '1.0')
        )

        contours = [self._deserialize_contour(c) for c in data.get('contours', [])]

        # TODO: 反序列化 slice_params 和 gcode_params

        return Project(
            meta=meta,
            contours=contours
        )

    def _deserialize_contour(self, data: dict) -> Contour:
        """反序列化轮廓"""
        outer_points = [Point(p[0], p[1]) for p in data['outer']['points']]
        outer = Path(
            points=outer_points,
            path_type=PathType.OUTER,
            start_index=data['outer'].get('start_index', 0)
        )

        holes = []
        for h in data.get('holes', []):
            hole_points = [Point(p[0], p[1]) for p in h['points']]
            holes.append(Path(
                points=hole_points,
                path_type=PathType.INNER,
                start_index=h.get('start_index', 0)
            ))

        return Contour(
            outer=outer,
            holes=holes,
            name=data.get('name', '')
        )
