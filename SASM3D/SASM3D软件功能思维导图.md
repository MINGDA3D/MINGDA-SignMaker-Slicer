# SASM3D软件功能全景

## 一、软件概述

### 基本信息
- 基于FreeCAD的专业发光字建模软件
- 核心功能：3D发光字(Channel Letters)建模

### 技术架构
- 底层引擎：FreeCAD
- GUI框架：PySide6
- 几何内核：OpenCASCADE

## 二、主界面功能

### 输入方式
- 文本输入
    - 输入文字直接生成轮廓
    - 支持自定义字体
    - 可设置文字高度
    - 可设置字间距
- 文件导入
    - CDR格式
    - DXF格式
    - EPS格式
    - SVG格式

### 工艺模式选择
- 标准工艺
    - 自动执行建模流程
    - 根据全局参数自动生成
- 非标准工艺
    - 手动调整参数
    - 点击"生成3D模型"执行

## 三、工艺类型（14种）

### 平面类工艺
- PROC_1：平面+正光
    - 壁和底部一体成型
    - 顶部：TOP_1
    - 墙体：WALL_1
    - 底部：BOT_1
- PROC_2：平面+正背光
    - 壁和底部分离
    - 顶部：TOP_1
    - 墙体：WALL_1
    - 底部：BOT_2

### 斜边类工艺
- PROC_3：斜边+正光
    - 外壳嵌入内壳
    - 顶部：TOP_1
    - 墙体：WALL_2
    - 底部：BOT_2
- PROC_4：斜边+正背光
    - 壁和底部分离
    - 顶部：TOP_1
    - 墙体：WALL_2
    - 底部：BOT_2

### 斜面类工艺
- PROC_5：斜面+正光
    - 顶部：TOP_1
    - 墙体：WALL_3
    - 底部：BOT_3
- PROC_6：斜面+正背光
    - 顶部：TOP_1
    - 墙体：WALL_3
    - 底部：BOT_4

### 圆角类工艺
- PROC_7：圆角+正光
    - 实心一体成型
    - 顶部：TOP_2
    - 墙体：WALL_1
    - 底部：BOT_1
- PROC_8：圆角+正背光
    - 顶部：TOP_2
    - 墙体：WALL_1
    - 底部：BOT_2

### 实心类工艺
- PROC_9：斜面实心墙
    - 墙体：WALL_4
- PROC_10：斜面曲面墙实心
    - 墙体：WALL_5
- PROC_11：圆弧曲面实心
    - 墙体：WALL_6
- PROC_12：锥形实心
    - 墙体：WALL_7
- PROC_13：管状实心
    - 墙体：WALL_8

### 自定义工艺
- PROC_14：DIY自定义
    - 用户自定义参数组合
    - 基于标准工艺修改

## 四、参数设置

### 顶部(Top)参数
- 台阶高度
    - 范围：2.0-5.0mm
    - 默认值：3.0mm
    - 步长：3.0mm
    - 用途：亚克力板厚度
- 台阶宽度
    - 范围：0.4-1.2mm
    - 默认值：0.4mm
    - 步长：0.6mm

### 墙体(Wall)参数
- 整体墙高
    - 范围：25.0-80.0mm
    - 默认值：25.0mm
    - 用途：字壳总高度
- 墙厚
    - 范围：1.2-3.2mm
    - 默认值：2.4mm
    - 建议：40cm以下用1.2mm，40cm以上用1.3mm
- 斜边角度
    - 范围：45.0-85.0°
    - 默认值：75°
    - 用途：斜边与垂直方向夹角
- 斜边基座高度
    - 范围：10.0-75.0mm
    - 默认值：10mm
    - 用途：斜边底部直边高度

### 底部(Bottom)参数
- 底边高度
    - 范围：2.0-5.0mm
    - 默认值：2.0mm
- 凹槽高度
    - 范围：2.0-10.0mm
    - 默认值：2.0mm
- 凸台宽度
    - 默认值：0.8mm

## 五、对象操作工具

### 基础操作
- 撤销(Undo)
    - 取消上一步操作
- 重做(Redo)
    - 恢复已取消的操作
- 删除(Delete)
    - 删除选中对象

### 变换操作
- 缩放(Zoom)
    - 进入缩放模式
    - 按i键：放大
    - 按o键：缩小
- 移动(Move)
    - 进入移动模式
    - 左/右方向键：X轴移动
    - 上/下方向键：Y轴移动
    - 按u键：Z轴向上
    - 按d键：Z轴向下
    - 移动步长：4.0mm
- 旋转(Rotate)
    - 进入旋转模式
    - 按住x键+方向键：绕X轴旋转
    - 按住y键+方向键：绕Y轴旋转
    - 按住z键+方向键：绕Z轴旋转
    - 旋转步长：5.0°
- 镜像(Mirror)
    - 沿XY平面镜像
    - 沿YZ平面镜像
    - 沿XZ平面镜像
- 缩放比例(Scale)
    - 按比例整体拉伸
    - 按X轴单独拉伸
    - 按Y轴单独拉伸
    - 按Z轴单独拉伸

### 组合操作
- 布尔运算(Boolean)
    - 并集(Union)：合并两个对象
    - 交集(Intersection)：保留重叠部分
    - 差集(Difference)：从第一个对象减去第二个
- 合并(Merge/Compound)
    - 将多个对象组合为一个组
    - 至少选择2个对象
- 拆分(Split/Explode)
    - 将组拆分为独立对象
    - 分离Compound中的Solid

### 特殊操作
- 连桥(Bridge)
    - 在两个对象底部创建连接
    - 可选类型：三角形/菱形
    - 参数：直径
- 打孔(Hole)
    - 在对象表面打孔
    - 可选形状：圆形/六边形
    - 参数：直径、长度

## 六、导出功能

### STL导出
- 用途：3D打印
- 格式：STL文件
- 功能：导出当前发光字模型

### PLT导出
- 用途：激光切割
- 格式：PLT文件
- 功能：导出亚克力板切割路径
- 参数：路径偏移补偿
    - 正值：向外偏移
    - 负值：向内偏移

### STL加密
- 功能：保护STL文件
- 防止未授权使用

## 七、高级功能

### 轮廓处理
- 轮廓偏移
    - 向内偏移
    - 向外偏移
    - 孔洞方向自动识别
- 孔洞识别
    - 自动识别闭合区域
    - 区分外轮廓和内孔
- Wire分析
    - 曲线有效性检查
    - 闭合性检查

### SVG处理
- SVG预检查
    - 导入前验证文件
    - 检查路径有效性
- CDR转SVG
    - 通过Inkscape转换
- EPS转SVG
    - 通过Inkscape转换

### 草图操作
- Wire转草图
    - 将Wire转换为Sketcher草图
- 草图附着
    - 将草图附着到面

## 八、FreeCAD基础模块

### Part模块
- 基础形状创建
- 布尔运算
- 复合工具
- BOPTools

### PartDesign模块
- 零件设计
- 齿轮生成
- 链轮生成

### Sketcher模块
- 2D草图绘制
- 约束系统
- 轮廓编辑

### Draft模块
- 2D绘图工具
- 阵列
- 偏移

### Mesh模块
- 网格处理
- 网格修复
- 网格转换

### 其他模块
- Surface：曲面建模
- Spreadsheet：电子表格
- OpenSCAD：OpenSCAD集成
- Import：文件导入
- Material：材质管理
- Measure：测量工具

## 九、单位系统

### 支持单位
- 毫米(mm)：默认
- 英寸(inch)

### 单位转换
- 1 inch = 25.4 mm

## 十、核心源代码文件

### 主界面文件
- sidewindow.py：主侧边栏窗口
- SideBartt_ui.py：侧边栏UI定义
- horizontal_buttons.py：水平工具按钮
- vertical_buttons.py：垂直工具按钮

### 操作文件
- horizontal_operations.py：水平操作实现
- vertical_operations.py：垂直操作实现
- operations_common.py：通用操作函数

### 配置文件
- process_config.py：工艺类型配置
- processes_config.csv：工艺参数CSV
- tool_tips.py：工具提示文本

### 建模文件
- sasm_create_base_component.py：基础组件创建
- sasm_create_pad.py：拉伸操作
- sasm_create_sweep_psolid0716.py：扫掠实体
- sasm_attach_sketch.py：草图附着
- create_profile_04.py：轮廓创建
- create_pd_sweep.py：PartDesign扫掠

### 轮廓处理文件
- SASMOffsetFromText.py：文字轮廓偏移
- simple_offset.py：简单偏移
- improved_offset_quality.py：改进的偏移质量
- improved_perpendicular_offset.py：改进的垂直偏移
- hole_identify.py：孔洞识别
- outlines_and_holes.py：轮廓与孔洞

### 导入导出文件
- dxf_export_svg.py：DXF导出SVG
- svg_pre_check.py：SVG预检查
- export_compoun_wires_to_plt.py：导出PLT
- SASM_STLEncryptor.py：STL加密
- cdr_to_svg.py：CDR转SVG
- ink_eps_svg.py：EPS转SVG

### Wire处理文件
- wire_curve_analyzer.py：Wire曲线分析
- wire_to_sketch_wire.py：Wire转草图
- wire_to_sketch_degree.py：Wire转草图(角度)
- wire_sketch_wire.py：Wire草图操作
- get_wire_pairs.py：获取Wire对
- WireIntersectionChecker.py：Wire交叉检查
- check_offset_wire.py：检查偏移Wire

### 对话框文件
- text_dialog.py：文本输入对话框
- global_dialog.py：全局设置对话框
- diy_dialog.py：DIY设置对话框
- hole_dialog.py：打孔对话框
- scale_dialog.py：缩放对话框
- detail_dialog.py：详细设置对话框
- processes_dialog.py：工艺选择对话框

### UI文件
- text.ui / text_ui.py
- global.ui / global_ui.py
- diy.ui / diy_ui.py
- hole.ui / hole_ui.py
- scale.ui / scale_ui.py
- detail.ui / detail_ui.py
- processes.ui / processes_ui.py

## 十一、参数速查表

### 顶部参数默认值
- 台阶高度：3.0mm
- 台阶宽度：0.4mm

### 墙体参数默认值
- 整体墙高：25.0mm
- 墙厚：2.4mm
- 斜边角度：75°
- 斜边基座高度：10mm

### 底部参数默认值
- 底边高度：2.0mm
- 凹槽高度：2.0mm
- 凸台宽度：0.8mm

### 操作参数默认值
- 移动步长：4.0mm
- 缩放因子：1.1 (10%)
- 旋转步长：5.0°
