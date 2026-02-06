@echo off
REM MINGDA SignMaker - 快速打包脚本 (Windows)
REM 使用方法: 双击运行或在cmd中执行 build.bat

echo ========================================
echo   MINGDA SignMaker - 快速打包
echo ========================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python
    pause
    exit /b 1
)

REM 安装PyInstaller（如果未安装）
echo [1/3] 检查PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo 正在安装PyInstaller...
    pip install pyinstaller
)

REM 运行打包脚本
echo.
echo [2/3] 开始打包应用...
python build.py

REM 检查结果
if exist "dist\SignMaker\SignMaker.exe" (
    echo.
    echo [3/3] 打包成功！
    echo.
    echo 应用位置: dist\SignMaker\
    echo 可执行文件: dist\SignMaker\SignMaker.exe
    echo.
    echo 按任意键打开输出目录...
    pause >nul
    explorer dist\SignMaker
) else (
    echo.
    echo [错误] 打包失败，请检查错误信息
    pause
)
