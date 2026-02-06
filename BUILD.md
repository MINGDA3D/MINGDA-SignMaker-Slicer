# MINGDA SignMaker - 打包相关说明

## 快速打包

### Windows用户
直接双击运行：
```
build.bat
```

或在命令行中：
```bash
python build.py
```

### Linux/Mac用户
```bash
python build.py
```

## 打包步骤

打包脚本会自动完成以下步骤：

1. **检查依赖** - 自动安装PyInstaller（如果未安装）
2. **编译资源** - 编译Qt资源文件（.qrc → .py）
3. **编译翻译** - 编译翻译文件（.ts → .qm）
4. **打包应用** - 使用PyInstaller生成可执行文件

## 输出结果

打包完成后，应用位于：
```
dist/SignMaker/
├── SignMaker.exe          # 主程序
├── translations/          # 翻译文件
├── docs/images/          # 图标和资源
└── 其他依赖库文件
```

## 手动打包

如果自动打包脚本有问题，可以手动执行：

```bash
# 1. 安装PyInstaller
pip install pyinstaller

# 2. 运行打包
pyinstaller build.spec
```

## 打包配置

打包配置文件：`build.spec`

主要配置项：
- `datas`: 需要包含的数据文件
- `hiddenimports`: 需要显式导入的模块
- `excludes`: 排除不需要的模块（减小体积）
- `console=False`: 不显示控制台窗口

## 常见问题

### 1. 打包后程序无法运行

**可能原因：**
- 缺少依赖文件
- OpenGL驱动问题

**解决方法：**
- 在目标机器上安装最新的显卡驱动
- 检查 dist/SignMaker/ 目录是否包含所有依赖

### 2. 打包体积过大

**优化方法：**
- 在 build.spec 的 `excludes` 中添加不需要的模块
- 使用 UPX 压缩（已启用）

### 3. 图标或资源文件缺失

**检查：**
- `resources/rc_resources.py` 是否存在
- `translations/*.qm` 文件是否存在
- `docs/images/` 目录是否有所需图标

## 创建安装程序（可选）

### 使用NSIS（推荐）

1. 下载安装NSIS: https://nsis.sourceforge.io/
2. 创建安装脚本（待实现）
3. 生成安装程序

### 使用Inno Setup

1. 下载Inno Setup: https://jrsoftware.org/isinfo.php
2. 创建安装脚本
3. 生成安装程序

## 版本信息

在打包前修改版本信息：
- `main.py` 中的应用信息
- `build.spec` 中的版本号

## 测试

打包完成后，建议测试：
1. 在干净的Windows系统上运行
2. 测试所有主要功能
3. 测试多语言切换
4. 测试文件导入/导出
5. 测试3D预览

## 发布清单

打包发布前检查：
- [ ] 版本号已更新
- [ ] 所有功能正常工作
- [ ] 翻译文件已编译
- [ ] 图标正确显示
- [ ] 文件大小合理（< 200MB）
- [ ] 在干净系统上测试通过
