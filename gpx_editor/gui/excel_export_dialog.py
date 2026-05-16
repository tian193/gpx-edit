# -*- coding: utf-8 -*-
"""
航点Excel导出对话框
功能: 选择导出属性和航点，导出为Excel文件
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
import os
import subprocess
import platform
from collections import OrderedDict

from ..core.excel_exporter import ExcelExporter, FIELD_CONFIG


class ExcelExportDialog(tk.Toplevel):
    """航点Excel导出对话框"""

    def __init__(self, parent, initial_file=None):
        """
        初始化对话框
        Args:
            parent: 父窗口
            initial_file: 初始加载的GPX文件路径（可选）
        """
        super().__init__(parent)

        self.title("导出航点到Excel")
        self.geometry("800x600")
        self.resizable(True, True)

        self.transient(parent)
        self.grab_set()

        # 字段勾选变量
        self.field_vars = {}
        for field_code, field_name in FIELD_CONFIG.items():
            self.field_vars[field_code] = tk.BooleanVar(value=True)

        # 文件数据存储: {文件路径: [waypoint_info, ...]}
        self.file_data = OrderedDict()

        self._create_widgets()
        self._center_window()

        # 自动加载初始文件
        if initial_file and os.path.exists(initial_file):
            self._load_gpx_file(initial_file)

    def _load_gpx_file(self, file_path):
        """加载单个GPX文件"""
        try:
            import gpxpy
            with open(file_path, 'r', encoding='utf-8') as f:
                gpx = gpxpy.parse(f)

            waypoints = []
            for wp in gpx.waypoints:
                waypoints.append({
                    'waypoint': wp,
                    'checked': tk.BooleanVar(value=True),
                    'file_path': file_path
                })

            self.file_data[file_path] = waypoints
            self._add_file_to_tree(file_path, waypoints)
        except Exception as e:
            messagebox.showerror("错误", f"加载文件失败:\n{file_path}\n{e}")
        finally:
            self._update_export_state()

    def _add_file_to_tree(self, file_path, waypoints):
        """将文件及其航点添加到树形控件"""
        filename = os.path.basename(file_path)
        checked_count = sum(1 for wp in waypoints if wp['checked'].get())
        total_count = len(waypoints)

        # 插入文件节点
        file_node = self.tree.insert("", tk.END, text=f"▼ 📄 {filename} ({checked_count}/{total_count})",
                                      values=(file_path,), open=True)

        # 插入航点节点
        for i, wp_info in enumerate(waypoints, 1):
            wp = wp_info['waypoint']
            check_mark = "✓" if wp_info['checked'].get() else ""
            self.tree.insert(file_node, tk.END, values=(
                file_path,
                check_mark,
                i,
                wp.name or "",
                f"{wp.latitude:.6f}",
                f"{wp.longitude:.6f}"
            ))

    def _refresh_file_node(self, file_item, file_path):
        """刷新文件节点显示（更新勾选计数）"""
        waypoints = self.file_data.get(file_path, [])
        checked_count = sum(1 for wp in waypoints if wp['checked'].get())
        total_count = len(waypoints)
        filename = os.path.basename(file_path)

        # 更新文件节点文本
        self.tree.item(file_item, text=f"▼ 📄 {filename} ({checked_count}/{total_count})")

        # 更新子节点勾选状态
        children = self.tree.get_children(file_item)
        for i, child in enumerate(children):
            if i < len(waypoints):
                check_mark = "✓" if waypoints[i]['checked'].get() else ""
                values = list(self.tree.item(child, "values"))
                values[1] = check_mark
                self.tree.item(child, values=values)

    def _on_tree_click(self, event):
        """点击树形节点"""
        item = self.tree.identify_row(event.y)
        if not item:
            return

        if self.tree.parent(item) == "":
            # 点击的是文件节点 → 切换该文件所有航点
            self._toggle_file_waypoints(item)
        else:
            # 点击的是航点节点 → 切换单个航点
            self._toggle_single_waypoint(item)

    def _toggle_file_waypoints(self, file_item):
        """切换文件节点下所有航点的勾选状态"""
        file_path = self.tree.item(file_item, "values")[0]
        waypoints = self.file_data.get(file_path, [])

        # 计算新状态（如果全部选中则取消，否则全选）
        all_checked = all(wp['checked'].get() for wp in waypoints)
        new_state = not all_checked

        for wp_info in waypoints:
            wp_info['checked'].set(new_state)

        self._refresh_file_node(file_item, file_path)
        self._update_export_state()

    def _toggle_single_waypoint(self, wp_item):
        """切换单个航点的勾选状态"""
        parent = self.tree.parent(wp_item)
        file_path = self.tree.item(parent, "values")[0]

        # 获取航点索引
        children = self.tree.get_children(parent)
        idx = list(children).index(wp_item)

        waypoints = self.file_data.get(file_path, [])
        if 0 <= idx < len(waypoints):
            wp_info = waypoints[idx]
            wp_info['checked'].set(not wp_info['checked'].get())

            # 更新显示
            check_mark = "✓" if wp_info['checked'].get() else ""
            values = list(self.tree.item(wp_item, "values"))
            values[1] = check_mark
            self.tree.item(wp_item, values=values)

            self._refresh_file_node(parent, file_path)
            self._update_export_state()

    def _add_files(self):
        """添加GPX文件（支持多选）"""
        files = filedialog.askopenfilenames(
            filetypes=[("GPX文件", "*.gpx"), ("所有文件", "*.*")]
        )
        for f in files:
            if f not in self.file_data:
                self._load_gpx_file(f)

    def _add_folder(self):
        """添加文件夹，自动扫描所有GPX文件"""
        folder = filedialog.askdirectory()
        if folder:
            added_count = 0
            for f in os.listdir(folder):
                if f.lower().endswith('.gpx'):
                    full_path = os.path.join(folder, f)
                    if full_path not in self.file_data:
                        self._load_gpx_file(full_path)
                        added_count += 1
            if added_count == 0:
                messagebox.showinfo("提示", "文件夹中没有新的GPX文件")

    def _remove_selected(self):
        """移除选中的文件及其航点"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("提示", "请先选择要移除的文件或航点")
            return

        # 收集要移除的文件节点
        files_to_remove = set()
        for item in selected_items:
            parent = self.tree.parent(item)
            if parent == "":
                # 选中的是文件节点
                file_path = self.tree.item(item, "values")[0]
                files_to_remove.add(file_path)
            else:
                # 选中的是航点节点，获取其父文件节点
                file_path = self.tree.item(parent, "values")[0]
                files_to_remove.add(file_path)

        # 确认删除
        if len(files_to_remove) > 1:
            if not messagebox.askyesno("确认", f"确定要移除 {len(files_to_remove)} 个文件吗？"):
                return

        # 执行移除
        for file_path in files_to_remove:
            if file_path in self.file_data:
                del self.file_data[file_path]
            # 查找并删除树节点
            for child in self.tree.get_children(""):
                if self.tree.item(child, "values")[0] == file_path:
                    self.tree.delete(child)
                    break

        self._update_export_state()

    def _center_window(self):
        """窗口居中"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def _create_widgets(self):
        """创建界面组件"""
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=BOTH, expand=True)

        # 上半部分：左右分栏
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=BOTH, expand=True, pady=(0, 10))

        # ===== 左侧：属性选择 =====
        left_frame = ttk.LabelFrame(top_frame, text="选择导出属性", padding=10)
        left_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 5))

        # 全选按钮
        btn_row = ttk.Frame(left_frame)
        btn_row.pack(fill=X, pady=(0, 5))
        ttk.Button(btn_row, text="全选", command=self._select_all_fields, bootstyle=INFO).pack(side=LEFT, padx=2)
        ttk.Button(btn_row, text="取消全选", command=self._deselect_all_fields, bootstyle=INFO).pack(side=LEFT, padx=2)

        # 字段勾选框
        for field_code, field_name in FIELD_CONFIG.items():
            ttk.Checkbutton(
                left_frame,
                text=field_name,
                variable=self.field_vars[field_code],
                command=self._update_export_state
            ).pack(anchor=W, pady=2)

        # ===== 右侧：航点列表 =====
        right_frame = ttk.LabelFrame(top_frame, text="选择航点", padding=10)
        right_frame.pack(side=RIGHT, fill=BOTH, expand=True, padx=(5, 0))

        # 全选按钮（将在Task 6中重新实现）
        wp_btn_row = ttk.Frame(right_frame)
        wp_btn_row.pack(fill=X, pady=(0, 5))
        self.wp_select_all_btn = ttk.Button(wp_btn_row, text="全选", bootstyle=INFO, state=DISABLED)
        self.wp_select_all_btn.pack(side=LEFT, padx=2)
        self.wp_deselect_all_btn = ttk.Button(wp_btn_row, text="取消全选", bootstyle=INFO, state=DISABLED)
        self.wp_deselect_all_btn.pack(side=LEFT, padx=2)

        # 航点Treeview
        tree_frame = ttk.Frame(right_frame)
        tree_frame.pack(fill=BOTH, expand=True)

        columns = ("check", "index", "name", "lat", "lon")
        self.waypoint_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=12)
        self.waypoint_tree.heading("check", text="✓")
        self.waypoint_tree.heading("index", text="序号")
        self.waypoint_tree.heading("name", text="名称")
        self.waypoint_tree.heading("lat", text="纬度")
        self.waypoint_tree.heading("lon", text="经度")

        self.waypoint_tree.column("check", width=30, anchor=CENTER)
        self.waypoint_tree.column("index", width=50, anchor=CENTER)
        self.waypoint_tree.column("name", width=120)
        self.waypoint_tree.column("lat", width=80)
        self.waypoint_tree.column("lon", width=80)

        scrollbar = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.waypoint_tree.yview)
        self.waypoint_tree.configure(yscrollcommand=scrollbar.set)
        self.waypoint_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        # ===== 底部按钮 =====
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=X, pady=10)

        self.export_btn = ttk.Button(btn_frame, text="导出", command=self._do_export, bootstyle=SUCCESS)
        self.export_btn.pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self.destroy, bootstyle=SECONDARY).pack(side=RIGHT, padx=5)

        # 状态标签
        self.status_label = ttk.Label(btn_frame, text="", foreground="gray")
        self.status_label.pack(side=LEFT, padx=15)

    def _select_all_fields(self):
        """全选属性"""
        for var in self.field_vars.values():
            var.set(True)
        self._update_export_state()

    def _deselect_all_fields(self):
        """取消全选属性"""
        for var in self.field_vars.values():
            var.set(False)
        self._update_export_state()

    def _update_export_state(self):
        """更新导出按钮状态"""
        # 临时占位，将在Task 6中重新实现
        self.export_btn.config(state=DISABLED)
        self.status_label.config(text="请添加GPX文件")

    def _do_export(self):
        """执行导出"""
        # 临时占位，将在Task 6中重新实现
        messagebox.showinfo("提示", "功能开发中")

    def _open_file_directory(self, filepath):
        """打开文件所在目录"""
        directory = os.path.dirname(os.path.abspath(filepath))
        if platform.system() == "Windows":
            subprocess.Popen(["explorer", directory])
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", directory])
        else:
            subprocess.Popen(["xdg-open", directory])
