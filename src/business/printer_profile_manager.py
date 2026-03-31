"""
独立打印机档案管理器。

负责 Klipper 单喷头打印机档案的持久化、加载和 CRUD。
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional

from src.core.types import PrinterProfile, SliceParams
from .settings_manager import SettingsManager


def serialize_printer_profile(profile: PrinterProfile) -> dict:
    """将打印机档案序列化为 JSON 兼容字典。"""
    return asdict(profile)


def deserialize_printer_profile(data: dict) -> PrinterProfile:
    """从字典恢复打印机档案。"""
    if not data:
        return PrinterProfile()
    return PrinterProfile(
        id=data.get("id", PrinterProfile().id),
        name=data.get("name", "Klipper Default"),
        bed_width=float(data.get("bed_width", 800.0)),
        bed_depth=float(data.get("bed_depth", 1200.0)),
        bed_height=float(data.get("bed_height", 100.0)),
        nozzle_diameter=float(data.get("nozzle_diameter", 0.8)),
        filament_diameter=float(data.get("filament_diameter", 1.75)),
        retract_length=float(data.get("retract_length", 2.0)),
        retract_speed=float(data.get("retract_speed", 40.0)),
        z_hop_short=float(data.get("z_hop_short", 0.5)),
        z_hop_long=float(data.get("z_hop_long", 5.0)),
        long_travel_threshold=float(data.get("long_travel_threshold", 100.0)),
        start_gcode=data.get("start_gcode", "G28"),
        end_gcode=data.get("end_gcode", ""),
        color_change_command_template=data.get("color_change_command_template", "T{index}"),
    )


def clone_printer_profile(profile: PrinterProfile) -> PrinterProfile:
    """深拷贝打印机档案。"""
    return deserialize_printer_profile(serialize_printer_profile(profile))


def apply_printer_profile_to_params(params: SliceParams, profile: PrinterProfile) -> None:
    """将打印机档案同步到 SliceParams 的 machine/gcode 快照。"""
    params.machine.name = profile.name
    params.machine.bed_width = profile.bed_width
    params.machine.bed_depth = profile.bed_depth
    params.machine.bed_height = profile.bed_height
    params.machine.nozzle_diameter = profile.nozzle_diameter
    params.machine.extruder_count = 1

    params.gcode.machine_type = "Klipper"
    params.gcode.retract_length = profile.retract_length
    params.gcode.retract_speed = profile.retract_speed
    params.gcode.z_hop_height1 = profile.z_hop_short
    params.gcode.z_hop_height2 = profile.z_hop_long
    params.gcode.distance_threshold = profile.long_travel_threshold
    params.gcode.filament_diameter = profile.filament_diameter
    params.gcode.start_gcode = profile.start_gcode
    params.gcode.end_gcode = profile.end_gcode
    params.gcode.color_change_command_template = profile.color_change_command_template


def printer_profile_from_params(
    params: SliceParams,
    *,
    profile_id: str = "",
    name: Optional[str] = None,
) -> PrinterProfile:
    """从当前 SliceParams 的 machine/gcode 快照构建打印机档案。"""
    return PrinterProfile(
        id=profile_id or PrinterProfile().id,
        name=name or params.machine.name or "Klipper Default",
        bed_width=params.machine.bed_width,
        bed_depth=params.machine.bed_depth,
        bed_height=params.machine.bed_height,
        nozzle_diameter=params.machine.nozzle_diameter,
        filament_diameter=params.gcode.filament_diameter,
        retract_length=params.gcode.retract_length,
        retract_speed=params.gcode.retract_speed,
        z_hop_short=params.gcode.z_hop_height1,
        z_hop_long=params.gcode.z_hop_height2,
        long_travel_threshold=params.gcode.distance_threshold,
        start_gcode=params.gcode.start_gcode,
        end_gcode=params.gcode.end_gcode,
        color_change_command_template=(
            params.gcode.color_change_command_template or "T{index}"
        ),
    )


class PrinterProfileManager:
    """独立打印机档案管理器。"""

    FILE_NAME = "printer_profiles.json"
    FILE_VERSION = "1.0"

    def __init__(self, config_dir: Optional[str] = None):
        if config_dir:
            self._config_dir = Path(config_dir)
        else:
            self._config_dir = SettingsManager._get_default_config_dir()
        self._file_path = self._config_dir / self.FILE_NAME
        self._profiles: Dict[str, PrinterProfile] = {}
        self._default_profile_id: str = ""
        self._load()

    def _build_default_profile(self) -> PrinterProfile:
        return PrinterProfile(name="Klipper Default")

    def _ensure_defaults(self) -> None:
        if self._profiles:
            if self._default_profile_id in self._profiles:
                return
            self._default_profile_id = next(iter(self._profiles))
            return

        profile = self._build_default_profile()
        self._profiles[profile.id] = profile
        self._default_profile_id = profile.id

    def _load(self) -> None:
        self._profiles = {}
        self._default_profile_id = ""

        if self._file_path.exists():
            try:
                with open(self._file_path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                self._default_profile_id = data.get("default_profile_id", "")
                for item in data.get("profiles", []):
                    profile = deserialize_printer_profile(item)
                    self._profiles[profile.id] = profile
            except Exception:
                self._profiles = {}
                self._default_profile_id = ""

        self._ensure_defaults()

    def _save(self) -> None:
        self._ensure_defaults()
        self._config_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "version": self.FILE_VERSION,
            "default_profile_id": self._default_profile_id,
            "profiles": [
                serialize_printer_profile(profile)
                for profile in self.list_profiles()
            ],
        }
        with open(self._file_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)

    def list_profiles(self) -> List[PrinterProfile]:
        return sorted(
            (clone_printer_profile(profile) for profile in self._profiles.values()),
            key=lambda profile: (profile.name.lower(), profile.id),
        )

    def get_profile(self, profile_id: str) -> Optional[PrinterProfile]:
        profile = self._profiles.get(profile_id)
        if profile is None:
            return None
        return clone_printer_profile(profile)

    def get_default_profile_id(self) -> str:
        self._ensure_defaults()
        return self._default_profile_id

    def set_default_profile_id(self, profile_id: str) -> bool:
        if profile_id not in self._profiles:
            return False
        self._default_profile_id = profile_id
        self._save()
        return True

    def save_profile(self, profile: PrinterProfile) -> PrinterProfile:
        self._profiles[profile.id] = clone_printer_profile(profile)
        if not self._default_profile_id:
            self._default_profile_id = profile.id
        self._save()
        return clone_printer_profile(self._profiles[profile.id])

    def create_profile(
        self,
        name: str,
        base_profile: Optional[PrinterProfile] = None,
    ) -> PrinterProfile:
        profile = clone_printer_profile(base_profile or self._build_default_profile())
        profile.id = PrinterProfile().id
        profile.name = name
        return self.save_profile(profile)

    def delete_profile(self, profile_id: str) -> bool:
        if profile_id not in self._profiles:
            return False

        del self._profiles[profile_id]
        self._ensure_defaults()
        self._save()
        return True
