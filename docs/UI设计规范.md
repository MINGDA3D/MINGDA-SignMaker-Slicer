# SignMaker Slicer UI 设计规范

> **设计风格：现代深蓝科技 (Modern Dark Blue Tech)**
> 基于 UI/UX Pro Max 设计智能分析
> 创建日期：2026-01-06
> 更新日期：2026-01-07

---

## 一、设计理念

### 1.1 设计原则

| 原则 | 说明 |
|------|------|
| **功能优先** | 界面服务于功能，减少装饰性元素 |
| **数据密集** | 最大化信息展示，合理利用屏幕空间 |
| **专业感** | 工业软件风格，深色主题，精确控制 |
| **高效操作** | 减少点击层级，常用功能一键触达 |
| **视觉层次** | 清晰的信息层级，重点突出 |

### 1.2 目标用户

- 广告字制作从业者
- 3D打印操作人员
- 需要长时间使用软件的专业用户

---

## 二、色彩系统

### 2.1 深蓝科技主题（主要）

```
┌─────────────────────────────────────────────────────────────────┐
│  SignMaker Slicer 深蓝科技主题色板                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  背景层级 (深蓝渐变)                                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ #0A0E14 │ │ #0D1219 │ │ #131A24 │ │ #1A2332 │ │ #1F2A3C │   │
│  │ 基础背景 │ │ 主背景  │ │ 次背景  │ │ 卡片背景 │ │ 高亮背景 │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘   │
│                                                                 │
│  文字层级                                                        │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐                           │
│  │ #E6EDF3 │ │ #9CA3AF │ │ #6B7280 │                           │
│  │ 主文字  │ │ 次文字  │ │ 禁用文字 │                           │
│  └─────────┘ └─────────┘ └─────────┘                           │
│                                                                 │
│  强调色 (品牌渐变: 蓝 → 青)                                      │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ #3B82F6 │ │ #06B6D4 │ │ #10B981 │ │ #F59E0B │ │ #EF4444 │   │
│  │ 主强调  │ │ 次强调  │ │ 成功    │ │ 警告    │ │ 错误    │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘   │
│                                                                 │
│  边框 & 分隔                                                    │
│  ┌─────────┐ ┌─────────┐                                       │
│  │ #334155 │ │ #3B82F6 │                                       │
│  │ 默认边框 │ │ 焦点边框 │                                       │
│  └─────────┘ └─────────┘                                       │
│                                                                 │
│  挤出机颜色                                                      │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐                           │
│  │ #3B82F6 │ │ #EC4899 │ │ #F59E0B │                           │
│  │ 1号蓝色 │ │ 2号粉色 │ │ 3号橙色 │                           │
│  └─────────┘ └─────────┘ └─────────┘                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 颜色变量定义

```python
# PySide6 颜色定义 (深蓝科技主题)
COLORS = {
    # 背景层级
    "bg_base": "#0A0E14",           # 基础背景
    "bg_primary": "#0D1219",        # 主背景
    "bg_secondary": "#131A24",      # 次背景（侧边栏）
    "bg_card": "#1A2332",           # 卡片背景
    "bg_elevated": "#1F2A3C",       # 高亮背景
    "bg_hover": "#253345",          # 悬浮背景

    # 文字
    "text_primary": "#E6EDF3",      # 主文字
    "text_secondary": "#9CA3AF",    # 次文字
    "text_muted": "#6B7280",        # 禁用/提示文字

    # 强调色 (品牌渐变)
    "accent_primary": "#3B82F6",    # 主强调（蓝色）
    "accent_secondary": "#06B6D4",  # 次强调（青色）
    "success": "#10B981",           # 成功（绿色）
    "warning": "#F59E0B",           # 警告（橙色）
    "error": "#EF4444",             # 错误（红色）

    # 边框
    "border_default": "#334155",    # 默认边框
    "border_focus": "#3B82F6",      # 焦点边框

    # 挤出机颜色（预览用）
    "extruder_1": "#3B82F6",        # 挤出机1（蓝色）
    "extruder_2": "#EC4899",        # 挤出机2（粉色）
    "extruder_3": "#F59E0B",        # 挤出机3（橙色）

    # 路径颜色
    "path_shell": "#3B82F6",        # 字壳路径
    "path_fill": "#10B981",         # 填充路径
    "path_travel": "#6B7280",       # 空走路径
    "path_skirt": "#F59E0B",        # 裙边路径
}
```

### 2.3 语义化颜色应用

| 场景 | 颜色 | 用途 |
|------|------|------|
| 选中状态 | `#58A6FF` | 选中的图形、激活的标签页 |
| 路径预览-字壳 | `#58A6FF` | 字壳打印路径 |
| 路径预览-填充 | `#3FB950` | 填充打印路径 |
| 路径预览-空走 | `#8B949E` | 空走移动路径 |
| 错误提示 | `#F85149` | 参数错误、文件错误 |
| 警告提示 | `#F59E0B` | 参数警告、注意事项 |
| 成功提示 | `#3FB950` | 操作成功、计算完成 |

---

## 三、字体系统

### 3.1 字体选择

```python
# 字体定义
FONTS = {
    "family_primary": "Microsoft YaHei UI",  # 主字体（中文）
    "family_mono": "Consolas",               # 等宽字体（数值）
    "family_fallback": "Segoe UI, Arial",    # 后备字体

    # 字号
    "size_h1": 18,      # 大标题
    "size_h2": 14,      # 面板标题
    "size_h3": 12,      # 分组标题
    "size_body": 11,    # 正文
    "size_small": 10,   # 小字/提示
    "size_mono": 11,    # 等宽数值

    # 字重
    "weight_bold": 600,
    "weight_normal": 400,
    "weight_light": 300,
}
```

### 3.2 字体应用场景

| 场景 | 字体 | 字号 | 字重 |
|------|------|------|------|
| 窗口标题 | Microsoft YaHei UI | 18px | 600 |
| 面板标题 | Microsoft YaHei UI | 14px | 600 |
| 分组标题 | Microsoft YaHei UI | 12px | 600 |
| 标签文本 | Microsoft YaHei UI | 11px | 400 |
| 数值输入 | Consolas | 11px | 400 |
| 提示文本 | Microsoft YaHei UI | 10px | 400 |
| 状态栏 | Microsoft YaHei UI | 10px | 400 |

---

## 四、布局系统

### 4.1 主窗口布局

```
┌─────────────────────────────────────────────────────────────────────┐
│  菜单栏 (Menu Bar)                                         ─ □ ✕   │
├─────────────────────────────────────────────────────────────────────┤
│  工具栏 (Toolbar)                                                    │
│  [打开] [保存] [导入] [导出] │ [结合] [打散] [旋转] [镜像] │ [预览] │
├────────────────┬────────────────────────────────────┬───────────────┤
│                │                                    │               │
│   项目面板      │                                    │   参数面板     │
│   (Project)    │                                    │   (Params)    │
│                │                                    │               │
│   ┌──────────┐ │          2D 画布预览               │  ┌──────────┐ │
│   │ 文件列表  │ │          (Canvas)                 │  │ 字壳工艺  │ │
│   │          │ │                                    │  │ 换色层数  │ │
│   │          │ │      ┌─────────────────┐          │  │ 台阶V槽   │ │
│   │          │ │      │                 │          │  │ 防翘裙边  │ │
│   │          │ │      │    字          │          │  │ 连襟字    │ │
│   │          │ │      │                 │          │  │ 包边勾边  │ │
│   │          │ │      └─────────────────┘          │  │ 面板打印  │ │
│   │          │ │                                    │  │ 生成底板  │ │
│   └──────────┘ │                                    │  └──────────┘ │
│                │                                    │               │
│   宽度: 200px  │          自适应宽度                 │   宽度: 320px │
│                │                                    │               │
├────────────────┴────────────────────────────────────┴───────────────┤
│  状态栏 (Status Bar)                          打印时间: -- | 耗材: -- │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 尺寸规范

```python
# 布局尺寸
LAYOUT = {
    # 窗口
    "window_min_width": 1280,
    "window_min_height": 720,

    # 面板
    "sidebar_left_width": 200,      # 左侧项目面板
    "sidebar_right_width": 320,     # 右侧参数面板
    "toolbar_height": 40,           # 工具栏高度
    "statusbar_height": 24,         # 状态栏高度
    "menubar_height": 28,           # 菜单栏高度

    # 间距
    "spacing_xs": 4,
    "spacing_sm": 8,
    "spacing_md": 12,
    "spacing_lg": 16,
    "spacing_xl": 24,

    # 圆角
    "radius_sm": 4,
    "radius_md": 6,
    "radius_lg": 8,

    # 边框
    "border_width": 1,
}
```

### 4.3 参数面板布局

```
┌─────────────────────────────────────┐
│  [字壳工艺] [换色] [台阶] [裙边] ... │  ← 标签页
├─────────────────────────────────────┤
│                                     │
│  ┌─ 基本设置 ─────────────────────┐ │
│  │                               │ │
│  │  字边类型   [直边 ▼]          │ │
│  │                               │ │
│  │  字壳高度   [    30    ] mm   │ │
│  │                               │ │
│  │  层高       [   0.3    ] mm   │ │
│  │                               │ │
│  └───────────────────────────────┘ │
│                                     │
│  ┌─ 壁厚设置 ─────────────────────┐ │
│  │                               │ │
│  │  壁厚       [   1.2    ] mm   │ │
│  │                               │ │
│  │  走线次数   [    1     ]      │ │
│  │                               │ │
│  │  走线偏移   [   0.8    ] mm   │ │
│  │                               │ │
│  └───────────────────────────────┘ │
│                                     │
│  ┌─ 斜边设置 ─────────────────────┐ │
│  │                               │ │
│  │  斜边宽度   [    5     ] mm   │ │
│  │                               │ │
│  │  底板厚度   [   10     ] mm   │ │
│  │                               │ │
│  └───────────────────────────────┘ │
│                                     │
├─────────────────────────────────────┤
│  [计算路径]  [预览]  [文件输出]     │  ← 操作按钮
└─────────────────────────────────────┘
```

---

## 五、组件规范

### 5.1 按钮 (Button)

```python
# 按钮样式
BUTTON_STYLES = {
    "primary": {
        "bg": "#58A6FF",
        "bg_hover": "#79B8FF",
        "bg_pressed": "#388BFD",
        "text": "#FFFFFF",
        "border": "none",
    },
    "secondary": {
        "bg": "#21262D",
        "bg_hover": "#30363D",
        "bg_pressed": "#161B22",
        "text": "#C9D1D9",
        "border": "#30363D",
    },
    "danger": {
        "bg": "#F85149",
        "bg_hover": "#FF6B6B",
        "bg_pressed": "#DA3633",
        "text": "#FFFFFF",
        "border": "none",
    },
    "ghost": {
        "bg": "transparent",
        "bg_hover": "#30363D",
        "bg_pressed": "#21262D",
        "text": "#C9D1D9",
        "border": "none",
    },
}
```

**按钮尺寸：**

| 类型 | 高度 | 内边距 | 字号 |
|------|------|--------|------|
| 大按钮 | 36px | 16px 24px | 13px |
| 默认按钮 | 28px | 8px 16px | 11px |
| 小按钮 | 24px | 4px 12px | 10px |
| 图标按钮 | 28px | 6px | - |

### 5.2 输入框 (Input)

```
┌─────────────────────────────────────┐
│  标签文本                            │
│  ┌─────────────────────┬─────────┐ │
│  │      数值输入        │   单位  │ │
│  └─────────────────────┴─────────┘ │
│  提示文本（可选）                    │
└─────────────────────────────────────┘

默认状态:   边框 #30363D, 背景 #0D1117
悬浮状态:   边框 #484F58, 背景 #0D1117
焦点状态:   边框 #58A6FF, 背景 #0D1117
错误状态:   边框 #F85149, 背景 #0D1117
禁用状态:   边框 #21262D, 背景 #161B22, 文字 #8B949E
```

### 5.3 下拉框 (ComboBox)

```
┌─────────────────────────────────────┐
│  直边                          ▼   │
└─────────────────────────────────────┘
         ↓ 点击展开
┌─────────────────────────────────────┐
│  直边                          ✓   │
├─────────────────────────────────────┤
│  斜边                               │
├─────────────────────────────────────┤
│  异形边                             │
└─────────────────────────────────────┘
```

### 5.4 标签页 (TabWidget)

```
┌──────────┬──────────┬──────────┬──────────┐
│  字壳工艺 │  换色层  │  台阶V槽  │  防翘裙边 │
├──────────┴──────────┴──────────┴──────────┤
│                                           │
│              标签页内容                     │
│                                           │
└───────────────────────────────────────────┘

激活标签:   背景 #21262D, 文字 #F0F6FC, 底部边框 #58A6FF
非激活:     背景 transparent, 文字 #8B949E
悬浮:       背景 #30363D, 文字 #C9D1D9
```

### 5.5 分组框 (GroupBox)

```
┌─ 基本设置 ────────────────────────────┐
│                                       │
│   内容区域                             │
│                                       │
└───────────────────────────────────────┘

标题:      字号 12px, 字重 600, 颜色 #C9D1D9
边框:      颜色 #30363D, 圆角 6px
内边距:    12px
```

### 5.6 滑块 (Slider)

```
      最小值                      最大值
        ├────────────●────────────┤
                     ↑
                  当前值: 50

轨道:      高度 4px, 背景 #30363D, 圆角 2px
已填充:    背景 #58A6FF
滑块:      直径 14px, 背景 #F0F6FC, 边框 #58A6FF
```

### 5.7 复选框 (CheckBox)

```
☐ 未选中    边框 #30363D, 背景 transparent
☑ 选中      边框 #58A6FF, 背景 #58A6FF, 勾 #FFFFFF
◻ 禁用未选  边框 #21262D, 背景 #161B22
```

### 5.8 工具栏按钮 (ToolButton)

```
┌─────────────────────────────────────────────────────┐
│  [📂] [💾] [📥] [📤] │ [🔗] [💥] [🔄] [↔️] │ [👁️]  │
└─────────────────────────────────────────────────────┘

图标大小:   20x20 px
按钮大小:   32x32 px
间距:       4px
分隔线:     宽度 1px, 颜色 #30363D, 边距 8px
```

---

## 六、图标规范

### 6.1 图标来源

推荐使用以下图标库：
- **Feather Icons**: 简洁线性图标
- **Lucide Icons**: Feather 的社区版本
- **Material Icons**: Google Material Design

### 6.2 图标尺寸

| 场景 | 尺寸 | 线宽 |
|------|------|------|
| 工具栏 | 20x20 px | 1.5px |
| 菜单项 | 16x16 px | 1.5px |
| 按钮内 | 16x16 px | 1.5px |
| 状态图标 | 14x14 px | 1.5px |

### 6.3 常用图标映射

| 功能 | 图标名 | 描述 |
|------|--------|------|
| 打开 | folder-open | 打开文件 |
| 保存 | save | 保存文件 |
| 导入 | download | 导入DXF |
| 导出 | upload | 导出文件 |
| 结合 | link | 结合图形 |
| 打散 | unlink | 打散图形 |
| 旋转 | rotate-cw | 旋转 |
| 镜像 | flip-horizontal | 水平镜像 |
| 预览 | eye | 3D预览 |
| 计算 | cpu | 计算路径 |
| 设置 | settings | 设置 |
| 放大 | zoom-in | 放大视图 |
| 缩小 | zoom-out | 缩小视图 |
| 适应 | maximize | 适应窗口 |

---

## 七、交互规范

### 7.1 鼠标交互

| 操作 | 画布行为 |
|------|----------|
| 左键单击 | 选中图形 |
| 左键拖拽 | 框选/移动图形 |
| 右键单击 | 上下文菜单 |
| 滚轮 | 缩放视图 |
| 中键拖拽 | 平移视图 |
| Ctrl+左键 | 多选 |

### 7.2 键盘快捷键

| 快捷键 | 功能 |
|--------|------|
| Ctrl+O | 打开文件 |
| Ctrl+S | 保存文件 |
| Ctrl+I | 导入DXF |
| Ctrl+E | 导出 |
| Ctrl+Z | 撤销 |
| Ctrl+Y | 重做 |
| Ctrl+A | 全选 |
| Delete | 删除选中 |
| Ctrl+G | 结合 |
| Ctrl+U | 打散 |
| R | 旋转 |
| M | 镜像 |
| F | 适应窗口 |
| Space | 切换预览 |

### 7.3 状态反馈

| 状态 | 反馈方式 |
|------|----------|
| 加载中 | 进度条 + 状态栏文字 |
| 计算中 | 进度对话框 + 百分比 |
| 成功 | 状态栏绿色提示 (3秒消失) |
| 警告 | 状态栏橙色提示 + 图标 |
| 错误 | 弹窗 + 状态栏红色提示 |

---

## 八、动画规范

### 8.1 过渡时间

| 类型 | 时长 | 缓动函数 |
|------|------|----------|
| 悬浮变化 | 150ms | ease-out |
| 展开/收起 | 200ms | ease-in-out |
| 页面切换 | 250ms | ease-in-out |
| 进度动画 | 300ms | linear |

### 8.2 PySide6 动画示例

```python
from PySide6.QtCore import QPropertyAnimation, QEasingCurve

# 悬浮动画
animation = QPropertyAnimation(widget, b"opacity")
animation.setDuration(150)
animation.setEasingCurve(QEasingCurve.OutCubic)
animation.setStartValue(0.8)
animation.setEndValue(1.0)
animation.start()
```

---

## 九、响应式设计

### 9.1 窗口尺寸断点

| 断点 | 宽度 | 布局调整 |
|------|------|----------|
| 紧凑 | < 1280px | 隐藏左侧面板，标签页变图标 |
| 标准 | 1280-1600px | 标准三栏布局 |
| 宽屏 | > 1600px | 增加画布区域，面板可调宽 |

### 9.2 面板可调节

```
用户可拖拽调整：
- 左侧面板宽度: 150px - 300px
- 右侧面板宽度: 280px - 450px
- 面板可折叠/展开
```

---

## 十、无障碍设计

### 10.1 颜色对比度

所有文字与背景的对比度符合 WCAG AA 标准（最小 4.5:1）

| 文字颜色 | 背景颜色 | 对比度 |
|----------|----------|--------|
| #F0F6FC | #0D1117 | 15.8:1 |
| #C9D1D9 | #0D1117 | 11.3:1 |
| #8B949E | #0D1117 | 5.9:1 |

### 10.2 焦点指示

所有可交互元素在获得焦点时显示明显的焦点环：
```css
outline: 2px solid #58A6FF;
outline-offset: 2px;
```

### 10.3 文字提示

- 所有图标按钮都有 tooltip
- 所有输入框都有标签
- 错误信息明确可读

---

## 十一、PySide6 样式表模板

```python
STYLESHEET = """
/* 全局样式 */
QWidget {
    background-color: #0D1117;
    color: #F0F6FC;
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 11px;
}

/* 主窗口 */
QMainWindow {
    background-color: #0D1117;
}

/* 菜单栏 */
QMenuBar {
    background-color: #161B22;
    border-bottom: 1px solid #30363D;
    padding: 4px;
}

QMenuBar::item {
    padding: 4px 12px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #30363D;
}

/* 工具栏 */
QToolBar {
    background-color: #161B22;
    border-bottom: 1px solid #30363D;
    padding: 4px;
    spacing: 4px;
}

QToolButton {
    background-color: transparent;
    border: none;
    border-radius: 4px;
    padding: 6px;
}

QToolButton:hover {
    background-color: #30363D;
}

QToolButton:pressed {
    background-color: #21262D;
}

/* 按钮 */
QPushButton {
    background-color: #21262D;
    border: 1px solid #30363D;
    border-radius: 6px;
    padding: 8px 16px;
    color: #C9D1D9;
}

QPushButton:hover {
    background-color: #30363D;
    border-color: #484F58;
}

QPushButton:pressed {
    background-color: #161B22;
}

QPushButton:disabled {
    background-color: #161B22;
    color: #8B949E;
    border-color: #21262D;
}

QPushButton#primary {
    background-color: #58A6FF;
    border: none;
    color: #FFFFFF;
}

QPushButton#primary:hover {
    background-color: #79B8FF;
}

/* 输入框 */
QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #0D1117;
    border: 1px solid #30363D;
    border-radius: 6px;
    padding: 6px 10px;
    color: #F0F6FC;
    selection-background-color: #58A6FF;
}

QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {
    border-color: #484F58;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #58A6FF;
}

/* 下拉框 */
QComboBox {
    background-color: #21262D;
    border: 1px solid #30363D;
    border-radius: 6px;
    padding: 6px 10px;
    color: #F0F6FC;
}

QComboBox:hover {
    border-color: #484F58;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox::down-arrow {
    image: url(icons/chevron-down.svg);
    width: 12px;
    height: 12px;
}

QComboBox QAbstractItemView {
    background-color: #21262D;
    border: 1px solid #30363D;
    border-radius: 6px;
    selection-background-color: #30363D;
}

/* 标签页 */
QTabWidget::pane {
    background-color: #21262D;
    border: 1px solid #30363D;
    border-radius: 6px;
    border-top-left-radius: 0;
}

QTabBar::tab {
    background-color: transparent;
    border: none;
    padding: 8px 16px;
    color: #8B949E;
}

QTabBar::tab:selected {
    background-color: #21262D;
    color: #F0F6FC;
    border-bottom: 2px solid #58A6FF;
}

QTabBar::tab:hover:!selected {
    background-color: #30363D;
    color: #C9D1D9;
}

/* 分组框 */
QGroupBox {
    background-color: #161B22;
    border: 1px solid #30363D;
    border-radius: 6px;
    margin-top: 12px;
    padding: 12px;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #C9D1D9;
}

/* 滚动条 */
QScrollBar:vertical {
    background-color: #0D1117;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background-color: #30363D;
    border-radius: 6px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #484F58;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* 状态栏 */
QStatusBar {
    background-color: #161B22;
    border-top: 1px solid #30363D;
    color: #8B949E;
}

/* 复选框 */
QCheckBox {
    spacing: 8px;
    color: #C9D1D9;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #30363D;
    border-radius: 4px;
    background-color: transparent;
}

QCheckBox::indicator:hover {
    border-color: #484F58;
}

QCheckBox::indicator:checked {
    background-color: #58A6FF;
    border-color: #58A6FF;
    image: url(icons/check.svg);
}

/* 滑块 */
QSlider::groove:horizontal {
    height: 4px;
    background-color: #30363D;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    width: 14px;
    height: 14px;
    margin: -5px 0;
    background-color: #F0F6FC;
    border: 2px solid #58A6FF;
    border-radius: 7px;
}

QSlider::handle:horizontal:hover {
    background-color: #FFFFFF;
}

QSlider::sub-page:horizontal {
    background-color: #58A6FF;
    border-radius: 2px;
}

/* 进度条 */
QProgressBar {
    background-color: #30363D;
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #58A6FF;
    border-radius: 4px;
}

/* 分割线 */
QSplitter::handle {
    background-color: #30363D;
}

QSplitter::handle:horizontal {
    width: 1px;
}

QSplitter::handle:vertical {
    height: 1px;
}

/* 工具提示 */
QToolTip {
    background-color: #21262D;
    border: 1px solid #30363D;
    border-radius: 4px;
    padding: 6px 10px;
    color: #F0F6FC;
}
"""
```

---

## 十二、设计资产清单

### 12.1 需要的图标 (SVG)

| 文件名 | 用途 |
|--------|------|
| folder-open.svg | 打开文件 |
| save.svg | 保存 |
| download.svg | 导入 |
| upload.svg | 导出 |
| link.svg | 结合 |
| unlink.svg | 打散 |
| rotate-cw.svg | 旋转 |
| flip-horizontal.svg | 镜像 |
| eye.svg | 预览 |
| cpu.svg | 计算 |
| settings.svg | 设置 |
| zoom-in.svg | 放大 |
| zoom-out.svg | 缩小 |
| maximize.svg | 适应 |
| chevron-down.svg | 下拉箭头 |
| check.svg | 勾选 |
| x.svg | 关闭 |
| minus.svg | 最小化 |
| square.svg | 最大化 |
| alert-circle.svg | 警告 |
| info.svg | 信息 |
| check-circle.svg | 成功 |
| x-circle.svg | 错误 |

### 12.2 应用图标

| 尺寸 | 用途 |
|------|------|
| 16x16 | 任务栏小图标 |
| 32x32 | 任务栏图标 |
| 48x48 | 应用列表 |
| 64x64 | 桌面图标 |
| 128x128 | 高DPI桌面 |
| 256x256 | 安装程序/关于 |

---

## 十三、UI 效果图索引

### 13.1 主界面效果图

| 文件名 | 描述 | 尺寸 |
|--------|------|------|
| `UI_Modern.png` | 项目模式 - 2D视图 (主界面) | 1600×1000 |
| `UI_Modern_3D.png` | 项目模式 - 3D视图 | 1600×1000 |
| `UI_Slice_Mode.png` | 切片模式 - 路径预览 | 1600×1000 |
| `UI_Preview_Mode.png` | 预览模式 - 3D打印模拟 | 1600×1000 |

### 13.2 参数面板效果图

| 文件名 | 描述 | 尺寸 |
|--------|------|------|
| `UI_Params_Complete.png` | 完整参数面板 (13个分组) | 480×4200 |
| `UI_Params_Full.png` | 参数面板详细版 | 450×2800 |
| `UI_Params_Expanded.png` | 参数面板展开视图 | 420×1800 |

### 13.3 设计特征

**品牌渐变按钮**
```
主按钮使用蓝→青渐变: #3B82F6 → #06B6D4
├── 用于"生成 G-Code"等主要操作
└── 圆角 10px，高度 44px
```

**可折叠参数分组**
```
▼ 字壳工艺        (展开状态)
▶ 换色层设置      (折叠状态)
▶ 台阶/V槽        (折叠状态)
...
```

**三栏布局**
```
┌──────────┬────────────────────────────┬────────────┐
│ 左侧边栏  │          画布区域          │  参数面板   │
│  220px   │          自适应            │   360px    │
│          │                            │            │
│ • 图形列表 │  • 2D/3D 切换              │ • 快速参数  │
│ • 文件操作 │  • 编辑工具栏              │ • 参数分组  │
│          │  • 网格背景                 │ • 操作按钮  │
└──────────┴────────────────────────────┴────────────┘
```

---

*文档创建日期：2026-01-06*
*更新日期：2026-01-07*
*基于 UI/UX Pro Max 设计智能分析*
