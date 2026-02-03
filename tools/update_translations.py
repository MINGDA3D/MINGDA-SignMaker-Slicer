#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Translation file management tool

Used to generate, update and compile translation files.

Usage:
    # Extract strings from source code and update .ts files
    python tools/update_translations.py extract

    # Compile .ts files to .qm files
    python tools/update_translations.py compile

    # Open Qt Linguist to edit translations
    python tools/update_translations.py edit en_US
"""

import subprocess
import sys
from pathlib import Path

# Try to find PySide6 tools path
try:
    import PySide6
    PYSIDE6_PATH = Path(PySide6.__path__[0])
except ImportError:
    PYSIDE6_PATH = None

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent
TRANSLATIONS_DIR = PROJECT_ROOT / "translations"
SRC_DIR = PROJECT_ROOT / "src"

# Supported languages
LANGUAGES = [
    "zh_CN",    # Chinese (source language)
    "en_US",    # English
    "ru_RU",    # Russian
    "uk_UA",    # Ukrainian
    "de_DE",    # German
    "fr_FR",    # French
    "es_ES",    # Spanish
    "pt_BR",    # Portuguese
    "it_IT",    # Italian
    "he_IL",    # Hebrew
    "ar_SA",    # Arabic
    "ja_JP",    # Japanese
    "ko_KR",    # Korean
    "tr_TR",    # Turkish
]


def get_tool_path(tool_name: str) -> str:
    """Get the full path for a PySide6 tool"""
    if PYSIDE6_PATH:
        tool_path = PYSIDE6_PATH / f"{tool_name}.exe"
        if tool_path.exists():
            return str(tool_path)
        tool_path = PYSIDE6_PATH / tool_name
        if tool_path.exists():
            return str(tool_path)
    # Fallback to system path
    return tool_name


def find_python_files() -> list:
    """Find all Python files that need translation"""
    files = []
    for pattern in ["**/*.py"]:
        files.extend(SRC_DIR.glob(pattern))
    return [str(f) for f in files]


def extract_strings():
    """Extract translatable strings from source code and update .ts files"""
    print("=" * 60)
    print("Extracting translatable strings")
    print("=" * 60)

    # Ensure translations directory exists
    TRANSLATIONS_DIR.mkdir(exist_ok=True)

    # Find all Python files
    py_files = find_python_files()
    print(f"Found {len(py_files)} Python files")

    for lang in LANGUAGES:
        ts_file = TRANSLATIONS_DIR / f"signmaker_{lang}.ts"
        print(f"\nUpdating: {ts_file.name}")

        cmd = [
            get_tool_path("lupdate"),
            *py_files,
            "-ts", str(ts_file)
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"  [OK] Success")
            else:
                print(f"  [FAIL] Error: {result.stderr}")
        except FileNotFoundError:
            print("  [FAIL] Error: pyside6-lupdate not found")
            print("  Please ensure PySide6 is installed: pip install PySide6")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("Done! Please use Qt Linguist to edit translation files")
    print("Run: python tools/update_translations.py edit <language_code>")
    print("=" * 60)


def compile_translations():
    """Compile .ts files to .qm files"""
    print("=" * 60)
    print("Compiling translation files")
    print("=" * 60)

    for lang in LANGUAGES:
        ts_file = TRANSLATIONS_DIR / f"signmaker_{lang}.ts"
        qm_file = TRANSLATIONS_DIR / f"signmaker_{lang}.qm"

        if not ts_file.exists():
            print(f"\nSkipping: {ts_file.name} (file does not exist)")
            continue

        print(f"\nCompiling: {ts_file.name} -> {qm_file.name}")

        cmd = [get_tool_path("lrelease"), str(ts_file), "-qm", str(qm_file)]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"  [OK] Success")
            else:
                print(f"  [FAIL] Error: {result.stderr}")
        except FileNotFoundError:
            print("  [FAIL] Error: pyside6-lrelease not found")
            print("  Please ensure PySide6 is installed: pip install PySide6")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


def edit_translation(lang: str):
    """Open Qt Linguist to edit the specified language translation"""
    ts_file = TRANSLATIONS_DIR / f"signmaker_{lang}.ts"

    if not ts_file.exists():
        print(f"Error: Translation file does not exist: {ts_file}")
        print("Please run: python tools/update_translations.py extract")
        sys.exit(1)

    print(f"Opening Qt Linguist: {ts_file}")

    try:
        subprocess.Popen([get_tool_path("linguist"), str(ts_file)])
    except FileNotFoundError:
        print("Error: Qt Linguist not found")
        print("Please ensure PySide6 is installed")
        sys.exit(1)


def create_initial_ts_files():
    """Create initial .ts files with basic structure"""
    print("=" * 60)
    print("Creating initial translation files")
    print("=" * 60)

    TRANSLATIONS_DIR.mkdir(exist_ok=True)

    ts_template = '''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="{lang_code}">
</TS>
'''

    for lang_code in LANGUAGES:
        ts_file = TRANSLATIONS_DIR / f"signmaker_{lang_code}.ts"
        if not ts_file.exists():
            content = ts_template.format(lang_code=lang_code.replace("_", "-"))
            ts_file.write_text(content, encoding='utf-8')
            print(f"Created: {ts_file.name}")
        else:
            print(f"Skipped: {ts_file.name} (already exists)")

    print("\n" + "=" * 60)
    print("Done!")
    print("Now run: python tools/update_translations.py extract")
    print("=" * 60)


def print_usage():
    """Print usage help"""
    print("""
Translation File Management Tool

Usage:
    python tools/update_translations.py <command> [args]

Commands:
    init        Create initial .ts files
    extract     Extract strings from source code and update .ts files
    compile     Compile .ts files to .qm files
    edit <lang> Open Qt Linguist to edit the specified language

Examples:
    python tools/update_translations.py init
    python tools/update_translations.py extract
    python tools/update_translations.py compile
    python tools/update_translations.py edit en_US

Supported languages:
    """ + ", ".join(LANGUAGES))


def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "init":
        create_initial_ts_files()
    elif command == "extract":
        extract_strings()
    elif command == "compile":
        compile_translations()
    elif command == "edit":
        if len(sys.argv) < 3:
            print("Error: Please specify language code")
            print("Example: python tools/update_translations.py edit en_US")
            sys.exit(1)
        edit_translation(sys.argv[2])
    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
