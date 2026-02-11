# -*- mode: python ; coding: utf-8 -*-
"""
MINGDA SignMaker - PyInstaller打包配置

使用方法：
    pyinstaller build.spec
"""

import sys
from pathlib import Path

block_cipher = None

# 项目根目录
PROJECT_ROOT = Path('.').absolute()

# Collect data files
datas = [
    # Qt resources
    ('resources', 'resources'),
    # Translations
    ('translations/*.qm', 'translations'),
]

# Resources already added above, no need for additional logo path

# 收集所有隐藏导入
hiddenimports = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtOpenGL',
    'PySide6.QtOpenGLWidgets',
    'OpenGL.GL',
    'OpenGL.GLU',
    'OpenGL.GLUT',
    'ezdxf',
    'svgpathtools',
    'pyclipper',
    'numpy',
    'stl',
    'trimesh',
    'shapely',
    'mapbox_earcut',
    'PIL',
    'resources.rc_resources',
]

# 分析主程序
a = Analysis(
    ['main.py'],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'pandas',
        'IPython',
        'jupyter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 打包资源
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 生成可执行文件
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SignMaker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/logos/MINGDA_logo.ico',  # 应用图标 (使用.ico格式)
)

# 收集所有文件
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SignMaker',
)
