"""
MINGDA SignMaker - DXF文件写入模块

用于生成底板和面板的DXF文件，支持：
- 根据字壳轮廓生成底板/面板轮廓
- 应用对齐补偿（偏移调整）
- 考虑边缘类型（直边/斜边/异形边）确定正确轮廓
"""

from __future__ import annotations
from typing import List, Optional

import ezdxf

from .types import (
    Point, Path as ContourPath, Contour, SliceParams,
    EdgeType, BevelDirection, JoinType, resolve_shell_wall_thickness,
    calculate_u_shape_offset_at_z,
    resolve_bottom_face_thickness,
)
from .path_offset import PathOffset


class DXFWriter:
    """DXF文件写入器"""

    DXF_VERSION = "R12"
    ASCII_ENCODING = "cp1252"

    def __init__(self):
        """初始化写入器"""
        self.path_offset = PathOffset()

    def export_baseplate(
        self,
        contours: List[Contour],
        file_path: str,
        params: SliceParams,
        alignment_compensation: float = 0.0
    ) -> bool:
        """
        导出底板DXF文件

        底板DXF取字壳 z=0 处轮廓，先换算到内壁台面安装位，
        再应用外轮廓/内孔独立公差以及激光 kerf 补偿。

        Args:
            contours: 轮廓列表
            file_path: 输出DXF文件路径
            params: 切片参数
            alignment_compensation: 兼容旧逻辑的额外补偿（mm），默认0mm

        Returns:
            是否导出成功
        """
        if not contours:
            return False

        # 获取底板轮廓
        baseplate_contours = self._get_baseplate_contours(contours, params)

        baseplate_contours = self._apply_cutting_compensation(
            baseplate_contours, params, alignment_compensation
        )

        # 写入DXF
        return self._write_dxf(baseplate_contours, file_path, "BASEPLATE")

    def export_panel(
        self,
        contours: List[Contour],
        file_path: str,
        params: SliceParams,
        alignment_compensation: float = 0.0
    ) -> bool:
        """
        导出面板DXF文件

        面板DXF取字壳最高处轮廓，先换算到内壁台面安装位，
        再应用外轮廓/内孔独立公差以及激光 kerf 补偿。

        Args:
            contours: 轮廓列表
            file_path: 输出DXF文件路径
            params: 切片参数
            alignment_compensation: 兼容旧逻辑的额外补偿（mm），默认0mm

        Returns:
            是否导出成功
        """
        if not contours:
            return False

        # 获取面板轮廓
        panel_contours = self._get_panel_contours(contours, params)

        panel_contours = self._apply_cutting_compensation(
            panel_contours, params, alignment_compensation
        )

        # 写入DXF
        return self._write_dxf(panel_contours, file_path, "PANEL")

    def _get_baseplate_contours(
        self,
        contours: List[Contour],
        params: SliceParams
    ) -> List[Contour]:
        """
        获取底板轮廓

        取 z=0 处的字壳轮廓，再换算为内壁台面安装轮廓。
        """
        shell_contours = self._get_shell_contours_at_z(contours, 0.0, params)
        return self._get_inner_wall_contours(shell_contours, params)

    def _get_panel_contours(
        self,
        contours: List[Contour],
        params: SliceParams
    ) -> List[Contour]:
        """
        获取面板轮廓

        取最高处（z=total_height）的字壳轮廓，再换算为内壁台面安装轮廓。
        """
        shell_contours = self._get_shell_contours_at_z(contours, params.shell.height, params)
        return self._get_inner_wall_contours(shell_contours, params)

    def _get_shell_contours_at_z(
        self,
        contours: List[Contour],
        z: float,
        params: SliceParams
    ) -> List[Contour]:
        """获取指定高度处的字壳轮廓。"""
        result = []
        shell = params.shell

        u_flat_height = resolve_bottom_face_thickness(params)

        for contour in contours:
            transformed = self._apply_edge_profile(
                contour,
                z,
                shell,
                u_flat_height,
            )
            if transformed:
                result.append(transformed)

        return result

    def _get_inner_wall_contours(
        self,
        contours: List[Contour],
        params: SliceParams
    ) -> List[Contour]:
        """
        将字壳轮廓换算为内壁台面安装轮廓。

        亚克力落在外轮廓与内孔之间的台面上，因此外轮廓和内孔都要先考虑壁厚：
        - 外轮廓向内缩一个壁厚
        - 内孔向孔外扩一个壁厚
        """
        wall_thickness = max(
            resolve_shell_wall_thickness(
                params.shell.line_width,
                params.shell.wall_count,
                params.shell.layer_height,
                wall_thickness=params.shell.wall_thickness,
            ),
            0.0,
        )
        if wall_thickness < 0.001:
            return [self._copy_contour(contour) for contour in contours]

        result = []
        for contour in contours:
            inner_contour = self.path_offset.offset_contour(contour, -wall_thickness)
            if inner_contour:
                result.append(inner_contour)
        return result

    def _apply_edge_profile(
        self,
        contour: Contour,
        z: float,
        shell,
        u_flat_height: float = 0.0,
    ) -> Optional[Contour]:
        """根据边缘类型计算指定高度处的字壳轮廓。"""
        z = max(0.0, min(z, shell.height))
        offset = self._get_edge_offset_at_z(z, shell, u_flat_height)

        if abs(offset) < 0.001:
            return self._copy_contour(contour)

        if shell.edge_type == EdgeType.U_SHAPED:
            return self.path_offset.offset_contour(contour, offset, JoinType.MITER)

        return self._offset_contour_same_direction(contour, offset)

    def _get_edge_offset_at_z(
        self,
        z: float,
        shell,
        u_flat_height: float = 0.0,
    ) -> float:
        """计算指定高度处的整体轮廓偏移量。"""
        if shell.edge_type == EdgeType.STRAIGHT:
            return 0.0

        if shell.edge_type == EdgeType.BEVELED:
            if shell.bevel_direction == BevelDirection.TOP_SMALL:
                return self._get_top_small_offset_at_z(z, shell)
            return self._get_top_large_offset_at_z(z, shell)

        if shell.edge_type == EdgeType.CUSTOM and shell.edge_profile:
            normalized_z = z / shell.height if shell.height > 0 else 0.0
            return shell.edge_profile.get_offset_at_height(
                normalized_z,
                shell.bevel_width,
                shell.height
            )

        if shell.edge_type == EdgeType.U_SHAPED:
            return calculate_u_shape_offset_at_z(z, shell, u_flat_height)

        return 0.0

    def _get_top_small_offset_at_z(self, z: float, shell) -> float:
        """上小下大型斜边在指定高度处的偏移。"""
        baseplate_top = shell.baseplate_thickness
        panel_bottom = shell.height - shell.panel_thickness

        if z < baseplate_top:
            return 0.0
        if z < panel_bottom:
            bevel_height = panel_bottom - baseplate_top
            if bevel_height <= 0:
                return 0.0
            progress = (z - baseplate_top) / bevel_height
            return -progress * shell.bevel_width
        return -shell.bevel_width

    def _get_top_large_offset_at_z(self, z: float, shell) -> float:
        """上大下小型斜边在指定高度处的偏移。"""
        baseplate_top = shell.baseplate_thickness
        panel_bottom = shell.height - shell.panel_thickness

        if z < baseplate_top:
            return 0.0
        if z < panel_bottom:
            bevel_height = panel_bottom - baseplate_top
            if bevel_height <= 0:
                return 0.0
            progress = (z - baseplate_top) / bevel_height
            return progress * shell.bevel_width
        return shell.bevel_width

    def _get_bottom_offset(self, shell) -> float:
        """
        计算底部（z=0）的偏移量

        Returns:
            偏移量（正=外扩，负=内缩）
        """
        return self._get_edge_offset_at_z(0.0, shell)

    def _get_top_offset(self, shell) -> float:
        """
        计算顶部（z=total_height）的偏移量

        Returns:
            偏移量（正=外扩，负=内缩）
        """
        return self._get_edge_offset_at_z(shell.height, shell)

    def _apply_cutting_compensation(
        self,
        contours: List[Contour],
        params: SliceParams,
        legacy_compensation: float = 0.0
    ) -> List[Contour]:
        """
        应用 DXF 切割补偿。

        Args:
            contours: 轮廓列表
            params: 切片参数
            legacy_compensation: 兼容旧版本的额外补偿值

        Returns:
            补偿后的轮廓列表
        """
        shell = params.shell
        kerf_radius = max(shell.dxf_laser_kerf, 0.0) / 2.0
        legacy_extra = abs(legacy_compensation)
        outer_offset = -(max(shell.dxf_outer_clearance, 0.0) + kerf_radius + legacy_extra)
        hole_offset = max(shell.dxf_hole_clearance, 0.0) + kerf_radius + legacy_extra

        result = []
        for contour in contours:
            compensated = self._offset_contour_split(contour, outer_offset, hole_offset)
            if compensated:
                result.append(compensated)
        return result

    def _offset_contour_split(
        self,
        contour: Contour,
        outer_offset: float,
        hole_offset: float
    ) -> Optional[Contour]:
        """对外轮廓和内孔应用独立偏移。"""
        outer_results = self.path_offset.offset(contour.outer, outer_offset, JoinType.MITER)
        if not outer_results:
            return None

        new_outer = outer_results[0]
        new_holes = []
        for hole in contour.holes:
            hole_results = self.path_offset.offset(hole, hole_offset, JoinType.MITER)
            new_holes.extend(hole_results)

        return Contour(
            outer=new_outer,
            holes=new_holes,
            connected_frames=[self._copy_path(p) for p in contour.connected_frames],
            patterns=[self._copy_path(p) for p in contour.patterns],
            name=contour.name,
            group_id=contour.group_id,
            start_point_index=contour.start_point_index,
            print_order=contour.print_order
        )

    def _offset_contour_same_direction(
        self,
        contour: Contour,
        distance: float
    ) -> Optional[Contour]:
        """
        对整个轮廓进行同方向偏移。

        斜边/异形边是整体缩放，内孔也必须同向变化。
        """
        outer_results = self.path_offset.offset(contour.outer, distance, JoinType.MITER)
        if not outer_results:
            return None

        new_outer = outer_results[0]
        new_holes = []
        for hole in contour.holes:
            hole_results = self.path_offset.offset(hole, distance, JoinType.MITER)
            new_holes.extend(hole_results)

        return Contour(
            outer=new_outer,
            holes=new_holes,
            connected_frames=[self._copy_path(p) for p in contour.connected_frames],
            patterns=[self._copy_path(p) for p in contour.patterns],
            name=contour.name,
            group_id=contour.group_id,
            start_point_index=contour.start_point_index,
            print_order=contour.print_order
        )

    def _copy_path(self, path: ContourPath) -> ContourPath:
        """复制路径"""
        return ContourPath(
            points=[Point(p.x, p.y) for p in path.points],
            path_type=path.path_type,
            color=path.color,
            is_closed=path.is_closed,
            start_point_index=path.start_point_index,
            print_order=path.print_order,
        )

    def _copy_contour(self, contour: Contour) -> Contour:
        """复制轮廓。"""
        return Contour(
            outer=self._copy_path(contour.outer),
            holes=[self._copy_path(h) for h in contour.holes],
            connected_frames=[self._copy_path(p) for p in contour.connected_frames],
            patterns=[self._copy_path(p) for p in contour.patterns],
            name=contour.name,
            group_id=contour.group_id,
            start_point_index=contour.start_point_index,
            print_order=contour.print_order
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
            doc = ezdxf.new(dxfversion=self.DXF_VERSION)
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
            doc.saveas(file_path, encoding=self.ASCII_ENCODING, fmt="asc")
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
        msp.add_polyline2d(
            points,
            close=path.is_closed,
            dxfattribs={'layer': layer_name}
        )


def export_baseplate_dxf(
    contours: List[Contour],
    file_path: str,
    params: SliceParams,
    alignment_compensation: float = 0.0
) -> bool:
    """
    导出底板DXF文件（便捷函数）

    Args:
        contours: 轮廓列表
        file_path: 输出DXF文件路径
        params: 切片参数
        alignment_compensation: 兼容旧逻辑的额外补偿（mm），默认0mm

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
        alignment_compensation: 兼容旧逻辑的额外补偿（mm），默认0mm

    Returns:
        是否导出成功
    """
    writer = DXFWriter()
    return writer.export_panel(contours, file_path, params, alignment_compensation)
