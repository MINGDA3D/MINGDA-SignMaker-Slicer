"""
SignMaker Slicer - 台阶/V槽生成器模块

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

    def _generate_v_step(self, contour: Contour,
                         step_config: StepConfig,
                         params: StepParams,
                         wall_thickness: float,
                         extrusion_width: float,
                         extruder: ExtruderType) -> List[LayerPath]:
        """
        生成V型台阶

        V型台阶结构：
                    壁
                   ┌─┐
        step_end → │╲│  ← 台阶顶部（无偏移）
                   │ ╲
                   │  ╲ ← V槽斜面（逐层偏移）
                   │   ╲
        step_pos → │    ╲ ← 台阶底部（最大偏移）
                   │    │
                   └────┘

        V型台阶需要多层偏移形成斜面
        """
        paths = []

        step_width = step_config.width
        step_height = step_config.height
        step_thickness = params.step_thickness

        # 计算需要多少层形成V槽
        layers = max(int(step_height / step_thickness), 1)

        for i in range(layers):
            # 计算当前层的偏移量
            # 从底部(i=0)最大偏移，到顶部(i=layers-1)最小偏移
            progress = (i + 1) / layers
            current_width = step_width * (1.0 - progress)

            if current_width < 0.1:
                continue

            # 从壁内侧向内偏移
            # 壁的内边缘在 -wall_thickness/2 位置
            offset = -(wall_thickness / 2 + current_width / 2)

            # 偏移外轮廓
            offset_paths = self.path_offset.offset(
                contour.outer, offset, JoinType.MITER
            )

            for offset_path in offset_paths:
                layer_path = LayerPath(
                    points=offset_path.points,
                    role=PathRole.V_GROOVE,
                    extruder=extruder,
                    line_width=current_width,
                    is_closed=True,
                    speed_multiplier=0.7  # V槽打印稍慢
                )
                paths.append(layer_path)

            # 偏移内孔（方向相反）
            for hole in contour.holes:
                hole_offset_paths = self.path_offset.offset(
                    hole, -offset, JoinType.MITER
                )
                for hole_path in hole_offset_paths:
                    layer_path = LayerPath(
                        points=hole_path.points,
                        role=PathRole.V_GROOVE,
                        extruder=extruder,
                        line_width=current_width,
                        is_closed=True,
                        speed_multiplier=0.7
                    )
                    paths.append(layer_path)

        return paths

    def _generate_flat_step(self, contour: Contour,
                            step_config: StepConfig,
                            wall_thickness: float,
                            extrusion_width: float,
                            extruder: ExtruderType) -> List[LayerPath]:
        """
        生成平台阶

        平台阶结构：
                    壁
                   ┌─┐
                   │ │
                   │ ├───── ← 平台阶（固定宽度水平延伸）
                   │ │
                   │ │
                   └─┘

        平台阶是水平的台阶面，宽度固定
        """
        paths = []
        step_width = step_config.width

        # 从壁内侧向内偏移
        # 壁的内边缘在 -wall_thickness/2 位置
        # 台阶中心线位置 = -wall_thickness/2 - step_width/2
        offset = -(wall_thickness / 2 + step_width / 2)

        # 偏移外轮廓生成台阶
        offset_paths = self.path_offset.offset(
            contour.outer, offset, JoinType.MITER
        )

        for offset_path in offset_paths:
            layer_path = LayerPath(
                points=offset_path.points,
                role=PathRole.STEP,
                extruder=extruder,
                line_width=step_width,
                is_closed=True,
                speed_multiplier=0.8  # 台阶打印稍慢
            )
            paths.append(layer_path)

        # 内孔的平台阶（方向相反：向外延伸）
        for hole in contour.holes:
            hole_offset_paths = self.path_offset.offset(
                hole, -offset, JoinType.MITER
            )
            for hole_path in hole_offset_paths:
                layer_path = LayerPath(
                    points=hole_path.points,
                    role=PathRole.STEP,
                    extruder=extruder,
                    line_width=step_width,
                    is_closed=True,
                    speed_multiplier=0.8
                )
                paths.append(layer_path)

        return paths

    def generate_step_for_layer(self, contour: Contour,
                                 z_height: float,
                                 layer_height: float,
                                 step_config: StepConfig,
                                 params: StepParams,
                                 wall_thickness: float = 1.2,
                                 extruder: ExtruderType = ExtruderType.EXTRUDER_1) -> List[LayerPath]:
        """
        为指定层生成台阶路径（用于逐层切片）

        根据当前层高度判断是否需要生成台阶，并计算正确的偏移量

        Args:
            contour: 轮廓
            z_height: 当前层高度
            layer_height: 层高
            step_config: 台阶配置
            params: 台阶参数
            wall_thickness: 壁厚
            extruder: 挤出机

        Returns:
            台阶路径列表
        """
        paths = []

        if not step_config.enabled:
            return paths

        step_position = step_config.position
        step_height = step_config.height
        step_width = step_config.width
        is_v_groove = step_config.is_v_groove

        # 台阶的Z范围
        step_start = step_position
        step_end = step_position + max(step_height, layer_height)

        # 当前层的Z范围
        layer_bottom = z_height
        layer_top = z_height + layer_height

        # 检查当前层是否与台阶区域重叠
        if layer_top <= step_start or layer_bottom >= step_end:
            return paths

        if is_v_groove and step_height > layer_height:
            # V槽：根据层在V槽中的位置计算偏移
            layer_center = z_height + layer_height / 2

            # progress: 0=V槽底部（最大偏移），1=V槽顶部（无偏移）
            if step_height > 0:
                progress = (layer_center - step_start) / step_height
                progress = max(0.0, min(1.0, progress))
            else:
                progress = 0.5

            current_width = step_width * (1.0 - progress)

            if current_width < 0.1:
                return paths

            # 生成V槽路径
            offset = -(wall_thickness / 2 + current_width / 2)

            offset_paths = self.path_offset.offset(
                contour.outer, offset, JoinType.MITER
            )

            for offset_path in offset_paths:
                layer_path = LayerPath(
                    points=offset_path.points,
                    role=PathRole.V_GROOVE,
                    extruder=extruder,
                    line_width=current_width,
                    is_closed=True,
                    speed_multiplier=0.7
                )
                paths.append(layer_path)

            # 内孔
            for hole in contour.holes:
                hole_offset_paths = self.path_offset.offset(
                    hole, -offset, JoinType.MITER
                )
                for hole_path in hole_offset_paths:
                    layer_path = LayerPath(
                        points=hole_path.points,
                        role=PathRole.V_GROOVE,
                        extruder=extruder,
                        line_width=current_width,
                        is_closed=True,
                        speed_multiplier=0.7
                    )
                    paths.append(layer_path)
        else:
            # 平台阶
            paths = self._generate_flat_step(
                contour, step_config,
                wall_thickness, params.extrusion_width, extruder
            )

        return paths

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
        台阶从 (total_height - panel_step_height) 开始，到 total_height 结束。

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

        # 台阶区域：从 (总高度 - 台阶高度) 到 总高度
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
            wall_thickness, extruder
        )

    def generate_baseplate_step_for_layer(self, contour: Contour,
                                           z_height: float,
                                           layer_height: float,
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
            wall_thickness, extruder
        )
