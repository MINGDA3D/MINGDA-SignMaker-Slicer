"""
MINGDA SignMaker - 台阶/V槽生成器模块

生成台阶和V槽结构，用于安装面板和底板。

台阶结构说明：
- 平台阶：在字壳内侧向内延伸的水平平台，用于放置面板/底板
- V槽：在字壳内侧形成V型凹槽，面板/底板可卡入

打印原理：
┌─────────────────────┐  ← 顶部
│                     │
├──┐               ┌──┤  ← 顶部台阶（安装面板）
│  │               │  │
│  │  字壳主体     │  │
│  │               │  │
├──┘               └──┤  ← 底部台阶（安装底板）
│                     │
└─────────────────────┘  ← 底部

支持功能：
1. 自定义台阶（1-7个）- 在任意高度生成台阶
2. 顶部台阶 - 用于安装亚克力面板
3. 底部凹槽 - 用于安装底板
4. V型槽 - 斜面嵌入式安装
"""

from __future__ import annotations
import math
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass

from .types import (
    Contour, StepParams, StepConfig, LayerPath, PathRole,
    ExtruderType, Point, Path, LayerInfo
)
from .path_offset import PathOffset, JoinType


@dataclass
class StepLayerInfo:
    """台阶层信息"""
    z_height: float          # 层高度
    offset: float            # 偏移量（向内为负）
    line_width: float        # 线宽
    step_index: int          # 台阶索引
    is_v_groove: bool        # 是否V槽


class StepGenerator:
    """台阶/V槽生成器"""

    SUPPORTED_FLAT_STEP_LINE_WIDTH_SCALE = 1.15
    SUPPORTED_FLAT_STEP_OVERLAP_RATIO = 0.45
    _STEP_LAYER_EPSILON = 1e-6

    def __init__(self, path_offset: Optional[PathOffset] = None):
        self.path_offset = path_offset or PathOffset()

    def generate_steps(self, contour: Contour,
                       step_config: StepConfig,
                       params: StepParams,
                       wall_thickness: float = 1.2,
                       extruder: ExtruderType = ExtruderType.EXTRUDER_1) -> List[LayerPath]:
        """
        在指定高度生成台阶路径

        台阶类型：
        - V型台阶 (is_v_groove=True 或 height > 0): 向内倾斜的V型凹槽
        - 平台阶 (is_v_groove=False 且 height = 0): 向内的平面台阶

        Args:
            contour: 字形轮廓
            step_config: 当前台阶配置
            params: 台阶参数
            wall_thickness: 壁厚
            extruder: 使用的挤出机

        Returns:
            台阶路径列表
        """
        paths = []

        if not step_config.enabled:
            return paths

        # 使用参数中的吐丝宽度
        extrusion_width = params.extrusion_width

        if step_config.is_v_groove or step_config.height > 0:
            # V型台阶
            step_paths = self._generate_v_step(
                contour, step_config, params,
                wall_thickness, extrusion_width, extruder
            )
        else:
            # 平台阶
            step_paths = self._generate_flat_step(
                contour, step_config,
                wall_thickness, extrusion_width, extruder
            )

        paths.extend(step_paths)
        return paths

    def _create_step_paths_for_width(
        self,
        contour: Contour,
        width: float,
        role: PathRole,
        wall_thickness: float,
        extruder: ExtruderType,
        speed_multiplier: float,
    ) -> List[LayerPath]:
        """Generate one closed ring whose physical span matches the requested width."""
        if width <= 0.0:
            return []

        paths: List[LayerPath] = []

        paths.extend(
            self._create_outer_step_paths_for_centerline(
                contour=contour,
                center_from_wall_inner_edge=width / 2,
                line_width=width,
                role=role,
                wall_thickness=wall_thickness,
                extruder=extruder,
                speed_multiplier=speed_multiplier,
            )
        )
        paths.extend(
            self._create_hole_step_paths_for_centerline(
                contour=contour,
                center_from_hole_boundary=width / 2,
                line_width=width,
                role=role,
                extruder=extruder,
                speed_multiplier=speed_multiplier,
            )
        )
        return paths

    def _create_outer_step_paths_for_centerline(
        self,
        contour: Contour,
        center_from_wall_inner_edge: float,
        line_width: float,
        role: PathRole,
        wall_thickness: float,
        extruder: ExtruderType,
        speed_multiplier: float,
    ) -> List[LayerPath]:
        """Create one outer-loop pass centered at the requested distance from the wall inner edge."""
        if line_width <= 0.0:
            return []

        shell_inner_offset = max(wall_thickness, 0.0)
        outer_centerline_offset = -(shell_inner_offset + center_from_wall_inner_edge)
        paths: List[LayerPath] = []

        for offset_path in self.path_offset.offset(
            contour.outer, outer_centerline_offset, JoinType.MITER
        ):
            paths.append(
                LayerPath(
                    points=offset_path.points,
                    role=role,
                    extruder=extruder,
                    line_width=line_width,
                    is_closed=True,
                    speed_multiplier=speed_multiplier,
                )
            )

        return paths

    def _create_hole_step_paths_for_centerline(
        self,
        contour: Contour,
        center_from_hole_boundary: float,
        line_width: float,
        role: PathRole,
        extruder: ExtruderType,
        speed_multiplier: float,
    ) -> List[LayerPath]:
        """Create one pass for each hole centered at the requested distance from the opening boundary."""
        if line_width <= 0.0:
            return []

        paths: List[LayerPath] = []

        for hole in contour.holes:
            for hole_path in self.path_offset.offset(
                hole, center_from_hole_boundary, JoinType.MITER
            ):
                paths.append(
                LayerPath(
                    points=hole_path.points,
                    role=role,
                    extruder=extruder,
                    line_width=line_width,
                    is_closed=True,
                    speed_multiplier=speed_multiplier,
                )
            )

        return paths

    def _resolve_supported_flat_pass_width(
        self,
        target_width: float,
        extrusion_width: float,
        path_line_width: float = 0.0,
    ) -> float:
        """Resolve the preferred per-pass width for horizontal step support passes."""
        base_width = path_line_width if path_line_width > 0.0 else extrusion_width
        if base_width <= 0.0:
            base_width = target_width
        if base_width <= 0.0:
            return target_width
        return base_width * self.SUPPORTED_FLAT_STEP_LINE_WIDTH_SCALE

    def _build_supported_outer_flat_passes(
        self,
        step_width: float,
        extrusion_width: float,
        path_line_width: float = 0.0,
    ) -> List[Tuple[float, float]]:
        """Build outer-loop flat-step passes with intentional wall overlap for support."""
        if step_width <= 0.0:
            return []

        overlap_ratio = self.SUPPORTED_FLAT_STEP_OVERLAP_RATIO
        contribution_ratio = 1.0 - overlap_ratio
        if contribution_ratio <= 0.0:
            return [(step_width / 2, step_width)]

        preferred_pass_width = self._resolve_supported_flat_pass_width(
            step_width,
            extrusion_width,
            path_line_width=path_line_width,
        )
        contribution_target = preferred_pass_width * contribution_ratio
        if contribution_target <= 1e-6:
            return [(step_width / 2, step_width)]

        pass_count = max(1, math.ceil(step_width / contribution_target - 1e-9))
        contribution = step_width / pass_count
        pass_width = step_width / (pass_count * contribution_ratio)
        first_center = contribution - pass_width / 2

        return [
            (first_center + i * contribution, pass_width)
            for i in range(pass_count)
        ]

    def _build_supported_hole_flat_passes(
        self,
        step_width: float,
        extrusion_width: float,
        path_line_width: float = 0.0,
    ) -> List[Tuple[float, float]]:
        """Build hole-step passes anchored at the opening boundary and overlapping inward."""
        if step_width <= 0.0:
            return []

        overlap_ratio = self.SUPPORTED_FLAT_STEP_OVERLAP_RATIO
        contribution_ratio = 1.0 - overlap_ratio
        if contribution_ratio <= 0.0:
            return [(step_width / 2, step_width)]

        preferred_pass_width = self._resolve_supported_flat_pass_width(
            step_width,
            extrusion_width,
            path_line_width=path_line_width,
        )
        if step_width <= preferred_pass_width + 1e-6:
            return [(step_width / 2, step_width)]

        extra_width_per_pass = preferred_pass_width * contribution_ratio
        if extra_width_per_pass <= 1e-6:
            return [(step_width / 2, step_width)]

        pass_count = 1 + max(
            1,
            math.ceil((step_width - preferred_pass_width) / extra_width_per_pass - 1e-9),
        )
        pass_width = step_width / (1.0 + (pass_count - 1) * contribution_ratio)
        spacing = pass_width * contribution_ratio

        return [
            (pass_width / 2 + i * spacing, pass_width)
            for i in range(pass_count)
        ]

    def _generate_supported_flat_paths(
        self,
        contour: Contour,
        width: float,
        wall_thickness: float,
        extrusion_width: float,
        path_line_width: float,
        role: PathRole,
        extruder: ExtruderType,
        speed_multiplier: float,
    ) -> List[LayerPath]:
        """Generate flat horizontal step passes as overlapping narrow rings."""
        if width <= 0.0:
            return []

        paths: List[LayerPath] = []

        for center_from_wall_inner_edge, pass_width in self._build_supported_outer_flat_passes(
            width,
            extrusion_width,
            path_line_width=path_line_width,
        ):
            paths.extend(
                self._create_outer_step_paths_for_centerline(
                    contour=contour,
                    center_from_wall_inner_edge=center_from_wall_inner_edge,
                    line_width=pass_width,
                    role=role,
                    wall_thickness=wall_thickness,
                    extruder=extruder,
                    speed_multiplier=speed_multiplier,
                )
            )

        for center_from_hole_boundary, pass_width in self._build_supported_hole_flat_passes(
            width,
            extrusion_width,
            path_line_width=path_line_width,
        ):
            paths.extend(
                self._create_hole_step_paths_for_centerline(
                    contour=contour,
                    center_from_hole_boundary=center_from_hole_boundary,
                    line_width=pass_width,
                    role=role,
                    extruder=extruder,
                    speed_multiplier=speed_multiplier,
                )
            )

        return paths

    def _compute_v_step_width(
        self,
        step_width: float,
        step_height: float,
        step_start: float,
        layer_bottom: float,
        layer_top: float,
        layer_height: float,
        full_width_at_end: bool = True,
    ) -> float:
        """Compute the effective width for one V-step layer.

        V-groove uses a fixed 10-layer ramp. The ramp is anchored to the step
        boundary where the ledge is widest, so the whole V-step occupies at most
        10 layers instead of turning into a long full-width platform.
        """
        if step_width <= 0.0 or step_height <= 0.0:
            return 0.0

        ramp_height = min(step_height, max(layer_height, 0.0) * 10.0)
        if ramp_height <= 0.0:
            return step_width

        step_end = step_start + step_height
        if full_width_at_end:
            ramp_start = max(step_start, step_end - ramp_height)
            if layer_top <= ramp_start or layer_bottom >= step_end:
                return 0.0
            local_top = min(layer_top, step_end)
            progress = (local_top - ramp_start) / ramp_height
        else:
            ramp_end = min(step_end, step_start + ramp_height)
            if layer_top <= step_start or layer_bottom >= ramp_end:
                return 0.0
            local_bottom = max(layer_bottom, step_start)
            progress = (ramp_end - local_bottom) / ramp_height

        progress = max(0.0, min(1.0, progress))
        return step_width * progress

    def _generate_v_step(self, contour: Contour,
                         step_config: StepConfig,
                         params: StepParams,
                         wall_thickness: float,
                         extrusion_width: float,
                         extruder: ExtruderType,
                         full_width_at_end: bool = True) -> List[LayerPath]:
        """Generate all layer rings for a sloped V-step."""
        paths = []

        step_width = step_config.width
        step_height = step_config.height
        step_thickness = params.step_thickness
        layers = max(int(step_height / step_thickness), 1)
        layer_step_height = step_height / layers if layers > 0 else step_height

        for i in range(layers):
            layer_bottom = i * layer_step_height
            layer_top = (i + 1) * layer_step_height
            current_width = self._compute_v_step_width(
                step_width=step_width,
                step_height=step_height,
                step_start=0.0,
                layer_bottom=layer_bottom,
                layer_top=layer_top,
                layer_height=layer_step_height,
                full_width_at_end=full_width_at_end,
            )

            if current_width < 0.1:
                continue

            paths.extend(
                self._create_step_paths_for_width(
                    contour=contour,
                    width=current_width,
                    role=PathRole.V_GROOVE,
                    wall_thickness=wall_thickness,
                    extruder=extruder,
                    speed_multiplier=0.7,
                )
            )

        return paths

    def _generate_flat_step(self, contour: Contour,
                            step_config: StepConfig,
                            wall_thickness: float,
                            extrusion_width: float,
                            extruder: ExtruderType,
                            path_line_width: float = 0.0) -> List[LayerPath]:
        """Generate a supported flat step using overlapping narrow passes."""
        step_width = step_config.width
        return self._generate_supported_flat_paths(
            contour=contour,
            width=step_width,
            role=PathRole.STEP,
            wall_thickness=wall_thickness,
            extrusion_width=extrusion_width,
            path_line_width=path_line_width,
            extruder=extruder,
            speed_multiplier=0.8,
        )

    def _align_flat_step_layer_z(
        self,
        step_position: float,
        layer_height: float,
        total_height: Optional[float] = None,
    ) -> Optional[float]:
        """Align a flat step anchor to the single printable layer that should carry it."""
        if layer_height <= 0.0:
            return None

        aligned_position = max(step_position, 0.0)
        if total_height is not None:
            max_layer_z = max(total_height - layer_height, 0.0)
            aligned_position = min(aligned_position, max_layer_z)

        layer_index = max(
            0,
            int(math.floor(aligned_position / layer_height + self._STEP_LAYER_EPSILON)),
        )
        return round(layer_index * layer_height, 6)

    def _is_flat_step_layer(
        self,
        z_height: float,
        layer_height: float,
        step_position: float,
        total_height: Optional[float] = None,
    ) -> bool:
        """Return True only for the single aligned layer used by a flat step."""
        aligned_z = self._align_flat_step_layer_z(step_position, layer_height, total_height)
        if aligned_z is None:
            return False
        return abs(z_height - aligned_z) <= self._STEP_LAYER_EPSILON

    def generate_step_for_layer(self, contour: Contour,
                                 z_height: float,
                                 layer_height: float,
                                 step_config: StepConfig,
                                 params: StepParams,
                                 wall_thickness: float = 1.2,
                                 extruder: ExtruderType = ExtruderType.EXTRUDER_1,
                                 full_width_at_end: bool = True,
                                 path_line_width: float = 0.0) -> List[LayerPath]:
        """Generate step paths for one sliced layer."""
        paths = []

        if not step_config.enabled:
            return paths

        step_position = step_config.position
        step_height = step_config.height
        step_width = step_config.width
        is_v_groove = step_config.is_v_groove

        if is_v_groove and step_height > 0:
            step_start = step_position
            step_end = step_position + max(step_height, layer_height)
            layer_bottom = z_height
            layer_top = z_height + layer_height

            if layer_top <= step_start or layer_bottom >= step_end:
                return paths

            current_width = self._compute_v_step_width(
                step_width=step_width,
                step_height=step_height,
                step_start=step_start,
                layer_bottom=layer_bottom,
                layer_top=layer_top,
                layer_height=layer_height,
                full_width_at_end=full_width_at_end,
            )

            if current_width < 0.1:
                return paths

            return self._create_step_paths_for_width(
                contour=contour,
                width=current_width,
                role=PathRole.V_GROOVE,
                wall_thickness=wall_thickness,
                extruder=extruder,
                speed_multiplier=0.7,
            )

        if not self._is_flat_step_layer(z_height, layer_height, step_position):
            return paths

        return self._generate_flat_step(
            contour, step_config,
            wall_thickness, params.extrusion_width, extruder,
            path_line_width=path_line_width,
        )

    def get_step_layers(self, params: StepParams,
                        total_height: float,
                        layer_height: float) -> Dict[float, StepConfig]:
        """
        获取需要生成台阶的层高度映射

        Args:
            params: 台阶参数
            total_height: 字壳总高度
            layer_height: 层高

        Returns:
            层高度到台阶配置的映射
        """
        step_layers: Dict[float, StepConfig] = {}

        if not params.enabled:
            return step_layers

        for step in params.steps:
            if not step.enabled:
                continue
            if step.position < 0 or step.position > total_height:
                continue

            # 计算台阶覆盖的层范围
            if not step.is_v_groove:
                aligned_z = self._align_flat_step_layer_z(
                    step.position,
                    layer_height,
                    total_height=total_height,
                )
                if aligned_z is not None:
                    step_layers.setdefault(aligned_z, step)
                continue

            step_start = step.position
            step_end = step.position + max(step.height, layer_height)

            # 找出所有与台阶重叠的层
            layer_count = max(1, int(total_height / layer_height))
            for i in range(layer_count):
                z = i * layer_height
                z_top = z + layer_height

                # 检查层是否与台阶重叠
                if z_top > step_start and z < step_end:
                    # 对齐到层高
                    aligned_z = round(z / layer_height) * layer_height
                    if aligned_z not in step_layers:
                        step_layers[aligned_z] = step

        return step_layers

    def generate_top_step(self, contour: Contour,
                          params: StepParams,
                          total_height: float,
                          wall_thickness: float = 1.2,
                          extruder: ExtruderType = ExtruderType.EXTRUDER_1) -> List[LayerPath]:
        """
        生成顶部台阶（用于安装面板）

        顶部台阶在字壳顶部向内延伸，用于放置亚克力面板

        Args:
            contour: 轮廓
            params: 台阶参数
            total_height: 字壳总高度
            wall_thickness: 壁厚
            extruder: 挤出机

        Returns:
            顶部台阶路径列表
        """
        if not params.top_step_enabled:
            return []

        step_config = StepConfig(
            enabled=True,
            position=total_height - params.top_step_height,
            width=params.top_step_width,
            height=params.top_step_height,
            is_v_groove=False
        )

        return self._generate_flat_step(
            contour, step_config,
            wall_thickness, params.extrusion_width, extruder
        )

    def generate_bottom_groove(self, contour: Contour,
                               z_height: float,
                               layer_height: float,
                               params: StepParams,
                               wall_thickness: float = 1.2,
                               extruder: ExtruderType = ExtruderType.EXTRUDER_1,
                               path_line_width: float = 0.0) -> List[LayerPath]:
        """
        生成底部凹槽（用于安装底板）

        底部凹槽在字壳底部向内凹陷，用于放置底板

        Args:
            contour: 轮廓
            z_height: 当前层高度
            layer_height: 层高
            params: 台阶参数
            wall_thickness: 壁厚
            extruder: 挤出机

        Returns:
            底部凹槽路径列表
        """
        if not params.bottom_groove_enabled:
            return []

        groove_height = params.bottom_groove_height
        groove_depth = params.bottom_groove_depth

        # 检查当前层是否在凹槽范围内
        if z_height >= groove_height:
            return []

        return self._generate_supported_flat_paths(
            contour=contour,
            width=groove_depth,
            role=PathRole.STEP,
            wall_thickness=wall_thickness,
            extrusion_width=params.extrusion_width,
            path_line_width=path_line_width,
            extruder=extruder,
            speed_multiplier=0.8,
        )

    def calculate_step_bounds(self, contour: Contour,
                              step_config: StepConfig,
                              wall_thickness: float = 1.2) -> Tuple[float, float, float, float]:
        """
        计算台阶的边界范围

        Returns:
            (min_x, min_y, max_x, max_y) 台阶区域边界
        """
        step_width = step_config.width
        offset = -(max(wall_thickness, 0.0) + step_width / 2)

        # 偏移轮廓获取台阶边界
        offset_paths = self.path_offset.offset(
            contour.outer, offset, JoinType.MITER
        )

        if offset_paths and offset_paths[0].points:
            offset_path = offset_paths[0]
            xs = [p.x for p in offset_path.points]
            ys = [p.y for p in offset_path.points]
            return (min(xs), min(ys), max(xs), max(ys))

        return contour.outer.bounds

    def is_step_layer(self, z_height: float,
                      layer_height: float,
                      params: StepParams) -> Tuple[bool, Optional[StepConfig]]:
        """
        检查指定高度是否为台阶层

        Args:
            z_height: 层高度
            layer_height: 层高
            params: 台阶参数

        Returns:
            (是否台阶层, 台阶配置)
        """
        if not params.enabled:
            return False, None

        layer_top = z_height + layer_height

        for step in params.steps:
            if not step.enabled:
                continue

            if not step.is_v_groove:
                if self._is_flat_step_layer(z_height, layer_height, step.position):
                    return True, step
                continue

            step_start = step.position
            step_end = step.position + max(step.height, layer_height)

            if layer_top > step_start and z_height < step_end:
                return True, step

        return False, None

    def generate_panel_step_for_layer(self, contour: Contour,
                                       z_height: float,
                                       layer_height: float,
                                       total_height: float,
                                       params: StepParams,
                                       wall_thickness: float = 1.2,
                                       extruder: ExtruderType = ExtruderType.EXTRUDER_1,
                                       path_line_width: float = 0.0) -> List[LayerPath]:
        """
        为指定层生成面板台阶路径（顶部台阶）

        面板台阶位于字壳顶部，用于安装亚克力面板。
        普通台阶保持顶部区间逻辑；V槽使用固定10层斜坡区间。

        Args:
            contour: 轮廓
            z_height: 当前层高度
            layer_height: 层高
            total_height: 字壳总高度
            params: 台阶参数
            wall_thickness: 壁厚
            extruder: 挤出机

        Returns:
            面板台阶路径列表
        """
        if not params.panel_step_enabled:
            return []

        step_height = params.panel_step_height
        step_width = params.panel_step_width
        is_v_groove = params.panel_step_is_v_groove

        # 限制顶部卡槽范围：不低于字壳一半高度
        min_step_height = total_height / 2
        if step_height < min_step_height:
            step_height = min_step_height

        if is_v_groove:
            # V槽区间：从 min(panel_step_height - 10层高度, 0) 到 panel_step_height
            step_start = min(step_height - layer_height * 10, 0)
            step_end = step_height
            step_height = step_end - step_start
            step_position = step_start
        else:
            # 普通台阶保持原来的顶部区间逻辑
            step_position = step_height
            step_start = self._align_flat_step_layer_z(
                step_position,
                layer_height,
                total_height=total_height,
            )
            step_end = step_start + layer_height

        # 当前层范围
        layer_bottom = z_height
        layer_top = z_height + layer_height

        # 检查当前层是否与台阶区域重叠
        if layer_top <= step_start or layer_bottom >= step_end:
            return []

        # 创建临时台阶配置
        step_config = StepConfig(
            enabled=True,
            position=step_position,
            width=step_width,
            height=step_height if is_v_groove else 0.0,
            is_v_groove=is_v_groove
        )

        return self.generate_step_for_layer(
            contour, z_height, layer_height,
            step_config, params,
            wall_thickness, extruder,
            full_width_at_end=True,
            path_line_width=path_line_width,
        )

    def generate_baseplate_step_for_layer(self, contour: Contour,
                                           z_height: float,
                                           layer_height: float,
                                           total_height: float,
                                           params: StepParams,
                                           wall_thickness: float = 1.2,
                                           extruder: ExtruderType = ExtruderType.EXTRUDER_1,
                                           path_line_width: float = 0.0) -> List[LayerPath]:
        """
        为指定层生成底板台阶路径（底部台阶）

        底板台阶位于字壳底部，用于安装底板。
        台阶从 0 开始，到 baseplate_step_height 结束。

        Args:
            contour: 轮廓
            z_height: 当前层高度
            layer_height: 层高
            total_height: 字壳总高度
            params: 台阶参数
            wall_thickness: 壁厚
            extruder: 挤出机

        Returns:
            底板台阶路径列表
        """
        if not params.baseplate_step_enabled:
            return []

        step_height = params.baseplate_step_height
        step_width = params.baseplate_step_width
        is_v_groove = params.baseplate_step_is_v_groove

        # 限制底部卡槽范围：不超过字壳一半高度
        max_step_height = total_height / 2
        if step_height > max_step_height:
            step_height = max_step_height

        # 台阶区域：从 0 到 台阶高度
        step_start = (
            0.0
            if is_v_groove
            else self._align_flat_step_layer_z(
                step_height,
                layer_height,
                total_height=total_height,
            )
        )
        step_end = step_height if is_v_groove else step_start + layer_height

        # 当前层范围
        layer_bottom = z_height
        layer_top = z_height + layer_height

        # 检查当前层是否与台阶区域重叠
        if layer_top <= step_start or layer_bottom >= step_end:
            return []

        # 创建临时台阶配置
        step_config = StepConfig(
            enabled=True,
            position=step_start if is_v_groove else step_height,
            width=step_width,
            height=step_height if is_v_groove else 0.0,
            is_v_groove=is_v_groove
        )

        return self.generate_step_for_layer(
            contour, z_height, layer_height,
            step_config, params,
            wall_thickness, extruder,
            full_width_at_end=True,
            path_line_width=path_line_width,
        )
