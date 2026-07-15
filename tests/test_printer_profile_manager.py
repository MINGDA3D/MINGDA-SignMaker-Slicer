import json
import shutil
import uuid
from pathlib import Path

import pytest

from src.business.printer_profile_manager import (
    DEFAULT_PRINTER_PROFILE_SPECS,
    DEFAULT_PRINTER_PROFILE_SPEC,
    PrinterProfileManager,
    deserialize_printer_profile,
)
from src.core.types import (
    MINGDA_BED_EXCLUDE_AREA_600X800,
    MINGDA_BED_EXCLUDE_AREA_800X1200,
    default_bed_exclude_area_for_bed,
)


@pytest.fixture
def temp_profile_dir():
    base_dir = Path.cwd() / ".tmp_pytest_profile_manager"
    base_dir.mkdir(parents=True, exist_ok=True)
    tmpdir = base_dir / f"case_{uuid.uuid4().hex}"
    tmpdir.mkdir(parents=True, exist_ok=True)
    try:
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_manager_seeds_only_requested_builtin_profiles(temp_profile_dir):
    manager = PrinterProfileManager(config_dir=str(temp_profile_dir))

    profiles = manager.list_profiles()

    assert [profile.name for profile in profiles] == [
        spec["name"] for spec in DEFAULT_PRINTER_PROFILE_SPECS
    ]
    assert [(profile.bed_width, profile.bed_depth, profile.nozzle_diameter) for profile in profiles] == [
        (spec["bed_width"], spec["bed_depth"], spec["nozzle_diameter"])
        for spec in DEFAULT_PRINTER_PROFILE_SPECS
    ]
    assert [profile.bed_exclude_area for profile in profiles] == [
        default_bed_exclude_area_for_bed(spec["bed_width"], spec["bed_depth"])
        for spec in DEFAULT_PRINTER_PROFILE_SPECS
    ]
    assert all(
        profile.start_gcode
        == "START_PRINT EXTRUDER={nozzle_temperature_initial_layer[0]} "
        "BED=[first_layer_bed_temperature] TOOL=[initial_tool]"
        for profile in profiles
    )
    assert all(profile.end_gcode == "END_PRINT" for profile in profiles)
    assert manager.get_default_profile_id() == DEFAULT_PRINTER_PROFILE_SPEC["id"]


def test_manager_discards_non_builtin_profiles_and_keeps_only_builtin_profiles(temp_profile_dir):
    config_path = temp_profile_dir / PrinterProfileManager.FILE_NAME
    config_path.write_text(
        json.dumps(
            {
                "version": PrinterProfileManager.FILE_VERSION,
                "default_profile_id": "custom-profile",
                "profiles": [
                    {
                        "id": "custom-profile",
                        "name": "Custom Profile",
                        "bed_width": 123.0,
                        "bed_depth": 456.0,
                        "bed_height": 100.0,
                        "nozzle_diameter": 0.5,
                    },
                    {
                        "id": DEFAULT_PRINTER_PROFILE_SPECS[3]["id"],
                        "name": DEFAULT_PRINTER_PROFILE_SPECS[3]["name"],
                        "bed_width": 810.0,
                        "bed_depth": 1210.0,
                        "bed_height": 100.0,
                        "nozzle_diameter": 0.4,
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    manager = PrinterProfileManager(config_dir=str(temp_profile_dir))

    profiles = manager.list_profiles()

    assert len(profiles) == len(DEFAULT_PRINTER_PROFILE_SPECS)
    assert [profile.id for profile in profiles] == [
        spec["id"] for spec in DEFAULT_PRINTER_PROFILE_SPECS
    ]
    assert all(profile.name != "Custom Profile" for profile in profiles)
    assert manager.get_profile(DEFAULT_PRINTER_PROFILE_SPECS[3]["id"]).bed_width == 810.0
    assert manager.get_default_profile_id() == DEFAULT_PRINTER_PROFILE_SPEC["id"]

    saved_data = json.loads(config_path.read_text(encoding="utf-8"))
    assert [profile["id"] for profile in saved_data["profiles"]] == [
        spec["id"] for spec in DEFAULT_PRINTER_PROFILE_SPECS
    ]


def test_large_ad_series_profiles_use_requested_bed_exclude_area(temp_profile_dir):
    manager = PrinterProfileManager(config_dir=str(temp_profile_dir))

    profiles = [
        profile
        for profile in manager.list_profiles()
        if (
            "AD-F4 Mini" not in profile.name
            and any(model in profile.name for model in ("AD-F4", "AD-F6", "AD-F10"))
        )
    ]

    assert len(profiles) == 12
    assert all(profile.bed_width == 800.0 for profile in profiles)
    assert all(profile.bed_depth == 1200.0 for profile in profiles)
    assert all(profile.bed_exclude_area == MINGDA_BED_EXCLUDE_AREA_800X1200 for profile in profiles)


def test_ad_f4_mini_profiles_use_requested_bed_exclude_area(temp_profile_dir):
    manager = PrinterProfileManager(config_dir=str(temp_profile_dir))

    profiles = [
        profile
        for profile in manager.list_profiles()
        if "AD-F4 Mini" in profile.name
    ]

    assert len(profiles) == 3
    assert all(profile.bed_width == 600.0 for profile in profiles)
    assert all(profile.bed_depth == 800.0 for profile in profiles)
    assert all(profile.bed_exclude_area == MINGDA_BED_EXCLUDE_AREA_600X800 for profile in profiles)


def test_renamed_large_ad_series_profile_names_are_seeded(temp_profile_dir):
    manager = PrinterProfileManager(config_dir=str(temp_profile_dir))

    names = {profile.name for profile in manager.list_profiles()}

    assert "MINGDA AD-F6 Pro 0.4mm Nozzle" in names
    assert "MINGDA AD-F6 Pro 0.6mm Nozzle" in names
    assert "MINGDA AD-F6 Pro 0.8mm Nozzle" in names
    assert "MINGDA AD-F10 Ultra 0.4mm Nozzle" in names
    assert "MINGDA AD-F10 Ultra 0.6mm Nozzle" in names
    assert "MINGDA AD-F10 Ultra 0.8mm Nozzle" in names


def test_manager_upgrades_legacy_builtin_start_and_end_gcode_defaults(temp_profile_dir):
    config_path = temp_profile_dir / PrinterProfileManager.FILE_NAME
    config_path.write_text(
        json.dumps(
            {
                "version": PrinterProfileManager.FILE_VERSION,
                "default_profile_id": DEFAULT_PRINTER_PROFILE_SPECS[0]["id"],
                "profiles": [
                    {
                        "id": DEFAULT_PRINTER_PROFILE_SPECS[0]["id"],
                        "name": DEFAULT_PRINTER_PROFILE_SPECS[0]["name"],
                        "bed_width": DEFAULT_PRINTER_PROFILE_SPECS[0]["bed_width"],
                        "bed_depth": DEFAULT_PRINTER_PROFILE_SPECS[0]["bed_depth"],
                        "bed_height": 100.0,
                        "nozzle_diameter": DEFAULT_PRINTER_PROFILE_SPECS[0]["nozzle_diameter"],
                        "start_gcode": "G28",
                        "end_gcode": "",
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    manager = PrinterProfileManager(config_dir=str(temp_profile_dir))
    profile = manager.get_profile(DEFAULT_PRINTER_PROFILE_SPECS[0]["id"])

    assert profile is not None
    assert (
        profile.start_gcode
        == "START_PRINT EXTRUDER={nozzle_temperature_initial_layer[0]} "
        "BED=[first_layer_bed_temperature] TOOL=[initial_tool]"
    )
    assert profile.end_gcode == "END_PRINT"


@pytest.mark.parametrize(
    "legacy_area",
    [
        [
            "0x730,70x730,70x800,0x800",
            "530x730,600x730,600x800,530x800",
            "0x0,70x0,70x70,0x70",
            "430x0,600x0,600x100,430x100",
            "70x0,430x0,430x20,70x20",
        ],
        [
            "0x0,71x0,71x25,0x25",
            "536x0,600x0,600x40,536x40",
            "566x40,600x40,600x80,566x80",
            "571x182,600x182,600x471,571x471",
            "541x792,600x792,600x800,541x800",
            "0x792,67x792,67x800,0x800",
        ],
    ],
)
def test_manager_upgrades_legacy_ad_f4_mini_bed_exclude_area(
    temp_profile_dir,
    legacy_area,
):
    config_path = temp_profile_dir / PrinterProfileManager.FILE_NAME
    config_path.write_text(
        json.dumps(
            {
                "version": PrinterProfileManager.FILE_VERSION,
                "default_profile_id": DEFAULT_PRINTER_PROFILE_SPECS[0]["id"],
                "profiles": [
                    {
                        "id": DEFAULT_PRINTER_PROFILE_SPECS[0]["id"],
                        "name": DEFAULT_PRINTER_PROFILE_SPECS[0]["name"],
                        "bed_width": DEFAULT_PRINTER_PROFILE_SPECS[0]["bed_width"],
                        "bed_depth": DEFAULT_PRINTER_PROFILE_SPECS[0]["bed_depth"],
                        "bed_height": 100.0,
                        "bed_exclude_area": legacy_area,
                        "nozzle_diameter": DEFAULT_PRINTER_PROFILE_SPECS[0]["nozzle_diameter"],
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    manager = PrinterProfileManager(config_dir=str(temp_profile_dir))
    profile = manager.get_profile(DEFAULT_PRINTER_PROFILE_SPECS[0]["id"])

    assert profile is not None
    assert profile.bed_exclude_area == MINGDA_BED_EXCLUDE_AREA_600X800


def test_manager_upgrades_legacy_large_ad_series_bed_exclude_area(temp_profile_dir):
    config_path = temp_profile_dir / PrinterProfileManager.FILE_NAME
    legacy_area = [
        "0x1130,70x1130,70x1200,0x1200",
        "730x1130,800x1130,800x1200,730x1200",
        "0x0,70x0,70x70,0x70",
        "630x0,800x0,800x100,630x100",
        "70x0,630x0,630x20,70x20",
    ]
    profile_specs = DEFAULT_PRINTER_PROFILE_SPECS[3:]
    config_path.write_text(
        json.dumps(
            {
                "version": PrinterProfileManager.FILE_VERSION,
                "default_profile_id": DEFAULT_PRINTER_PROFILE_SPECS[3]["id"],
                "profiles": [
                    {
                        "id": spec["id"],
                        "name": spec["name"],
                        "bed_width": spec["bed_width"],
                        "bed_depth": spec["bed_depth"],
                        "bed_height": 100.0,
                        "bed_exclude_area": legacy_area,
                        "nozzle_diameter": spec["nozzle_diameter"],
                    }
                    for spec in profile_specs
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    manager = PrinterProfileManager(config_dir=str(temp_profile_dir))
    profiles = [
        profile
        for profile in manager.list_profiles()
        if (
            "AD-F4 Mini" not in profile.name
            and any(model in profile.name for model in ("AD-F4", "AD-F6", "AD-F10"))
        )
    ]

    assert len(profiles) == 12
    assert all(profile.bed_exclude_area == MINGDA_BED_EXCLUDE_AREA_800X1200 for profile in profiles)


def test_deserialize_printer_profile_upgrades_legacy_default_gcode_scripts():
    profile = deserialize_printer_profile(
        {
            "name": "Legacy Snapshot",
            "start_gcode": "G28",
            "end_gcode": "",
        }
    )

    assert (
        profile.start_gcode
        == "START_PRINT EXTRUDER={nozzle_temperature_initial_layer[0]} "
        "BED=[first_layer_bed_temperature] TOOL=[initial_tool]"
    )
    assert profile.end_gcode == "END_PRINT"
