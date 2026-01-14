"""
切片管理器模块

负责协调DXF解析、切片引擎和G-code生成。
"""

from typing import List, Optional, Dict
from PySide6.QtCore import QObject, Signal, QThread

from src.core.types import Contour, SliceParams, GCodeParams, SliceResult
from src.core.dxf_parser import DXFParser
from src.core.slice_engine import SliceEngine
from src.core.gcode_writer import GCodeWriter


class SliceWorker(QThread):
    """切片工作线程"""

    progress = Signal(int, str)  # (进度百分比, 当前步骤)
    finished = Signal(object)  # SliceResult
    error = Signal(str)

    def __init__(self, engine: SliceEngine, contours: List[Contour],
                 params: SliceParams):
        super().__init__()
        self.engine = engine
        self.contours = contours
        self.params = params

    def run(self):
        try:
            self.progress.emit(10, "准备切片...")
            result = self.engine.slice(self.contours, self.params)
            self.progress.emit(100, "切片完成")
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class SliceManager(QObject):
    """切片管理器"""

    # 信号
    slice_started = Signal()
    slice_progress = Signal(int, str)  # (进度百分比, 当前步骤)
    slice_completed = Signal(object)  # SliceResult
    slice_failed = Signal(str)

    def __init__(self):
        super().__init__()
        self.engine = SliceEngine()
        self.parser = DXFParser()
        self._worker: Optional[SliceWorker] = None

    def import_dxf(self, file_path: str) -> List[Contour]:
        """导入DXF文件"""
        return self.parser.parse(file_path)

    def slice(self, contours: List[Contour],
              params: SliceParams) -> SliceResult:
        """执行切片（同步）"""
        return self.engine.slice(contours, params)

    def slice_async(self, contours: List[Contour],
                    params: SliceParams) -> None:
        """异步执行切片"""
        if self._worker is not None and self._worker.isRunning():
            return

        self.slice_started.emit()

        self._worker = SliceWorker(self.engine, contours, params)
        self._worker.progress.connect(self.slice_progress.emit)
        self._worker.finished.connect(self._on_slice_completed)
        self._worker.error.connect(self.slice_failed.emit)
        self._worker.start()

    def _on_slice_completed(self, result: SliceResult):
        """切片完成回调"""
        self.slice_completed.emit(result)

    def export_gcode(self, result: SliceResult,
                     params: GCodeParams,
                     output_path: str) -> None:
        """导出G-code"""
        writer = GCodeWriter(params)
        writer.write(result, output_path)

    def calculate_estimate(self, result: SliceResult) -> Dict:
        """计算预计时间和线材用量"""
        return {
            'total_layers': result.total_layers,
            'total_height': result.total_height,
            'estimated_time': result.estimated_time,
            'estimated_filament': result.estimated_filament,
            'filament_per_extruder': result.filament_per_extruder
        }
