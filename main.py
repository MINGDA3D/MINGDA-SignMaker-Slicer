#!/usr/bin/env python3
"""
SignMaker Slicer - 发光字3D打印切片软件

主程序入口
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.ui.main_window import main

if __name__ == "__main__":
    main()
