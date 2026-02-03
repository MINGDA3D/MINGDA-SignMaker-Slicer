"""
MINGDA SignMaker - 网格工具类

提供基础网格操作的通用工具方法，被其他网格生成器共享使用。
"""

from __future__ import annotations
from typing import List, Tuple, Optional
import math

import numpy as np
import trimesh
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.validation import make_valid


class MeshUtils:
    """网格生成工具类"""

    def extrude_polygon(self, polygon: ShapelyPolygon, height: float,
                        z_offset: float = 0.0) -> Optional[trimesh.Trimesh]:
        """
        使用trimesh挤出多边形

        Args:
            polygon: Shapely多边形（可以带孔）
            height: 挤出高度
            z_offset: Z轴偏移

        Returns:
            挤出后的3D网格
        """
        try:
            # 使用trimesh的extrude_polygon函数
            mesh = trimesh.creation.extrude_polygon(polygon, height)

            # 如果有Z偏移，平移网格
            if z_offset != 0:
                mesh.apply_translation([0, 0, z_offset])

            return mesh
        except Exception as e:
            print(f"警告：挤出多边形失败: {e}")
            return None

    def create_ruled_surface(self, coords1: list, z1: float,
                             coords2: list, z2: float,
                             flip_normals: bool = False) -> Optional[trimesh.Trimesh]:
        """
        创建两个轮廓之间的直纹面

        使用轮廓的参数化（弧长）对应来处理点数不同的情况。

        Args:
            coords1: 第一个轮廓坐标列表
            z1: 第一个轮廓的Z高度
            coords2: 第二个轮廓坐标列表
            z2: 第二个轮廓的Z高度
            flip_normals: 是否翻转法向

        Returns:
            直纹面网格
        """
        if not coords1 or not coords2:
            return None

        try:
            # 计算轮廓的累积弧长参数
            def compute_arc_params(coords):
                n = len(coords)
                lengths = [0.0]
                for i in range(1, n):
                    dx = coords[i][0] - coords[i-1][0]
                    dy = coords[i][1] - coords[i-1][1]
                    lengths.append(lengths[-1] + math.sqrt(dx*dx + dy*dy))
                # 加上闭合段
                dx = coords[0][0] - coords[-1][0]
                dy = coords[0][1] - coords[-1][1]
                total = lengths[-1] + math.sqrt(dx*dx + dy*dy)
                # 归一化到[0, 1]
                if total > 1e-9:
                    return [l / total for l in lengths], total
                return lengths, 0.0

            params1, total1 = compute_arc_params(coords1)
            params2, total2 = compute_arc_params(coords2)

            if total1 < 1e-9 or total2 < 1e-9:
                return None

            # 使用统一的采样点数
            n_samples = max(len(coords1), len(coords2), 100)

            # 在轮廓上按参数采样
            def sample_point(coords, params, t):
                """在归一化参数t处采样轮廓上的点"""
                n = len(coords)
                t = t % 1.0  # 确保t在[0, 1)范围内

                # 找到t所在的段
                for i in range(n - 1):
                    if params[i] <= t <= params[i + 1]:
                        if params[i + 1] - params[i] < 1e-9:
                            return coords[i]
                        s = (t - params[i]) / (params[i + 1] - params[i])
                        x = coords[i][0] + s * (coords[i + 1][0] - coords[i][0])
                        y = coords[i][1] + s * (coords[i + 1][1] - coords[i][1])
                        return (x, y)

                # t在最后一段（从最后一点到第一点）
                if params[-1] <= t <= 1.0:
                    if 1.0 - params[-1] < 1e-9:
                        return coords[-1]
                    s = (t - params[-1]) / (1.0 - params[-1])
                    x = coords[-1][0] + s * (coords[0][0] - coords[-1][0])
                    y = coords[-1][1] + s * (coords[0][1] - coords[-1][1])
                    return (x, y)

                return coords[0]

            # 生成采样点和面
            vertices = []
            faces = []

            for i in range(n_samples):
                t = i / n_samples
                p1 = sample_point(coords1, params1, t)
                p2 = sample_point(coords2, params2, t)

                # 添加顶点对（底部点和顶部点）
                vertices.append([p1[0], p1[1], z1])
                vertices.append([p2[0], p2[1], z2])

            # 生成三角面
            for i in range(n_samples):
                i_next = (i + 1) % n_samples

                # 当前段的顶点索引
                v1_curr = i * 2      # 底部当前
                v2_curr = i * 2 + 1  # 顶部当前
                v1_next = i_next * 2      # 底部下一个
                v2_next = i_next * 2 + 1  # 顶部下一个

                if flip_normals:
                    # 法向朝内
                    faces.append([v1_curr, v2_next, v1_next])
                    faces.append([v1_curr, v2_curr, v2_next])
                else:
                    # 法向朝外
                    faces.append([v1_curr, v1_next, v2_next])
                    faces.append([v1_curr, v2_next, v2_curr])

            vertices = np.array(vertices)
            faces = np.array(faces)

            return trimesh.Trimesh(vertices=vertices, faces=faces)

        except Exception as e:
            print(f"警告：创建直纹面失败: {e}")
            return None

    def resample_coords(self, coords: List[tuple], target_n: int) -> List[tuple]:
        """
        重采样坐标点到指定数量

        Args:
            coords: 原始坐标列表 [(x, y), ...]
            target_n: 目标点数

        Returns:
            重采样后的坐标列表
        """
        if len(coords) == target_n:
            return coords

        # 计算原始路径的累积长度
        lengths = [0.0]
        for i in range(1, len(coords)):
            dx = coords[i][0] - coords[i-1][0]
            dy = coords[i][1] - coords[i-1][1]
            lengths.append(lengths[-1] + math.sqrt(dx*dx + dy*dy))

        # 闭合路径的总长度
        dx = coords[0][0] - coords[-1][0]
        dy = coords[0][1] - coords[-1][1]
        total_length = lengths[-1] + math.sqrt(dx*dx + dy*dy)

        if total_length < 1e-6:
            return coords[:target_n] if len(coords) >= target_n else coords

        # 按等距重采样
        new_coords = []
        for i in range(target_n):
            target_dist = (i / target_n) * total_length

            # 找到对应的线段
            for j in range(len(lengths) - 1):
                if lengths[j] <= target_dist <= lengths[j + 1]:
                    # 在 j 和 j+1 之间插值
                    t = (target_dist - lengths[j]) / (lengths[j + 1] - lengths[j]) if lengths[j + 1] != lengths[j] else 0
                    x = coords[j][0] + t * (coords[j + 1][0] - coords[j][0])
                    y = coords[j][1] + t * (coords[j + 1][1] - coords[j][1])
                    new_coords.append((x, y))
                    break
            else:
                # 在最后一段（回到起点）
                remaining = target_dist - lengths[-1]
                segment_length = total_length - lengths[-1]
                t = remaining / segment_length if segment_length > 0 else 0
                x = coords[-1][0] + t * (coords[0][0] - coords[-1][0])
                y = coords[-1][1] + t * (coords[0][1] - coords[-1][1])
                new_coords.append((x, y))

        return new_coords

    def create_wall_segment(self, x1: float, y1: float, x2: float, y2: float,
                            z_bottom: float, z_top: float,
                            thickness: float) -> Optional[trimesh.Trimesh]:
        """
        创建一段墙壁（薄壁矩形）

        Args:
            x1, y1: 起点
            x2, y2: 终点
            z_bottom: 底部Z坐标
            z_top: 顶部Z坐标
            thickness: 壁厚

        Returns:
            墙壁网格
        """
        # 计算边的方向
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx * dx + dy * dy)

        if length < 0.001:
            return None

        # 归一化方向
        dx /= length
        dy /= length

        # 法线方向（垂直于边）
        nx = -dy
        ny = dx

        # 半壁厚
        half_t = thickness / 2

        # 8个顶点（内外两侧，上下两层）
        vertices = np.array([
            # 外侧底层
            [x1 + nx * half_t, y1 + ny * half_t, z_bottom],  # 0
            [x2 + nx * half_t, y2 + ny * half_t, z_bottom],  # 1
            # 外侧顶层
            [x1 + nx * half_t, y1 + ny * half_t, z_top],     # 2
            [x2 + nx * half_t, y2 + ny * half_t, z_top],     # 3
            # 内侧底层
            [x1 - nx * half_t, y1 - ny * half_t, z_bottom],  # 4
            [x2 - nx * half_t, y2 - ny * half_t, z_bottom],  # 5
            # 内侧顶层
            [x1 - nx * half_t, y1 - ny * half_t, z_top],     # 6
            [x2 - nx * half_t, y2 - ny * half_t, z_top],     # 7
        ])

        # 12个三角面
        faces = np.array([
            # 外侧面
            [0, 1, 3],
            [0, 3, 2],
            # 内侧面
            [4, 6, 7],
            [4, 7, 5],
            # 顶面
            [2, 3, 7],
            [2, 7, 6],
            # 底面
            [0, 4, 5],
            [0, 5, 1],
            # 左端面
            [0, 2, 6],
            [0, 6, 4],
            # 右端面
            [1, 5, 7],
            [1, 7, 3],
        ])

        return trimesh.Trimesh(vertices=vertices, faces=faces)

    def create_continuous_wall(self, path_points: list,
                               z_bottom: float, z_top: float,
                               thickness: float) -> Optional[trimesh.Trimesh]:
        """
        沿路径创建连续的薄壁结构，转角处平滑连接

        Args:
            path_points: 路径点列表 [(x, y), ...]
            z_bottom: 底部Z坐标
            z_top: 顶部Z坐标
            thickness: 壁厚

        Returns:
            连续墙壁网格
        """
        n = len(path_points)
        if n < 2:
            return None

        half_t = thickness / 2
        vertices = []
        faces = []

        # 计算每个点的平均法线（用于平滑转角）
        normals = []
        for i in range(n):
            # 计算当前点的法线
            if i == 0:
                # 第一个点：只用下一段的法线
                dx = path_points[1][0] - path_points[0][0]
                dy = path_points[1][1] - path_points[0][1]
                length = math.sqrt(dx * dx + dy * dy)
                if length > 0.001:
                    nx, ny = -dy / length, dx / length
                else:
                    nx, ny = 0, 1
            elif i == n - 1:
                # 最后一个点：只用上一段的法线
                dx = path_points[n-1][0] - path_points[n-2][0]
                dy = path_points[n-1][1] - path_points[n-2][1]
                length = math.sqrt(dx * dx + dy * dy)
                if length > 0.001:
                    nx, ny = -dy / length, dx / length
                else:
                    nx, ny = 0, 1
            else:
                # 中间点：使用相邻两段的平均法线
                # 前一段
                dx1 = path_points[i][0] - path_points[i-1][0]
                dy1 = path_points[i][1] - path_points[i-1][1]
                len1 = math.sqrt(dx1 * dx1 + dy1 * dy1)
                if len1 > 0.001:
                    nx1, ny1 = -dy1 / len1, dx1 / len1
                else:
                    nx1, ny1 = 0, 1

                # 后一段
                dx2 = path_points[i+1][0] - path_points[i][0]
                dy2 = path_points[i+1][1] - path_points[i][1]
                len2 = math.sqrt(dx2 * dx2 + dy2 * dy2)
                if len2 > 0.001:
                    nx2, ny2 = -dy2 / len2, dx2 / len2
                else:
                    nx2, ny2 = 0, 1

                # 平均法线
                nx = (nx1 + nx2) / 2
                ny = (ny1 + ny2) / 2
                avg_len = math.sqrt(nx * nx + ny * ny)
                if avg_len > 0.001:
                    nx /= avg_len
                    ny /= avg_len

            normals.append((nx, ny))

        # 为每个点生成4个顶点（内外两侧，上下两层）
        for i in range(n):
            x, y = path_points[i]
            nx, ny = normals[i]

            # 外侧底层
            vertices.append([x + nx * half_t, y + ny * half_t, z_bottom])
            # 外侧顶层
            vertices.append([x + nx * half_t, y + ny * half_t, z_top])
            # 内侧底层
            vertices.append([x - nx * half_t, y - ny * half_t, z_bottom])
            # 内侧顶层
            vertices.append([x - nx * half_t, y - ny * half_t, z_top])

        # 生成面（连接相邻点）
        for i in range(n - 1):
            base = i * 4
            next_base = (i + 1) * 4

            # 外侧面
            faces.append([base + 0, next_base + 0, next_base + 1])
            faces.append([base + 0, next_base + 1, base + 1])

            # 内侧面
            faces.append([base + 2, base + 3, next_base + 3])
            faces.append([base + 2, next_base + 3, next_base + 2])

            # 顶面
            faces.append([base + 1, next_base + 1, next_base + 3])
            faces.append([base + 1, next_base + 3, base + 3])

            # 底面
            faces.append([base + 0, base + 2, next_base + 2])
            faces.append([base + 0, next_base + 2, next_base + 0])

        # 添加两端的封口面
        # 起始端
        faces.append([0, 1, 3])
        faces.append([0, 3, 2])

        # 结束端
        end_base = (n - 1) * 4
        faces.append([end_base + 0, end_base + 2, end_base + 3])
        faces.append([end_base + 0, end_base + 3, end_base + 1])

        vertices = np.array(vertices)
        faces = np.array(faces)

        return trimesh.Trimesh(vertices=vertices, faces=faces)

    @staticmethod
    def merge_meshes(meshes: List[trimesh.Trimesh]) -> Optional[trimesh.Trimesh]:
        """
        合并多个网格

        Args:
            meshes: 网格列表

        Returns:
            合并后的网格，如果列表为空则返回None
        """
        if not meshes:
            return None

        if len(meshes) == 1:
            return meshes[0]

        return trimesh.util.concatenate(meshes)

    @staticmethod
    def validate_polygon(polygon: ShapelyPolygon) -> Optional[ShapelyPolygon]:
        """
        验证并修复多边形

        Args:
            polygon: 输入多边形

        Returns:
            修复后的多边形，如果无效则返回None
        """
        if not polygon.is_valid:
            polygon = make_valid(polygon)

        if polygon.is_empty or polygon.area < 1e-6:
            return None

        return polygon

    @staticmethod
    def ensure_closed(coords: List[tuple]) -> List[tuple]:
        """
        确保坐标列表闭合

        Args:
            coords: 坐标列表

        Returns:
            闭合的坐标列表
        """
        if coords and coords[0] != coords[-1]:
            return coords + [coords[0]]
        return coords
