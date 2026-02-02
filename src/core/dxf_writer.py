"""
SignMaker Slicer - DXF文件写入模块

用于生成底板和面板的DXF文件，支持：
- 根据字壳轮廓生成底板/面板轮廓
- 应用对齐补偿（偏移调整）
- 考虑边缘类型（直边/斜边/异形边）确定正确轮廓
"""

from __future__ import annotations
from typing import List, Optional
from pathlib import Path

import ezdxf
from ezdxf.enums import TextEntityAlignment

from .types import (
    Point, Path as ContourPath, Contour, SliceParams,
    EdgeType, BevelDirection
)
from .path_offset import PathOffset


class DXFWriter:
    """DXF文件写入器"""

    def __init__(self):
        """初始化写入器"""
        self.path_offset = PathOffset()

    def export_baseplate(
        self,
        contours: List[Contour],
        file_path: str,
        params: SliceParams,
        alignment_compensation: float = -0.4
    ) -> bool:
        """
        导出底板DXF文件

        底板位于字壳底部（z=0），轮廓取决于边缘类型：
        - 直边：使用原始轮廓
        - 斜边（上小下大）：使用原始轮廓（底部最大）
        - 斜边（上大下小）：使用内缩轮廓（底部最小）
        - 异形边：根据z=0处的偏移量确定

        Args:
            contours: 轮廓列表
            file_path: 输出DXF文件路径
            params: 切片参数
            alignment_compensation: 对齐补偿（mm），默认-0.4mm

        Returns:
            是否导出成功
        """
        if not contours:
            return False

        # 获取底板轮廓
        baseplate_contours = self._get_baseplate_contours(contours, params)

        # 应用对齐补偿
        if abs(alignment_compensation) > 0.001:
            baseplate_contours = self._apply_compensation(
                baseplate_contours, alignment_compensation
            )

        # 写入DXF
        return self._write_dxf(baseplate_contours, file_path, "底板")

    def export_panel(
        self,
        contours: List[Contour],
        file_path: str,
        params: SliceParams,
        alignment_compensation: float = 0.0
    ) -> bool:
        """
        导出面板DXF文件

        面板位于字壳顶部（z=total_height），轮廓取决于边缘类型：
        - 直边：使用原始轮廓
        - 斜边（上小下大）：使用内缩轮廓（顶部最小）
        - 斜边（上大下小）：使用原始轮廓（顶部最大）
        - 异形边：根据z=total_height处的偏移量确定

        Args:
            contours: 轮廓列表
            file_path: 输出DXF文件路径
            params: 切片参数
            alignment_compensation: 对齐补偿（mm），默认0mm

        Returns:
            是否导出成功
        """
        if not contours:
            return False

        # 获取面板轮廓
        panel_contours = self._get_panel_contours(contours, params)

        # 应用对齐补偿
        if abs(alignment_compensation) > 0.001:
            panel_contours = self._apply_compensation(
                panel_contours, alignment_compensation
            )

        # 写入DXF
        return self._write_dxf(panel_contours, file_path, "面板")

    def _get_baseplate_contours(
        self,
        contours: List[Contour],
        params: SliceParams
    ) -> List[Contour]:
        """
        获取底板轮廓

        根据边缘类型确定底板（z=0处）的轮廓。
        """
        result = []
        shell = params.shell

        for contour in contours:
            # 计算底部偏移量
            offset = self._get_bottom_offset(shell)

            if abs(offset) < 0.001:
                # 无偏移，直接使用原始轮廓
                result.append(Contour(
                    outer=self._copy_path(contour.outer),
                    holes=[self._copy_path(h) for h in contour.holes],
                    name=contour.name
                ))
            else:
                # 应用偏移
                new_contour = self.path_offset.offset_contour(contour, offset)
                if new_contour:
                    result.append(new_contour)

        return result

    def _get_panel_contours(
        self,
        contours: List[Contour],
        params: SliceParams
    ) -> List[Contour]:
        """
        获取面板轮廓

        根据边缘类型确定面板（z=total_height处）的轮廓。
        """
        result = []
        shell = params.shell

        for contour in contours:
            # 计算顶部偏移量
            offset = self._get_top_offset(shell)

            if abs(offset) < 0.001:
                # 无偏移，直接使用原始轮廓
                result.append(Contour(
                    outer=self._copy_path(contour.outer),
                    holes=[self._copy_path(h) for h in contour.holes],
                    name=contour.name
                ))
            else:
                # 应用偏移
                new_contour = self.path_offset.offset_contour(contour, offset)
                if new_contour:
                    result.append(new_contour)

        return result

    def _get_bottom_offset(self, shell) -> float:
        """
        计算底部（z=0）的偏移量

        Returns:
            偏移量（正=外扩，负=内缩）
        """
        if shell.edge_type == EdgeType.STRAIGHT:
            # 直边：无偏移
            return 0.0

        elif shell.edge_type == EdgeType.BEVELED:
            if shell.bevel_direction == BevelDirection.TOP_SMALL:
                # 上小下大：底部最大，无偏移
                return 0.0
            else:  # TOP_LARGE
                # 上大下小：底部最小，内缩bevel_width
                return -shell.bevel_width

        elif shell.edge_type == EdgeType.CUSTOM and shell.edge_profile:
            # 异形边：获取z=0处的偏移
            profile = shell.edge_profile
            offset = profile.get_offset_at_height(
                0.0,  # normalized_z = 0 (底部)
                shell.bevel_width,
                shell.height
            )
            return offset

        return 0.0

    def _get_top_offset(self, shell) -> float:
        """
        计算顶部（z=total_height）的偏移量

        Returns:
            偏移量（正=外扩，负=内缩）
        """
        if shell.edge_type == EdgeType.STRAIGHT:
            # 直边：无偏移
            return 0.0

        elif shell.edge_type == EdgeType.BEVELED:
            if shell.bevel_direction == BevelDirection.TOP_SMALL:
                # 上小下大：顶部最小，内缩bevel_width
                return -shell.bevel_width
            else:  # TOP_LARGE
                # 上大下小：顶部最大，无偏移
                return 0.0

        elif shell.edge_type == EdgeType.CUSTOM and shell.edge_profile:
            # 异形边：获取z=1处的偏移
            profile = shell.edge_profile
            offset = profile.get_offset_at_height(
                1.0,  # normalized_z = 1 (顶部)
                shell.bevel_width,
                shell.height
            )
            return offset

        return 0.0

    def _apply_compensation(
        self,
        contours: List[Contour],
        compensation: float
    ) -> List[Contour]:
        """
        应用对齐补偿

        Args:
            contours: 轮廓列表
            compensation: 补偿值（正=外扩，负=内缩）

        Returns:
            补偿后的轮廓列表
        """
        result = []
        for contour in contours:
            new_contour = self.path_offset.offset_contour(contour, compensation)
            if new_contour:
                result.append(new_contour)
        return result

    def _copy_path(self, path: ContourPath) -> ContourPath:
        """复制路径"""
        return ContourPath(
            points=[Point(p.x, p.y) for p in path.points],
            path_type=path.path_type,
            color=path.color,
            is_closed=path.is_closed
        )

    def _write_dxf(
        self,
        contours: List[Contour],
        file_path: str,
        layer_name: str = "0"
    ) -> bool:
        """
        将轮廓写入DXF文件

        Args:
            contours: 轮廓列表
            file_path: 输出文件路径
            layer_name: 图层名称

        Returns:
            是否写入成功
        """
        try:
            # 创建新的DXF文档
            doc = ezdxf.new(dxfversion='R2010')
            msp = doc.modelspace()

            # 创建图层
            doc.layers.add(layer_name, color=7)  # 白色

            # 写入所有轮廓
            for contour in contours:
                # 写入外轮廓
                self._write_polyline(msp, contour.outer, layer_name)

                # 写入内孔
                for hole in contour.holes:
                    self._write_polyline(msp, hole, layer_name)

            # 保存文件
            doc.saveas(file_path)
            return True

        except Exception as e:
            print(f"DXF写入失败: {e}")
            return False

    def _write_polyline(
        self,
        msp,
        path: ContourPath,
        layer_name: str
    ):
        """
        将路径写入为多段线

        Args:
            msp: 模型空间
            path: 路径
            layer_name: 图层名称
        """
        if not path.points or len(path.points) < 2:
            return

        # 转换点为元组列表
        points = [(p.x, p.y) for p in path.points]

        # 创建多段线
        msp.add_lwpolyline(
            points,
            close=path.is_closed,
            dxfattribs={'layer': layer_name}
        )


def export_baseplate_dxf(
    contours: List[Contour],
    file_path: str,
    params: SliceParams,
    alignment_compensation: float = -0.4
) -> bool:
    """
    导出底板DXF文件（便捷函数）

    Args:
        contours: 轮廓列表
        file_path: 输出DXF文件路径
        params: 切片参数
        alignment_compensation: 对齐补偿（mm），默认-0.4mm

    Returns:
        是否导出成功
    """
    writer = DXFWriter()
    return writer.export_baseplate(contours, file_path, params, alignment_compensation)


def export_panel_dxf(
    contours: List[Contour],
    file_path: str,
    params: SliceParams,
    alignment_compensation: float = 0.0
) -> bool:
    """
    导出面板DXF文件（便捷函数）

    Args:
        contours: 轮廓列表
        file_path: 输出DXF文件路径
        params: 切片参数
        alignment_compensation: 对齐补偿（mm），默认0mm

    Returns:
        是否导出成功
    """
    writer = DXFWriter()
    return writer.export_panel(contours, file_path, params, alignment_compensation)
