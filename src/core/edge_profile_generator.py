"""
MINGDA SignMaker - 异形边轮廓生成器

提供多种插值算法来生成异形边轮廓曲线，支持：
- 线性插值
- 三次样条插值
- 贝塞尔曲线插值
- B样条插值（兼容INC-S）
"""

from __future__ import annotations
from typing import List, Tuple, Dict, Optional
import math

from .types import EdgeProfile, InterpolationType


class EdgeProfileGenerator:
    """异形边轮廓生成器

    根据EdgeProfile定义生成轮廓曲线，并映射到各层的偏移量。

    使用示例:
        generator = EdgeProfileGenerator()

        # 生成轮廓曲线
        curve = generator.generate_profile_curve(profile, bevel_width=5.0, shell_height=30.0)

        # 映射到各层
        offsets = generator.map_profile_to_layers(curve, layer_height=0.3, shell_height=30.0)
    """

    def generate_profile_curve(
        self,
        profile: EdgeProfile,
        bevel_width: float,
        shell_height: float
    ) -> List[Tuple[float, float]]:
        """
        生成异形边轮廓曲线

        Args:
            profile: 边缘轮廓定义
            bevel_width: 边缘宽度（mm）- 作为最大限制
            shell_height: 字壳高度（mm）

        Returns:
            采样点列表 [(x, z), ...], x和z为实际尺寸（mm）
            x: 水平偏移量（正值表示向外，用于路径内缩时取负）
            z: 高度
        """
        if not profile.control_points:
            # 无控制点时返回简单直线
            return [(0.0, 0.0), (0.0, shell_height)]

        # 计算实际使用的边缘宽度（保持原始宽高比）
        actual_edge_width = bevel_width
        if profile.original_width > 0 and profile.original_height > 0 and shell_height > 0:
            # 使用原始宽高比计算等比例缩放的边缘宽度
            aspect_ratio = profile.original_width / profile.original_height
            proportional_width = shell_height * aspect_ratio
            # 使用等比例计算的宽度，但不超过用户设置的bevel_width
            actual_edge_width = min(proportional_width, bevel_width) if bevel_width > 0 else proportional_width

        # 1. 归一化控制点到实际尺寸
        scaled_points = [
            (nx * actual_edge_width, nz * shell_height)
            for nx, nz in profile.control_points
        ]

        # 按Z坐标排序
        scaled_points = sorted(scaled_points, key=lambda p: p[1])

        # 2. 根据插值类型生成曲线
        num_samples = profile.sample_points

        if profile.interpolation == InterpolationType.LINEAR:
            return self._linear_interpolation(scaled_points, num_samples)
        elif profile.interpolation == InterpolationType.CUBIC:
            return self._cubic_spline_interpolation(scaled_points, num_samples)
        elif profile.interpolation == InterpolationType.BEZIER:
            return self._bezier_interpolation(scaled_points, num_samples)
        elif profile.interpolation == InterpolationType.BSPLINE:
            return self._bspline_interpolation(scaled_points, num_samples)
        else:
            # 默认使用线性插值
            return self._linear_interpolation(scaled_points, num_samples)

    def _linear_interpolation(
        self,
        points: List[Tuple[float, float]],
        num_samples: int
    ) -> List[Tuple[float, float]]:
        """
        线性插值

        Args:
            points: 控制点列表 [(x, z), ...]，按Z排序
            num_samples: 采样点数

        Returns:
            采样点列表 [(x, z), ...]
        """
        if len(points) < 2:
            return points if points else [(0.0, 0.0)]

        try:
            import numpy as np

            xs = [p[0] for p in points]
            zs = [p[1] for p in points]

            # 生成均匀的Z采样点
            z_samples = np.linspace(zs[0], zs[-1], num_samples)

            # 线性插值X值
            x_samples = np.interp(z_samples, zs, xs)

            return list(zip(x_samples.tolist(), z_samples.tolist()))
        except ImportError:
            # 无numpy时使用纯Python实现
            return self._linear_interpolation_pure(points, num_samples)

    def _linear_interpolation_pure(
        self,
        points: List[Tuple[float, float]],
        num_samples: int
    ) -> List[Tuple[float, float]]:
        """纯Python线性插值实现"""
        if len(points) < 2:
            return points if points else [(0.0, 0.0)]

        z_min = points[0][1]
        z_max = points[-1][1]
        z_range = z_max - z_min

        if z_range <= 0:
            return [(points[0][0], z_min)]

        result = []
        for i in range(num_samples):
            z = z_min + (z_range * i / (num_samples - 1)) if num_samples > 1 else z_min

            # 查找z所在的区间
            x = points[0][0]
            for j in range(len(points) - 1):
                x1, z1 = points[j]
                x2, z2 = points[j + 1]
                if z1 <= z <= z2:
                    if z2 == z1:
                        x = x1
                    else:
                        t = (z - z1) / (z2 - z1)
                        x = x1 + t * (x2 - x1)
                    break
            else:
                x = points[-1][0]

            result.append((x, z))

        return result

    def _cubic_spline_interpolation(
        self,
        points: List[Tuple[float, float]],
        num_samples: int
    ) -> List[Tuple[float, float]]:
        """
        三次样条插值

        Args:
            points: 控制点列表 [(x, z), ...]，按Z排序
            num_samples: 采样点数

        Returns:
            采样点列表 [(x, z), ...]
        """
        if len(points) < 3:
            return self._linear_interpolation(points, num_samples)

        try:
            import numpy as np
            from scipy.interpolate import CubicSpline

            xs = np.array([p[0] for p in points])
            zs = np.array([p[1] for p in points])

            # 确保Z坐标严格递增（去重）
            unique_indices = [0]
            for i in range(1, len(zs)):
                if zs[i] > zs[unique_indices[-1]]:
                    unique_indices.append(i)

            if len(unique_indices) < 2:
                return self._linear_interpolation(points, num_samples)

            xs_unique = xs[unique_indices]
            zs_unique = zs[unique_indices]

            # 创建三次样条
            cs = CubicSpline(zs_unique, xs_unique)

            # 采样
            z_samples = np.linspace(zs_unique[0], zs_unique[-1], num_samples)
            x_samples = cs(z_samples)

            return list(zip(x_samples.tolist(), z_samples.tolist()))

        except ImportError:
            # 无scipy时回退到线性插值
            return self._linear_interpolation(points, num_samples)

    def _bezier_interpolation(
        self,
        points: List[Tuple[float, float]],
        num_samples: int
    ) -> List[Tuple[float, float]]:
        """
        贝塞尔曲线插值（De Casteljau算法）

        Args:
            points: 控制点列表 [(x, z), ...]
            num_samples: 采样点数

        Returns:
            采样点列表 [(x, z), ...]
        """
        if len(points) < 2:
            return points if points else [(0.0, 0.0)]

        n = len(points) - 1
        result = []

        for i in range(num_samples):
            t = i / (num_samples - 1) if num_samples > 1 else 0

            # 计算贝塞尔曲线上的点
            x, z = self._de_casteljau(points, t)
            result.append((x, z))

        # 按Z坐标排序（贝塞尔曲线可能不是按Z递增的）
        result = sorted(result, key=lambda p: p[1])

        return result

    def _de_casteljau(
        self,
        points: List[Tuple[float, float]],
        t: float
    ) -> Tuple[float, float]:
        """De Casteljau算法计算贝塞尔曲线上的点"""
        if len(points) == 1:
            return points[0]

        new_points = []
        for i in range(len(points) - 1):
            x = (1 - t) * points[i][0] + t * points[i + 1][0]
            z = (1 - t) * points[i][1] + t * points[i + 1][1]
            new_points.append((x, z))

        return self._de_casteljau(new_points, t)

    def _bspline_interpolation(
        self,
        points: List[Tuple[float, float]],
        num_samples: int,
        degree: int = 3
    ) -> List[Tuple[float, float]]:
        """
        B样条插值（兼容INC-S的SPLINE格式）

        Args:
            points: 控制点列表 [(x, z), ...]
            num_samples: 采样点数
            degree: 样条阶数

        Returns:
            采样点列表 [(x, z), ...]
        """
        if len(points) < 2:
            return points if points else [(0.0, 0.0)]

        try:
            import numpy as np
            from scipy.interpolate import splprep, splev

            xs = np.array([p[0] for p in points])
            zs = np.array([p[1] for p in points])

            # 使用参数化B样条拟合
            k = min(degree, len(points) - 1)

            # 创建参数化样条
            tck, u = splprep([xs, zs], k=k, s=0)

            # 均匀采样
            u_new = np.linspace(0, 1, num_samples)
            x_new, z_new = splev(u_new, tck)

            result = list(zip(x_new.tolist(), z_new.tolist()))

            # 按Z坐标排序
            result = sorted(result, key=lambda p: p[1])

            return result

        except (ImportError, Exception):
            # 回退到三次样条
            return self._cubic_spline_interpolation(points, num_samples)

    def map_profile_to_layers(
        self,
        profile_curve: List[Tuple[float, float]],
        layer_height: float,
        shell_height: float
    ) -> Dict[int, float]:
        """
        将轮廓曲线映射到各层的偏移量

        Args:
            profile_curve: 轮廓曲线采样点 [(x, z), ...]
            layer_height: 层高（mm）
            shell_height: 字壳总高度（mm）

        Returns:
            字典 {layer_index: offset_distance}
            layer_index: 层索引（0为底层）
            offset_distance: 该层的偏移距离（mm），负值表示内缩
        """
        if not profile_curve:
            return {}

        num_layers = int(shell_height / layer_height)
        layer_offsets = {}

        for layer_idx in range(num_layers):
            # 计算该层中心的Z高度
            z = (layer_idx + 0.5) * layer_height

            # 在轮廓曲线中查找对应的X值（偏移量）
            offset = self._interpolate_offset_at_z(profile_curve, z)
            # 转换为负值（内缩）
            layer_offsets[layer_idx] = -offset

        return layer_offsets

    def _interpolate_offset_at_z(
        self,
        profile_curve: List[Tuple[float, float]],
        z: float
    ) -> float:
        """
        在给定Z高度处插值计算X偏移量

        Args:
            profile_curve: 轮廓曲线 [(x, z), ...]
            z: 目标Z高度

        Returns:
            X偏移量（mm）
        """
        if not profile_curve:
            return 0.0

        # 按Z排序（确保）
        sorted_curve = sorted(profile_curve, key=lambda p: p[1])

        # 边界情况
        if z <= sorted_curve[0][1]:
            return sorted_curve[0][0]
        if z >= sorted_curve[-1][1]:
            return sorted_curve[-1][0]

        # 找到z值所在的区间
        for i in range(len(sorted_curve) - 1):
            x1, z1 = sorted_curve[i]
            x2, z2 = sorted_curve[i + 1]

            if z1 <= z <= z2:
                # 线性插值
                if z2 == z1:
                    return x1
                t = (z - z1) / (z2 - z1)
                return x1 + t * (x2 - x1)

        return sorted_curve[-1][0]

    def get_offset_at_layer(
        self,
        profile: EdgeProfile,
        layer_idx: int,
        layer_height: float,
        shell_height: float,
        bevel_width: float
    ) -> float:
        """
        获取指定层的偏移量（便捷方法）

        Args:
            profile: 边缘轮廓定义
            layer_idx: 层索引
            layer_height: 层高（mm）
            shell_height: 字壳高度（mm）
            bevel_width: 斜边宽度（mm）

        Returns:
            偏移量（mm），负值表示内缩
        """
        # 计算归一化高度
        z = (layer_idx + 0.5) * layer_height
        normalized_z = z / shell_height if shell_height > 0 else 0

        # 使用EdgeProfile的方法
        return profile.get_offset_at_height(normalized_z, bevel_width, shell_height)

    def generate_preview_points(
        self,
        profile: EdgeProfile,
        bevel_width: float,
        shell_height: float,
        num_points: int = 50
    ) -> List[Tuple[float, float]]:
        """
        生成用于UI预览的轮廓点

        Args:
            profile: 边缘轮廓定义
            bevel_width: 斜边宽度（mm）
            shell_height: 字壳高度（mm）
            num_points: 预览点数

        Returns:
            预览点列表 [(x, z), ...]
        """
        # 临时设置采样点数
        original_samples = profile.sample_points
        profile.sample_points = num_points

        curve = self.generate_profile_curve(profile, bevel_width, shell_height)

        # 恢复
        profile.sample_points = original_samples

        return curve
