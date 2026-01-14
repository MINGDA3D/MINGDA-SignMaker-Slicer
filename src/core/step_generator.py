"""
台阶V槽生成器模块

生成台阶和V槽结构，用于安装面板和底板。
"""

from typing import List, Optional, Dict
from src.core.types import (
    Contour, StepParams, StepConfig, LayerPath, PathRole,
    ExtruderType, Point, Path
)
from src.core.path_offset import PathOffset


class StepGenerator:
    """台阶V槽生成器"""

    def __init__(self, path_offset: Optional[PathOffset] = None):
        self.path_offset = path_offset or PathOffset()

    def generate_steps(self, contour: Contour, step_config: StepConfig,
                       params: StepParams) -> List[LayerPath]:
        """
        在指定高度生成台阶路径

        台阶类型：
        - V型台阶 (height > 0): 向内倾斜的V型凹槽
        - 平台阶 (height = 0): 向内的平面台阶

        Args:
            contour: 字形轮廓
            step_config: 当前台阶配置
            params: 台阶参数

        Returns:
            台阶路径列表
        """
        paths = []

        if not step_config.enabled:
            return paths

        if step_config.height > 0:
            # V型台阶
            step_paths = self._generate_v_step(contour, step_config, params)
        else:
            # 平台阶
            step_paths = self._generate_flat_step(contour, step_config, params)

        paths.extend(step_paths)
        return paths

    def _generate_v_step(self, contour: Contour, step_config: StepConfig,
                         params: StepParams) -> List[LayerPath]:
        """
        生成V型台阶

        V型台阶是向内倾斜的凹槽，用于嵌入面板
        """
        paths = []

        # V型台阶需要多层偏移形成斜面
        step_width = step_config.width
        step_height = step_config.height
        layers = max(int(step_height / params.step_thickness), 1)

        for i in range(layers):
            # 计算当前层的偏移量
            progress = (i + 1) / layers
            offset = -step_width * progress

            # 偏移外轮廓
            offset_paths = self.path_offset.offset(contour.outer, offset)

            for offset_path in offset_paths:
                layer_path = LayerPath(
                    points=offset_path.points,
                    role=PathRole.STEP,
                    extruder=ExtruderType.EXTRUDER_1,
                    line_width=params.extrusion_width
                )
                paths.append(layer_path)

            # 偏移内孔（方向相反）
            for hole in contour.holes:
                hole_offset_paths = self.path_offset.offset(hole, -offset)
                for hole_path in hole_offset_paths:
                    layer_path = LayerPath(
                        points=hole_path.points,
                        role=PathRole.STEP,
                        extruder=ExtruderType.EXTRUDER_1,
                        line_width=params.extrusion_width
                    )
                    paths.append(layer_path)

        return paths

    def _generate_flat_step(self, contour: Contour, step_config: StepConfig,
                            params: StepParams) -> List[LayerPath]:
        """
        生成平台阶

        平台阶是水平的台阶面，宽度固定
        """
        paths = []
        step_width = step_config.width

        # 生成偏移轮廓
        offset_paths = self.path_offset.offset(contour.outer, -step_width)

        for offset_path in offset_paths:
            layer_path = LayerPath(
                points=offset_path.points,
                role=PathRole.STEP,
                extruder=ExtruderType.EXTRUDER_1,
                line_width=params.extrusion_width
            )
            paths.append(layer_path)

        # 内孔的平台阶
        for hole in contour.holes:
            hole_offset_paths = self.path_offset.offset(hole, step_width)
            for hole_path in hole_offset_paths:
                layer_path = LayerPath(
                    points=hole_path.points,
                    role=PathRole.STEP,
                    extruder=ExtruderType.EXTRUDER_1,
                    line_width=params.extrusion_width
                )
                paths.append(layer_path)

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
        step_layers = {}

        for step in params.steps:
            if step.enabled and 0 <= step.position <= total_height:
                # 对齐到层高
                aligned_z = round(step.position / layer_height) * layer_height
                step_layers[aligned_z] = step

        return step_layers

    def calculate_step_bounds(self, contour: Contour,
                              step_config: StepConfig) -> tuple:
        """
        计算台阶的边界范围

        Returns:
            (min_x, min_y, max_x, max_y) 台阶区域边界
        """
        step_width = step_config.width

        # 偏移轮廓获取台阶边界
        offset_paths = self.path_offset.offset(contour.outer, -step_width)

        if offset_paths:
            offset_path = offset_paths[0]
            xs = [p.x for p in offset_path.points]
            ys = [p.y for p in offset_path.points]
            return (min(xs), min(ys), max(xs), max(ys))

        return contour.outer.bounds
