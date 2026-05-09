# -*- coding: utf-8 -*-
"""
GPX属性编辑器对话框
功能: 解析、修改GPX文件属性，坐标移动
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
import threading
import os

from ..core.gpx_editor import GpxEditor


class GpxEditorDialog(tk.Toplevel):
    """GPX属性编辑器对话框"""

    def __init__(self, parent):
        super().__init__(parent)

        self.title("GPX属性编辑器")
        self.geometry("950x800")
        self.resizable(True, True)

        self.transient(parent)
        self.grab_set()

        # 变量
        self.file_path = tk.StringVar()
        self.dir_path = tk.StringVar()
        self.modify_output_dir = tk.StringVar()
        self.offset_output_dir = tk.StringVar()

        # 属性修改变量
        self.attr_type = tk.StringVar(value="waypoint")
        self.attr_name = tk.StringVar(value="name")
        self.new_value = tk.StringVar()
        self.modify_target = tk.StringVar(value="all")
        self.target_name = tk.StringVar()

        # 坐标移动变量
        self.x_offset = tk.StringVar(value="0")
        self.y_offset = tk.StringVar(value="0")
        self.offset_target = tk.StringVar(value="all")

        # 当前解析结果
        self.current_info = None

        self._create_widgets()
        self._center_window()

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
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=BOTH, expand=True)

        # ===== 文件选择区域 =====
        file_frame = ttk.LabelFrame(main_frame, text="文件选择", padding=5)
        file_frame.pack(fill=X, pady=(0, 5))

        ttk.Label(file_frame, text="单个文件:").grid(row=0, column=0, sticky=W, pady=2)
        ttk.Entry(file_frame, textvariable=self.file_path, width=50).grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(file_frame, text="选择", command=self._select_file, bootstyle=INFO).grid(row=0, column=2, pady=2)

        ttk.Label(file_frame, text="批量目录:").grid(row=1, column=0, sticky=W, pady=2)
        ttk.Entry(file_frame, textvariable=self.dir_path, width=50).grid(row=1, column=1, padx=5, pady=2)
        ttk.Button(file_frame, text="选择", command=self._select_dir, bootstyle=INFO).grid(row=1, column=2, pady=2)

        ttk.Button(file_frame, text="解析", command=self._parse_file, bootstyle=SUCCESS).grid(row=0, column=3, rowspan=2, padx=10, pady=2)

        # ===== 解析结果区域 =====
        result_frame = ttk.LabelFrame(main_frame, text="解析结果", padding=5)
        result_frame.pack(fill=BOTH, expand=True, pady=(0, 5))

        self.result_text = tk.Text(result_frame, height=12, state=DISABLED)
        scrollbar = ttk.Scrollbar(result_frame, orient=VERTICAL, command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=scrollbar.set)
        self.result_text.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        # ===== 修改属性区域 =====
        modify_frame = ttk.LabelFrame(main_frame, text="修改属性", padding=5)
        modify_frame.pack(fill=X, pady=(0, 5))

        # 第一行：属性类型和属性名
        row0 = ttk.Frame(modify_frame)
        row0.pack(fill=X, pady=2)

        ttk.Label(row0, text="属性类型:").pack(side=LEFT, padx=(0, 5))
        attr_type_combo = ttk.Combobox(row0, textvariable=self.attr_type, values=["file", "waypoint", "track"], state="readonly", width=10)
        attr_type_combo.pack(side=LEFT, padx=(0, 10))
        attr_type_combo.bind("<<ComboboxSelected>>", self._on_attr_type_changed)

        ttk.Label(row0, text="属性名:").pack(side=LEFT, padx=(0, 5))
        self.attr_name_combo = ttk.Combobox(row0, textvariable=self.attr_name, values=["name", "ele", "time", "cmt", "desc", "sym", "type"], state="readonly", width=10)
        self.attr_name_combo.pack(side=LEFT, padx=(0, 10))

        ttk.Label(row0, text="新值:").pack(side=LEFT, padx=(0, 5))
        ttk.Entry(row0, textvariable=self.new_value, width=20).pack(side=LEFT, padx=(0, 10))

        # 第二行：目标和输出目录
        row1 = ttk.Frame(modify_frame)
        row1.pack(fill=X, pady=2)

        ttk.Label(row1, text="目标:").pack(side=LEFT, padx=(0, 5))
        ttk.Radiobutton(row1, text="全部", variable=self.modify_target, value="all").pack(side=LEFT, padx=(0, 5))
        ttk.Radiobutton(row1, text="指定名称:", variable=self.modify_target, value="named").pack(side=LEFT, padx=(0, 5))
        ttk.Entry(row1, textvariable=self.target_name, width=15).pack(side=LEFT, padx=(0, 10))

        ttk.Label(row1, text="输出目录:").pack(side=LEFT, padx=(0, 5))
        ttk.Entry(row1, textvariable=self.modify_output_dir, width=20).pack(side=LEFT, padx=(0, 5))
        ttk.Button(row1, text="选择", command=self._select_modify_output, bootstyle=INFO).pack(side=LEFT, padx=(0, 10))

        # 第三行：按钮
        row2 = ttk.Frame(modify_frame)
        row2.pack(fill=X, pady=2)

        ttk.Button(row2, text="应用修改", command=self._apply_modify, bootstyle=WARNING).pack(side=LEFT, padx=5)
        ttk.Button(row2, text="批量应用到所有文件", command=self._batch_modify, bootstyle=DANGER).pack(side=LEFT, padx=5)

        # ===== 坐标移动区域 =====
        offset_frame = ttk.LabelFrame(main_frame, text="坐标移动", padding=5)
        offset_frame.pack(fill=X, pady=(0, 5))

        # 第一行：偏移量
        row3 = ttk.Frame(offset_frame)
        row3.pack(fill=X, pady=2)

        ttk.Label(row3, text="X偏移(米):").pack(side=LEFT, padx=(0, 5))
        ttk.Entry(row3, textvariable=self.x_offset, width=10).pack(side=LEFT, padx=(0, 5))
        ttk.Label(row3, text="(正=东, 负=西)").pack(side=LEFT, padx=(0, 15))

        ttk.Label(row3, text="Y偏移(米):").pack(side=LEFT, padx=(0, 5))
        ttk.Entry(row3, textvariable=self.y_offset, width=10).pack(side=LEFT, padx=(0, 5))
        ttk.Label(row3, text="(正=北, 负=南)").pack(side=LEFT, padx=(0, 15))

        ttk.Label(row3, text="目标:").pack(side=LEFT, padx=(0, 5))
        ttk.Radiobutton(row3, text="全部", variable=self.offset_target, value="all").pack(side=LEFT, padx=(0, 5))
        ttk.Radiobutton(row3, text="航点", variable=self.offset_target, value="waypoint").pack(side=LEFT, padx=(0, 5))
        ttk.Radiobutton(row3, text="航迹", variable=self.offset_target, value="track").pack(side=LEFT, padx=(0, 5))

        # 第二行：输出目录和按钮
        row4 = ttk.Frame(offset_frame)
        row4.pack(fill=X, pady=2)

        ttk.Label(row4, text="输出目录:").pack(side=LEFT, padx=(0, 5))
        ttk.Entry(row4, textvariable=self.offset_output_dir, width=20).pack(side=LEFT, padx=(0, 5))
        ttk.Button(row4, text="选择", command=self._select_offset_output, bootstyle=INFO).pack(side=LEFT, padx=(0, 10))

        ttk.Button(row4, text="应用移动", command=self._apply_offset, bootstyle=WARNING).pack(side=LEFT, padx=5)
        ttk.Button(row4, text="批量应用到所有文件", command=self._batch_offset, bootstyle=DANGER).pack(side=LEFT, padx=5)

        # ===== 关闭按钮 =====
        ttk.Button(main_frame, text="关闭", command=self.destroy, bootstyle=SECONDARY).pack(pady=5)

    def _on_attr_type_changed(self, event=None):
        """属性类型改变时更新属性名选项"""
        attr_type = self.attr_type.get()
        if attr_type == "file":
            self.attr_name_combo['values'] = ["version", "creator", "name", "description"]
            self.attr_name.set("name")
        elif attr_type == "waypoint":
            self.attr_name_combo['values'] = ["name", "ele", "time", "cmt", "desc", "sym", "type"]
            self.attr_name.set("name")
        elif attr_type == "track":
            self.attr_name_combo['values'] = ["name", "desc", "cmt", "type"]
            self.attr_name.set("name")

    def _select_file(self):
        """选择单个文件"""
        filetypes = [("GPX文件", "*.gpx"), ("所有文件", "*.*")]
        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            self.file_path.set(path)

    def _select_dir(self):
        """选择目录"""
        path = filedialog.askdirectory()
        if path:
            self.dir_path.set(path)

    def _select_modify_output(self):
        """选择修改输出目录"""
        path = filedialog.askdirectory()
        if path:
            self.modify_output_dir.set(path)

    def _select_offset_output(self):
        """选择偏移输出目录"""
        path = filedialog.askdirectory()
        if path:
            self.offset_output_dir.set(path)

    def _parse_file(self):
        """解析文件"""
        file_path = self.file_path.get()
        dir_path = self.dir_path.get()

        if file_path:
            # 解析单个文件
            try:
                info = GpxEditor.parse_file(file_path)
                self.current_info = info
                self._display_result([info])
            except Exception as e:
                messagebox.showerror("错误", f"解析失败: {e}")
        elif dir_path:
            # 批量解析目录
            try:
                gpx_files = [f for f in os.listdir(dir_path) if f.lower().endswith('.gpx')]
                if not gpx_files:
                    messagebox.showinfo("提示", "目录中没有GPX文件")
                    return

                results = []
                for filename in gpx_files[:20]:  # 最多显示20个
                    filepath = os.path.join(dir_path, filename)
                    info = GpxEditor.parse_file(filepath)
                    results.append(info)

                self.current_info = results[0] if results else None
                self._display_result(results)

                if len(gpx_files) > 20:
                    messagebox.showinfo("提示", f"目录中有{len(gpx_files)}个文件，仅显示前20个")
            except Exception as e:
                messagebox.showerror("错误", f"解析失败: {e}")
        else:
            messagebox.showwarning("提示", "请选择文件或目录")

    def _display_result(self, results):
        """显示解析结果"""
        self.result_text.config(state=NORMAL)
        self.result_text.delete(1.0, END)

        for info in results:
            self.result_text.insert(END, f"文件: {info.filename}\n")
            self.result_text.insert(END, f"  版本: {info.version} | 创建者: {info.creator}\n")

            if info.waypoints:
                self.result_text.insert(END, f"\n  航点 ({len(info.waypoints)}个):\n")
                for wp in info.waypoints:
                    self.result_text.insert(END, f"    [{wp.index}] {wp.name} | {wp.lat:.6f}, {wp.lon:.6f}\n")
                    self.result_text.insert(END, f"        ele={wp.ele} | cmt={wp.comment} | sym={wp.symbol}\n")

            if info.tracks:
                self.result_text.insert(END, f"\n  航迹 ({len(info.tracks)}个):\n")
                for trk in info.tracks:
                    self.result_text.insert(END, f"    [{trk.index}] {trk.name} | 航段: {trk.segment_count} | 点数: {trk.point_count}\n")

            self.result_text.insert(END, "\n" + "=" * 60 + "\n\n")

        self.result_text.config(state=DISABLED)

    def _apply_modify(self):
        """应用属性修改"""
        file_path = self.file_path.get()
        if not file_path:
            messagebox.showwarning("提示", "请先选择单个文件并解析")
            return

        output_dir = self.modify_output_dir.get()
        if not output_dir:
            messagebox.showwarning("提示", "请选择输出目录")
            return

        attr_type = self.attr_type.get()
        attr_name = self.attr_name.get()
        new_value = self.new_value.get()
        target = self.modify_target.get()
        target_name = self.target_name.get()

        if not new_value:
            messagebox.showwarning("提示", "请输入新值")
            return

        filename = os.path.basename(file_path)
        output_path = os.path.join(output_dir, filename)

        success, msg = GpxEditor.modify_attribute(
            file_path, output_path, attr_type, attr_name, new_value, target, target_name
        )

        if success:
            messagebox.showinfo("成功", msg)
        else:
            messagebox.showerror("错误", msg)

    def _batch_modify(self):
        """批量修改属性"""
        dir_path = self.dir_path.get()
        if not dir_path:
            messagebox.showwarning("提示", "请选择批量目录")
            return

        output_dir = self.modify_output_dir.get()
        if not output_dir:
            messagebox.showwarning("提示", "请选择输出目录")
            return

        attr_type = self.attr_type.get()
        attr_name = self.attr_name.get()
        new_value = self.new_value.get()
        target = self.modify_target.get()
        target_name = self.target_name.get()

        if not new_value:
            messagebox.showwarning("提示", "请输入新值")
            return

        gpx_files = [f for f in os.listdir(dir_path) if f.lower().endswith('.gpx')]
        if not gpx_files:
            messagebox.showinfo("提示", "目录中没有GPX文件")
            return

        success_count = 0
        fail_count = 0

        for filename in gpx_files:
            filepath = os.path.join(dir_path, filename)
            output_path = os.path.join(output_dir, filename)

            success, msg = GpxEditor.modify_attribute(
                filepath, output_path, attr_type, attr_name, new_value, target, target_name
            )

            if success:
                success_count += 1
            else:
                fail_count += 1

        messagebox.showinfo("完成", f"批量修改完成\n成功: {success_count}\n失败: {fail_count}")

    def _apply_offset(self):
        """应用坐标偏移"""
        file_path = self.file_path.get()
        if not file_path:
            messagebox.showwarning("提示", "请先选择单个文件并解析")
            return

        output_dir = self.offset_output_dir.get()
        if not output_dir:
            messagebox.showwarning("提示", "请选择输出目录")
            return

        try:
            x_meters = float(self.x_offset.get())
            y_meters = float(self.y_offset.get())
        except ValueError:
            messagebox.showwarning("提示", "请输入有效的偏移量")
            return

        target = self.offset_target.get()
        filename = os.path.basename(file_path)
        output_path = os.path.join(output_dir, filename)

        success, msg = GpxEditor.offset_file(file_path, output_path, x_meters, y_meters, target)

        if success:
            messagebox.showinfo("成功", msg)
        else:
            messagebox.showerror("错误", msg)

    def _batch_offset(self):
        """批量坐标偏移"""
        dir_path = self.dir_path.get()
        if not dir_path:
            messagebox.showwarning("提示", "请选择批量目录")
            return

        output_dir = self.offset_output_dir.get()
        if not output_dir:
            messagebox.showwarning("提示", "请选择输出目录")
            return

        try:
            x_meters = float(self.x_offset.get())
            y_meters = float(self.y_offset.get())
        except ValueError:
            messagebox.showwarning("提示", "请输入有效的偏移量")
            return

        target = self.offset_target.get()

        gpx_files = [f for f in os.listdir(dir_path) if f.lower().endswith('.gpx')]
        if not gpx_files:
            messagebox.showinfo("提示", "目录中没有GPX文件")
            return

        success_count = 0
        fail_count = 0

        for filename in gpx_files:
            filepath = os.path.join(dir_path, filename)
            output_path = os.path.join(output_dir, filename)

            success, msg = GpxEditor.offset_file(filepath, output_path, x_meters, y_meters, target)

            if success:
                success_count += 1
            else:
                fail_count += 1

        messagebox.showinfo("完成", f"批量偏移完成\n成功: {success_count}\n失败: {fail_count}")
