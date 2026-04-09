from pathlib import Path
import re
import xml.etree.ElementTree as ET


TRANSLATIONS_DIR = Path(__file__).resolve().parent.parent / "translations"
ZH_CN_REQUIRED = {
    "MainWindow": {
        "Export G-code...",
        "Loading 3D preview...",
        "3D preview loading failed",
        "Failed to prepare 3D preview:",
        "Export Blocked",
        "Cannot export G-code:",
        "Export G-code",
        "G-code Files (*.gcode);;All Files (*)",
        "G-code exported: ",
        "G-code saved to:",
        "Failed to export G-code:",
        "Exporting G-code...",
        "Text",
        "Add Contours",
        "Text added",
        "Error",
        "Asset",
        "Intersection",
        "Difference",
        "Group",
        "Version: ",
    },
    "ParamPanel": {
        "2D Vector Settings",
        "Contour shaping, shell geometry, wraps, slots, and DXF output.",
        "Machine Settings",
        "Printer profile, printable area, nozzle, and material-related hardware values.",
        "Print Settings",
        "Speed, temperature, cooling, color-change points, and start/end print commands.",
        "Project Snapshot",
        "Color Change",
        "Enable Color Change",
        "Initial color comes from Start G-code. Each change point runs the selected T macro.",
        "Change At Height",
        "Macro Index",
        "Preview",
        "Add Change Point",
        "Remove Selected",
        "Color change disabled.",
        "Initial color comes from Start G-code. No automatic changes are configured.",
        "At {height:.2f}mm -> {command}",
        "Prime Tower",
        "Enable Prime Tower",
        "Prime tower geometry is defined by its center point in bed coordinates.",
        "Center X:",
        "Center Y:",
        "Tower Width:",
        "Tower Depth:",
        "Infill Density:",
        "Printer Profile",
        "New",
        "Duplicate",
        "Rename",
        "Delete",
        "Set Default",
        "Printable Area X:",
        "Printable Area Y:",
        "Printable Area Z:",
        "Nozzle Diameter:",
        "Filament Diameter:",
        "Retract Length:",
        "Retract Speed:",
        "Short Z-Hop:",
        "Long Z-Hop:",
        "Long Travel Threshold:",
        "Color Change Template:",
        "Machine G-code",
        "Machine start G-code",
        "Machine end G-code",
        "Edit Start G-code",
        "Start G-code",
        "Edit End G-code",
        "End G-code",
        "{name} (Project Snapshot)",
        "Using embedded project profile snapshot.",
        "Profile changes are saved immediately.",
        "New Printer Profile",
        "Profile Name:",
        "Duplicate Printer Profile",
        "New Profile Name:",
        "{name} Copy",
        "Rename Printer Profile",
        "Delete Printer Profile",
        "Delete printer profile '{name}'?",
        "Empty",
        "{first} (+{count} more lines)",
        "Klipper Profile",
        "Temperature Settings",
        "Cooling Settings",
        "Skirt Speed:",
        "Step Speed:",
        "First Layer Nozzle Temperature:",
        "Other Layers Nozzle Temperature:",
        "First Layer Bed Temperature:",
        "Other Layers Bed Temperature:",
        "First Layer Fan Speed:",
        "Other Layers Fan Speed:",
    },
    "Preview3D": {
        "Loading 3D preview...",
    },
    "TitleBar": {
        "Export G-code...",
    },
    "GCodeWriter": {
        "Color change is enabled but no change points are configured.",
    },
}

SECONDARY_LOCALE_MUST_DIFFER_FROM_SOURCE = {
    "ParamPanel": {
        "Printer profile, printable area, nozzle, and material-related hardware values.",
        "Printable Area X:",
        "Printable Area Y:",
        "Printable Area Z:",
    },
}


def _collect_messages(ts_name: str, required_contexts: dict[str, set[str]]) -> dict[tuple[str, str], ET.Element]:
    root = ET.parse(TRANSLATIONS_DIR / ts_name).getroot()
    messages = {}
    for context in root.findall("context"):
        ctx_name = context.findtext("name")
        if ctx_name not in required_contexts:
            continue
        for message in context.findall("message"):
            source = message.findtext("source") or ""
            if source in required_contexts[ctx_name]:
                messages[(ctx_name, source)] = message.find("translation")
    return messages


def _assert_required_translations_finished(ts_name: str, required_contexts: dict[str, set[str]]):
    messages = _collect_messages(ts_name, required_contexts)
    missing = []
    unfinished = []
    empty = []
    for ctx_name, sources in required_contexts.items():
        for source in sources:
            translation = messages.get((ctx_name, source))
            if translation is None:
                missing.append((ctx_name, source))
                continue
            if translation.get("type") == "unfinished":
                unfinished.append((ctx_name, source))
            if not (translation.text or "").strip():
                empty.append((ctx_name, source))

    assert not missing
    assert not unfinished
    assert not empty


def test_translation_files_do_not_contain_corruption_markers():
    suspicious = []
    for ts_file in TRANSLATIONS_DIR.glob("signmaker_*.ts"):
        root = ET.parse(ts_file).getroot()
        for context in root.findall("context"):
            ctx_name = context.findtext("name") or ""
            for message in context.findall("message"):
                source = message.findtext("source") or ""
                translation = message.find("translation")
                if translation is None:
                    continue
                text = "".join(translation.itertext())
                if "\ufffd" in text or re.search(r"\?{3,}", text):
                    suspicious.append((ts_file.name, ctx_name, source, text))
                    continue
                if text.count("?") > source.count("?"):
                    suspicious.append((ts_file.name, ctx_name, source, text))
    assert not suspicious


def test_zh_cn_targeted_translations_are_finished():
    _assert_required_translations_finished("signmaker_zh_CN.ts", ZH_CN_REQUIRED)


def test_secondary_locale_targeted_translations_are_finished():
    for ts_file in TRANSLATIONS_DIR.glob("signmaker_*.ts"):
        if ts_file.name == "signmaker_zh_CN.ts":
            continue
        _assert_required_translations_finished(ts_file.name, ZH_CN_REQUIRED)


def test_secondary_locale_printable_area_translations_are_localized():
    for ts_file in TRANSLATIONS_DIR.glob("signmaker_*.ts"):
        if ts_file.name in {"signmaker_zh_CN.ts", "signmaker_en_US.ts"}:
            continue

        messages = _collect_messages(ts_file.name, SECONDARY_LOCALE_MUST_DIFFER_FROM_SOURCE)
        for ctx_name, sources in SECONDARY_LOCALE_MUST_DIFFER_FROM_SOURCE.items():
            for source in sources:
                translation = messages.get((ctx_name, source))
                assert translation is not None
                text = "".join(translation.itertext()).strip()
                assert text
                assert text != source
