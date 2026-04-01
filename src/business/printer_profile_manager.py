"""
Standalone printer profile manager.

Handles persistence, loading, default seeding, and CRUD for Klipper printer profiles.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional

from src.core.types import (
    PrinterProfile,
    SliceParams,
    normalize_default_gcode_scripts,
)

from .settings_manager import SettingsManager


DEFAULT_BUILTIN_START_GCODE = PrinterProfile().start_gcode
DEFAULT_BUILTIN_END_GCODE = PrinterProfile().end_gcode
LEGACY_START_GCODE = "G28"
LEGACY_END_GCODE = ""


DEFAULT_PRINTER_PROFILE_SPECS = (
    {
        "id": "builtin-mignda-ad-f4-mini-0p4",
        "name": "MIGNDA AD-F4 Mini 0.4mm Nozzle",
        "bed_width": 600.0,
        "bed_depth": 800.0,
        "nozzle_diameter": 0.4,
    },
    {
        "id": "builtin-mignda-ad-f4-mini-0p6",
        "name": "MIGNDA AD-F4 Mini 0.6mm Nozzle",
        "bed_width": 600.0,
        "bed_depth": 800.0,
        "nozzle_diameter": 0.6,
    },
    {
        "id": "builtin-mignda-ad-f4-mini-0p8",
        "name": "MIGNDA AD-F4 Mini 0.8mm Nozzle",
        "bed_width": 600.0,
        "bed_depth": 800.0,
        "nozzle_diameter": 0.8,
    },
    {
        "id": "builtin-mignda-ad-f4-0p4",
        "name": "MIGNDA AD-F4 0.4mm Nozzle",
        "bed_width": 800.0,
        "bed_depth": 1200.0,
        "nozzle_diameter": 0.4,
    },
    {
        "id": "builtin-mignda-ad-f4-0p6",
        "name": "MIGNDA AD-F4 0.6mm Nozzle",
        "bed_width": 800.0,
        "bed_depth": 1200.0,
        "nozzle_diameter": 0.6,
    },
    {
        "id": "builtin-mignda-ad-f4-0p8",
        "name": "MIGNDA AD-F4 0.8mm Nozzle",
        "bed_width": 800.0,
        "bed_depth": 1200.0,
        "nozzle_diameter": 0.8,
    },
    {
        "id": "builtin-mignda-ad-f6-0p4",
        "name": "MIGNDA AD-F6 0.4mm Nozzle",
        "bed_width": 800.0,
        "bed_depth": 1200.0,
        "nozzle_diameter": 0.4,
    },
    {
        "id": "builtin-mignda-ad-f6-0p6",
        "name": "MIGNDA AD-F6 0.6mm Nozzle",
        "bed_width": 800.0,
        "bed_depth": 1200.0,
        "nozzle_diameter": 0.6,
    },
    {
        "id": "builtin-mignda-ad-f6-0p8",
        "name": "MIGNDA AD-F6 0.8mm Nozzle",
        "bed_width": 800.0,
        "bed_depth": 1200.0,
        "nozzle_diameter": 0.8,
    },
    {
        "id": "builtin-mignda-ad-f10-0p4",
        "name": "MIGNDA AD-F10 0.4mm Nozzle",
        "bed_width": 800.0,
        "bed_depth": 1200.0,
        "nozzle_diameter": 0.4,
    },
    {
        "id": "builtin-mignda-ad-f10-0p6",
        "name": "MIGNDA AD-F10 0.6mm Nozzle",
        "bed_width": 800.0,
        "bed_depth": 1200.0,
        "nozzle_diameter": 0.6,
    },
    {
        "id": "builtin-mignda-ad-f10-0p8",
        "name": "MIGNDA AD-F10 0.8mm Nozzle",
        "bed_width": 800.0,
        "bed_depth": 1200.0,
        "nozzle_diameter": 0.8,
    },
)

DEFAULT_PRINTER_PROFILE_NAME = DEFAULT_PRINTER_PROFILE_SPECS[0]["name"]
DEFAULT_PRINTER_PROFILE_ORDER = {
    spec["id"]: index for index, spec in enumerate(DEFAULT_PRINTER_PROFILE_SPECS)
}


def _build_profile_from_spec(spec: dict) -> PrinterProfile:
    return PrinterProfile(
        id=spec["id"],
        name=spec["name"],
        bed_width=spec["bed_width"],
        bed_depth=spec["bed_depth"],
        nozzle_diameter=spec["nozzle_diameter"],
    )


def serialize_printer_profile(profile: PrinterProfile) -> dict:
    """Serialize a printer profile into a JSON-compatible dict."""
    return asdict(profile)


def deserialize_printer_profile(data: dict) -> PrinterProfile:
    """Restore a printer profile from a dict."""
    if not data:
        return PrinterProfile(
            name=DEFAULT_PRINTER_PROFILE_NAME,
            bed_width=DEFAULT_PRINTER_PROFILE_SPECS[0]["bed_width"],
            bed_depth=DEFAULT_PRINTER_PROFILE_SPECS[0]["bed_depth"],
            nozzle_diameter=DEFAULT_PRINTER_PROFILE_SPECS[0]["nozzle_diameter"],
        )
    start_gcode, end_gcode = normalize_default_gcode_scripts(
        data.get("start_gcode", DEFAULT_BUILTIN_START_GCODE),
        data.get("end_gcode", DEFAULT_BUILTIN_END_GCODE),
    )
    return PrinterProfile(
        id=data.get("id", PrinterProfile().id),
        name=data.get("name", DEFAULT_PRINTER_PROFILE_NAME),
        bed_width=float(data.get("bed_width", DEFAULT_PRINTER_PROFILE_SPECS[0]["bed_width"])),
        bed_depth=float(data.get("bed_depth", DEFAULT_PRINTER_PROFILE_SPECS[0]["bed_depth"])),
        bed_height=float(data.get("bed_height", 100.0)),
        nozzle_diameter=float(
            data.get("nozzle_diameter", DEFAULT_PRINTER_PROFILE_SPECS[0]["nozzle_diameter"])
        ),
        filament_diameter=float(data.get("filament_diameter", 1.75)),
        retract_length=float(data.get("retract_length", 2.0)),
        retract_speed=float(data.get("retract_speed", 40.0)),
        z_hop_short=float(data.get("z_hop_short", 0.5)),
        z_hop_long=float(data.get("z_hop_long", 5.0)),
        long_travel_threshold=float(data.get("long_travel_threshold", 100.0)),
        start_gcode=start_gcode,
        end_gcode=end_gcode,
        color_change_command_template=data.get("color_change_command_template", "T{index}"),
    )


def clone_printer_profile(profile: PrinterProfile) -> PrinterProfile:
    """Deep-copy a printer profile."""
    return deserialize_printer_profile(serialize_printer_profile(profile))


def apply_printer_profile_to_params(params: SliceParams, profile: PrinterProfile) -> None:
    """Sync printer profile data into SliceParams machine/gcode snapshots."""
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
    """Build a printer profile from the current SliceParams machine/gcode snapshot."""
    return PrinterProfile(
        id=profile_id or PrinterProfile().id,
        name=name or params.machine.name or DEFAULT_PRINTER_PROFILE_NAME,
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
    """Standalone printer profile manager."""

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
        return _build_profile_from_spec(DEFAULT_PRINTER_PROFILE_SPECS[0])

    def _build_default_profiles(self) -> List[PrinterProfile]:
        return [_build_profile_from_spec(spec) for spec in DEFAULT_PRINTER_PROFILE_SPECS]

    @staticmethod
    def _profile_sort_key(profile: PrinterProfile):
        builtin_index = DEFAULT_PRINTER_PROFILE_ORDER.get(profile.id)
        if builtin_index is not None:
            return (0, builtin_index, profile.id)
        return (1, profile.name.lower(), profile.id)

    def _ensure_defaults(self) -> bool:
        changed = False
        existing_profiles = dict(self._profiles)
        self._profiles = {}

        for profile in self._build_default_profiles():
            saved_profile = existing_profiles.get(profile.id)
            if saved_profile is None:
                self._profiles[profile.id] = profile
                changed = True
                continue

            normalized_profile = clone_printer_profile(saved_profile)
            if (
                normalized_profile.start_gcode == LEGACY_START_GCODE
                and normalized_profile.end_gcode == LEGACY_END_GCODE
            ):
                normalized_profile.start_gcode = profile.start_gcode
                normalized_profile.end_gcode = profile.end_gcode
                changed = True

            self._profiles[profile.id] = normalized_profile

        if set(existing_profiles) != set(self._profiles):
            changed = True

        if self._default_profile_id not in self._profiles:
            self._default_profile_id = self._build_default_profile().id
            changed = True

        return changed

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

        defaults_changed = self._ensure_defaults()
        if defaults_changed and self._file_path.exists():
            self._save()

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
            key=self._profile_sort_key,
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
        if profile.id not in self._profiles:
            raise ValueError("Only the built-in printer profiles are supported.")
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
        raise ValueError("Creating additional printer profiles is disabled.")

    def delete_profile(self, profile_id: str) -> bool:
        if profile_id not in self._profiles:
            return False

        del self._profiles[profile_id]
        self._ensure_defaults()
        self._save()
        return True
