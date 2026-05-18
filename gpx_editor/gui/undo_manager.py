# -*- coding: utf-8 -*-
"""
撤销/重做管理器
功能: 命令模式实现撤销和重做
"""


class UndoManager:
    """撤销/重做管理器"""

    def __init__(self, max_history=50):
        self._undo_stack = []
        self._redo_stack = []
        self._max_history = max_history

    def push(self, command):
        """推入一个命令
        command: dict, 包含:
            - type: 操作类型 ('add_waypoint', 'edit_waypoint', 'delete_waypoint',
                             'add_track', 'edit_track', 'delete_track')
            - data: 正向操作所需数据
            - reverse_data: 反向操作所需数据
        """
        self._undo_stack.append(command)
        if len(self._undo_stack) > self._max_history:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo(self):
        """撤销最后一个操作，返回命令"""
        if not self._undo_stack:
            return None
        cmd = self._undo_stack.pop()
        self._redo_stack.append(cmd)
        return cmd

    def redo(self):
        """重做最后一个撤销的操作，返回命令"""
        if not self._redo_stack:
            return None
        cmd = self._redo_stack.pop()
        self._undo_stack.append(cmd)
        return cmd

    def can_undo(self):
        """是否可以撤销"""
        return bool(self._undo_stack)

    def can_redo(self):
        """是否可以重做"""
        return bool(self._redo_stack)

    def clear(self):
        """清空所有历史"""
        self._undo_stack.clear()
        self._redo_stack.clear()
