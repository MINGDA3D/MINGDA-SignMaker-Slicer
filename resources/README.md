# 资源目录

此目录包含应用程序所需的资源文件。

## 子目录

- `icons/` - 工具栏和UI图标
- `logos/` - 品牌Logo和示例图片
- `fonts/` - 字体文件
- `images/` - 其他图片资源

## Qt 资源系统

本项目使用 Qt 资源系统 (QRC) 来管理资源文件。

### 资源文件
- `resources.qrc` - 资源描述文件 (XML格式)
- `rc_resources.py` - 编译后的 Python 资源模块

### 重新编译资源

当添加或修改资源文件后，需要重新编译：

```bash
cd resources
pyside6-rcc resources.qrc -o rc_resources.py
```

### 在代码中使用资源

```python
# 1. 导入资源模块
from resources import rc_resources  # noqa: F401

# 2. 使用 :/ 前缀访问资源
from PySide6.QtGui import QIcon
icon = QIcon(":/icons/icons/check.svg")
logo = QIcon(":/logos/logos/MINGDA_logo.png")
```
