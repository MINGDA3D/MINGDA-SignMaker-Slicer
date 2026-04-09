#!/usr/bin/env python3
"""
MINGDA SignMaker - PyInstaller打包脚本

运行方式：
    python build_exe.py
"""

import subprocess
import sys
from pathlib import Path

from tools.build_softkey_bridge import collect_code_dog_artifacts


def build():
    """构建exe文件"""
    project_root = Path(__file__).parent
    code_dog_artifacts = collect_code_dog_artifacts(project_root)

    # PyInstaller参数
    args = [
        sys.executable, "-m", "PyInstaller",
        "--name=MINGDA SignMaker",
        "--windowed",  # 无控制台窗口
        "--onefile",   # 单文件模式
        f"--icon={project_root / 'resources' / 'logos' / 'MINGDA_logo.ico'}",
        # 添加资源文件
        f"--add-data={project_root / 'resources'};resources",
        f"--add-data={project_root / 'VERSION'};.",
        # 隐藏导入
        "--hidden-import=PySide6.QtSvg",
        "--hidden-import=PySide6.QtOpenGL",
        "--hidden-import=PySide6.QtOpenGLWidgets",
        "--hidden-import=ezdxf",
        "--hidden-import=pyclipper",
        "--hidden-import=svgpathtools",
        "--hidden-import=numpy",
        "--hidden-import=OpenGL",
        "--hidden-import=OpenGL.GL",
        "--hidden-import=OpenGL.GLU",
        "--hidden-import=shapely",
        "--hidden-import=trimesh",
        "--hidden-import=mapbox_earcut",
        # 输出目录
        f"--distpath={project_root / 'dist'}",
        f"--workpath={project_root / 'build'}",
        f"--specpath={project_root}",
        # 清理之前的构建
        "--clean",
        # 确认覆盖
        "-y",
        # 入口文件
        str(project_root / "main.py"),
    ]

    if code_dog_artifacts.bridge_dll is not None:
        args.append(f"--add-binary={code_dog_artifacts.bridge_dll};native")
    if code_dog_artifacts.marker_file is not None:
        args.append(f"--add-data={code_dog_artifacts.marker_file};runtime")

    print("Building MINGDA SignMaker...")
    print(f"Command: {' '.join(args[2:])}")
    print()

    result = subprocess.run(args, cwd=project_root)

    if result.returncode == 0:
        exe_path = project_root / "dist" / "MINGDA SignMaker.exe"
        print()
        print("=" * 50)
        print("Build successful!")
        print(f"Output: {exe_path}")
        print("=" * 50)
    else:
        print("Build failed!")
        sys.exit(1)

if __name__ == "__main__":
    build()
