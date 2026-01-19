"""
撤销/重做管理器单元测试
"""

import pytest
from copy import deepcopy

from src.core.types import Point, Path, Contour, PathType
from src.business.undo_manager import (
    UndoManager, Command, CompositeCommand,
    MoveCommand, RotateCommand, ScaleCommand, MirrorCommand,
    DeleteCommand, AddContoursCommand, ReplaceContoursCommand,
    TransformCommand
)


def create_test_contour(x_offset: float = 0, y_offset: float = 0) -> Contour:
    """创建测试用轮廓"""
    points = [
        Point(0 + x_offset, 0 + y_offset),
        Point(100 + x_offset, 0 + y_offset),
        Point(100 + x_offset, 100 + y_offset),
        Point(0 + x_offset, 100 + y_offset),
    ]
    outer = Path(points=points, path_type=PathType.OUTER)
    return Contour(outer=outer)


class TestUndoManager:
    """UndoManager 基础功能测试"""

    def test_initial_state(self):
        """测试初始状态"""
        manager = UndoManager()
        assert not manager.can_undo
        assert not manager.can_redo
        assert not manager.is_modified

    def test_push_command(self):
        """测试推送命令"""
        contours = [create_test_contour()]
        manager = UndoManager()

        cmd = MoveCommand(contours, [0], 10, 20)
        manager.push(cmd)

        assert manager.can_undo
        assert not manager.can_redo
        assert manager.is_modified

    def test_undo(self):
        """测试撤销操作"""
        contours = [create_test_contour()]
        original_x = contours[0].outer.points[0].x
        manager = UndoManager()

        # 移动轮廓
        cmd = MoveCommand(contours, [0], 50, 50)
        manager.push(cmd)

        # 验证移动后的位置
        assert contours[0].outer.points[0].x == original_x + 50

        # 撤销
        assert manager.undo()

        # 验证回到原位
        assert contours[0].outer.points[0].x == original_x
        assert not manager.can_undo
        assert manager.can_redo

    def test_redo(self):
        """测试重做操作"""
        contours = [create_test_contour()]
        original_x = contours[0].outer.points[0].x
        manager = UndoManager()

        # 移动轮廓
        cmd = MoveCommand(contours, [0], 50, 50)
        manager.push(cmd)

        # 撤销
        manager.undo()
        assert contours[0].outer.points[0].x == original_x

        # 重做
        assert manager.redo()
        assert contours[0].outer.points[0].x == original_x + 50

    def test_clear_redo_on_new_action(self):
        """测试新操作清空重做栈"""
        contours = [create_test_contour()]
        manager = UndoManager()

        # 执行两次移动
        manager.push(MoveCommand(contours, [0], 10, 0))
        manager.push(MoveCommand(contours, [0], 10, 0))

        # 撤销一次
        manager.undo()
        assert manager.can_redo

        # 执行新操作
        manager.push(MoveCommand(contours, [0], 0, 10))

        # 重做栈应该被清空
        assert not manager.can_redo

    def test_max_undo_levels(self):
        """测试最大撤销层数限制"""
        contours = [create_test_contour(), create_test_contour(100, 0)]
        manager = UndoManager(max_undo_levels=5)

        # 推送超过限制的命令（使用不同索引避免合并）
        for i in range(10):
            # 交替操作不同的轮廓，避免命令合并
            manager.push(MoveCommand(contours, [i % 2], 1, 0))

        # 只能撤销 5 次
        count = 0
        while manager.can_undo:
            manager.undo()
            count += 1

        assert count == 5


class TestMoveCommand:
    """移动命令测试"""

    def test_execute(self):
        """测试执行移动"""
        contours = [create_test_contour()]
        original = deepcopy(contours[0].outer.points[0])

        cmd = MoveCommand(contours, [0], 25.5, 30.5)
        cmd.execute()

        assert contours[0].outer.points[0].x == original.x + 25.5
        assert contours[0].outer.points[0].y == original.y + 30.5

    def test_undo(self):
        """测试撤销移动"""
        contours = [create_test_contour()]
        original = deepcopy(contours[0].outer.points[0])

        cmd = MoveCommand(contours, [0], 25, 30)
        cmd.execute()
        cmd.undo()

        assert abs(contours[0].outer.points[0].x - original.x) < 0.001
        assert abs(contours[0].outer.points[0].y - original.y) < 0.001

    def test_merge(self):
        """测试移动命令合并"""
        contours = [create_test_contour()]

        cmd1 = MoveCommand(contours, [0], 10, 20)
        cmd2 = MoveCommand(contours, [0], 5, 10)

        merged = cmd1.merge_with(cmd2)
        assert merged is not None
        assert merged.dx == 15
        assert merged.dy == 30

    def test_no_merge_different_indices(self):
        """测试不同索引不合并"""
        contours = [create_test_contour(), create_test_contour()]

        cmd1 = MoveCommand(contours, [0], 10, 20)
        cmd2 = MoveCommand(contours, [1], 5, 10)

        merged = cmd1.merge_with(cmd2)
        assert merged is None


class TestMirrorCommand:
    """镜像命令测试"""

    def test_mirror_x(self):
        """测试 X 轴镜像"""
        contours = [create_test_contour()]  # 点在 (0,0) 到 (100,100)
        center_x = 50  # 中心点 x

        cmd = MirrorCommand(contours, [0], center_x, 50, 'x')
        cmd.execute()

        # 原来 x=0 的点应该变成 x=100
        assert contours[0].outer.points[0].x == 100
        # 原来 x=100 的点应该变成 x=0
        assert contours[0].outer.points[1].x == 0

    def test_mirror_y(self):
        """测试 Y 轴镜像"""
        contours = [create_test_contour()]
        center_y = 50

        cmd = MirrorCommand(contours, [0], 50, center_y, 'y')
        cmd.execute()

        # 原来 y=0 的点应该变成 y=100
        assert contours[0].outer.points[0].y == 100

    def test_mirror_undo(self):
        """测试镜像撤销（镜像是自反的）"""
        contours = [create_test_contour()]
        original_points = deepcopy(contours[0].outer.points)

        cmd = MirrorCommand(contours, [0], 50, 50, 'x')
        cmd.execute()
        cmd.undo()

        for i, p in enumerate(contours[0].outer.points):
            assert abs(p.x - original_points[i].x) < 0.001
            assert abs(p.y - original_points[i].y) < 0.001


class TestDeleteCommand:
    """删除命令测试"""

    def test_delete_single(self):
        """测试删除单个轮廓"""
        contours = [create_test_contour(), create_test_contour(200, 0)]
        assert len(contours) == 2

        cmd = DeleteCommand(contours, [0])
        cmd.execute()

        assert len(contours) == 1

    def test_delete_undo(self):
        """测试删除撤销"""
        contours = [create_test_contour(), create_test_contour(200, 0)]

        cmd = DeleteCommand(contours, [0])
        cmd.execute()
        assert len(contours) == 1

        cmd.undo()
        assert len(contours) == 2

    def test_delete_multiple(self):
        """测试删除多个轮廓"""
        contours = [
            create_test_contour(0, 0),
            create_test_contour(200, 0),
            create_test_contour(400, 0)
        ]

        cmd = DeleteCommand(contours, [0, 2])
        cmd.execute()

        assert len(contours) == 1


class TestCompositeCommand:
    """复合命令测试"""

    def test_execute_all(self):
        """测试执行所有子命令"""
        contours = [create_test_contour()]
        original = deepcopy(contours[0].outer.points[0])

        commands = [
            MoveCommand(contours, [0], 10, 0),
            MoveCommand(contours, [0], 0, 10),
        ]
        composite = CompositeCommand(commands, "移动两次")
        composite.execute()

        assert contours[0].outer.points[0].x == original.x + 10
        assert contours[0].outer.points[0].y == original.y + 10

    def test_undo_all(self):
        """测试撤销所有子命令"""
        contours = [create_test_contour()]
        original = deepcopy(contours[0].outer.points[0])

        commands = [
            MoveCommand(contours, [0], 10, 0),
            MoveCommand(contours, [0], 0, 10),
        ]
        composite = CompositeCommand(commands, "移动两次")
        composite.execute()
        composite.undo()

        assert abs(contours[0].outer.points[0].x - original.x) < 0.001
        assert abs(contours[0].outer.points[0].y - original.y) < 0.001


class TestBatchOperations:
    """批量操作测试"""

    def test_batch_operations(self):
        """测试批量操作"""
        contours = [create_test_contour()]
        manager = UndoManager()

        manager.begin_batch("批量移动")
        manager.push(MoveCommand(contours, [0], 10, 0))
        manager.push(MoveCommand(contours, [0], 0, 10))
        manager.end_batch()

        # 只应该有一个可撤销的操作
        assert manager.can_undo

        manager.undo()
        assert not manager.can_undo  # 两个移动一起被撤销


class TestReplaceContoursCommand:
    """替换轮廓命令测试"""

    def test_replace(self):
        """测试替换所有轮廓"""
        contours = [create_test_contour()]
        new_contours = [create_test_contour(100, 0), create_test_contour(200, 0)]

        cmd = ReplaceContoursCommand(contours, new_contours, "加载文件")
        cmd.execute()

        assert len(contours) == 2
        assert contours[0].outer.points[0].x == 100

    def test_replace_undo(self):
        """测试替换撤销"""
        contours = [create_test_contour()]
        original_x = contours[0].outer.points[0].x

        new_contours = [create_test_contour(100, 0)]

        cmd = ReplaceContoursCommand(contours, new_contours, "加载文件")
        cmd.execute()
        cmd.undo()

        assert len(contours) == 1
        assert abs(contours[0].outer.points[0].x - original_x) < 0.001


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
