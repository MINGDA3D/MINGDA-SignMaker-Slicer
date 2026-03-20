"""
MINGDA SignMaker - 撤销/重做管理器

实现命令模式（Command Pattern）的撤销/重做系统。

主要组件：
- Command: 命令基类，定义执行和撤销接口
- UndoManager: 管理撤销/重做栈
- 各种具体命令类：移动、旋转、缩放、镜像、删除等
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Any, TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

if TYPE_CHECKING:
    from src.core.types import Contour, Point


class Command(ABC):
    """
    命令基类

    所有可撤销的操作都应该继承此类，
    并实现 execute() 和 undo() 方法。
    """

    def __init__(self, description: str = ""):
        self.description = description
        self._is_executed = False

    @abstractmethod
    def execute(self) -> bool:
        """
        执行命令

        Returns:
            True 表示执行成功，False 表示失败
        """
        pass

    @abstractmethod
    def undo(self) -> bool:
        """
        撤销命令

        Returns:
            True 表示撤销成功，False 表示失败
        """
        pass

    def redo(self) -> bool:
        """
        重做命令（默认与 execute 相同）
        """
        return self.execute()

    def merge_with(self, other: Command) -> Optional[Command]:
        """
        尝试与另一个命令合并

        用于连续的同类型操作（如连续拖拽）合并成一个命令。

        Returns:
            合并后的命令，如果不能合并则返回 None
        """
        return None


class CompositeCommand(Command):
    """
    复合命令

    将多个命令组合成一个原子操作。
    """

    def __init__(self, commands: List[Command], description: str = ""):
        super().__init__(description or "复合操作")
        self.commands = commands

    def execute(self) -> bool:
        for cmd in self.commands:
            if not cmd.execute():
                # 回滚已执行的命令
                for executed in reversed(self.commands[:self.commands.index(cmd)]):
                    executed.undo()
                return False
        self._is_executed = True
        return True

    def undo(self) -> bool:
        # 逆序撤销
        for cmd in reversed(self.commands):
            if not cmd.undo():
                return False
        self._is_executed = False
        return True


class UndoManager(QObject):
    """
    撤销/重做管理器

    维护撤销栈和重做栈，提供撤销/重做功能。
    """

    # 信号
    can_undo_changed = Signal(bool)  # 可撤销状态变化
    can_redo_changed = Signal(bool)  # 可重做状态变化
    command_executed = Signal(str)   # 命令执行（描述）
    command_undone = Signal(str)     # 命令撤销（描述）
    command_redone = Signal(str)     # 命令重做（描述）
    stack_changed = Signal()         # 栈变化

    def __init__(self, max_undo_levels: int = 100, parent=None):
        super().__init__(parent)

        self._undo_stack: List[Command] = []
        self._redo_stack: List[Command] = []
        self._max_levels = max_undo_levels

        # 用于批量操作
        self._batch_commands: Optional[List[Command]] = None
        self._batch_description: str = ""

        # 保存点（用于判断是否有未保存的修改）
        self._save_point: int = 0

    @property
    def can_undo(self) -> bool:
        """是否可以撤销"""
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        """是否可以重做"""
        return len(self._redo_stack) > 0

    @property
    def is_modified(self) -> bool:
        """是否有未保存的修改"""
        return len(self._undo_stack) != self._save_point

    @property
    def undo_text(self) -> str:
        """获取撤销操作的描述"""
        if self._undo_stack:
            return f"撤销 {self._undo_stack[-1].description}"
        return "撤销"

    @property
    def redo_text(self) -> str:
        """获取重做操作的描述"""
        if self._redo_stack:
            return f"重做 {self._redo_stack[-1].description}"
        return "重做"

    def push(self, command: Command, execute: bool = True) -> bool:
        """
        推送命令到撤销栈

        Args:
            command: 要执行的命令
            execute: 是否立即执行命令

        Returns:
            命令是否成功执行（如果 execute=True）
        """
        # 如果正在批量操作，添加到批量列表
        if self._batch_commands is not None:
            self._batch_commands.append(command)
            if execute:
                return command.execute()
            return True

        # 执行命令
        if execute:
            if not command.execute():
                return False

        # 尝试与上一个命令合并
        if self._undo_stack:
            merged = self._undo_stack[-1].merge_with(command)
            if merged:
                self._undo_stack[-1] = merged
                self._emit_changes()
                return True

        # 添加到撤销栈
        self._undo_stack.append(command)

        # 清空重做栈
        self._redo_stack.clear()

        # 限制栈大小
        while len(self._undo_stack) > self._max_levels:
            self._undo_stack.pop(0)
            if self._save_point > 0:
                self._save_point -= 1

        self._emit_changes()
        self.command_executed.emit(command.description)

        return True

    def undo(self) -> bool:
        """撤销上一个命令"""
        if not self.can_undo:
            return False

        command = self._undo_stack.pop()

        if command.undo():
            self._redo_stack.append(command)
            self._emit_changes()
            self.command_undone.emit(command.description)
            return True
        else:
            # 撤销失败，放回去
            self._undo_stack.append(command)
            return False

    def redo(self) -> bool:
        """重做上一个被撤销的命令"""
        if not self.can_redo:
            return False

        command = self._redo_stack.pop()

        if command.redo():
            self._undo_stack.append(command)
            self._emit_changes()
            self.command_redone.emit(command.description)
            return True
        else:
            # 重做失败，放回去
            self._redo_stack.append(command)
            return False

    def clear(self):
        """清空所有历史记录"""
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._save_point = 0
        self._emit_changes()

    def set_save_point(self):
        """设置保存点"""
        self._save_point = len(self._undo_stack)

    def begin_batch(self, description: str = "批量操作"):
        """
        开始批量操作

        批量操作期间的所有命令会合并成一个复合命令。
        """
        if self._batch_commands is not None:
            raise RuntimeError("已经在批量操作中")
        self._batch_commands = []
        self._batch_description = description

    def end_batch(self) -> bool:
        """
        结束批量操作

        Returns:
            批量命令是否成功添加到栈中
        """
        if self._batch_commands is None:
            return False

        commands = self._batch_commands
        description = self._batch_description
        self._batch_commands = None
        self._batch_description = ""

        if not commands:
            return True

        if len(commands) == 1:
            # 只有一个命令，直接添加
            command = commands[0]
            command.description = description or command.description
        else:
            # 多个命令，创建复合命令
            command = CompositeCommand(commands, description)

        # 命令已经在 push 时执行过，这里不再执行
        return self.push(command, execute=False)

    def cancel_batch(self):
        """
        取消批量操作

        撤销批量操作期间已执行的所有命令。
        """
        if self._batch_commands is None:
            return

        # 逆序撤销已执行的命令
        for cmd in reversed(self._batch_commands):
            cmd.undo()

        self._batch_commands = None
        self._batch_description = ""

    def get_undo_history(self, limit: int = 10) -> List[str]:
        """获取撤销历史记录"""
        return [cmd.description for cmd in reversed(self._undo_stack[-limit:])]

    def get_redo_history(self, limit: int = 10) -> List[str]:
        """获取重做历史记录"""
        return [cmd.description for cmd in reversed(self._redo_stack[-limit:])]

    def _emit_changes(self):
        """发出状态变化信号"""
        self.can_undo_changed.emit(self.can_undo)
        self.can_redo_changed.emit(self.can_redo)
        self.stack_changed.emit()


# =============================================================================
# 具体命令类
# =============================================================================

@dataclass
class ContourSnapshot:
    """轮廓快照，用于保存和恢复轮廓状态"""
    index: int
    contour_data: Any  # deepcopy of Contour

    @classmethod
    def from_contour(cls, index: int, contour: 'Contour') -> 'ContourSnapshot':
        return cls(index=index, contour_data=deepcopy(contour))

    def restore_to(self, contours: List['Contour']):
        """恢复快照到轮廓列表"""
        if 0 <= self.index < len(contours):
            contours[self.index] = deepcopy(self.contour_data)


class MoveCommand(Command):
    """移动命令"""

    def __init__(self, contours: List['Contour'], indices: List[int],
                 dx: float, dy: float):
        super().__init__("移动")
        self.contours = contours
        self.indices = list(indices)
        self.dx = dx
        self.dy = dy

    def execute(self) -> bool:
        self._apply_move(self.dx, self.dy)
        self._is_executed = True
        return True

    def undo(self) -> bool:
        self._apply_move(-self.dx, -self.dy)
        self._is_executed = False
        return True

    def _apply_move(self, dx: float, dy: float):
        from src.core.types import Point
        for idx in self.indices:
            if 0 <= idx < len(self.contours):
                contour = self.contours[idx]
                # 移动外轮廓
                contour.outer.points = [
                    Point(p.x + dx, p.y + dy) for p in contour.outer.points
                ]
                # 移动内孔
                for hole in contour.holes:
                    hole.points = [
                        Point(p.x + dx, p.y + dy) for p in hole.points
                    ]

    def merge_with(self, other: Command) -> Optional[Command]:
        """合并连续的移动命令"""
        if isinstance(other, MoveCommand):
            if set(self.indices) == set(other.indices):
                return MoveCommand(
                    self.contours,
                    self.indices,
                    self.dx + other.dx,
                    self.dy + other.dy
                )
        return None


class RotateCommand(Command):
    """旋转命令"""

    def __init__(self, contours: List['Contour'], indices: List[int],
                 center_x: float, center_y: float, angle_degrees: float):
        super().__init__("旋转")
        self.contours = contours
        self.indices = list(indices)
        self.center_x = center_x
        self.center_y = center_y
        self.angle = angle_degrees

        # 保存原始状态用于撤销
        self._snapshots = [
            ContourSnapshot.from_contour(idx, contours[idx])
            for idx in indices if 0 <= idx < len(contours)
        ]

    def execute(self) -> bool:
        import math
        angle_rad = math.radians(self.angle)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        from src.core.types import Point

        for idx in self.indices:
            if 0 <= idx < len(self.contours):
                contour = self.contours[idx]
                self._rotate_path(contour.outer, cos_a, sin_a)
                for hole in contour.holes:
                    self._rotate_path(hole, cos_a, sin_a)

        self._is_executed = True
        return True

    def undo(self) -> bool:
        for snapshot in self._snapshots:
            snapshot.restore_to(self.contours)
        self._is_executed = False
        return True

    def _rotate_path(self, path, cos_a: float, sin_a: float):
        from src.core.types import Point
        cx, cy = self.center_x, self.center_y
        new_points = []
        for p in path.points:
            # 平移到原点
            px, py = p.x - cx, p.y - cy
            # 旋转
            new_x = px * cos_a - py * sin_a + cx
            new_y = px * sin_a + py * cos_a + cy
            new_points.append(Point(new_x, new_y))
        path.points = new_points


class ScaleCommand(Command):
    """缩放命令"""

    def __init__(self, contours: List['Contour'], indices: List[int],
                 center_x: float, center_y: float,
                 scale_x: float, scale_y: float):
        super().__init__("缩放")
        self.contours = contours
        self.indices = list(indices)
        self.center_x = center_x
        self.center_y = center_y
        self.scale_x = scale_x
        self.scale_y = scale_y

        # 保存原始状态
        self._snapshots = [
            ContourSnapshot.from_contour(idx, contours[idx])
            for idx in indices if 0 <= idx < len(contours)
        ]

    def execute(self) -> bool:
        from src.core.types import Point

        for idx in self.indices:
            if 0 <= idx < len(self.contours):
                contour = self.contours[idx]
                self._scale_path(contour.outer)
                for hole in contour.holes:
                    self._scale_path(hole)

        self._is_executed = True
        return True

    def undo(self) -> bool:
        for snapshot in self._snapshots:
            snapshot.restore_to(self.contours)
        self._is_executed = False
        return True

    def _scale_path(self, path):
        from src.core.types import Point
        cx, cy = self.center_x, self.center_y
        new_points = []
        for p in path.points:
            new_x = cx + (p.x - cx) * self.scale_x
            new_y = cy + (p.y - cy) * self.scale_y
            new_points.append(Point(new_x, new_y))
        path.points = new_points


class MirrorCommand(Command):
    """镜像命令"""

    def __init__(self, contours: List['Contour'], indices: List[int],
                 center_x: float, center_y: float, axis: str):
        super().__init__(f"镜像 {axis.upper()}")
        self.contours = contours
        self.indices = list(indices)
        self.center_x = center_x
        self.center_y = center_y
        self.axis = axis  # 'x' or 'y'

    def execute(self) -> bool:
        self._apply_mirror()
        self._is_executed = True
        return True

    def undo(self) -> bool:
        # 镜像是自反操作，再次执行即可撤销
        self._apply_mirror()
        self._is_executed = False
        return True

    def _apply_mirror(self):
        from src.core.types import Point

        for idx in self.indices:
            if 0 <= idx < len(self.contours):
                contour = self.contours[idx]
                self._mirror_path(contour.outer)
                for hole in contour.holes:
                    self._mirror_path(hole)

    def _mirror_path(self, path):
        from src.core.types import Point
        new_points = []
        for p in path.points:
            if self.axis == 'x':
                new_x = 2 * self.center_x - p.x
                new_points.append(Point(new_x, p.y))
            else:  # 'y'
                new_y = 2 * self.center_y - p.y
                new_points.append(Point(p.x, new_y))
        path.points = new_points


class DeleteCommand(Command):
    """删除命令"""

    def __init__(self, contours: List['Contour'], indices: List[int]):
        super().__init__("删除")
        self.contours = contours
        self.indices = sorted(indices, reverse=True)  # 从后往前删除

        # 保存被删除的轮廓
        self._deleted = [
            (idx, deepcopy(contours[idx]))
            for idx in self.indices if 0 <= idx < len(contours)
        ]

    def execute(self) -> bool:
        for idx in self.indices:
            if 0 <= idx < len(self.contours):
                del self.contours[idx]
        self._is_executed = True
        return True

    def undo(self) -> bool:
        # 按原始顺序恢复
        for idx, contour in reversed(self._deleted):
            self.contours.insert(idx, deepcopy(contour))
        self._is_executed = False
        return True


class AddContoursCommand(Command):
    """添加轮廓命令"""

    def __init__(self, contours: List['Contour'], new_contours: List['Contour'],
                 description: str = "添加轮廓"):
        super().__init__(description)
        self.contours = contours
        self.new_contours = [deepcopy(c) for c in new_contours]
        self._added_count = 0

    def execute(self) -> bool:
        self._added_count = len(self.new_contours)
        self.contours.extend(deepcopy(self.new_contours))
        self._is_executed = True
        return True

    def undo(self) -> bool:
        for _ in range(self._added_count):
            if self.contours:
                self.contours.pop()
        self._is_executed = False
        return True


class ReplaceContoursCommand(Command):
    """替换所有轮廓命令（用于加载文件）"""

    def __init__(self, contours: List['Contour'], new_contours: List['Contour'],
                 description: str = "加载文件"):
        super().__init__(description)
        self.contours = contours
        self.new_contours = [deepcopy(c) for c in new_contours]
        self._old_contours = [deepcopy(c) for c in contours]

    def execute(self) -> bool:
        self.contours.clear()
        self.contours.extend(deepcopy(self.new_contours))
        self._is_executed = True
        return True

    def undo(self) -> bool:
        self.contours.clear()
        self.contours.extend(deepcopy(self._old_contours))
        self._is_executed = False
        return True


class ReplaceSelectedContoursCommand(Command):
    """替换选中轮廓命令（用于布尔运算等局部编辑）"""

    def __init__(
        self,
        contours: List['Contour'],
        indices: List[int],
        new_contours: List['Contour'],
        description: str = "替换轮廓",
        selection_callback: Optional[Callable[[List[int]], None]] = None,
        old_selection: Optional[List[int]] = None,
        new_selection: Optional[List[int]] = None,
    ):
        super().__init__(description)
        self.contours = contours
        self.indices = sorted(
            idx for idx in set(indices)
            if 0 <= idx < len(contours)
        )
        self.insert_at = self.indices[0] if self.indices else len(contours)
        self._old_contours = [contours[idx] for idx in self.indices]
        self._new_contours = [deepcopy(contour) for contour in new_contours]
        self._selection_callback = selection_callback
        self._old_selection = list(old_selection or self.indices)
        if new_selection is None:
            self._new_selection = list(
                range(self.insert_at, self.insert_at + len(self._new_contours))
            )
        else:
            self._new_selection = list(new_selection)

    def execute(self) -> bool:
        self._remove_old_contours()
        self._insert_new_contours()
        self._apply_selection(self._new_selection)
        self._is_executed = True
        return True

    def undo(self) -> bool:
        self._remove_new_contours()
        self._restore_old_contours()
        self._apply_selection(self._old_selection)
        self._is_executed = False
        return True

    def _remove_old_contours(self):
        for idx in reversed(self.indices):
            if 0 <= idx < len(self.contours):
                del self.contours[idx]

    def _insert_new_contours(self):
        for offset, contour in enumerate(self._new_contours):
            self.contours.insert(self.insert_at + offset, contour)

    def _remove_new_contours(self):
        for _ in range(len(self._new_contours)):
            if self.insert_at < len(self.contours):
                del self.contours[self.insert_at]

    def _restore_old_contours(self):
        for idx, contour in zip(self.indices, self._old_contours):
            self.contours.insert(idx, contour)

    def _apply_selection(self, indices: List[int]):
        if self._selection_callback is not None:
            self._selection_callback(indices)


class TransformCommand(Command):
    """通用变换命令（保存快照方式）"""

    def __init__(self, contours: List['Contour'], indices: List[int],
                 description: str = "变换"):
        super().__init__(description)
        self.contours = contours
        self.indices = list(indices)

        # 保存变换前的快照
        self._before_snapshots = [
            ContourSnapshot.from_contour(idx, contours[idx])
            for idx in indices if 0 <= idx < len(contours)
        ]
        self._after_snapshots: List[ContourSnapshot] = []

    def capture_after(self):
        """在变换完成后调用，捕获变换后的状态"""
        self._after_snapshots = [
            ContourSnapshot.from_contour(idx, self.contours[idx])
            for idx in self.indices if 0 <= idx < len(self.contours)
        ]

    def execute(self) -> bool:
        # 如果有 after 快照，恢复到 after 状态
        if self._after_snapshots:
            for snapshot in self._after_snapshots:
                snapshot.restore_to(self.contours)
        self._is_executed = True
        return True

    def undo(self) -> bool:
        for snapshot in self._before_snapshots:
            snapshot.restore_to(self.contours)
        self._is_executed = False
        return True
