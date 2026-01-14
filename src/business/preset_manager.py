"""
预设管理器模块

负责参数预设的加载、保存和管理。
"""

import json
import os
from typing import Dict, List, Optional
from dataclasses import asdict, fields

from src.core.types import SliceParams, ShellParams, EdgeType


class PresetManager:
    """预设/模板管理器"""

    # 内置预设
    BUILTIN_PRESETS = {
        "标准直边字": {
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
            "description": "适用于40cm以下的斜边发光字",
            "shell": {
                "height": 30.0,
                "edge_type": "BEVELED",
                "wall_thickness": 1.2,
                "layer_height": 0.3,
                "bevel_width": 5.0,
                "baseplate_thickness": 10.0,
                "panel_thickness": 3.0
            }
        },
        "大字直边": {
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
            "description": "适用于40cm以上的大型斜边发光字",
            "shell": {
                "height": 35.0,
                "edge_type": "BEVELED",
                "wall_thickness": 1.3,
                "layer_height": 0.3,
                "bevel_width": 8.0,
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

    def _load_preset_file(self, file_path: str) -> dict:
        """从文件加载预设"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_preset(self, name: str) -> SliceParams:
        """加载预设并返回SliceParams"""
        if name not in self.presets:
            raise ValueError(f"预设 '{name}' 不存在")

        preset_data = self.presets[name]
        return self._create_params_from_preset(preset_data)

    def save_preset(self, name: str, params: SliceParams,
                    description: str = "") -> None:
        """保存预设"""
        preset_data = {
            "description": description,
            "shell": self._serialize_shell_params(params.shell),
            # 可以添加其他参数组
        }

        # 保存到文件
        file_path = os.path.join(self.presets_dir, f"{name}.preset")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(preset_data, f, ensure_ascii=False, indent=2)

        # 更新内存中的预设
        self.presets[name] = preset_data

    def delete_preset(self, name: str) -> None:
        """删除预设"""
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
        """列出所有预设"""
        return list(self.presets.keys())

    def get_preset_info(self, name: str) -> dict:
        """获取预设信息"""
        if name not in self.presets:
            raise ValueError(f"预设 '{name}' 不存在")

        preset = self.presets[name]
        return {
            "name": name,
            "description": preset.get("description", ""),
            "is_builtin": name in self.BUILTIN_PRESETS
        }

    def get_default_preset(self) -> SliceParams:
        """获取默认预设"""
        return self.load_preset("标准直边字")

    def _create_params_from_preset(self, preset_data: dict) -> SliceParams:
        """从预设数据创建SliceParams"""
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

            edge_type_str = shell_data.get("edge_type", "STRAIGHT")
            params.shell.edge_type = EdgeType[edge_type_str]

        return params

    def _serialize_shell_params(self, shell: ShellParams) -> dict:
        """序列化ShellParams"""
        return {
            "height": shell.height,
            "edge_type": shell.edge_type.name,
            "wall_thickness": shell.wall_thickness,
            "layer_height": shell.layer_height,
            "wall_count": shell.wall_count,
            "bevel_width": shell.bevel_width,
            "baseplate_thickness": shell.baseplate_thickness,
            "panel_thickness": shell.panel_thickness
        }
