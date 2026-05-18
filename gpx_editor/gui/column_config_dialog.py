# -*- coding: utf-8 -*-
"""
列配置对话框
功能: 配置树形列表中显示的列、列顺序和列宽度
"""

import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
import json
import os
from typing import List, Optional


# 列定义
COLUMN_DEFINITIONS = [
    {"id": "type", "name": "类型", "width": 60, "category": "native"},
    {"id": "name", "name": "名称", "width": 120, "category": "native"},
    {"id": "lat", "name": "纬度", "width": 100, "category": "native"},
    {"id": "lon", "name": "经度", "width": 100, "category": "native"},
    {"id": "ele", "name": "海拔", "width": 80, "category": "native"},
    {"id": "time", "name": "时间", "width": 140, "category": "native"},
    {"id": "desc", "name": "描述", "width": 120, "category": "native"},
    {"id": "cmt", "name": "备注", "width": 100, "category": "native"},
    {"id": "sym", "name": "符号", "width": 80, "category": "native"},
    {"id": "source", "name": "来源", "width": 80, "category": "native"},
    {"id": "cgcs2000_x", "name": "CGCS2000 X", "width": 110, "category": "computed"},
    {"id": "cgcs2000_y", "name": "CGCS2000 Y", "width": 110, "category": "computed"},
]

DEFAULT_VISIBLE = ["type", "name", "lat", "lon"]
DEFAULT_ORDER = [col["id"] for col in COLUMN_DEFINITIONS]


class ColumnConfigManager:
    """列配置管理器，负责列配置的持久化存储"""

    def __init__(self, config_dir=None):
        """
        初始化列配置管理器
        Args:
            config_dir: 配置文件目录，默认为 ~/.gpx_editor
        """
        if config_dir is None:
            config_dir = os.path.join(os.path.expanduser("~"), ".gpx_editor")
        self._config_dir = config_dir
        self._config_file = os.path.join(config_dir, "column_config.json")
        self._config = self._load_config()

    def _load_config(self) -> dict:
        """从文件加载配置，如果文件不存在则使用默认配置"""
        if os.path.exists(self._config_file):
            try:
                with open(self._config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                # 验证配置结构完整性
                default = self._get_default_config()
                for key in default:
                    if key not in config:
                        config[key] = default[key]
                return config
            except (json.JSONDecodeError, IOError):
                return self._get_default_config()
        return self._get_default_config()

    def _get_default_config(self) -> dict:
        """获取默认配置"""
        column_widths = {col["id"]: col["width"] for col in COLUMN_DEFINITIONS}
        return {
            "visible_columns": list(DEFAULT_VISIBLE),
            "column_order": list(DEFAULT_ORDER),
            "column_widths": column_widths,
        }

    def save(self):
        """保存配置到文件"""
        os.makedirs(self._config_dir, exist_ok=True)
        with open(self._config_file, "w", encoding="utf-8") as f:
            json.dump(self._config, f, ensure_ascii=False, indent=2)

    def reset_to_default(self):
        """重置为默认配置"""
        self._config = self._get_default_config()

    @property
    def visible_columns(self) -> List[str]:
        """获取当前可见列ID列表"""
        return list(self._config["visible_columns"])

    @visible_columns.setter
    def visible_columns(self, value: List[str]):
        """设置可见列ID列表"""
        self._config["visible_columns"] = list(value)

    @property
    def column_order(self) -> List[str]:
        """获取列顺序"""
        return list(self._config["column_order"])

    @column_order.setter
    def column_order(self, value: List[str]):
        """设置列顺序"""
        self._config["column_order"] = list(value)

    def get_column_width(self, col_id: str) -> int:
        """获取指定列的宽度"""
        return self._config["column_widths"].get(col_id, 100)

    def set_column_width(self, col_id: str, width: int):
        """设置指定列的宽度"""
        self._config["column_widths"][col_id] = width

    def get_column_def(self, col_id: str) -> Optional[dict]:
        """根据列ID获取列定义"""
        for col in COLUMN_DEFINITIONS:
            if col["id"] == col_id:
                return col
        return None

    def get_ordered_visible_columns(self) -> List[dict]:
        """获取按顺序排列的可见列定义列表"""
        result = []
        for col_id in self._config["column_order"]:
            if col_id in self._config["visible_columns"]:
                col_def = self.get_column_def(col_id)
                if col_def:
                    result.append(col_def)
        return result


class ColumnConfigDialog:
    """列配置对话框，用于配置树形列表中显示的列"""

    def __init__(self, parent, config_manager: ColumnConfigManager):
        """
        初始化列配置对话框
        Args:
            parent: 父窗口
            config_manager: 列配置管理器
        """
        self._config_manager = config_manager
        self.result = False  # True表示点击了确定

        # 创建临时配置（对话框内的修改不影响原始配置）
        self._temp_visible = list(config_manager.visible_columns)
        self._temp_order = list(config_manager.column_order)

        # 创建对话框窗口
        self._dialog = tk.Toplevel(parent)
        self._dialog.title("GPX编辑器 - 列配置")
        self._dialog.geometry("700x500")
        self._dialog.resizable(True, True)
        self._dialog.transient(parent)
        self._dialog.grab_set()

        self._create_widgets()
        self._center_window()

        # 等待对话框关闭
        self._dialog.wait_window()

    def _center_window(self):
        """窗口居中"""
        self._dialog.update_idletasks()
        width = self._dialog.winfo_width()
        height = self._dialog.winfo_height()
        x = (self._dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self._dialog.winfo_screenheight() // 2) - (height // 2)
        self._dialog.geometry(f'{width}x{height}+{x}+{y}')

    def _get_display_name(self, col_def: dict) -> str:
        """获取列的显示名称，计算列添加[计算]前缀"""
        if col_def["category"] == "computed":
            return f"[计算] {col_def['name']}"
        return col_def["name"]

    def _get_available_columns(self) -> List[dict]:
        """获取当前不可见的列（可用列）"""
        return [col for col in COLUMN_DEFINITIONS if col["id"] not in self._temp_visible]

    def _create_widgets(self):
        """创建界面组件"""
        main_frame = ttk.Frame(self._dialog, padding=15)
        main_frame.pack(fill=BOTH, expand=True)

        # ===== 上半部分：左右分栏 =====
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=BOTH, expand=True, pady=(0, 10))

        # 左侧：可用列
        left_frame = ttk.LabelFrame(top_frame, text="可用列", padding=10)
        left_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 5))

        self._available_listbox = tk.Listbox(left_frame, height=15, selectmode=tk.EXTENDED)
        avail_scrollbar = ttk.Scrollbar(left_frame, orient=VERTICAL, command=self._available_listbox.yview)
        self._available_listbox.configure(yscrollcommand=avail_scrollbar.set)
        self._available_listbox.pack(side=LEFT, fill=BOTH, expand=True)
        avail_scrollbar.pack(side=RIGHT, fill=Y)
        self._available_listbox.bind("<Double-Button-1>", lambda e: self._add_selected())

        # 中间：操作按钮
        mid_frame = ttk.Frame(top_frame)
        mid_frame.pack(side=LEFT, fill=Y, padx=5)
        mid_frame_inner = ttk.Frame(mid_frame)
        mid_frame_inner.pack(expand=True)

        ttk.Button(mid_frame_inner, text="添加 >>", command=self._add_selected, bootstyle=INFO, width=10).pack(pady=3)
        ttk.Button(mid_frame_inner, text="<< 移除", command=self._remove_selected, bootstyle=INFO, width=10).pack(pady=3)
        ttk.Button(mid_frame_inner, text="全部添加", command=self._add_all, bootstyle=INFO, width=10).pack(pady=3)
        ttk.Button(mid_frame_inner, text="全部移除", command=self._remove_all, bootstyle=INFO, width=10).pack(pady=3)

        # 右侧：已选列
        right_frame = ttk.LabelFrame(top_frame, text="显示列", padding=10)
        right_frame.pack(side=RIGHT, fill=BOTH, expand=True, padx=(5, 0))

        right_inner = ttk.Frame(right_frame)
        right_inner.pack(fill=BOTH, expand=True)

        self._visible_listbox = tk.Listbox(right_inner, height=15, selectmode=tk.EXTENDED)
        vis_scrollbar = ttk.Scrollbar(right_inner, orient=VERTICAL, command=self._visible_listbox.yview)
        self._visible_listbox.configure(yscrollcommand=vis_scrollbar.set)
        self._visible_listbox.pack(side=LEFT, fill=BOTH, expand=True)
        vis_scrollbar.pack(side=RIGHT, fill=Y)
        self._visible_listbox.bind("<Double-Button-1>", lambda e: self._remove_selected())

        # 右侧：上下移动按钮
        btn_right_frame = ttk.Frame(right_frame)
        btn_right_frame.pack(fill=X, pady=(5, 0))
        ttk.Button(btn_right_frame, text="上移", command=self._move_up, bootstyle=INFO, width=8).pack(side=LEFT, padx=2)
        ttk.Button(btn_right_frame, text="下移", command=self._move_down, bootstyle=INFO, width=8).pack(side=LEFT, padx=2)

        # ===== 底部按钮 =====
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=X, pady=(10, 0))

        ttk.Button(bottom_frame, text="恢复默认", command=self._reset_to_default, bootstyle=WARNING).pack(side=LEFT, padx=5)
        ttk.Button(bottom_frame, text="确定", command=self._on_ok, bootstyle=SUCCESS, width=10).pack(side=RIGHT, padx=5)
        ttk.Button(bottom_frame, text="取消", command=self._on_cancel, bootstyle=SECONDARY, width=10).pack(side=RIGHT, padx=5)

        # 初始化列表显示
        self._refresh_lists()

    def _refresh_lists(self):
        """刷新左右两个列表的显示"""
        self._available_listbox.delete(0, tk.END)
        self._visible_listbox.delete(0, tk.END)

        # 填充可用列列表
        for col in self._get_available_columns():
            self._available_listbox.insert(tk.END, self._get_display_name(col))

        # 填充已选列列表（按顺序）
        for col_id in self._temp_order:
            if col_id in self._temp_visible:
                col_def = next((c for c in COLUMN_DEFINITIONS if c["id"] == col_id), None)
                if col_def:
                    self._visible_listbox.insert(tk.END, self._get_display_name(col_def))

    def _add_selected(self):
        """将选中的可用列添加到已选列"""
        selection = self._available_listbox.curselection()
        if not selection:
            return

        available = self._get_available_columns()
        for idx in selection:
            if idx < len(available):
                col = available[idx]
                if col["id"] not in self._temp_visible:
                    self._temp_visible.append(col["id"])
                    # 如果不在顺序列表中则添加到末尾
                    if col["id"] not in self._temp_order:
                        self._temp_order.append(col["id"])

        self._refresh_lists()

    def _remove_selected(self):
        """将选中的已选列移回可用列"""
        selection = self._visible_listbox.curselection()
        if not selection:
            return

        # 收集要移除的列ID
        visible_ids = [col_id for col_id in self._temp_order if col_id in self._temp_visible]
        ids_to_remove = []
        for idx in selection:
            if idx < len(visible_ids):
                ids_to_remove.append(visible_ids[idx])

        for col_id in ids_to_remove:
            if col_id in self._temp_visible:
                self._temp_visible.remove(col_id)

        self._refresh_lists()

    def _add_all(self):
        """添加所有可用列"""
        for col in COLUMN_DEFINITIONS:
            if col["id"] not in self._temp_visible:
                self._temp_visible.append(col["id"])
                if col["id"] not in self._temp_order:
                    self._temp_order.append(col["id"])
        self._refresh_lists()

    def _remove_all(self):
        """移除所有已选列"""
        self._temp_visible.clear()
        self._refresh_lists()

    def _move_up(self):
        """将选中的已选列上移"""
        selection = self._visible_listbox.curselection()
        if not selection or len(selection) != 1:
            return

        visible_ids = [col_id for col_id in self._temp_order if col_id in self._temp_visible]
        idx = selection[0]
        if idx <= 0 or idx >= len(visible_ids):
            return

        col_id = visible_ids[idx]
        # 在_temp_order中找到该列并上移
        order_idx = self._temp_order.index(col_id)
        # 找到前一个可见列在_order中的位置
        prev_col_id = visible_ids[idx - 1]
        prev_order_idx = self._temp_order.index(prev_col_id)

        # 交换位置
        self._temp_order[order_idx], self._temp_order[prev_order_idx] = (
            self._temp_order[prev_order_idx], self._temp_order[order_idx]
        )

        self._refresh_lists()
        # 保持选中状态
        self._visible_listbox.selection_set(idx - 1)

    def _move_down(self):
        """将选中的已选列下移"""
        selection = self._visible_listbox.curselection()
        if not selection or len(selection) != 1:
            return

        visible_ids = [col_id for col_id in self._temp_order if col_id in self._temp_visible]
        idx = selection[0]
        if idx < 0 or idx >= len(visible_ids) - 1:
            return

        col_id = visible_ids[idx]
        order_idx = self._temp_order.index(col_id)
        next_col_id = visible_ids[idx + 1]
        next_order_idx = self._temp_order.index(next_col_id)

        # 交换位置
        self._temp_order[order_idx], self._temp_order[next_order_idx] = (
            self._temp_order[next_order_idx], self._temp_order[order_idx]
        )

        self._refresh_lists()
        # 保持选中状态
        self._visible_listbox.selection_set(idx + 1)

    def _reset_to_default(self):
        """恢复默认配置"""
        self._temp_visible = list(DEFAULT_VISIBLE)
        self._temp_order = list(DEFAULT_ORDER)
        self._refresh_lists()

    def _on_ok(self):
        """点击确定按钮"""
        if not self._temp_visible:
            messagebox.showwarning("提示", "请至少选择一列显示", parent=self._dialog)
            return

        # 将临时配置写回config_manager
        self._config_manager.visible_columns = self._temp_visible
        self._config_manager.column_order = self._temp_order
        self._config_manager.save()

        self.result = True
        self._dialog.destroy()

    def _on_cancel(self):
        """点击取消按钮"""
        self.result = False
        self._dialog.destroy()
