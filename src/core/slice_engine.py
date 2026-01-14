"""
SignMaker Slicer - 切片引擎模块

核心切片逻辑，协调各子生成器，将轮廓数据转换为打印层数据。

支持功能：
- 直边切片（基础）
- 斜边切片
- 多壁生成
- 层规划（换色层、台阶层）
- 预打边线（安全线）
"""

from __future__ import annotations
import math
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from .types import (
    Point, Path, Contour, Layer, LayerPath, LayerInfo,
    PathType, PathRole, EdgeType, ExtruderType,
    SliceParams, ShellParams, StepConfig,
    SliceResult
)
from .path_offset import PathOffset, JoinType


@dataclass
class BevelProfile:
    """斜边轮廓缓存"""
    z_to_offset: Dict[float, float] = field(default_factory=dict)


class SliceEngine:
    """切片引擎"""

    def __init__(self):
        self.path_offset = PathOffset()
        # 子生成器可以后续添加
        # self.bevel_generator = BevelGenerator(self.path_offset)
        # self.step_generator = StepGenerator(self.path_offset)
        # self.fill_generator = FillGenerator(self.path_offset)

    def slice(self, contours: List[Contour], params: SliceParams) -> SliceResult:
        """
        执行切片操作

        主流程：
        1. 计算层规划
        2. 逐层生成路径
        3. 添加预打边线
        4. 计算统计信息

        Args:
            contours: 轮廓列表
            params: 切片参数

        Returns:
            切片结果
        """
        if not contours:
            return SliceResult()

        # 1. 计算层规划
        layer_infos = self._plan_layers(params)

        # 2. 逐层生成
        layers = []
        for info in layer_infos:
            layer = self._generate_layer(contours, info, params)
            if layer.paths:  # 只添加有路径的层
                layers.append(layer)

        # 3. 添加预打边线（安全线）
        if params.shell.safety_line_count > 0:
            safety_layers = self._generate_safety_lines(contours, params)
            # 安全线在最底层之前打印
            layers = safety_layers + layers

        # 4. 计算统计
        result = self._create_result(layers, params)

        return result

    def _plan_layers(self, params: SliceParams) -> List[LayerInfo]:
        """
        规划所有层

        考虑因素：
        - 总高度和层高
        - 换色层配置
        - 台阶位置
        - 防翘裙边位置
        - 包边/勾边位置
        """
        layer_height = params.shell.layer_height
        total_height = params.shell.height
        layer_count = max(1, int(total_height / layer_height))

        # 构建换色层映射
        color_layer_map = self._build_color_layer_map(params)

        # 构建台阶层映射
        step_layer_map = self._build_step_layer_map(params, layer_height)

        layer_infos = []
        for i in range(layer_count):
            z = i * layer_height

            # 确定挤出机
            extruder = self._get_extruder_at_height(z, color_layer_map)

            # 检查是否台阶层
            is_step = z in step_layer_map
            step_config = step_layer_map.get(z)

            # 检查是否首层（需要防翘裙边）
            is_first = (i == 0)
            has_skirt = is_first and params.skirt.enabled

            # 检查是否顶层（需要包边/勾边）
            is_last = (i == layer_count - 1)
            has_edge_wrap = is_last and (params.edge_wrap.wrap_enabled or
                                          params.edge_wrap.outline_enabled)

            info = LayerInfo(
                z_height=z,
                layer_height=layer_height,
                extruder=extruder,
                is_first_layer=is_first,
                is_step_layer=is_step,
                step_config=step_config,
                has_skirt=has_skirt,
                has_edge_wrap=has_edge_wrap
            )
            layer_infos.append(info)

        return layer_infos

    def _build_color_layer_map(self, params: SliceParams) -> Dict[float, Tuple[float, ExtruderType]]:
        """构建换色层高度-挤出机映射"""
        if not params.color.enabled or not params.color.layers:
            return {}

        mapping = {}
        current_height = 0

        for config in params.color.layers:
            end_height = current_height + config.height
            # 将该高度范围映射到指定挤出机
            mapping[current_height] = (end_height, config.extruder)
            current_height = end_height

        return mapping

    def _build_step_layer_map(self, params: SliceParams,
                               layer_height: float) -> Dict[float, StepConfig]:
        """构建台阶层高度-配置映射"""
        mapping = {}

        if not params.step.enabled:
            return mapping

        for step in params.step.steps:
            if step.enabled:
                # 对齐到层高
                aligned_z = round(step.position / layer_height) * layer_height
                mapping[aligned_z] = step

        return mapping

    def _get_extruder_at_height(self, z: float,
                                 color_layers: Dict) -> ExtruderType:
        """获取指定高度应使用的挤出机"""
        for start_z, (end_z, extruder) in color_layers.items():
            if start_z <= z < end_z:
                return extruder
        return ExtruderType.EXTRUDER_1

    def _generate_layer(self, contours: List[Contour],
                        info: LayerInfo,
                        params: SliceParams) -> Layer:
        """
        生成单层

        处理顺序：
        1. 应用边缘轮廓（斜边收缩）
        2. 生成壁路径
        3. 生成台阶（如需要）
        4. 生成防翘裙边（如需要）
        """
        layer = Layer(
            z_height=info.z_height,
            layer_height=info.layer_height,
            extruder=info.extruder
        )

        for contour in contours:
            # 1. 应用边缘轮廓
            modified_contour = self._apply_edge_profile(
                contour, info.z_height, params.shell
            )
            if not modified_contour:
                continue

            # 2. 生成壁路径
            wall_paths = self._generate_wall_paths(
                modified_contour, info, params.shell
            )
            layer.paths.extend(wall_paths)

            # 3. 生成防翘裙边（仅首层）
            if info.has_skirt:
                skirt_paths = self._generate_skirt_paths(
                    modified_contour, params
                )
                layer.paths.extend(skirt_paths)

        return layer

    def _apply_edge_profile(self, contour: Contour, z: float,
                             params: ShellParams) -> Optional[Contour]:
        """
        根据边缘类型和高度应用轮廓变换

        Args:
            contour: 原始轮廓
            z: 当前层高度
            params: 字壳参数

        Returns:
            变换后的轮廓（可能缩小到消失返回None）
        """
        if params.edge_type == EdgeType.STRAIGHT:
            return self._apply_straight_edge(contour, z, params)
        elif params.edge_type == EdgeType.BEVELED:
            return self._apply_beveled_edge(contour, z, params)
        elif params.edge_type == EdgeType.CUSTOM:
            return self._apply_custom_edge(contour, z, params)
        else:
            return contour

    def _apply_straight_edge(self, contour: Contour, z: float,
                              params: ShellParams) -> Contour:
        """
        直边处理

        直边字壳从底到顶保持相同尺寸
        """
        # 直边不需要偏移
        return contour

    def _apply_beveled_edge(self, contour: Contour, z: float,
                             params: ShellParams) -> Optional[Contour]:
        """
        斜边处理

        斜边结构：
        ┌─────────┐ ← 面板位置（最内收缩）
        │ ╲     ╱ │
        │  ╲   ╱  │ ← 斜边区域（线性收缩）
        │   ╲ ╱   │
        │    │    │ ← 底板区域（不收缩）
        └────┴────┘

        收缩方向：从外向内
        """
        baseplate_top = params.baseplate_thickness
        bevel_end = baseplate_top + params.bevel_width
        max_offset = params.bevel_width  # 最大内缩距离

        if z < baseplate_top:
            # 底板区域：不收缩
            offset = 0
        elif z < bevel_end:
            # 斜边区域：线性收缩
            progress = (z - baseplate_top) / params.bevel_width
            offset = -progress * max_offset
        else:
            # 面板区域：保持最大收缩
            offset = -max_offset

        if abs(offset) < 0.001:
            return contour

        # 应用偏移
        return self.path_offset.offset_contour(contour, offset)

    def _apply_custom_edge(self, contour: Contour, z: float,
                            params: ShellParams) -> Optional[Contour]:
        """
        异形边处理

        根据EdgeProfile定义的点序列进行插值
        """
        if not params.edge_profile:
            return contour

        profile = params.edge_profile
        total_height = params.height

        # 归一化高度
        normalized_z = z / total_height if total_height > 0 else 0

        # 在profile中查找对应的偏移量
        offset = self._interpolate_profile(profile, normalized_z)

        if abs(offset) < 0.001:
            return contour

        return self.path_offset.offset_contour(contour, offset)

    def _interpolate_profile(self, profile, normalized_z: float) -> float:
        """在异形边轮廓中插值"""
        points = profile.points
        if not points:
            return 0

        # 找到z所在的区间
        for i in range(len(points) - 1):
            z1, offset1 = points[i].x, points[i].y
            z2, offset2 = points[i + 1].x, points[i + 1].y

            if z1 <= normalized_z <= z2:
                # 线性插值
                t = (normalized_z - z1) / (z2 - z1) if z2 != z1 else 0
                return offset1 + t * (offset2 - offset1)

        # 超出范围，使用边界值
        if normalized_z < points[0].x:
            return points[0].y
        return points[-1].y

    def _generate_wall_paths(self, contour: Contour,
                              info: LayerInfo,
                              params: ShellParams) -> List[LayerPath]:
        """
        生成壁路径

        支持多层壁（走线次数）
        """
        paths = []
        wall_thickness = params.wall_thickness
        wall_count = params.wall_count
        wall_offset = params.wall_offset if params.wall_offset > 0 else wall_thickness

        for i in range(wall_count):
            # 计算当前壁的偏移距离
            # 第一壁偏移 wall_thickness/2（让壁中心线在原轮廓上）
            # 后续壁依次向内偏移
            offset_distance = -(wall_thickness / 2 + i * wall_offset)

            # 偏移外轮廓
            offset_results = self.path_offset.offset(
                contour.outer, offset_distance, JoinType.MITER
            )

            for offset_path in offset_results:
                layer_path = LayerPath(
                    points=offset_path.points,
                    role=PathRole.WALL,
                    extruder=info.extruder,
                    line_width=wall_thickness,
                    is_closed=True
                )
                paths.append(layer_path)

            # 偏移内孔（方向相反）
            for hole in contour.holes:
                hole_offset_results = self.path_offset.offset(
                    hole, -offset_distance, JoinType.MITER
                )
                for offset_hole in hole_offset_results:
                    layer_path = LayerPath(
                        points=offset_hole.points,
                        role=PathRole.WALL,
                        extruder=info.extruder,
                        line_width=wall_thickness,
                        is_closed=True
                    )
                    paths.append(layer_path)

        return paths

    def _generate_skirt_paths(self, contour: Contour,
                               params: SliceParams) -> List[LayerPath]:
        """
        生成防翘裙边路径

        裙边在首层生成，围绕轮廓外部
        """
        paths = []
        skirt_params = params.skirt

        if not skirt_params.enabled:
            return paths

        # 向外偏移
        offset_distance = skirt_params.offset + skirt_params.width / 2
        skirt_results = self.path_offset.offset(
            contour.outer, offset_distance, JoinType.ROUND
        )

        for skirt_path in skirt_results:
            layer_path = LayerPath(
                points=skirt_path.points,
                role=PathRole.SKIRT,
                extruder=ExtruderType.EXTRUDER_1,
                line_width=skirt_params.width,
                is_closed=True
            )
            paths.append(layer_path)

        return paths

    def _generate_safety_lines(self, contours: List[Contour],
                                params: SliceParams) -> List[Layer]:
        """
        生成预打边线（安全线）

        围绕所有字形外围生成边线，防止首层打印时材料粘附不良
        """
        layers = []
        offset = params.shell.safety_line_offset
        count = params.shell.safety_line_count

        for i in range(count):
            layer = Layer(
                z_height=0,
                layer_height=params.shell.layer_height,
                extruder=ExtruderType.EXTRUDER_1
            )

            for contour in contours:
                # 向外偏移
                offset_distance = offset + i * params.shell.wall_thickness
                offset_paths = self.path_offset.offset(
                    contour.outer, offset_distance, JoinType.MITER
                )

                for path in offset_paths:
                    layer_path = LayerPath(
                        points=path.points,
                        role=PathRole.SAFETY_LINE,
                        extruder=ExtruderType.EXTRUDER_1,
                        line_width=params.shell.wall_thickness,
                        is_closed=True
                    )
                    layer.paths.append(layer_path)

            if layer.paths:
                layers.append(layer)

        return layers

    def _create_result(self, layers: List[Layer],
                       params: SliceParams) -> SliceResult:
        """创建切片结果，计算统计信息"""
        total_distance = 0
        filament_per_extruder: Dict[ExtruderType, float] = {
            ExtruderType.EXTRUDER_1: 0,
            ExtruderType.EXTRUDER_2: 0,
            ExtruderType.EXTRUDER_3: 0,
        }

        for layer in layers:
            for path in layer.paths:
                # 计算路径长度
                distance = self._calculate_path_length(path.points, path.is_closed)
                total_distance += distance

                # 按挤出机统计
                filament_per_extruder[path.extruder] += distance

        # 估算时间（基于打印速度）
        avg_speed = params.speed.print_speed if params.speed.print_speed > 0 else 40
        estimated_time = total_distance / avg_speed

        # 将距离转换为线材长度（考虑截面积）
        line_width = params.shell.wall_thickness
        layer_height = params.shell.layer_height
        filament_diameter = params.gcode.filament_diameter

        cross_section_ratio = (line_width * layer_height) / (
            math.pi * (filament_diameter / 2) ** 2
        )

        estimated_filament = total_distance * cross_section_ratio / 1000  # 转换为米

        return SliceResult(
            layers=layers,
            total_layers=len(layers),
            total_height=params.shell.height,
            estimated_time=estimated_time,
            estimated_filament=estimated_filament,
            filament_per_extruder={
                k: v * cross_section_ratio / 1000
                for k, v in filament_per_extruder.items()
            }
        )

    def _calculate_path_length(self, points: List[Point], is_closed: bool = True) -> float:
        """计算路径总长度"""
        if len(points) < 2:
            return 0

        length = 0
        n = len(points)

        for i in range(n - 1):
            dx = points[i + 1].x - points[i].x
            dy = points[i + 1].y - points[i].y
            length += math.sqrt(dx * dx + dy * dy)

        # 闭合路径需要加上首尾连接
        if is_closed and n >= 2:
            dx = points[0].x - points[-1].x
            dy = points[0].y - points[-1].y
            length += math.sqrt(dx * dx + dy * dy)

        return length


# 为了兼容types.py中的引用
from typing import Tuple
