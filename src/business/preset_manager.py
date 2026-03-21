"""
预设管理器模块

负责参数预设的加载、保存和管理。
支持完整的 SliceParams 序列化。
"""

import json
import os
from typing import Dict, List, Optional
from dataclasses import asdict, fields

from src.core.types import (
    SliceParams, ShellParams, EdgeType,
    serialize_params, deserialize_params
)


class PresetManager:
    """预设/模板管理器

    管理切片参数预设，支持：
    - 内置预设（标准直边字、标准斜边字等）
    - 用户自定义预设
    - 完整参数序列化（所有参数组）
    """

    # 预设文件版本
    PRESET_VERSION = "2.0"

    # 内置预设（简化版，仅包含核心参数）
    BUILTIN_PRESETS = {
        "标准直边字": {
            "version": "2.0",
            "description": "适用于40cm以下的直边发光字",
            "shell": {
                "height": 30.0,
                "edge_type": "STRAIGHT",
                "wall_thickness": 1.2,
                "layer_height": 0.3,
                "wall_count": 1
            }
        },
        "标准斜边字": {
            "version": "2.0",
            "description": "适用于40cm以下的斜边发光字",
            "shell": {
                "height": 30.0,
                "edge_type": "BEVELED",
                "wall_thickness": 1.2,
                "layer_height": 0.3,
                "bevel_width": 5.0,
                "bevel_direction": "TOP_SMALL",
                "baseplate_thickness": 10.0,
                "panel_thickness": 3.0
            }
        },
        "大字直边": {
            "version": "2.0",
            "description": "适用于40cm以上的大型直边发光字",
            "shell": {
                "height": 35.0,
                "edge_type": "STRAIGHT",
                "wall_thickness": 1.3,
                "layer_height": 0.3,
                "wall_count": 1
            }
        },
        "大字斜边": {
            "version": "2.0",
            "description": "适用于40cm以上的大型斜边发光字",
            "shell": {
                "height": 35.0,
                "edge_type": "BEVELED",
                "wall_thickness": 1.3,
                "layer_height": 0.3,
                "bevel_width": 8.0,
                "bevel_direction": "TOP_SMALL",
                "baseplate_thickness": 12.0,
                "panel_thickness": 3.0
            }
        }
    }

    def __init__(self, presets_dir: str = "presets"):
        self.presets_dir = presets_dir
        self.presets: Dict[str, dict] = {}
        self._ensure_presets_dir()
        self._load_all_presets()

    def _ensure_presets_dir(self):
        """确保预设目录存在"""
        if not os.path.exists(self.presets_dir):
            os.makedirs(self.presets_dir)

    def _load_all_presets(self):
        """加载所有预设"""
        # 加载内置预设
        self.presets.update(self.BUILTIN_PRESETS)

        # 加载用户预设
        try:
            for filename in os.listdir(self.presets_dir):
                if filename.endswith('.preset') or filename.endswith('.json'):
                    name = os.path.splitext(filename)[0]
                    try:
                        preset = self._load_preset_file(
                            os.path.join(self.presets_dir, filename)
                        )
                        self.presets[name] = preset
                    except Exception as e:
                        print(f"加载预设 {filename} 失败: {e}")
        except FileNotFoundError:
            pass

    def _load_preset_file(self, file_path: str) -> dict:
        """从文件加载预设"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_preset(self, name: str) -> SliceParams:
        """加载预设并返回SliceParams

        Args:
            name: 预设名称

        Returns:
            SliceParams 对象

        Raises:
            ValueError: 预设不存在时抛出
        """
        if name not in self.presets:
            raise ValueError(f"预设 '{name}' 不存在")

        preset_data = self.presets[name]
        return self._create_params_from_preset(preset_data)

    def save_preset(self, name: str, params: SliceParams,
                    description: str = "", full_params: bool = True) -> None:
        """保存预设

        Args:
            name: 预设名称
            params: 切片参数
            description: 预设描述
            full_params: 是否保存完整参数（True=所有参数，False=仅 shell 参数）
        """
        if full_params:
            # 使用完整序列化
            preset_data = serialize_params(params)
            preset_data["version"] = self.PRESET_VERSION
            preset_data["description"] = description
        else:
            # 仅保存 shell 参数（向后兼容）
            preset_data = {
                "version": self.PRESET_VERSION,
                "description": description,
                "shell": self._serialize_shell_params(params.shell),
            }

        # 保存到文件
        file_path = os.path.join(self.presets_dir, f"{name}.preset")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(preset_data, f, ensure_ascii=False, indent=2)

        # 更新内存中的预设
        self.presets[name] = preset_data

    def save_preset_full(self, name: str, params: SliceParams,
                         description: str = "") -> None:
        """保存完整预设（包含所有参数）

        这是 save_preset 的便捷方法，始终保存完整参数。

        Args:
            name: 预设名称
            params: 切片参数
            description: 预设描述
        """
        self.save_preset(name, params, description, full_params=True)

    def delete_preset(self, name: str) -> None:
        """删除预设

        Args:
            name: 预设名称

        Raises:
            ValueError: 尝试删除内置预设或预设不存在时抛出
        """
        if name in self.BUILTIN_PRESETS:
            raise ValueError(f"不能删除内置预设 '{name}'")

        if name not in self.presets:
            raise ValueError(f"预设 '{name}' 不存在")

        # 删除文件
        file_path = os.path.join(self.presets_dir, f"{name}.preset")
        if os.path.exists(file_path):
            os.remove(file_path)

        # 从内存中移除
        del self.presets[name]

    def list_presets(self) -> List[str]:
        """列出所有预设名称

        Returns:
            预设名称列表
        """
        return list(self.presets.keys())

    def get_preset_info(self, name: str) -> dict:
        """获取预设信息

        Args:
            name: 预设名称

        Returns:
            包含 name, description, is_builtin, version 的字典

        Raises:
            ValueError: 预设不存在时抛出
        """
        if name not in self.presets:
            raise ValueError(f"预设 '{name}' 不存在")

        preset = self.presets[name]
        return {
            "name": name,
            "description": preset.get("description", ""),
            "is_builtin": name in self.BUILTIN_PRESETS,
            "version": preset.get("version", "1.0")
        }

    def get_builtin_presets(self) -> List[str]:
        """获取内置预设列表

        Returns:
            内置预设名称列表
        """
        return list(self.BUILTIN_PRESETS.keys())

    def get_user_presets(self) -> List[str]:
        """获取用户预设列表

        Returns:
            用户预设名称列表
        """
        return [name for name in self.presets.keys()
                if name not in self.BUILTIN_PRESETS]

    def get_default_preset(self) -> SliceParams:
        """获取默认预设

        Returns:
            默认的 SliceParams 对象
        """
        return self.load_preset("标准直边字")

    def _create_params_from_preset(self, preset_data: dict) -> SliceParams:
        """从预设数据创建SliceParams

        支持两种格式：
        - v2.0: 完整参数格式（使用 deserialize_params）
        - v1.0: 旧格式（仅 shell 参数）

        Args:
            preset_data: 预设数据字典

        Returns:
            SliceParams 对象
        """
        version = preset_data.get("version", "1.0")

        # v2.0 格式：使用完整反序列化
        if version >= "2.0" and any(key in preset_data for key in
                                     ["step", "skirt", "connected", "speed", "gcode"]):
            # 移除非参数字段
            params_data = {k: v for k, v in preset_data.items()
                          if k not in ["version", "description", "name"]}
            return deserialize_params(params_data)

        # v1.0 格式：手动解析 shell 参数
        params = SliceParams()

        if "shell" in preset_data:
            shell_data = preset_data["shell"]
            params.shell.height = shell_data.get("height", 30.0)
            params.shell.wall_thickness = shell_data.get("wall_thickness", 1.2)
            params.shell.layer_height = shell_data.get("layer_height", 0.3)
            params.shell.wall_count = shell_data.get("wall_count", 1)
            params.shell.bevel_width = shell_data.get("bevel_width", 5.0)
            params.shell.baseplate_thickness = shell_data.get("baseplate_thickness", 10.0)
            params.shell.panel_thickness = shell_data.get("panel_thickness", 3.0)
            params.shell.dxf_outer_clearance = shell_data.get("dxf_outer_clearance", 1.0)
            params.shell.dxf_hole_clearance = shell_data.get("dxf_hole_clearance", 1.0)
            params.shell.dxf_laser_kerf = shell_data.get("dxf_laser_kerf", 0.0)

            edge_type_str = shell_data.get("edge_type", "STRAIGHT")
            try:
                params.shell.edge_type = EdgeType[edge_type_str]
            except KeyError:
                params.shell.edge_type = EdgeType.STRAIGHT

            # v1.0 也支持 bevel_direction
            bevel_dir_str = shell_data.get("bevel_direction", "TOP_SMALL")
            try:
                from src.core.types import BevelDirection
                params.shell.bevel_direction = BevelDirection[bevel_dir_str]
            except (KeyError, ImportError):
                pass

        return params

    def _serialize_shell_params(self, shell: ShellParams) -> dict:
        """序列化ShellParams（向后兼容）

        Args:
            shell: ShellParams 对象

        Returns:
            序列化后的字典
        """
        return {
            "height": shell.height,
            "edge_type": shell.edge_type.name,
            "wall_thickness": shell.wall_thickness,
            "layer_height": shell.layer_height,
            "wall_count": shell.wall_count,
            "bevel_width": shell.bevel_width,
            "bevel_direction": shell.bevel_direction.name,
            "baseplate_thickness": shell.baseplate_thickness,
            "panel_thickness": shell.panel_thickness,
            "dxf_outer_clearance": shell.dxf_outer_clearance,
            "dxf_hole_clearance": shell.dxf_hole_clearance,
            "dxf_laser_kerf": shell.dxf_laser_kerf,
        }

    def export_preset(self, name: str, file_path: str) -> None:
        """导出预设到指定文件

        Args:
            name: 预设名称
            file_path: 导出文件路径
        """
        if name not in self.presets:
            raise ValueError(f"预设 '{name}' 不存在")

        preset_data = self.presets[name]
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(preset_data, f, ensure_ascii=False, indent=2)

    def import_preset(self, file_path: str, name: Optional[str] = None) -> str:
        """从文件导入预设

        Args:
            file_path: 预设文件路径
            name: 预设名称（可选，默认使用文件名）

        Returns:
            导入的预设名称
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        preset_data = self._load_preset_file(file_path)

        # 确定预设名称
        if name is None:
            name = os.path.splitext(os.path.basename(file_path))[0]

        # 检查是否与内置预设冲突
        if name in self.BUILTIN_PRESETS:
            name = f"{name}_用户"

        # 保存到预设目录
        target_path = os.path.join(self.presets_dir, f"{name}.preset")
        with open(target_path, 'w', encoding='utf-8') as f:
            json.dump(preset_data, f, ensure_ascii=False, indent=2)

        # 更新内存
        self.presets[name] = preset_data

        return name

    def reload_presets(self) -> None:
        """重新加载所有预设"""
        self.presets.clear()
        self._load_all_presets()
