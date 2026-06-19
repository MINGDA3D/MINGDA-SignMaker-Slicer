# MINGDA SignMaker 教学视频大纲（当前版本）

本大纲用于录制 MINGDA SignMaker 当前版本的软件教学视频。教学顺序建议遵循一个原则：先让客户看懂完整生产闭环，再拆开讲参数和进阶功能。

核心主线：

`新建/打开项目 -> 导入图形或生成文字 -> 2D 编辑排版 -> 设置 Shape / Machine / Print 参数 -> Process 处理 -> 3D 预览检查 -> 导出 G-code / STL / DXF -> 保存 .smp 项目复用`

当前版本的客户教学重点应放在已开放且对生产有直接价值的功能：`DXF/SVG/SMP 打开`、`文字生成`、`2D 编辑`、`Shape 工艺模式`、`打印机档案`、`Klipper G-code 导出`、`STL 导出`、`底板/面板 DXF 导出`、`3D 预览检查`、`项目保存复用`。面板/底板填充图案等未形成完整主流程的内容，不建议放进主线教学。

## 录制前准备

建议准备 5 组案例，录制时按难度递进：

1. 简单直边案例：一个无内孔的英文或中文单字，用于快速演示完整流程。
2. 带内孔案例：如 A、O、R 或中文带孔字，用于讲内孔、起始点、打印顺序、台阶/V 槽。
3. 斜边案例：用于讲 `Beveled`、`Top Small / Top Large`、`Bevel Width`、`Baseplate Thickness`、`Panel Thickness`。
4. 异形边案例：用于讲 `Custom`、预设边型（包括 U 形字轮廓模板）和导入自定义边型 DXF。
5. 生产导出案例：包含打印机档案、G-code、STL、底板 DXF、面板 DXF 和 `.smp` 保存。

录制环境建议：

- 使用中文界面录制主版本；如面向海外客户，可额外录制一段语言切换。
- 提前准备一个可成功处理和导出的 `.smp` 项目，避免现场导入失败影响节奏。
- 屏幕缩放固定，右侧 `Settings` 面板、上方工具栏、左侧 `Shape List` 都要清晰可见。
- 录制前先运行一次 `Process` 和导出，确认案例参数不会触发越界、不可打印区域或 Prime Tower 校验错误。

## 推荐课程结构

| 章节 | 建议时长 | 目标 |
|---|---:|---|
| 1. 软件定位与完整闭环 | 4-6 分钟 | 让客户先知道软件能做什么、输出什么 |
| 2. 首页、项目页、预览页 | 5-8 分钟 | 建立界面导航和工具位置认知 |
| 3. 文件打开、文字生成与项目保存 | 8-12 分钟 | 掌握图形来源和 `.smp` 复用 |
| 4. 2D 编辑与排版 | 12-18 分钟 | 把设计稿整理成可生产图形 |
| 5. Shape 基础：高度、层高、线宽、壁厚 | 10-15 分钟 | 讲清当前版本的制造化参数逻辑 |
| 6. Wall 边型：直边、斜边、异形边 | 12-18 分钟 | 掌握不同字壳外形的选择方法 |
| 7. Top / Bottom 结构工艺 | 15-22 分钟 | 讲台阶、V 槽、封顶、封底、灯槽、包边 |
| 8. Other：裙边、连襟字、DXF 补偿 | 8-12 分钟 | 讲生产增强功能和板件配合 |
| 9. Machine 与 Print 设置 | 12-18 分钟 | 讲打印机档案、温度、速度、换色、Prime Tower |
| 10. Process 与 3D 预览检查 | 8-12 分钟 | 教客户处理后如何判断结构是否正确 |
| 11. 导出生产文件 | 10-15 分钟 | 区分 G-code、STL、底板 DXF、面板 DXF |
| 12. 常见问题与避坑 | 8-12 分钟 | 降低售后重复问题 |

如果要做短视频版本，可以压缩为 3 段：

1. 5 分钟完整流程：导入、设置、处理、预览、导出。
2. 15 分钟参数重点：Shape、Machine、Print。
3. 10 分钟进阶与避坑：台阶、灯槽、螺丝孔、连襟、DXF 补偿、常见错误。

## 1. 软件定位与完整闭环

本章建议先用一个简单案例跑通全流程，不要一开始解释所有参数。

讲解重点：

- MINGDA SignMaker 是用于 `3D 打印发光字字壳` 的专用软件。
- 图形输入可以来自 `DXF`、`SVG`，也可以直接通过 `Text` 工具生成文字。
- 项目文件使用 `.smp`，可以保存图形、参数和打印机档案快照，适合返单和重复生产。
- 生产输出分 4 类：
  - `G-code`：面向 Klipper 单喷头打印流程，可直接给打印机或上位机使用。
  - `STL`：用于三维模型检查，或交给其他切片软件继续处理。
  - `Baseplate DXF`：用于底板加工。
  - `Panel DXF`：用于面板加工。

建议口播逻辑：

> 这套软件不是通用建模软件，它的核心价值是把发光字轮廓快速变成可打印、可装配的生产文件。客户最需要掌握的是：图形进来以后，怎么设工艺、怎么检查结构、怎么导出生产文件。

## 2. 界面总览

按真实工作顺序介绍界面，不要按控件逐个介绍。

### 首页 Home

- `New Project`：新建空项目。
- `Open File`：打开 DXF、SVG 或 SMP。
- `Recent Projects`：最近项目卡片，支持预览、重新打开、打开所在文件夹、从最近列表移除。

### 项目页 Project

- 中间是 2D 画布，用于选择、排版、编辑图形。
- 左侧是 `Shape List`，按导入资产和轮廓组织图形，支持选中、删除、展开、分解资产。
- 顶部画布工具栏包含移动、旋转、缩放、镜像、布尔、组合、文字、起始点、打印顺序、螺丝孔。
- 右侧是 `Settings`，当前分为 `Shape`、`Machine`、`Print` 三个主页签。

### 预览页 Preview

- 用于查看处理后的 3D 结构。
- 支持鼠标旋转、缩放、平移。
- 显示平台、网格、不可打印区域、字壳实体和不同工艺结构。
- 层滑块显示当前 Z 高度和总高度，用于检查某个高度位置的结构。

### 顶部工具栏

- 打开、保存、导出菜单。
- 撤销、重做。
- `Home / Project / Preview` 导航。
- `Process` 处理按钮。
- 分体导出按钮，可在 `Export G-code` 和 `Export STL` 之间切换，并记住上次选择。

## 3. 新建项目、打开文件与保存项目

### 新建项目

演示路径：

1. 点击 `New Project`。
2. 如果当前项目有未保存修改，说明软件会提示确认，避免误清空。
3. 进入 Project 页面后，画布为空，等待导入或生成图形。

### 打开 DXF / SVG

演示重点：

- 支持常见 DXF 轮廓；当前版本已增强 `INSERT` 图块、`HATCH` 内孔识别、闭合 `LINE` 轮廓等兼容性。
- 导入后图形会进入 `Shape List`，并在 2D 画布显示。
- 多次导入时，软件会尽量自动排布新增图形，减少重叠。

### 打开 SMP 项目

演示重点：

- `.smp` 用于保存项目状态，不只是保存图形。
- 它会保存轮廓、工艺参数、打印机档案快照和项目预览图。
- 打开旧项目后，当前版本会对部分旧参数做兼容和归一化，例如旧的层数型高度参数会转换为当前毫米输入逻辑。

### 保存与另存为

演示重点：

- 保存前必须有图形。
- 保存后首页最近项目会出现预览卡片。
- 返单时建议优先打开 `.smp`，不要重新导入 DXF 后再手动调参数。

## 4. 文字生成

演示路径：

1. 点击画布工具栏 `Text`。
2. 输入文字。
3. 选择字体。
4. 设置 `Font Size (mm)` 和 `Character Spacing (mm)`。
5. 确认后文字会转成轮廓并加入画布。

讲解重点：

- 文字生成后，本质上与 DXF/SVG 导入的轮廓一样，可以移动、缩放、镜像、设置工艺并导出。
- 字距可以为负值，用于让字母或笔画更紧密。
- 字体选择会影响轮廓质量，生产前要在 2D 和 3D 中检查内孔、细笔画和尖角。

## 5. 2D 编辑与排版

本章目标是让客户理解：2D 编辑不是美术排版，而是把设计稿整理成可生产的几何。

### 选择与列表联动

- 在画布选择图形，左侧 `Shape List` 会同步选中。
- 在 `Shape List` 选择条目，画布也会同步。
- 删除可以通过列表删除按钮、键盘 `Delete / Backspace`，也可结合 `Ctrl+A` 全选。

### 移动、旋转、缩放

演示：

- `Move`：调整位置，确保图形在平台范围内。
- `Rotate`：按角度旋转。
- `Scale`：支持百分比缩放，也支持按宽高尺寸缩放。
- 缩放、旋转、移动都纳入撤销/重做。

重点提醒：

- 发光字生产更建议按实际尺寸确认宽高，不要只看视觉比例。
- 缩放后如果参数或轮廓发生变化，需要重新 `Process`。

### 镜像

- `Mirror Horizontal`：水平镜像。
- `Mirror Vertical`：垂直镜像。
- 用于左右方向设计稿转换、背面/正面工艺调整。

### 布尔运算、组合与分解

- `Intersection`：保留相交区域。
- `Difference`：从一个轮廓中减去另一个轮廓。
- `Group / Ungroup`：组织多个轮廓，便于整体操作。
- `Explode Asset`：将一次导入的多轮廓资产拆成独立对象，适合只调整其中某个字或某个部件。

### 起始点与打印顺序

适合作为进阶小节，不建议在第一遍完整流程中讲太深。

- `Start Point`：点击轮廓或内孔角点，控制打印起笔位置，减少接缝出现在显眼位置。
- `Print Order`：按希望的顺序点击外轮廓和内孔，控制打印顺序。
- 这两个设置会随项目保存，并影响 G-code 输出。

### 手动螺丝孔

使用条件：

- 必须启用 `Bottom Face`，因为螺丝孔是底面封闭结构上的开孔。

演示：

- 点击 `Screw Hole`。
- 在有效底面区域内点击添加孔。
- 点击已有孔选中，移动或 `Delete` 删除。
- `Esc` 退出编辑。

重点提醒：

- 先设置 `Screw Hole Diameter`，再布置孔位。
- 孔位要避开字壳壁、内孔边缘和太窄区域。

## 6. Shape 基础参数：高度、层高、线宽、壁厚

这是当前版本最需要讲清楚的一章。

### Shell Settings

必讲参数：

- `Shell Height`：字壳总高度，单位 mm。
- `Layer Height`：层高，同时决定 Z 向参数自动吸附的网格。
- `Line Width`：单道挤出线宽，当前版本会根据层高给出默认值。
- `Wall Thickness`：总壁厚，当前版本按 `Line Width` 的整数倍向上吸附，内部自动换算壁路径数量。

口播重点：

> 当前版本很多高度、厚度、深度都用毫米输入。软件在处理、3D 预览、STL 和 G-code 导出前，会把这些 Z 向尺寸向上吸附到当前层高网格，目的是避免实际打印出来比输入值偏小。

必须提醒：

- `Line Width` 必须适合当前喷嘴和层高，否则 `Process` 和导出会被阻止。
- `Wall Thickness` 不再建议理解成手动输入壁数，而应理解为最终希望得到的实体壁厚。
- 改变 `Layer Height` 后，要注意相关高度参数会按新的层高网格重新取整。

## 7. Wall 边型：直边、斜边、异形边

进入路径：`Settings -> Shape -> Wall`

当前 Wall 模式包含：

- `Straight`
- `Beveled`
- `Custom`

### Straight 直边

适合：

- 常规垂直字壳。
- 客户第一次学习。
- 需要稳定、快速出结果的生产场景。

教学重点：

- 只需要先讲 `Shell Height`、`Line Width`、`Wall Thickness`。
- 用它跑通完整流程。

### Beveled 斜边

必讲参数：

- `Bevel Direction`
  - `Top Small`：上小下大。
  - `Top Large`：上大下小。
- `Bevel Width`：斜边水平变化宽度。
- `Baseplate Thickness`：底部直边区域高度。
- `Panel Thickness`：顶部面板侧直边区域高度。

重点提醒：

- 原始轮廓始终按底面 `z=0` 作为基准。
- 斜边会改变不同高度的外形，所以台阶、底面、顶面等结构要以处理后的 3D 预览为准。

### Custom 异形边

演示：

- 从预设模板中选择异形边；第一个 `U-Shaped Letter` 是 U 形字轮廓模板。
- 导入自定义边型 DXF。
- 切换到 3D 预览检查侧面形态。

提醒：

- 自定义边型适合高阶客户。
- U 形字轮廓不再是独立 Wall 模式，而是 Custom 边的一个 DXF preset。
- 先用内置预设录一遍，再演示导入 DXF，降低理解成本。

## 8. Top 结构：顶面封闭、亚克力面板卡槽、亚克力面板 V 槽

进入路径：`Settings -> Shape -> Top`

当前 Top 使用互斥工艺模式，讲解时要强调“同一位置不要同时开多个冲突结构”。

### Top Face

用途：

- 在字壳顶部生成实心封闭层。
- 适合需要顶部封闭的特殊结构。

参数：

- `Top Face Thickness`：顶面封闭厚度，单位 mm，会按层高自动吸附。

### Acrylic Face Slot / Acrylic Face V-Groove

用途：

- 为亚克力面板或上盖预留卡槽。
- `Acrylic Face V-Groove` 用于形成亚克力面板 V 槽效果。

参数：

- `Face Slot Drop`：从 `Shell Height` 顶面向下到顶部 Acrylic Face Slot / Acrylic Face V-Groove 顶面的距离。
- `Face Slot Width`：顶部亚克力面板卡槽或 V 槽在 XY 方向的宽度。

重点提醒：

- `Top Shell` 与 `Acrylic Face Slot` / `Acrylic Face V-Groove` 互斥。
- `Face Slot Drop` 不是旧版本的“台阶高度”，它是从顶部往下量的距离。
- 顶部 Step 最大值会受字壳高度限制，通常不超过字壳高度的一半。

## 9. Bottom 结构：底面、背板卡槽、灯槽、包边/勾边

进入路径：`Settings -> Shape -> Bottom`

当前 Bottom 也使用互斥模式组织，重点讲清用途选择。

### Bottom Face

用途：

- 给字壳底部生成实心封闭层。
- 可配合手动螺丝孔。

参数：

- `Bottom Face Thickness`：底面封闭厚度。
- `Screw Hole Diameter`：螺丝孔直径。

教学顺序：

1. 先启用 Bottom Face。
2. 设置厚度和孔径。
3. 回到画布使用 `Screw Hole` 工具添加孔位。
4. `Process` 后进入 3D 预览检查孔位。

### Back Plate Slot / Back Plate V-Groove

用途：

- 为背板/底板装配生成卡槽或 V 槽。

参数：

- `Back Plate Slot Height`：背板卡槽或 V 槽所在 Z 高度。
- `Back Plate Slot Width`：背板卡槽或 V 槽宽度。

提醒：

- `Bottom Face`、`Back Plate Slot`、`Back Plate V-Groove`、`LED Strip Slot`、`Edge Wrap`、`Outline` 属于互斥或冲突场景，软件会自动收敛有效模式。
- 录课时不要同时打开多个底部模式，要一个案例只讲一种结构。

### LED Strip Slot

用途：

- 在字壳底部生成灯带槽。

参数：

- `Outer Slot` / `Hole Slot`：选择外轮廓或内孔是否生成灯槽。
- `Slot Width`：灯槽 XY 宽度。
- `Slot Depth`：灯槽深度。
- `Slot Floor Thickness`：槽底保留实心厚度。
- `Skip Small Hole Slots` 与 `Min Hole Span`：小内孔不生成灯槽，避免小孔区域生成不合理灯槽。

### Bottom Edge Wrap / Bottom Outline

用途：

- `Bottom Edge Wrap`：底部包边。
- `Bottom Outline`：底部勾边。

参数：

- 位置：`Inner` 或 `Outer`。
- 宽度、高度。

教学建议：

- 这部分放在进阶章节。
- 用 3D 预览对比开启前后差异，不要只讲参数名。

## 10. Other：防翘裙边、连襟字、DXF 导出补偿

进入路径：`Settings -> Shape -> Other`

### Anti-Warp Brim

用途：

- 增加底部附着，降低翘边。
- 当前版本支持外侧裙边、内侧裙边和多层裙边优先打印。

参数：

- `Brim Height`：防翘边高度。
- `Breakaway Gap`：防翘边连接线与字壳墙体的净空，便于拆除。
- `Outer Brim` / `Inner Brim`：选择外侧或内侧。

提醒：

- 默认先讲外侧裙边。
- 内侧裙边适合有较大内孔且也需要防翘的情况。

### Letter Bridges

用途：

- 连接离散字母或断开的笔画，让多个轮廓打印成一个整体。

参数：

- `Bridge Type`：三角形或菱形。
- `Auto-Detect Bridge Points`：自动寻找连接点。
- `Bridge Width`、`Bridge Bevel Height`、`Bridge Base Height`、`Bridge Support Offset`。

教学提醒：

- 连襟字只在确实需要连接离散笔画时启用。
- 第一次教学不要建议客户默认开启。

### DXF Export Compensation

用途：

- 控制底板 DXF 和面板 DXF 的装配补偿。

参数：

- `Outer Contour Clearance`：外轮廓安装公差。
- `Inner Hole Clearance`：内孔安装公差。
- `Laser Kerf Width`：激光切缝补偿。

重点口播：

> 导出底板和面板 DXF 前，一定要先确认这三个补偿值。它们直接影响板件能不能装进去、会不会太松或太紧。

## 11. Machine：打印机档案与平台限制

进入路径：`Settings -> Machine`

必讲内容：

- `Printer Profile`：选择打印机档案。
- 内置档案包含 MINGDA AD-F4 Mini、AD-F4、AD-F4 Pro、AD-F6 Pro、AD-F10 Ultra，以及 0.4 / 0.6 / 0.8 mm 喷嘴预设。
- `Printable Area X / Y / Z`：可打印区域。
- `Bed Exclude Area`：不可打印区域，使用 OrcaSlicer 风格坐标格式。
- `Nozzle Diameter`、`Filament Diameter`。
- 回抽和 Z-Hop：`Retract Length`、`Retract Speed`、`Short Z-Hop`、`Long Z-Hop`、`Long Travel Threshold`。

教学重点：

- 先选正确机器和喷嘴，再设置线宽和壁厚。
- 2D 画布和 3D 预览会显示不可打印区域；图形超出平台或压到不可打印区域时，`Process` 会被阻止。
- `.smp` 会保存项目的打印机档案快照，别人打开项目时能恢复当时的机器参数。

## 12. Print：G-code 打印参数

进入路径：`Settings -> Print`

### Speed Settings

- `Print Speed`
- `Travel Speed`
- `First Layer Speed`

讲解建议：

- 只讲常用原则，不要给所有材料固定值。
- 小字、细笔画、斜边和异形边建议更保守。

### Temperature Settings

- 首层喷嘴温度。
- 其他层喷嘴温度。
- 首层热床温度。
- 其他层热床温度。

### Cooling Settings

- 首层风扇百分比。
- 其他层风扇百分比。

### Color Change

当前版本是 Klipper 单喷头换色流程，不是多喷头自动混色。

讲解：

- `Enable Color Change`。
- 添加换色点：`Change At Height`。
- 设置 `Macro Index`。
- 预览列会显示实际写入的宏，例如默认模板下 `T3`。

提醒：

- 起始颜色来自 Start G-code。
- 换色点高度会按层高网格吸附。

### Prime Tower

用途：

- 用于换色或需要擦料的场景。

参数：

- `Center X / Center Y`
- `Tower Width / Tower Depth`
- `Infill Density`

提醒：

- Prime Tower 会在 2D 画布显示矩形占地。
- `Process` 时会校验它是否与模型或不可打印区域冲突。
- STL 导出不把 Prime Tower 当作字壳模型的一部分，重点用于 G-code 打印流程。

### Machine G-code

讲解：

- `Edit Start G-code`
- `Edit End G-code`
- 默认模板面向 Klipper `START_PRINT` / `END_PRINT` 工作流。

提醒：

- 普通客户只需确认打印机端宏匹配，不建议随意修改。
- 高级客户或售后可以根据机器宏做定制。

## 13. Process 处理

`Process` 是从 2D 轮廓和参数生成生产结构的关键步骤。

必须讲清楚：

- 没有图形不能处理。
- 参数不在可制造范围内会阻止处理。
- 图形超出平台或压到不可打印区域会阻止处理。
- Prime Tower 位置不合法会阻止处理。
- 修改图形、边型、尺寸、工艺参数后，建议重新 `Process`。

处理完成后：

- 状态栏会显示总高度和预计时间。
- 之后才能导出 G-code 或 STL。
- 如果当前已经在 Preview 页面，软件会准备 3D 预览。

建议口播：

> Process 可以理解成软件真正开始计算生产结构的按钮。前面所有图形和参数只是准备工作，只有处理完成后，预览和导出的生产文件才是当前参数对应的结果。

## 14. 3D 预览检查

进入路径：点击顶部 `Preview`。

讲解内容：

- 如果有图形但还没处理，进入 Preview 时会自动先处理。
- 首次进入预览会先显示轻量级图层预览，再异步生成实体网格。
- 支持鼠标旋转、缩放、平移。
- 支持正视、侧视、俯视、等轴测等视角预设。
- 平台网格、坐标轴、可打印区域和不可打印区域用于检查摆放是否合理。
- 层滑块显示当前 Z 高度和总高度，适合检查台阶、灯槽、底面、顶面、裙边等结构位置。

检查清单：

- 字壳高度是否符合输入。
- 斜边或异形边方向是否正确。
- 顶部台阶/底部台阶是否贴合内孔和外轮廓。
- 底面封闭是否保留内孔和螺丝孔。
- 灯槽是否出现在正确的外轮廓或内孔。
- 裙边是否在需要的位置，是否过近或过远。
- Prime Tower 是否在平台内且不与模型冲突。

## 15. 导出生产文件

### Export G-code

用途：

- 直接用于 Klipper 单喷头打印流程。
- 导出前必须已经 `Process`。

讲解重点：

- G-code 默认文件名会包含当前项目名和打印机档案名。
- 文件包含当前打印参数、温度、风扇、Start/End G-code、换色宏等信息。
- 当前版本增强了 OrcaSlicer / Moonraker / Mainsail 兼容信息和缩略图。

### Export STL

用途：

- 导出三维字壳模型。
- 可用于模型检查、第三方切片、客户确认。
- 导出前必须已经 `Process`。

提醒：

- STL 反映当前 Shape 工艺结果。
- 修改参数后要重新处理再导出。

### Export Baseplate DXF

用途：

- 导出底板加工轮廓。

讲解重点：

- 使用当前图形和 DXF 补偿参数。
- 导出成功提示会显示 `Outer Contour Clearance`、`Inner Hole Clearance`、`Laser Kerf Width`。

### Export Panel DXF

用途：

- 导出面板加工轮廓。

讲解重点：

- 同样受 DXF 补偿参数影响。
- 面板是否能准确装配，和 `Acrylic Face Slot / Acrylic Face V-Groove` 参数、DXF 补偿值都有关系。

## 16. 多语言、教程入口、更新与配置目录

可作为收尾章节或售后说明。

可讲内容：

- 菜单中支持 14 种语言切换。
- `Tutorial` 菜单会打开官方教学视频播放列表。
- `Check for Updates` 可手动检查更新，启动后也支持自动检查更新。
- `Show Configuration Folder` 可打开用户配置目录，用于售后查看本地配置、打印机档案和 UI 设置。

提醒：

- 语言切换通常需要重启后完整生效。
- 普通客户不需要直接修改配置目录文件。

## 17. 常见问题与避坑

录课最后建议专门做一章，减少售后重复解释。

### 无法处理

可能原因：

- 没有导入或生成任何图形。
- 图形超出打印平台。
- 图形压到不可打印区域。
- 线宽、壁厚、喷嘴、层高组合超出可打印范围。
- Prime Tower 和模型或平台限制冲突。

### 无法导出 G-code / STL

可能原因：

- 没有先 `Process`。
- 处理后又改了关键参数，但没有重新处理。
- 当前参数校验失败。

### 底板或面板装不上

优先检查：

- `Outer Contour Clearance`
- `Inner Hole Clearance`
- `Laser Kerf Width`
- 台阶宽度是否太小。
- DXF 加工设备实际切缝是否和输入一致。

### 斜边方向不对

检查：

- `Top Small / Top Large` 是否选反。
- 原始轮廓是以底面为基准，不要把顶部尺寸当成导入轮廓。

### 螺丝孔看不到或不能添加

检查：

- 是否启用 `Bottom Face`。
- 是否已经进入 `Screw Hole` 工具。
- 点击位置是否在有效底面区域内。

### 灯槽不在预期位置

检查：

- 是否选了 `Outer Slot` 或 `Hole Slot`。
- 小内孔是否被 `Skip Small Hole Slots` 跳过。
- `Slot Width` 是否让槽位没有足够空间生成。

### 换色没有按预期执行

检查：

- 是否启用 `Color Change`。
- 换色高度是否在字壳高度范围内。
- `Macro Index` 和打印机端宏是否匹配。
- Start G-code 中的初始工具或颜色是否设置正确。

## 不建议作为主线展开的内容

以下内容可以放到高级补充，不建议放进第一套客户教学主线：

- 内部算法细节，如路径偏移、轮廓分类、网格生成原理。
- 旧版本的层数字段逻辑。
- 面板/底板填充图案等尚未形成完整客户主流程的规划功能。
- 直接修改配置文件。
- 多喷头工作流；当前换色教学应按 Klipper 单喷头 T 宏讲。
- 一次性打开所有高级结构，例如同时开封底、底部台阶、灯槽、包边、勾边。

## 推荐最终录制顺序

最适合发布给客户的顺序如下：

1. 完整流程快速演示：用直边案例从导入到导出。
2. 界面和文件管理：Home、Project、Preview、SMP 保存。
3. 图形来源：DXF/SVG 导入与文字生成。
4. 2D 编辑：移动、旋转、缩放、镜像、布尔、组合、删除。
5. Shape 基础：Shell Height、Layer Height、Line Width、Wall Thickness。
6. Wall 边型：Straight、Beveled、Custom。
7. Top 工艺：Top Shell、Acrylic Face Slot、Acrylic Face V-Groove。
8. Bottom 工艺：Bottom Face、螺丝孔、Back Plate Slot、LED Strip Slot、Edge Wrap、Outline。
9. Other 工艺：Anti-Warp Brim、Letter Bridges、DXF Export Compensation。
10. Machine 设置：打印机档案、平台、喷嘴、不可打印区域。
11. Print 设置：速度、温度、冷却、换色、Prime Tower、Start/End G-code。
12. Process 与 Preview：处理、校验、3D 检查。
13. 导出：G-code、STL、底板 DXF、面板 DXF。
14. 常见问题：处理失败、导出失败、装配补偿、参数避坑。

录制时建议每章只围绕一个案例讲一个明确目标。不要在同一段视频里反复切换太多高级功能，否则客户会记住“参数很多”，但记不住“什么时候该用哪个参数”。
