"""
MINGDA SignMaker - 异形边DXF加载器

从DXF文件加载异形边轮廓，支持INC-S格式的SPLINE曲线。

INC-S异形边DXF文件特点：
- 每个文件包含单个SPLINE实体
- 使用B样条曲线定义轮廓
- 控制点可能有重复（用于控制切线方向）
- 标准高度为30mm，宽度0.5-6mm
"""

from __future__ import annotations
from typing import List, Tuple, Optional
from pathlib import Path
import os

from .types import EdgeProfile, EdgeProfileType, InterpolationType


class EdgeProfileDXFLoader:
    """从DXF文件加载异形边轮廓

    支持INC-S格式的异形边DXF文件，自动提取SPLINE曲线并归一化控制点。

    使用示例:
        loader = EdgeProfileDXFLoader()
        profile = loader.load_from_dxf("resources/profiles/profile_1.dxf")

        print(f"Width: {profile.original_width}mm")
        print(f"Height: {profile.original_height}mm")
        print(f"Control points: {len(profile.control_points)}")
    """

    def __init__(self):
        self._ezdxf_available = None

    def _check_ezdxf(self) -> bool:
        """检查ezdxf是否可用"""
        if self._ezdxf_available is None:
            try:
                import ezdxf
                self._ezdxf_available = True
            except ImportError:
                self._ezdxf_available = False
        return self._ezdxf_available

    def load_from_dxf(self, dxf_path: str) -> EdgeProfile:
        """
        从DXF文件加载异形边轮廓

        Args:
            dxf_path: DXF文件路径

        Returns:
            EdgeProfile对象

        Raises:
            ImportError: 如果ezdxf未安装
            FileNotFoundError: 如果文件不存在
            ValueError: 如果DXF中没有SPLINE实体
        """
        if not self._check_ezdxf():
            raise ImportError("ezdxf library is required to load DXF files. "
                            "Install it with: pip install ezdxf")

        import ezdxf

        if not os.path.exists(dxf_path):
            raise FileNotFoundError(f"DXF file not found: {dxf_path}")

        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()

        # 查找SPLINE实体
        splines = [e for e in msp if e.dxftype() == 'SPLINE']
        if not splines:
            # 尝试查找LWPOLYLINE或POLYLINE
            polylines = [e for e in msp if e.dxftype() in ('LWPOLYLINE', 'POLYLINE')]
            if polylines:
                return self._load_from_polyline(polylines[0], dxf_path)
            raise ValueError(f"No SPLINE or POLYLINE found in {dxf_path}")

        spline = splines[0]

        # 使用flattening获取真实的SPLINE曲线采样点（而不是控制点）
        # 控制点只是B样条的控制参数，曲线并不通过控制点
        try:
            flattened_points = list(spline.flattening(0.05))  # 0.05mm精度
            if flattened_points:
                # 转换为3D元组格式
                curve_points = [(p[0], p[1], 0) for p in flattened_points]
            else:
                # 回退到控制点
                curve_points = list(spline.control_points)
        except Exception:
            # 如果flattening失败，回退到控制点
            curve_points = list(spline.control_points)

        if not curve_points:
            raise ValueError(f"SPLINE has no points in {dxf_path}")

        # 归一化曲线点
        normalized, width, height = self._normalize_points(curve_points)

        # 提取文件名作为名称
        name = Path(dxf_path).stem

        return EdgeProfile(
            profile_type=EdgeProfileType.DXF,
            control_points=normalized,
            interpolation=InterpolationType.LINEAR,  # 已经是采样曲线，使用线性插值
            sample_points=100,
            original_width=width,
            original_height=height,
            source_file=dxf_path,
            name=name,
            description=f"Loaded from {Path(dxf_path).name}"
        )

    def _load_from_polyline(
        self,
        polyline,
        dxf_path: str
    ) -> EdgeProfile:
        """从LWPOLYLINE或POLYLINE加载"""
        if polyline.dxftype() == 'LWPOLYLINE':
            points = [(p[0], p[1], 0) for p in polyline.get_points()]
        else:
            points = [(v.dxf.location.x, v.dxf.location.y, 0)
                     for v in polyline.vertices]

        if not points:
            raise ValueError(f"Polyline has no points in {dxf_path}")

        normalized, width, height = self._normalize_points(points)
        name = Path(dxf_path).stem

        return EdgeProfile(
            profile_type=EdgeProfileType.DXF,
            control_points=normalized,
            interpolation=InterpolationType.LINEAR,  # 折线用线性插值
            sample_points=100,
            original_width=width,
            original_height=height,
            source_file=dxf_path,
            name=name,
            description=f"Loaded from {Path(dxf_path).name}"
        )

    def _normalize_points(
        self,
        points: List[Tuple[float, float, float]]
    ) -> Tuple[List[Tuple[float, float]], float, float]:
        """
        归一化SPLINE控制点

        将绝对坐标转换为[0,1]范围的归一化坐标。

        Args:
            points: 原始3D控制点 [(x, y, z), ...]

        Returns:
            (normalized_2d_points, width, height)
            - normalized_2d_points: 归一化后的点 [(nx, nz), ...]
            - width: 原始宽度（mm）
            - height: 原始高度（mm）
        """
        if not points:
            return [], 0.0, 0.0

        # 提取X和Y坐标（忽略Z，DXF中通常为0）
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]

        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)

        width = abs(x_max - x_min)
        height = abs(y_max - y_min)

        if width < 0.001 or height < 0.001:
            # 退化情况
            return [(0.0, 0.0), (0.0, 1.0)], width, height

        # 归一化到[0,1]范围
        normalized = []
        for x, y, _ in points:
            # X轴代表水平偏移（bevel_width方向）
            # Y轴代表高度（shell_height方向）
            # nx=0表示基线（无偏移），nx=1表示最大偏移（波浪/锯齿凸出）
            nx = (x - x_min) / width
            nz = (y - y_min) / height
            normalized.append((nx, nz))

        # 去除重复点
        unique_points = self._remove_duplicate_points(normalized)

        # 按Z坐标排序
        unique_points = sorted(unique_points, key=lambda p: p[1])

        return unique_points, width, height

    def _remove_duplicate_points(
        self,
        points: List[Tuple[float, float]],
        tolerance: float = 0.001
    ) -> List[Tuple[float, float]]:
        """
        移除接近重复的控制点

        INC-S的SPLINE有重复控制点（用于控制B样条切线方向），
        归一化后需要去重。

        Args:
            points: 控制点列表
            tolerance: 距离容差

        Returns:
            去重后的控制点列表
        """
        if not points:
            return []

        result = [points[0]]
        for p in points[1:]:
            last = result[-1]
            dist = ((p[0] - last[0])**2 + (p[1] - last[1])**2) ** 0.5
            if dist > tolerance:
                result.append(p)

        return result

    def load_all_from_directory(
        self,
        directory: str,
        pattern: str = "*.dxf"
    ) -> List[EdgeProfile]:
        """
        从目录加载所有DXF文件

        Args:
            directory: 目录路径
            pattern: 文件匹配模式

        Returns:
            EdgeProfile列表
        """
        import glob

        dxf_files = glob.glob(os.path.join(directory, pattern))
        profiles = []

        for dxf_path in sorted(dxf_files):
            try:
                profile = self.load_from_dxf(dxf_path)
                profiles.append(profile)
            except Exception as e:
                print(f"Warning: Failed to load {dxf_path}: {e}")

        return profiles

    def get_profile_info(self, dxf_path: str) -> dict:
        """
        获取DXF文件的轮廓信息（不完全加载）

        Args:
            dxf_path: DXF文件路径

        Returns:
            包含文件信息的字典
        """
        if not self._check_ezdxf():
            return {"error": "ezdxf not installed"}

        import ezdxf

        try:
            doc = ezdxf.readfile(dxf_path)
            msp = doc.modelspace()

            splines = [e for e in msp if e.dxftype() == 'SPLINE']
            if splines:
                spline = splines[0]
                cps = list(spline.control_points)
                xs = [p[0] for p in cps]
                ys = [p[1] for p in cps]

                return {
                    "name": Path(dxf_path).stem,
                    "type": "SPLINE",
                    "control_points": len(cps),
                    "width": abs(max(xs) - min(xs)),
                    "height": abs(max(ys) - min(ys)),
                    "path": dxf_path
                }

            polylines = [e for e in msp if e.dxftype() in ('LWPOLYLINE', 'POLYLINE')]
            if polylines:
                return {
                    "name": Path(dxf_path).stem,
                    "type": polylines[0].dxftype(),
                    "path": dxf_path
                }

            return {"error": "No valid entities found"}

        except Exception as e:
            return {"error": str(e)}
