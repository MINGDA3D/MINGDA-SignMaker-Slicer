#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MINGDA SignMaker - Build Script

Usage: python build.py
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.absolute()
os.chdir(PROJECT_ROOT)

def print_step(msg):
    print(f"\n>>> {msg}")

def print_ok(msg):
    print(f"[OK] {msg}")

def print_warn(msg):
    print(f"[WARN] {msg}")

def print_err(msg):
    print(f"[ERROR] {msg}")

def check_deps():
    print_step("Checking dependencies...")
    try:
        import PyInstaller
        print_ok(f"PyInstaller: {PyInstaller.__version__}")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        print_ok("PyInstaller installed")

def build_app():
    print_step("Building application...")
    spec_file = PROJECT_ROOT / "build.spec"
    if not spec_file.exists():
        print_err(f"Config not found: {spec_file}")
        return False

    try:
        build_dir = PROJECT_ROOT / "build"
        if build_dir.exists():
            shutil.rmtree(build_dir)

        subprocess.run([sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", str(spec_file)], check=True)
        print_ok("Build complete!")
        return True
    except subprocess.CalledProcessError as e:
        print_err(f"Build failed: {e}")
        return False

def show_results():
    print_step("Results:")
    dist_dir = PROJECT_ROOT / "dist" / "SignMaker"
    if dist_dir.exists():
        exe_file = dist_dir / "SignMaker.exe"
        if exe_file.exists():
            size_mb = exe_file.stat().st_size / (1024 * 1024)
            print_ok(f"Executable: SignMaker.exe ({size_mb:.1f} MB)")
            print(f"\nLocation: {dist_dir}")
            print(f"Run: {exe_file}")
    else:
        print_err("Output not found")

def main():
    print("\n" + "=" * 60)
    print("  MINGDA SignMaker - Build Tool")
    print("=" * 60)

    check_deps()
    if build_app():
        show_results()
        return 0
    return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print_err(f"Error: {e}")
        sys.exit(1)
