# 使用Claude开发大型项目技巧

---

## 一、项目规划阶段

### 1. 先让Claude生成项目蓝图

```
推荐做法：
┌─────────────────────────────────────────────────┐
│  ✅ 先做：                                      │
│     1. 让Claude分析需求，输出功能清单           │
│     2. 让Claude设计项目结构                     │
│     3. 让Claude定义核心数据结构/接口            │
│     4. 确认后再开始写代码                       │
│                                                │
│  ❌ 不要：                                      │
│     直接说"帮我写一个XXX软件"                  │
│     → 容易方向跑偏，返工成本高                  │
└─────────────────────────────────────────────────┘
```

### 2. 创建CLAUDE.md项目文档

```markdown
# CLAUDE.md - 项目上下文文档

## 项目概述
SignMaker Slicer - 发光字3D打印切片软件

## 技术栈
- Python 3.11
- PySide6
- pyclipper
- ezdxf

## 目录结构
src/
├── core/    # 核心算法
├── ui/      # 界面
└── utils/   # 工具

## 核心类
- SliceEngine: 切片引擎
- GCodeWriter: G-code生成器

## 开发规范
- 使用类型注解
- 每个函数写docstring
- 遵循PEP8

## 当前进度
- [x] 项目框架
- [x] DXF解析
- [ ] 切片引擎
- [ ] UI界面
```

**每次新对话开始时，让Claude先读这个文件**

---

## 二、模块化开发

### 3. 一次只做一个模块

```
好的拆分方式：
┌─────────────────────────────────────────────────┐
│  Session 1: "帮我实现DXF解析模块"               │
│  Session 2: "帮我实现路径偏移算法"              │
│  Session 3: "帮我实现切片引擎"                  │
│  Session 4: "帮我实现G-code生成"                │
│  Session 5: "帮我实现2D画布UI"                  │
│  ...                                           │
│                                                │
│  每个模块：                                     │
│  ├── 独立文件                                  │
│  ├── 明确的输入输出                            │
│  ├── 可单独测试                                │
│  └── 500行以内                                 │
└─────────────────────────────────────────────────┘
```

### 4. 定义清晰的接口

```python
# 先定义接口，再实现
# interfaces.py

from abc import ABC, abstractmethod
from typing import List, Tuple

Point = Tuple[float, float]
Path = List[Point]

class ISliceEngine(ABC):
    @abstractmethod
    def load_contours(self, paths: List[Path]) -> None:
        """加载轮廓"""
        pass

    @abstractmethod
    def slice(self, params: 'SliceParams') -> List['Layer']:
        """执行切片"""
        pass

class IGCodeWriter(ABC):
    @abstractmethod
    def generate(self, layers: List['Layer']) -> str:
        """生成G-code"""
        pass
```

**让Claude围绕接口实现，保持一致性**

---

## 三、与Claude高效沟通

### 5. 提供足够的上下文

```
❌ 不好的提问：
"这个函数有bug，帮我修复"

✅ 好的提问：
"src/core/slice_engine.py 的 offset_path 函数，
输入 [(0,0), (100,0), (100,100), (0,100)]，delta=-5 时
返回空列表，预期应该返回内缩5mm的矩形。
请帮我修复。"
```

### 6. 使用任务清单

```markdown
当前任务：实现斜边生成算法

需求：
1. 输入：2D轮廓 + 斜边参数（宽度、高度）
2. 输出：每层的轮廓路径
3. 斜边从底部开始，向内逐渐收缩

参考INC-S参数：
- 斜边宽度：5mm
- 底板厚度：10mm（底部直边高度）
- 字壳高度：30mm

请实现 BevelGenerator 类
```

### 7. 让Claude生成测试用例

```python
# 先让Claude写测试，再实现功能
def test_offset_path():
    """测试路径偏移"""
    # 正方形向内偏移5
    square = [(0,0), (100,0), (100,100), (0,100)]
    result = offset_path(square, -5)

    # 验证结果
    assert len(result) == 1
    assert len(result[0]) == 4
    # 内缩后应该是90x90
    # ...
```

---

## 四、代码管理

### 8. 及时提交Git

```bash
# 每完成一个功能就提交
git add .
git commit -m "feat: 实现DXF解析模块"

git commit -m "feat: 实现路径偏移算法"

git commit -m "feat: 实现基础切片引擎"

# 这样出问题可以回滚
```

### 9. 保持文件小而专注

```
文件大小建议：
┌─────────────────────────────────────────────────┐
│  < 200行   │ 理想，Claude能完整理解和修改       │
│  200-500行 │ 可接受，需要指明修改位置           │
│  > 500行   │ 应该拆分，Claude容易遗漏上下文     │
└─────────────────────────────────────────────────┘
```

### 10. 使用类型注解

```python
# Claude生成的代码有类型注解时更准确
from typing import List, Tuple, Optional

def offset_path(
    path: List[Tuple[float, float]],
    delta: float
) -> List[List[Tuple[float, float]]]:
    """
    路径偏移

    Args:
        path: 输入路径点列表
        delta: 偏移量，正=外扩，负=内缩

    Returns:
        偏移后的路径列表（可能产生多个）
    """
    ...
```

---

## 五、处理上下文限制

### 11. 新对话时恢复上下文

```
每次新对话的开场白模板：

"我正在开发SignMaker Slicer项目。
请先阅读 CLAUDE.md 了解项目背景。

当前进度：已完成DXF解析、路径偏移
本次任务：实现台阶V槽生成

相关文件：
- src/core/slice_engine.py（请先读取）
- src/core/geometry.py（数据结构定义）"
```

### 12. 分批次生成大文件

```
如果需要生成很长的代码：

❌ "帮我生成完整的MainWindow类（1000行）"

✅ 分步骤：
   1. "先生成MainWindow的框架和初始化"
   2. "添加菜单栏和工具栏"
   3. "添加2D画布区域"
   4. "添加参数面板"
   5. "添加事件处理"
```

---

## 六、调试与修复

### 13. 提供完整错误信息

```
❌ "运行报错了"

✅ "运行 python main.py 报错：

Traceback (most recent call last):
  File "main.py", line 15, in <module>
    engine.slice(params)
  File "slice_engine.py", line 42, in slice
    result = offset_path(contour, -delta)
TypeError: offset_path() takes 1 positional argument but 2 were given

请帮我修复"
```

### 14. 让Claude解释代码

```
在不理解Claude生成的代码时：

"请解释 BevelGenerator.generate() 方法的算法逻辑，
特别是第35-50行的偏移量计算部分"
```

---

## 七、实用命令模板

```
# 让Claude阅读现有代码
"请阅读 src/core/ 目录下所有文件，总结当前实现了哪些功能"

# 让Claude review代码
"请review src/core/slice_engine.py，指出潜在问题和改进建议"

# 让Claude补充测试
"请为 src/core/path_offset.py 编写单元测试"

# 让Claude重构
"请重构 SliceEngine 类，将填充逻辑抽取到单独的 FillGenerator 类"

# 让Claude写文档
"请为 src/core/slice_engine.py 生成API文档"

# 让Claude对比实现
"请对比我的实现和INC-S的功能，列出还缺少哪些功能"

# 让Claude优化性能
"这个函数处理大文件时很慢，请帮我优化性能"

# 让Claude生成配置
"请生成 pyproject.toml 和 requirements.txt"
```

---

## 八、项目开发流程模板

### 新项目启动清单

```
□ 1. 需求分析
   └── 让Claude列出功能清单

□ 2. 技术选型
   └── 让Claude推荐技术栈

□ 3. 项目结构
   └── 让Claude生成目录结构

□ 4. 创建CLAUDE.md
   └── 记录项目上下文

□ 5. 定义数据结构
   └── 让Claude定义核心类/接口

□ 6. 逐模块开发
   └── 每个模块独立session

□ 7. 集成测试
   └── 让Claude写测试用例

□ 8. 文档生成
   └── 让Claude写README和API文档

□ 9. 打包发布
   └── 让Claude配置打包脚本
```

### 每日开发流程

```
1. 开始新对话
   ↓
2. 让Claude读取CLAUDE.md
   ↓
3. 说明今日任务
   ↓
4. 让Claude读取相关代码文件
   ↓
5. 开始开发/修复
   ↓
6. 测试验证
   ↓
7. Git提交
   ↓
8. 更新CLAUDE.md进度
```

---

## 九、常见问题处理

### Claude生成的代码有错误

```
1. 提供完整错误信息
2. 说明期望的正确行为
3. 如果是逻辑错误，提供输入输出示例
```

### Claude忘记了之前的上下文

```
1. 让Claude重新读取相关文件
2. 简要复述之前的讨论结论
3. 保持CLAUDE.md更新
```

### 代码风格不一致

```
1. 在CLAUDE.md中明确代码规范
2. 提供示例代码作为参考
3. 让Claude统一重构
```

### 功能实现与预期不符

```
1. 提供更详细的需求描述
2. 给出具体的输入输出示例
3. 参考现有实现（如INC-S）说明
```

---

## 十、效率提升技巧

### 并行开发

```
如果有多个独立模块：
- 开多个Claude对话
- 每个对话负责一个模块
- 最后整合
```

### 代码复用

```
让Claude生成可复用的工具函数库：
- 文件操作工具
- 几何计算工具
- UI组件库
后续项目可直接复用
```

### 快速原型

```
先让Claude生成简化版本：
1. 硬编码参数
2. 最小功能集
3. 验证可行后再完善
```

### 学习新技术

```
让Claude解释代码时同时学习：
"请实现XXX功能，并解释关键代码的原理"
```

---

## 附录：SignMaker Slicer 开发计划

```
推荐开发顺序：
┌─────────────────────────────────────────────────┐
│  Week 1: 基础框架                               │
│  ├── Day 1: 项目结构 + CLAUDE.md               │
│  ├── Day 2: 数据结构定义                        │
│  ├── Day 3: DXF解析模块                        │
│  └── Day 4-5: 基础UI框架                       │
│                                                │
│  Week 2: 核心切片                               │
│  ├── Day 1: 路径偏移                           │
│  ├── Day 2: 分层切片                           │
│  ├── Day 3: G-code生成                         │
│  └── Day 4-5: 集成测试                         │
│                                                │
│  Week 3-4: 高级功能                            │
│  ├── 斜边生成                                  │
│  ├── 台阶V槽                                   │
│  ├── 填充算法                                  │
│  └── 3D预览                                    │
│                                                │
│  Week 5-6: 完善功能                            │
│  ├── 连襟/包边/勾边                            │
│  ├── 换色逻辑                                  │
│  ├── 参数面板                                  │
│  └── 打包发布                                  │
└─────────────────────────────────────────────────┘
```

---

*文档创建日期：2026年1月3日*
