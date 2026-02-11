"""
忙碌指示对话框 & 通用工作线程

用于在后台执行耗时操作时显示转圈圈动画，防止UI冻结。
"""

from typing import Any, Callable, Optional, Tuple

from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QPainter, QColor, QPen, QConicalGradient
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QWidget


class SpinnerWidget(QWidget):
    """转圈圈动画控件"""

    def __init__(self, size: int = 48, parent=None):
        super().__init__(parent)
        self._size = size
        self._angle = 0
        self.setFixedSize(size, size)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._timer.start(16)  # ~60fps

    def _rotate(self):
        self._angle = (self._angle + 5) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 圆弧参数
        pen_width = 4
        margin = pen_width // 2 + 1
        rect = self.rect().adjusted(margin, margin, -margin, -margin)

        # 底圈（暗色）
        bg_pen = QPen(QColor("#30363D"), pen_width)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.drawEllipse(rect)

        # 旋转弧（亮色渐变）
        arc_pen = QPen(QColor("#58A6FF"), pen_width)
        arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(arc_pen)

        start = int(self._angle * 16)
        span = 90 * 16  # 90度的弧
        painter.drawArc(rect, start, span)

        painter.end()

    def stop(self):
        self._timer.stop()


class BusyDialog(QDialog):
    """忙碌指示对话框 — 模态、转圈圈、提示文字"""

    def __init__(self, message: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("")
        self.setModal(True)
        self.setFixedSize(220, 140)

        # 去掉标题栏
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 布局
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # 转圈圈
        self._spinner = SpinnerWidget(48, self)
        layout.addWidget(self._spinner, alignment=Qt.AlignmentFlag.AlignCenter)

        # 提示文字
        self._label = QLabel(message)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setWordWrap(True)
        self._label.setStyleSheet("color: #C9D1D9; font-size: 13px;")
        layout.addWidget(self._label)

        self.setStyleSheet("""
            BusyDialog {
                background-color: #1C2128;
                border: 1px solid #30363D;
                border-radius: 12px;
            }
        """)

    def set_message(self, message: str):
        self._label.setText(message)

    def closeEvent(self, event):
        """禁止用户关闭"""
        event.ignore()

    def keyPressEvent(self, event):
        """屏蔽 Escape 关闭"""
        if event.key() == Qt.Key.Key_Escape:
            event.ignore()
        else:
            super().keyPressEvent(event)

    def done_close(self):
        """由 WorkerThread 完成后调用"""
        self._spinner.stop()
        self.accept()


class WorkerThread(QThread):
    """通用工作线程

    将任意耗时函数放到后台执行，完成后通过信号返回结果。

    Usage::

        def heavy_work():
            return some_expensive_call()

        worker = WorkerThread(heavy_work)
        worker.finished_result.connect(on_success)
        worker.error_occurred.connect(on_error)
        worker.start()
    """

    finished_result = Signal(object)   # 成功 → 返回值
    error_occurred = Signal(str)       # 失败 → 错误信息

    def __init__(self, func: Callable[[], Any], parent=None):
        super().__init__(parent)
        self._func = func

    def run(self):
        try:
            result = self._func()
            self.finished_result.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))


def run_async(parent, message: str, func: Callable[[], Any],
              on_success: Callable[[Any], None],
              on_error: Optional[Callable[[str], None]] = None):
    """便捷函数：弹出 BusyDialog + 后台执行 func

    Parameters
    ----------
    parent : QWidget
        父窗口
    message : str
        对话框提示文字
    func : callable
        无参数的耗时函数，在子线程执行
    on_success : callable
        func 成功后，在主线程回调，接收 func 返回值
    on_error : callable, optional
        func 失败后，在主线程回调，接收错误信息字符串
    """
    dialog = BusyDialog(message, parent)

    # 把 worker 挂到 dialog 上防止被 GC
    worker = WorkerThread(func, dialog)

    def _on_finished(result):
        dialog.done_close()
        on_success(result)

    def _on_error(err_msg):
        dialog.done_close()
        if on_error:
            on_error(err_msg)

    worker.finished_result.connect(_on_finished)
    worker.error_occurred.connect(_on_error)
    worker.start()

    dialog.exec()  # 模态阻塞，直到 done_close() 被调用
