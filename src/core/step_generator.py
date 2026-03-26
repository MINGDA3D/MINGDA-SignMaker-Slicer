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
        """Generate one closed ring with the requested effective width."""
        if width <= 0.0:
            return []

        offset = -(wall_thickness / 2 + width / 2)
        paths: List[LayerPath] = []

        for offset_path in self.path_offset.offset(
            contour.outer, offset, JoinType.MITER
        ):
            paths.append(
                LayerPath(
                    points=offset_path.points,
                    role=role,
                    extruder=extruder,
                    line_width=width,
                    is_closed=True,
                    speed_multiplier=speed_multiplier,
                )
            )

        for hole in contour.holes:
            for hole_path in self.path_offset.offset(
                hole, -offset, JoinType.MITER
            ):
                paths.append(
                    LayerPath(
                        points=hole_path.points,
                        role=role,
                        extruder=extruder,
                        line_width=width,
                        is_closed=True,
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
                            extruder: ExtruderType) -> List[LayerPath]:
        """Generate one constant-width step ring."""
        step_width = step_config.width
        return self._create_step_paths_for_width(
            contour=contour,
            width=step_width,
            role=PathRole.STEP,
            wall_thickness=wall_thickness,
            extruder=extruder,
            speed_multiplier=0.8,
        )

    def generate_step_for_layer(self, contour: Contour,
                                 z_height: float,
                                 layer_height: float,
                                 step_config: StepConfig,
                                 params: StepParams,
                                 wall_thickness: float = 1.2,
                                 extruder: ExtruderType = ExtruderType.EXTRUDER_1,
                                 full_width_at_end: bool = True) -> List[LayerPath]:
        """Generate step paths for one sliced layer."""
        paths = []

        if not step_config.enabled:
            return paths

        step_position = step_config.position
        step_height = step_config.height
        step_width = step_config.width
        is_v_groove = step_config.is_v_groove

        step_start = step_position
        step_end = step_position + max(step_height, layer_height)
        layer_bottom = z_height
        layer_top = z_height + layer_height

        if layer_top <= step_start or layer_bottom >= step_end:
            return paths

        if is_v_groove and step_height > 0:
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

        return self._generate_flat_step(
            contour, step_config,
            wall_thickness, params.extrusion_width, extruder
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
                               extruder: ExtruderType = ExtruderType.EXTRUDER_1) -> List[LayerPath]:
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

        paths = []

        # 从壁内侧向内偏移
        offset = -(wall_thickness / 2 + groove_depth / 2)

        offset_paths = self.path_offset.offset(
            contour.outer, offset, JoinType.MITER
        )

        for offset_path in offset_paths:
            layer_path = LayerPath(
                points=offset_path.points,
                role=PathRole.STEP,
                extruder=extruder,
                line_width=groove_depth,
                is_closed=True,
                speed_multiplier=0.8
            )
            paths.append(layer_path)

        # 内孔的凹槽
        for hole in contour.holes:
            hole_offset_paths = self.path_offset.offset(
                hole, -offset, JoinType.MITER
            )
            for hole_path in hole_offset_paths:
                layer_path = LayerPath(
                    points=hole_path.points,
                    role=PathRole.STEP,
                    extruder=extruder,
                    line_width=groove_depth,
                    is_closed=True,
                    speed_multiplier=0.8
                )
                paths.append(layer_path)

        return paths

    def calculate_step_bounds(self, contour: Contour,
                              step_config: StepConfig,
                              wall_thickness: float = 1.2) -> Tuple[float, float, float, float]:
        """
        计算台阶的边界范围

        Returns:
            (min_x, min_y, max_x, max_y) 台阶区域边界
        """
        step_width = step_config.width
        offset = -(wall_thickness / 2 + step_width / 2)

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
                                       extruder: ExtruderType = ExtruderType.EXTRUDER_1) -> List[LayerPath]:
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
        else:
            # 普通台阶保持原来的顶部区间逻辑
            step_start = total_height - step_height
            step_end = total_height

        # 当前层范围
        layer_bottom = z_height
        layer_top = z_height + layer_height

        # 检查当前层是否与台阶区域重叠
        if layer_top <= step_start or layer_bottom >= step_end:
            return []

        # 创建临时台阶配置
        step_config = StepConfig(
            enabled=True,
            position=step_start,
            width=step_width,
            height=step_height,
            is_v_groove=is_v_groove
        )

        return self.generate_step_for_layer(
            contour, z_height, layer_height,
            step_config, params,
            wall_thickness, extruder,
            full_width_at_end=True
        )

    def generate_baseplate_step_for_layer(self, contour: Contour,
                                           z_height: float,
                                           layer_height: float,
                                           total_height: float,
                                           params: StepParams,
                                           wall_thickness: float = 1.2,
                                           extruder: ExtruderType = ExtruderType.EXTRUDER_1) -> List[LayerPath]:
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
        step_start = 0
        step_end = step_height

        # 当前层范围
        layer_bottom = z_height
        layer_top = z_height + layer_height

        # 检查当前层是否与台阶区域重叠
        if layer_top <= step_start or layer_bottom >= step_end:
            return []

        # 创建临时台阶配置
        step_config = StepConfig(
            enabled=True,
            position=step_start,
            width=step_width,
            height=step_height,
            is_v_groove=is_v_groove
        )

        return self.generate_step_for_layer(
            contour, z_height, layer_height,
            step_config, params,
            wall_thickness, extruder,
            full_width_at_end=True
        )
