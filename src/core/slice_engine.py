"""
MINGDA SignMaker - 切片引擎模块

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
from copy import deepcopy
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from shapely.geometry import LineString, Polygon

from .types import (
    Point, Path, Contour, Layer, LayerPath, LayerInfo,
    PathType, PathRole, EdgeType, ExtruderType, BevelDirection,
    SliceParams, ShellParams, StepConfig, BottomFaceParams,
    SliceResult, EdgeProfile, InterpolationType, resolve_shell_line_width,
    resolve_shell_wall_thickness, resolve_contour_start_point_index,
    resolve_path_start_point_index,
    calculate_u_shape_offset_at_z, is_bottom_face_effective,
    resolve_bottom_face_thickness,
)
from .path_offset import PathOffset, JoinType
from .print_order import build_loop_order
from .step_generator import StepGenerator
from .edge_profile_generator import EdgeProfileGenerator
from .skirt_generator import SkirtGenerator
from .connected_generator import ConnectedGenerator, ConnectionBridge
from .bottom_face_geometry import BottomFaceGeometryBuilder
from .top_face_geometry import TopFaceGeometryBuilder
from .light_slot_geometry import LightSlotGeometry, LightSlotGeometryBuilder
from .prime_tower import PrimeTowerGenerator


@dataclass
class BevelProfile:
    """斜边轮廓缓存"""
    z_to_offset: Dict[float, float] = field(default_factory=dict)


@dataclass
class ConnectedPreviewContext:
    """Precomputed connected-letter data reused across preview layers."""
    contours: List[Contour] = field(default_factory=list)
    bridges: List[ConnectionBridge] = field(default_factory=list)


class SliceEngine:
    """切片引擎"""

    def __init__(self):
        self.path_offset = PathOffset()
        self.step_generator = StepGenerator(self.path_offset)
        self.edge_profile_generator = EdgeProfileGenerator()
        self.skirt_generator = SkirtGenerator()
        self.connected_generator = ConnectedGenerator(self.path_offset)
        self.bottom_face_geometry_builder = BottomFaceGeometryBuilder(self.path_offset)
        self.top_face_geometry_builder = TopFaceGeometryBuilder(self.path_offset)
        self.light_slot_geometry_builder = LightSlotGeometryBuilder(self.path_offset)
        self.prime_tower_generator = PrimeTowerGenerator(self.path_offset)

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

        layer_infos = self._plan_layers(params)
        base_params = params
        if params.prime_tower.enabled:
            base_params = deepcopy(params)
            base_params.prime_tower.enabled = False

        connected_context = self._build_connected_preview_context(contours, base_params)
        base_layers = [
            self._generate_layer(contours, info, base_params, connected_context)
            for info in layer_infos
        ]

        safety_layers: List[Layer] = []
        if params.shell.safety_line_count > 0:
            safety_layers = self._generate_safety_lines(contours, params)

        if params.prime_tower.enabled:
            self.prime_tower_generator.validate(params)
            for info, layer in zip(layer_infos, base_layers):
                prime_tower_paths = self.prime_tower_generator.generate_layer_paths(
                    info,
                    params,
                    self._generate_line_fill,
                )
                if prime_tower_paths:
                    layer.paths = prime_tower_paths + layer.paths

        layers = [layer for layer in base_layers if layer.paths]
        if safety_layers:
            layers = safety_layers + layers

        return self._create_result(layers, params)

    def validate_prime_tower_placement(
        self,
        contours: List[Contour],
        params: SliceParams,
    ) -> None:
        """Validate prime tower bounds and collisions without mutating slice output."""
        if not params.prime_tower.enabled:
            return

        if not contours:
            self.prime_tower_generator.validate(params)
            return

        base_params = deepcopy(params)
        base_params.prime_tower.enabled = False
        layer_infos = self._plan_layers(params)
        connected_context = self._build_connected_preview_context(contours, base_params)
        base_layers = [
            self._generate_layer(contours, info, base_params, connected_context)
            for info in layer_infos
        ]
        safety_layers: List[Layer] = []
        if params.shell.safety_line_count > 0:
            safety_layers = self._generate_safety_lines(contours, params)

        occupancy_geometry = self.prime_tower_generator.build_occupied_geometry(
            safety_layers + base_layers
        )
        self.prime_tower_generator.validate(params, occupancy_geometry)

    def validate_prime_tower_2d_placement(
        self,
        contours: List[Contour],
        params: SliceParams,
    ) -> None:
        """Validate prime tower placement against the source 2D contour footprint."""
        if not params.prime_tower.enabled:
            return

        if not contours:
            self.prime_tower_generator.validate(params)
            return

        contour_geometry = self.prime_tower_generator.build_contours_geometry(contours)
        self.prime_tower_generator.validate(params, contour_geometry)

    def _plan_layers(self, params: SliceParams) -> List[LayerInfo]:
        """
        规划所有层

        考虑因素：
        - 总高度和层高
        - 换色层配置
        - 台阶位置
        - 防翘裙边位置
        - 包边/勾边位置
        - 底面封闭位置
        """
        layer_height = params.shell.layer_height
        total_height = params.shell.height
        layer_count = max(1, int(total_height / layer_height))
        skirt_layer_count = self._get_skirt_layer_count(params, layer_height, layer_count)

        change_points = self._build_color_change_points(params)

        # 构建台阶层映射
        step_layer_map = self._build_step_layer_map(params, layer_height)

        # 底面层数（根据厚度自动计算）
        bottom_face_layer_count = 0
        bottom_face_thickness = resolve_bottom_face_thickness(params)
        if is_bottom_face_effective(params) and bottom_face_thickness > 0.0:
            bottom_face_layer_count = max(1, int(bottom_face_thickness / layer_height + 0.5))

        # 顶面层数（根据厚度自动计算）
        top_face_layer_count = 0
        if params.top_face.enabled:
            top_face_layer_count = max(1, int(params.top_face.thickness / layer_height + 0.5))

        layer_infos = []
        for i in range(layer_count):
            z = i * layer_height

            # 单喷头 Klipper：始终使用逻辑上的单喷头，颜色仅作为换色槽位
            extruder = ExtruderType.EXTRUDER_1
            color_index = self._get_color_index_at_height(z, change_points)

            # 检查是否台阶层
            is_step = z in step_layer_map
            step_config = step_layer_map.get(z)

            # 检查是否首层
            is_first = (i == 0)
            has_skirt = i < skirt_layer_count

            # 检查是否顶层（需要包边/勾边）
            is_last = (i == layer_count - 1)
            has_edge_wrap = is_last and (params.edge_wrap.wrap_enabled or
                                          params.edge_wrap.outline_enabled)

            # 检查是否底面层
            has_bottom_face = (i < bottom_face_layer_count) and is_bottom_face_effective(params)

            # 检查是否顶面层
            has_top_face = (i >= layer_count - top_face_layer_count) and params.top_face.enabled

            info = LayerInfo(
                z_height=z,
                layer_height=layer_height,
                extruder=extruder,
                color_index=color_index,
                is_first_layer=is_first,
                is_step_layer=is_step,
                step_config=step_config,
                has_skirt=has_skirt,
                has_edge_wrap=has_edge_wrap,
                has_bottom_face=has_bottom_face,
                has_top_face=has_top_face
            )
            layer_infos.append(info)

        return layer_infos

    @staticmethod
    def _get_skirt_layer_count(
        params: SliceParams,
        layer_height: float,
        total_layer_count: int,
    ) -> int:
        """Return how many leading layers should emit skirt paths."""
        if not params.skirt.enabled or total_layer_count <= 0:
            return 0
        if layer_height <= 0:
            return 1
        return min(
            total_layer_count,
            max(1, int(params.skirt.height / layer_height + 0.5)),
        )

    def _build_color_change_points(self, params: SliceParams) -> List[tuple[float, int]]:
        """构建换色高度与当前逻辑颜色槽位映射。"""
        if not params.color.enabled or not params.color.change_points:
            return []
        return [
            (point.height_mm, point.macro_index)
            for point in params.color.change_points
        ]

    def _build_step_layer_map(self, params: SliceParams,
                               layer_height: float) -> Dict[float, StepConfig]:
        """构建台阶层高度-配置映射"""
        # 使用台阶生成器来构建映射
        return self.step_generator.get_step_layers(
            params.step,
            params.shell.height,
            layer_height
        )

    def _get_color_index_at_height(
        self,
        z: float,
        change_points: List[tuple[float, int]],
    ) -> int:
        """获取指定高度对应的当前逻辑颜色槽位。"""
        color_index = 0
        for height_mm, macro_index in change_points:
            if z + 1e-6 >= height_mm:
                color_index = macro_index
            else:
                break
        return color_index

    def _sort_contours_for_print(self, contours: List[Contour]) -> List[Contour]:
        """按用户设置的打印顺序稳定排序轮廓。"""
        return [
            contour
            for _index, contour in sorted(
                enumerate(contours),
                key=lambda item: (item[1].print_order, item[0]),
            )
        ]

    def _generate_layer(self, contours: List[Contour],
                        info: LayerInfo,
                        params: SliceParams,
                        connected_context: Optional[ConnectedPreviewContext] = None) -> Layer:
        """
        生成单层

        处理顺序：
        1. 应用边缘轮廓（斜边收缩）
        2. 生成防翘裙边（如需要）
        3. 生成壁路径
        4. 生成底面填充（如需要）
        5. 生成自定义台阶（如需要）
        6. 生成面板台阶（顶部台阶）
        7. 生成底板台阶（底部台阶）
        """
        layer = Layer(
            z_height=info.z_height,
            layer_height=info.layer_height,
            extruder=info.extruder,
            color_index=info.color_index,
        )

        if info.has_skirt:
            layer.paths.extend(self._generate_all_skirt_paths(contours, params))

        modified_contours: List[Optional[Contour]] = []
        bottom_reference_contours: List[Optional[Contour]] = []
        light_slot_geometries: List[Optional[LightSlotGeometry]] = []

        u_flat_height = resolve_bottom_face_thickness(params)

        for contour in contours:
            modified_contour = self._apply_edge_profile(
                contour,
                info.z_height,
                params.shell,
                u_flat_height=u_flat_height,
            )
            modified_contours.append(modified_contour)

            if modified_contour is None:
                bottom_reference_contours.append(None)
                light_slot_geometries.append(None)
                continue

            bottom_reference_contour = modified_contour
            light_slot_geometry = None
            needs_bottom_reference = (
                params.light_slot.enabled and (
                    info.z_height < params.light_slot.depth or info.has_bottom_face
                )
            )
            if needs_bottom_reference:
                bottom_reference_contour = self._apply_edge_profile(
                    contour,
                    0.0,
                    params.shell,
                    u_flat_height=u_flat_height,
                ) or modified_contour
                light_slot_geometry = self.light_slot_geometry_builder.build(
                    bottom_reference_contour,
                    params,
                )

            bottom_reference_contours.append(bottom_reference_contour)
            light_slot_geometries.append(light_slot_geometry)

        layer.paths.extend(
            self._generate_wall_paths_in_loop_order(
                contours,
                modified_contours,
                info,
                params.shell,
            )
        )

        for modified_contour, bottom_reference_contour, light_slot_geometry in zip(
            modified_contours,
            bottom_reference_contours,
            light_slot_geometries,
        ):
            if modified_contour is None or bottom_reference_contour is None:
                continue

            shell_line_width = resolve_shell_line_width(
                params.shell.line_width,
                params.shell.layer_height,
                wall_thickness=params.shell.wall_thickness,
                wall_count=params.shell.wall_count,
            )
            shell_wall_thickness = resolve_shell_wall_thickness(
                params.shell.line_width,
                params.shell.wall_count,
                params.shell.layer_height,
                wall_thickness=params.shell.wall_thickness,
            )

            # 3. 生成灯槽（如需要）
            if light_slot_geometry is not None:
                light_slot_paths = self._generate_light_slot_paths(
                    light_slot_geometry,
                    info,
                    params,
                )
                layer.paths.extend(light_slot_paths)

            # 4. 生成底面填充（如需要）
            if info.has_bottom_face:
                bottom_face_paths = self._generate_bottom_face_paths(
                    bottom_reference_contour,
                    info,
                    params,
                    light_slot_geometry=light_slot_geometry,
                )
                layer.paths.extend(bottom_face_paths)

            # 4.5. 生成顶面填充（如需要）
            if info.has_top_face:
                top_face_paths = self._generate_top_face_paths(
                    modified_contour, info, params
                )
                layer.paths.extend(top_face_paths)

            # 5. 生成自定义台阶（如需要）
            if info.is_step_layer and info.step_config:
                step_paths = self.step_generator.generate_step_for_layer(
                    modified_contour,
                    info.z_height,
                    info.layer_height,
                    info.step_config,
                    params.step,
                    shell_wall_thickness,
                    info.extruder,
                    path_line_width=shell_line_width,
                )
                layer.paths.extend(step_paths)

            # 6. 生成面板台阶（顶部台阶）
            if params.step.panel_step_enabled:
                panel_step_paths = self.step_generator.generate_panel_step_for_layer(
                    modified_contour,
                    info.z_height,
                    info.layer_height,
                    params.shell.height,
                    params.step,
                    shell_wall_thickness,
                    info.extruder,
                    path_line_width=shell_line_width,
                )
                layer.paths.extend(panel_step_paths)

            # 7. 生成底板台阶（底部台阶）
            if params.step.baseplate_step_enabled:
                baseplate_step_paths = self.step_generator.generate_baseplate_step_for_layer(
                    modified_contour,
                    info.z_height,
                    info.layer_height,
                    params.shell.height,
                    params.step,
                    shell_wall_thickness,
                    info.extruder,
                    path_line_width=shell_line_width,
                )
                layer.paths.extend(baseplate_step_paths)

        # 8. 生成连襟结构（用于 3D 预览与切片导出）
        if connected_context is not None:
            connected_paths = self._generate_connected_paths_for_layer(
                connected_context, info.z_height, params
            )
            layer.paths.extend(connected_paths)

        return layer

    def _build_connected_preview_context(
        self,
        contours: List[Contour],
        params: SliceParams,
    ) -> Optional[ConnectedPreviewContext]:
        """Precompute connected-letter bridges once per slice."""
        if not params.connected.enabled or not contours:
            return None

        connected_contours: List[Contour] = []
        for contour in contours:
            base_contour = self._apply_edge_profile(
                contour,
                0.0,
                params.shell,
                u_flat_height=resolve_bottom_face_thickness(params),
            )
            if base_contour is not None:
                connected_contours.append(base_contour)

        if not connected_contours:
            return None

        context = ConnectedPreviewContext(contours=connected_contours)

        if params.connected.auto_detect:
            context.bridges = self.connected_generator.find_connection_bridges(
                connected_contours,
                params.connected,
            )

        return context

    def _generate_connected_paths_for_layer(
        self,
        context: ConnectedPreviewContext,
        z_height: float,
        params: SliceParams,
    ) -> List[LayerPath]:
        """Generate connected-letter preview paths using cached bridge data."""
        if not params.connected.enabled:
            return []

        if params.connected.auto_detect:
            if not context.bridges:
                return []
            return self.connected_generator.generate_connected_layer(
                context.bridges,
                z_height,
                params.connected,
            )

        return self.connected_generator.generate_connected(
            context.contours,
            z_height,
            params.connected,
        )

    def _apply_edge_profile(
        self,
        contour: Contour,
        z: float,
        params: ShellParams,
        u_flat_height: float = 0.0,
    ) -> Optional[Contour]:
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
        elif params.edge_type == EdgeType.U_SHAPED:
            return self._apply_u_shaped_edge(contour, z, params, u_flat_height)
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

        斜边结构（包含底板区域、斜边区域、面板区域三部分）：

        总高度 = 底板厚度 + 斜边高度 + 面板厚度
        斜边高度 = 总高度 - 底板厚度 - 面板厚度

        原始轮廓始终以底面 z=0 为基准。

        上小下大 (TOP_SMALL)：底面保持原始尺寸，顶部小
        ┌───────┐  ← 面板区域（最小，收缩 bevel_width）
        │╲     ╱│
        │ ╲   ╱ │  ← 斜边区域（线性收缩）
        │  ╲ ╱  │
        │   │   │  ← 底板区域（最大，不收缩）
        └───┴───┘

        上大下小 (TOP_LARGE)：底面保持原始尺寸，顶部大
        ┌─────────┐  ← 面板区域（最大，外扩 bevel_width）
        │ ╱     ╲ │
        │╱       ╲│  ← 斜边区域（线性外扩）
        │    │    │
        │    │    │  ← 底板区域（基准尺寸，不偏移）
        └───────┘
        """
        total_height = params.height
        baseplate_thickness = params.baseplate_thickness
        panel_thickness = params.panel_thickness
        bevel_width = params.bevel_width

        # 计算区域边界
        baseplate_top = baseplate_thickness  # 底板区域顶部
        panel_bottom = total_height - panel_thickness  # 面板区域底部

        # 斜边区域就是中间部分
        # 注意：如果底板+面板厚度超过总高度，则没有斜边区域

        if params.bevel_direction == BevelDirection.TOP_SMALL:
            # 上小下大：底面保持原始轮廓，向上逐渐内缩
            if z < baseplate_top:
                # 底板区域：不收缩
                offset = 0
            elif z < panel_bottom:
                # 斜边区域：线性收缩
                bevel_height = panel_bottom - baseplate_top
                if bevel_height > 0:
                    progress = (z - baseplate_top) / bevel_height
                    offset = -progress * bevel_width
                else:
                    offset = 0
            else:
                # 面板区域：最大收缩
                offset = -bevel_width
        else:
            # 上大下小：底面保持原始轮廓，向上逐渐外扩
            if z < baseplate_top:
                # 底板区域：保持基准尺寸
                offset = 0
            elif z < panel_bottom:
                # 斜边区域：从基准尺寸线性放大
                bevel_height = panel_bottom - baseplate_top
                if bevel_height > 0:
                    progress = (z - baseplate_top) / bevel_height
                    offset = progress * bevel_width
                else:
                    offset = 0
            else:
                # 面板区域：保持最大外扩
                offset = bevel_width

        if abs(offset) < 0.001:
            return contour

        # 应用偏移
        # 注意：对于斜边字，外轮廓和内孔需要同方向偏移（让整个字形缩放）
        # 而不是使用 offset_contour（它会让内孔反方向偏移以保持壁厚）
        return self._offset_contour_same_direction(contour, offset)

    def _apply_custom_edge(self, contour: Contour, z: float,
                            params: ShellParams) -> Optional[Contour]:
        """
        异形边处理

        使用EdgeProfileGenerator根据EdgeProfile定义的轮廓进行高级插值，
        支持线性、三次样条、贝塞尔曲线和B样条插值。

        Args:
            contour: 输入轮廓
            z: 当前层高度
            params: 字壳参数

        Returns:
            处理后的轮廓，如果消失则返回None
        """
        if not params.edge_profile:
            return contour

        profile = params.edge_profile
        total_height = params.height
        bevel_width = params.bevel_width

        # 归一化高度
        normalized_z = z / total_height if total_height > 0 else 0

        # 使用新的EdgeProfile方法获取偏移量
        if profile.control_points:
            # 新格式：使用control_points
            offset = profile.get_offset_at_height(normalized_z, bevel_width, total_height)
        elif profile.points:
            # 旧格式兼容：使用points列表
            offset = self._interpolate_profile_legacy(profile, normalized_z)
        else:
            return contour

        if abs(offset) < 0.001:
            return contour

        # 应用偏移（异形边需要同方向偏移，让整个字形缩放）
        return self._offset_contour_same_direction(contour, offset)

    def _apply_u_shaped_edge(
        self,
        contour: Contour,
        z: float,
        params: ShellParams,
        flat_height: float = 0.0,
    ) -> Optional[Contour]:
        """Apply the U-shaped bottom arc: outer expands outward, holes shrink inward."""
        offset = calculate_u_shape_offset_at_z(z, params, flat_height)
        if abs(offset) < 0.001:
            return contour

        return self.path_offset.offset_contour(contour, offset, JoinType.MITER)

    def _interpolate_profile_legacy(self, profile, normalized_z: float) -> float:
        """在异形边轮廓中插值（旧格式兼容）"""
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

    def _offset_contour_same_direction(self, contour: Contour,
                                        distance: float) -> Optional[Contour]:
        """
        对整个轮廓进行同方向偏移

        与 offset_contour 不同，这里外轮廓和内孔使用相同方向的偏移，
        用于实现斜边字的整体缩放效果。

        Args:
            contour: 输入轮廓
            distance: 偏移距离（正=外扩，负=内缩）

        Returns:
            偏移后的轮廓，如果消失则返回None
        """
        # 偏移外轮廓
        outer_results = self.path_offset.offset(contour.outer, distance, JoinType.MITER)
        if not outer_results:
            return None

        new_outer = outer_results[0]

        # 偏移内孔（同方向偏移）
        new_holes = []
        for hole in contour.holes:
            hole_results = self.path_offset.offset(hole, distance, JoinType.MITER)
            new_holes.extend(hole_results)

        return Contour(
            outer=new_outer,
            holes=new_holes,
            connected_frames=contour.connected_frames,
            patterns=contour.patterns,
            screw_hole_centers=[Point(point.x, point.y) for point in contour.screw_hole_centers],
            name=contour.name,
            asset_id=contour.asset_id,
            asset_name=contour.asset_name,
            group_id=contour.group_id,
            start_point_index=contour.start_point_index,
            print_order=contour.print_order,
        )

    def _generate_wall_paths_in_loop_order(
        self,
        contours: List[Contour],
        modified_contours: List[Optional[Contour]],
        info: LayerInfo,
        params: ShellParams,
    ) -> List[LayerPath]:
        """Generate wall paths in the global outer/hole loop order."""
        paths: List[LayerPath] = []

        for contour_index, hole_index in build_loop_order(contours):
            if not (0 <= contour_index < len(modified_contours)):
                continue

            modified_contour = modified_contours[contour_index]
            if modified_contour is None:
                continue

            if hole_index < 0:
                loop_path = modified_contour.outer
                start_point_index = resolve_contour_start_point_index(modified_contour)
                offset_sign = 1.0
            else:
                if hole_index >= len(modified_contour.holes):
                    continue
                loop_path = modified_contour.holes[hole_index]
                start_point_index = resolve_path_start_point_index(loop_path)
                offset_sign = -1.0

            paths.extend(
                self._generate_wall_paths_for_loop(
                    loop_path,
                    start_point_index,
                    offset_sign,
                    info,
                    params,
                )
            )

        return paths

    def _generate_wall_paths_for_loop(
        self,
        loop_path: Path,
        start_point_index: int,
        offset_sign: float,
        info: LayerInfo,
        params: ShellParams,
    ) -> List[LayerPath]:
        """Generate all wall passes for one loop as a consecutive block."""
        paths: List[LayerPath] = []
        line_width = resolve_shell_line_width(
            params.line_width,
            params.layer_height,
            wall_thickness=params.wall_thickness,
            wall_count=params.wall_count,
        )
        wall_offset = params.wall_offset if params.wall_offset > 0 else line_width

        for i in range(params.wall_count):
            offset_distance = -(line_width / 2 + i * wall_offset) * offset_sign
            offset_results = self.path_offset.offset(
                loop_path,
                offset_distance,
                JoinType.MITER,
            )

            for offset_path in offset_results:
                rotated_points = self._rotate_path_to_user_start(
                    offset_path.points,
                    loop_path.points,
                    start_point_index,
                )
                paths.append(
                    LayerPath(
                        points=rotated_points,
                        role=PathRole.WALL,
                        extruder=info.extruder,
                        line_width=line_width,
                        is_closed=True,
                    )
                )

        return paths

    def _rotate_path_to_user_start(
        self,
        points: List[Point],
        reference_points: List[Point],
        start_point_index: int,
    ) -> List[Point]:
        """让闭合路径尽量从用户选择的起点附近开始。"""
        if (
            not points
            or not reference_points
            or start_point_index < 0
            or start_point_index >= len(reference_points)
        ):
            return list(points)

        target = reference_points[start_point_index]
        closest_index = min(
            range(len(points)),
            key=lambda index: math.hypot(
                points[index].x - target.x,
                points[index].y - target.y,
            ),
        )
        return list(points[closest_index:] + points[:closest_index])

    def _generate_all_skirt_paths(self, contours: List[Contour],
                                   params: SliceParams) -> List[LayerPath]:
        """
        生成所有轮廓的防翘裙边路径（带壁区域裁剪）

        统一处理所有轮廓，确保裙边不侵入任何轮廓的壁区域。

        Args:
            contours: 所有轮廓
            params: 切片参数

        Returns:
            裁剪后的裙边路径列表
        """
        paths = []
        skirt_params = params.skirt

        if not skirt_params.enabled:
            return paths

        wall_thickness = resolve_shell_wall_thickness(
            params.shell.line_width,
            params.shell.wall_count,
            params.shell.layer_height,
            wall_thickness=params.shell.wall_thickness,
        )

        for contour in contours:
            contour_skirt_paths = self.skirt_generator.generate_skirt_clipped(
                contour=contour,
                all_contours=contours,
                params=skirt_params,
                wall_thickness=wall_thickness,
                path_offset=self.path_offset,
                path_line_width=(
                    params.machine.nozzle_diameter
                    if params.machine.nozzle_diameter > 0.0
                    else None
                ),
            )
            paths.extend(contour_skirt_paths)

        return paths

    def _generate_skirt_paths(self, contour: Contour,
                               params: SliceParams) -> List[LayerPath]:
        """
        生成防翘裙边路径（旧版，不带裁剪）

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

    def _generate_light_slot_paths(
        self,
        geometry: LightSlotGeometry,
        info: LayerInfo,
        params: SliceParams,
    ) -> List[LayerPath]:
        """Generate bottom light-slot floor fill and free-edge wall paths."""
        slot_params = params.light_slot
        if (
            not slot_params.enabled
            or slot_params.width <= 0.0
            or slot_params.depth <= 0.0
            or info.z_height >= slot_params.depth
        ):
            return []

        paths = [
            LayerPath(
                points=[Point(point.x, point.y) for point in free_edge_path.points],
                role=PathRole.LIGHT_SLOT,
                extruder=info.extruder,
                line_width=resolve_shell_line_width(
                    params.shell.line_width,
                    params.shell.layer_height,
                ),
                is_closed=free_edge_path.is_closed,
            )
            for free_edge_path in geometry.slot_free_edge_paths
            if free_edge_path.points
        ]

        floor_thickness = min(
            params.shell.layer_height * max(0, slot_params.floor_layers),
            slot_params.depth,
        )
        if info.z_height < floor_thickness:
            paths.extend(
                self._generate_fill_paths_for_polygons(
                    geometry.slot_band_polygons,
                    info,
                    resolve_shell_line_width(
                        params.shell.line_width,
                        params.shell.layer_height,
                    ),
                    PathRole.LIGHT_SLOT,
                )
            )

        return paths

    def _generate_fill_paths_for_polygons(
        self,
        polygons,
        info: LayerInfo,
        line_width: float,
        role: PathRole,
    ) -> List[LayerPath]:
        """Generate 100% line fill for a list of shapely polygons."""
        if not polygons or line_width <= 0.0:
            return []

        fill_spacing = line_width
        layer_index = int(info.z_height / info.layer_height) if info.layer_height > 0 else 0
        fill_angle = 45.0 + (layer_index * 90.0)

        paths: List[LayerPath] = []
        for polygon in polygons:
            contour = self._polygon_to_contour(polygon)
            if contour is None:
                continue

            fill_paths = self._generate_line_fill(
                contour,
                fill_spacing,
                fill_angle,
                line_width,
                info.extruder,
            )
            for path in fill_paths:
                path.role = role
            paths.extend(fill_paths)

        return paths

    def _polygon_to_contour(self, polygon) -> Optional[Contour]:
        """Convert a shapely polygon into a Contour for fill clipping."""
        if polygon is None or polygon.is_empty or polygon.area < 1e-6:
            return None

        exterior_coords = list(polygon.exterior.coords)
        if len(exterior_coords) < 4:
            return None

        outer = Path(
            points=[Point(x, y) for x, y in exterior_coords[:-1]],
            path_type=PathType.OUTER,
            is_closed=True,
        )

        holes = []
        for interior in polygon.interiors:
            hole_coords = list(interior.coords)
            if len(hole_coords) < 4:
                continue
            holes.append(
                Path(
                    points=[Point(x, y) for x, y in hole_coords[:-1]],
                    path_type=PathType.HOLE,
                    is_closed=True,
                )
            )

        return Contour(outer=outer, holes=holes)

    def _generate_bottom_face_paths(
        self,
        contour: Contour,
        info: LayerInfo,
        params: SliceParams,
        light_slot_geometry: Optional[LightSlotGeometry] = None,
    ) -> List[LayerPath]:
        """
        生成底面填充路径

        底面填充用于封闭字壳底部，生成密实填充层。
        使用固定的填充参数：100%密度、45度角、交替方向。

        Args:
            contour: 当前层的轮廓
            info: 层信息
            params: 切片参数

        Returns:
            底面填充路径列表
        """
        paths = []
        if not is_bottom_face_effective(params):
            return paths

        del light_slot_geometry
        fill_line_width = resolve_shell_line_width(
            params.shell.line_width,
            params.shell.layer_height,
            wall_thickness=params.shell.wall_thickness,
            wall_count=params.shell.wall_count,
        )
        geometry = self.bottom_face_geometry_builder.build(contour, params)

        for hole_path in geometry.hole_boundary_paths:
            paths.append(
                LayerPath(
                    points=[Point(point.x, point.y) for point in hole_path.points],
                    role=PathRole.FILL_BOTTOM_FACE,
                    extruder=info.extruder,
                    line_width=fill_line_width,
                    is_closed=True,
                )
            )

        paths.extend(
            self._generate_fill_paths_for_polygons(
                geometry.fill_polygons,
                info,
                fill_line_width,
                PathRole.FILL_BOTTOM_FACE,
            )
        )
        return paths

        # 固定填充参数
        fill_line_width = resolve_shell_line_width(
            params.shell.line_width,
            params.shell.layer_height,
            wall_thickness=params.shell.wall_thickness,
            wall_count=params.shell.wall_count,
        )
        fill_spacing = fill_line_width  # 100%密度：间距等于线宽

        # 计算填充区域（内缩壁厚）
        inset_distance = resolve_shell_wall_thickness(
            params.shell.line_width,
            params.shell.wall_count,
            params.shell.layer_height,
            wall_thickness=params.shell.wall_thickness,
        )

        # 计算填充角度（每层交替90度）
        layer_index = int(info.z_height / info.layer_height)
        fill_angle = 45.0 + (layer_index * 90.0)

        # 内缩轮廓
        inset_contour = self.path_offset.offset_contour(contour, -inset_distance)
        if not inset_contour:
            return paths

        # 生成填充线
        fill_paths = self._generate_line_fill(
            inset_contour,
            fill_spacing,
            fill_angle,
            fill_line_width,
            info.extruder
        )

        # 设置路径角色
        for path in fill_paths:
            path.role = PathRole.FILL_BOTTOM_FACE

        paths.extend(fill_paths)

        return paths

    def _generate_top_face_paths(self, contour: Contour,
                                    info: LayerInfo,
                                    params: SliceParams) -> List[LayerPath]:
        """
        生成顶面填充路径

        顶面填充用于封闭字壳顶部，生成密实填充层。
        使用固定的填充参数：100%密度、45度角、交替方向。

        Args:
            contour: 当前层的轮廓
            info: 层信息
            params: 切片参数

        Returns:
            顶面填充路径列表
        """
        paths = []
        top_params = params.top_face

        if not top_params.enabled:
            return paths

        fill_line_width = resolve_shell_line_width(
            params.shell.line_width,
            params.shell.layer_height,
            wall_thickness=params.shell.wall_thickness,
            wall_count=params.shell.wall_count,
        )
        geometry = self.top_face_geometry_builder.build(contour, params)
        paths.extend(
            self._generate_fill_paths_for_polygons(
                geometry.fill_polygons,
                info,
                fill_line_width,
                PathRole.FILL_TOP_FACE,
            )
        )

        return paths

    def _generate_line_fill(self, contour: Contour, spacing: float,
                            angle: float, line_width: float,
                            extruder: ExtruderType) -> List[LayerPath]:
        """
        生成线性填充

        算法：
        1. 获取边界框
        2. 生成旋转后的扫描线
        3. 与轮廓求交
        4. 连接相邻线段（减少空走）

        Args:
            contour: 填充区域轮廓
            spacing: 填充间距
            angle: 填充角度（度）
            line_width: 填充线宽
            extruder: 挤出机类型

        Returns:
            填充路径列表
        """
        if spacing <= 0:
            return []

        # 获取边界框
        min_x, min_y, max_x, max_y = contour.outer.bounds

        # 扩展边界（确保覆盖旋转后的区域）
        diagonal = math.sqrt((max_x - min_x) ** 2 + (max_y - min_y) ** 2)
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2

        # 旋转角度（弧度）
        rad = math.radians(angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        # 生成扫描线
        scan_lines = []
        y = center_y - diagonal / 2
        while y < center_y + diagonal / 2:
            # 旋转后的扫描线端点
            x1 = center_x - diagonal
            x2 = center_x + diagonal

            # 旋转回原坐标系
            start = Point(
                center_x + (x1 - center_x) * cos_a - (y - center_y) * sin_a,
                center_y + (x1 - center_x) * sin_a + (y - center_y) * cos_a
            )
            end = Point(
                center_x + (x2 - center_x) * cos_a - (y - center_y) * sin_a,
                center_y + (x2 - center_x) * sin_a + (y - center_y) * cos_a
            )

            scan_lines.append((start, end))
            y += spacing

        # 与轮廓求交
        clipped_segments = self._clip_lines_to_contour(scan_lines, contour)

        # 连接相邻线段
        connected_paths = self._connect_fill_segments(
            clipped_segments,
            fill_geometry=self._contour_to_polygon_geometry(contour),
        )

        # 创建LayerPath对象
        paths = []
        for segment_points in connected_paths:
            if len(segment_points) >= 2:
                path = LayerPath(
                    points=segment_points,
                    role=PathRole.FILL_BOTTOM_FACE,
                    extruder=extruder,
                    line_width=line_width,
                    is_closed=False
                )
                paths.append(path)

        return paths

    def _clip_lines_to_contour(self, lines: List[tuple],
                                contour: Contour) -> List[tuple]:
        """
        裁剪线段到轮廓内部

        使用线段-多边形求交算法

        Args:
            lines: 扫描线列表 [(start, end), ...]
            contour: 轮廓

        Returns:
            裁剪后的线段列表
        """
        clipped = []
        polygon = self._contour_to_polygon_geometry(contour)
        if polygon is None:
            return clipped

        for start, end in lines:
            scan_line = LineString([(start.x, start.y), (end.x, end.y)])
            intersection = polygon.intersection(scan_line)
            clipped.extend(
                self._extract_line_segments_from_geometry(intersection, start)
            )

        return clipped

    def _contour_to_polygon_geometry(self, contour: Contour) -> Optional[Polygon]:
        """Build a shapely polygon so fill clipping respects holes exactly."""
        outer_coords = [(point.x, point.y) for point in contour.outer.points]
        if len(outer_coords) < 3:
            return None

        hole_coords = []
        for hole in contour.holes:
            coords = [(point.x, point.y) for point in hole.points]
            if len(coords) >= 3:
                hole_coords.append(coords)

        polygon = Polygon(outer_coords, hole_coords)
        if not polygon.is_valid:
            polygon = polygon.buffer(0)
        if polygon.is_empty or polygon.area < 1e-6:
            return None
        return polygon

    def _extract_line_segments_from_geometry(
        self,
        geometry,
        scan_start: Point,
    ) -> List[tuple[Point, Point]]:
        """Flatten shapely intersections back into ordered printable segments."""
        if geometry.is_empty:
            return []

        if geometry.geom_type == "LineString":
            coords = list(geometry.coords)
            if len(coords) < 2 or geometry.length <= 1e-6:
                return []
            start = Point(coords[0][0], coords[0][1])
            end = Point(coords[-1][0], coords[-1][1])
            if (
                (end.x - scan_start.x) ** 2 + (end.y - scan_start.y) ** 2
                < (start.x - scan_start.x) ** 2 + (start.y - scan_start.y) ** 2
            ):
                start, end = end, start
            return [(start, end)]

        if geometry.geom_type in {"MultiLineString", "GeometryCollection"}:
            segments: List[tuple[Point, Point]] = []
            for child in geometry.geoms:
                segments.extend(
                    self._extract_line_segments_from_geometry(child, scan_start)
                )
            segments.sort(
                key=lambda segment: (
                    (segment[0].x - scan_start.x) ** 2
                    + (segment[0].y - scan_start.y) ** 2
                )
            )
            return segments

        return []

    def _line_polygon_intersections(self, start: Point, end: Point,
                                    polygon) -> List[Point]:
        """计算线段与多边形的所有交点"""
        intersections = []
        n = len(polygon.points)

        for i in range(n):
            j = (i + 1) % n
            p1 = polygon.points[i]
            p2 = polygon.points[j]

            intersection = self._line_line_intersection(start, end, p1, p2)
            if intersection:
                intersections.append(intersection)

        return intersections

    def _line_line_intersection(self, p1: Point, p2: Point,
                                p3: Point, p4: Point):
        """
        计算两线段的交点

        使用参数方程法
        """
        x1, y1 = p1.x, p1.y
        x2, y2 = p2.x, p2.y
        x3, y3 = p3.x, p3.y
        x4, y4 = p4.x, p4.y

        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 1e-10:
            return None

        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

        if 0 <= t <= 1 and 0 <= u <= 1:
            x = x1 + t * (x2 - x1)
            y = y1 + t * (y2 - y1)
            return Point(x, y)

        return None

    def _point_in_polygon(self, point: Point, polygon) -> bool:
        """
        判断点是否在多边形内

        使用射线法（Ray Casting）
        """
        n = len(polygon.points)
        inside = False

        p1x, p1y = polygon.points[0].x, polygon.points[0].y
        for i in range(1, n + 1):
            p2x, p2y = polygon.points[i % n].x, polygon.points[i % n].y
            if point.y > min(p1y, p2y):
                if point.y <= max(p1y, p2y):
                    if point.x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (point.y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or point.x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside

    def _connect_fill_segments(
        self,
        segments: List[tuple],
        fill_geometry: Optional[Polygon] = None,
    ) -> List[List[Point]]:
        """
        连接相邻线段减少空走

        使用贪心算法：按Y坐标排序，交替方向连接

        Args:
            segments: 线段列表 [(start, end), ...]

        Returns:
            连接后的路径点列表
        """
        if not segments:
            return []

        # 按起点Y坐标排序
        sorted_segments = sorted(segments, key=lambda s: s[0].y)

        connected = []
        current_path = []
        reverse_next = False

        for seg in sorted_segments:
            start, end = seg
            if reverse_next:
                start, end = end, start

            if current_path:
                # 检查���否可以连接
                last_point = current_path[-1]
                distance = math.sqrt(
                    (start.x - last_point.x) ** 2 +
                    (start.y - last_point.y) ** 2
                )

                can_connect = distance <= 5
                if can_connect and fill_geometry is not None and distance > 1e-6:
                    connector = LineString(
                        [(last_point.x, last_point.y), (start.x, start.y)]
                    )
                    can_connect = fill_geometry.buffer(1e-6).covers(connector)

                if not can_connect:  # 超过阈值或连接线离开合法填充区域，开始新路径
                    if len(current_path) >= 2:
                        connected.append(current_path)
                    current_path = [start, end]
                else:
                    current_path.extend([start, end])
            else:
                current_path = [start, end]

            reverse_next = not reverse_next

        if len(current_path) >= 2:
            connected.append(current_path)

        return connected

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
                offset_distance = offset + i * resolve_shell_wall_thickness(
                    params.shell.line_width,
                    params.shell.wall_count,
                    params.shell.layer_height,
                    wall_thickness=params.shell.wall_thickness,
                )
                offset_paths = self.path_offset.offset(
                    contour.outer, offset_distance, JoinType.MITER
                )

                for path in offset_paths:
                    layer_path = LayerPath(
                        points=path.points,
                        role=PathRole.SAFETY_LINE,
                        extruder=ExtruderType.EXTRUDER_1,
                        line_width=resolve_shell_line_width(
                            params.shell.line_width,
                            params.shell.layer_height,
                        ),
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
        line_width = resolve_shell_line_width(
            params.shell.line_width,
            params.shell.layer_height,
        )
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
