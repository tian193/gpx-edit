# -*- coding: utf-8 -*-
"""
批量航点匹配对话框
功能: 批量匹配航点的GUI界面
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
import threading
import os

from ..core.batch_matcher import BatchMatcher


class BatchMatchDialog(tk.Toplevel):
    """批量航点匹配对话框"""

    def __init__(self, parent):
        super().__init__(parent)

        self.title("批量航点匹配")
        self.geometry("950x750")
        self.resizable(True, True)

        self.transient(parent)
        self.grab_set()

        # 变量
        self.baseline_path = tk.StringVar()
        self.source_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.threshold = tk.StringVar(value="100")
        self.prefix = tk.StringVar(value="")

        # 处理状态
        self.is_processing = False

        # 基线航点缓存
        self.baseline_waypoints = None

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
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=BOTH, expand=True)

        # ===== 文件设置区域 =====
        file_frame = ttk.LabelFrame(main_frame, text="文件设置", padding=10)
        file_frame.pack(fill=X, pady=(0, 10))

        ttk.Label(file_frame, text="基线GPX文件:").grid(row=0, column=0, sticky=W, pady=5)
        ttk.Entry(file_frame, textvariable=self.baseline_path, width=55).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="选择", command=self._select_baseline, bootstyle=INFO).grid(row=0, column=2, pady=5)

        ttk.Label(file_frame, text="源文件目录:").grid(row=1, column=0, sticky=W, pady=5)
        ttk.Entry(file_frame, textvariable=self.source_dir, width=55).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="选择", command=self._select_source_dir, bootstyle=INFO).grid(row=1, column=2, pady=5)

        ttk.Label(file_frame, text="输出目录:").grid(row=2, column=0, sticky=W, pady=5)
        ttk.Entry(file_frame, textvariable=self.output_dir, width=55).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="选择", command=self._select_output_dir, bootstyle=INFO).grid(row=2, column=2, pady=5)

        ttk.Label(file_frame, text="匹配距离(米):").grid(row=3, column=0, sticky=W, pady=5)
        ttk.Entry(file_frame, textvariable=self.threshold, width=15).grid(row=3, column=1, sticky=W, padx=5, pady=5)

        ttk.Label(file_frame, text="航点前缀(可选):").grid(row=4, column=0, sticky=W, pady=5)
        ttk.Entry(file_frame, textvariable=self.prefix, width=15).grid(row=4, column=1, sticky=W, padx=5, pady=5)

        # ===== 预览区域 =====
        preview_frame = ttk.LabelFrame(main_frame, text="预览 (选择文件查看匹配结果)", padding=10)
        preview_frame.pack(fill=BOTH, expand=True, pady=(0, 10))

        # 预览控制栏
        preview_ctrl = ttk.Frame(preview_frame)
        preview_ctrl.pack(fill=X, pady=(0, 5))

        ttk.Label(preview_ctrl, text="选择源文件:").pack(side=LEFT, padx=(0, 5))
        self.file_combo = ttk.Combobox(preview_ctrl, state="readonly", width=35)
        self.file_combo.pack(side=LEFT, padx=(0, 10))

        ttk.Button(preview_ctrl, text="刷新文件列表", command=self._refresh_file_list, bootstyle=INFO).pack(side=LEFT, padx=3)
        ttk.Button(preview_ctrl, text="预览当前文件", command=self._preview_current_file, bootstyle=WARNING).pack(side=LEFT, padx=3)

        # 当前文件统计
        self.preview_stats = ttk.Label(preview_ctrl, text="", foreground="blue")
        self.preview_stats.pack(side=RIGHT, padx=5)

        # 预览树形列表
        tree_frame = ttk.Frame(preview_frame)
        tree_frame.pack(fill=BOTH, expand=True)

        columns = ("source_name", "lat", "lon", "matched_name", "distance", "status")
        self.preview_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=8)

        self.preview_tree.heading("source_name", text="源航点名称")
        self.preview_tree.heading("lat", text="纬度")
        self.preview_tree.heading("lon", text="经度")
        self.preview_tree.heading("matched_name", text="匹配基线航点")
        self.preview_tree.heading("distance", text="距离(米)")
        self.preview_tree.heading("status", text="状态")

        self.preview_tree.column("source_name", width=120)
        self.preview_tree.column("lat", width=80)
        self.preview_tree.column("lon", width=80)
        self.preview_tree.column("matched_name", width=120)
        self.preview_tree.column("distance", width=80)
        self.preview_tree.column("status", width=60)

        scrollbar = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.preview_tree.yview)
        self.preview_tree.configure(yscrollcommand=scrollbar.set)
        self.preview_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        # ===== 全局统计区域 =====
        global_frame = ttk.LabelFrame(main_frame, text="全局统计", padding=10)
        global_frame.pack(fill=X, pady=(0, 10))

        global_ctrl = ttk.Frame(global_frame)
        global_ctrl.pack(fill=X)

        ttk.Button(global_ctrl, text="扫描所有文件", command=self._scan_all_files, bootstyle=INFO).pack(side=LEFT, padx=5)

        self.global_stats = ttk.Label(global_ctrl, text="未扫描", foreground="darkgreen")
        self.global_stats.pack(side=LEFT, padx=20)

        # ===== 按钮和进度区域 =====
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=X, pady=10)

        self.start_btn = ttk.Button(btn_frame, text="开始批量处理", command=self._start_process, bootstyle=SUCCESS)
        self.start_btn.pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="关闭", command=self._on_close, bootstyle=SECONDARY).pack(side=RIGHT, padx=5)

        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=X)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=X, pady=(0, 5))

        self.progress_label = ttk.Label(progress_frame, text="就绪")
        self.progress_label.pack(fill=X)

    def _select_baseline(self):
        """选择基线文件"""
        filetypes = [("GPX文件", "*.gpx"), ("所有文件", "*.*")]
        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            self.baseline_path.set(path)
            self.baseline_waypoints = None

    def _select_source_dir(self):
        """选择源文件目录"""
        path = filedialog.askdirectory()
        if path:
            self.source_dir.set(path)
            self._refresh_file_list()

    def _select_output_dir(self):
        """选择输出目录"""
        path = filedialog.askdirectory()
        if path:
            self.output_dir.set(path)

    def _refresh_file_list(self):
        """刷新源文件列表"""
        source_dir = self.source_dir.get()
        if not source_dir or not os.path.isdir(source_dir):
            return
        gpx_files = [f for f in os.listdir(source_dir) if f.lower().endswith('.gpx')]
        self.file_combo['values'] = gpx_files
        if gpx_files:
            self.file_combo.current(0)

    def _load_baseline(self):
        """加载基线航点"""
        if self.baseline_waypoints is not None:
            return True
        baseline_path = self.baseline_path.get()
        if not baseline_path:
            messagebox.showwarning("提示", "请先选择基线GPX文件")
            return False
        try:
            self.baseline_waypoints = BatchMatcher.load_baseline(baseline_path)
            return True
        except Exception as e:
            messagebox.showerror("错误", f"加载基线文件失败:\n{e}")
            return False

    def _preview_current_file(self):
        """预览当前选中的文件"""
        if not self._load_baseline():
            return

        filename = self.file_combo.get()
        if not filename:
            messagebox.showwarning("提示", "请先选择源文件")
            return

        source_path = os.path.join(self.source_dir.get(), filename)

        try:
            threshold = float(self.threshold.get())
        except ValueError:
            messagebox.showwarning("提示", "请输入有效的距离阈值")
            return

        preview = BatchMatcher.preview_file(source_path, self.baseline_waypoints, threshold)

        # 清空并填充树形列表
        for item in self.preview_tree.get_children():
            self.preview_tree.delete(item)

        for wp in preview.waypoints:
            tags = ("keep",) if wp.status == "保留" else ("remove",)
            self.preview_tree.insert("", END, values=(
                wp.source_name,
                f"{wp.source_lat:.6f}",
                f"{wp.source_lon:.6f}",
                wp.matched_name,
                wp.distance,
                wp.status
            ), tags=tags)

        self.preview_tree.tag_configure("keep", background="#d4edda")
        self.preview_tree.tag_configure("remove", background="#f8d7da")

        self.preview_stats.config(
            text=f"当前文件: 匹配 {preview.matched} | 删除 {preview.removed} | 总计 {preview.matched + preview.removed}"
        )

    def _scan_all_files(self):
        """扫描所有源文件，显示全局统计"""
        if not self._load_baseline():
            return

        source_dir = self.source_dir.get()
        if not source_dir or not os.path.isdir(source_dir):
            messagebox.showwarning("提示", "请先选择源文件目录")
            return

        try:
            threshold = float(self.threshold.get())
        except ValueError:
            messagebox.showwarning("提示", "请输入有效的距离阈值")
            return

        gpx_files = [f for f in os.listdir(source_dir) if f.lower().endswith('.gpx')]
        if not gpx_files:
            messagebox.showinfo("提示", "源目录中没有GPX文件")
            return

        self.global_stats.config(text="扫描中...", foreground="orange")
        self.update()

        total_files = len(gpx_files)
        total_waypoints = 0
        total_matched = 0
        total_removed = 0

        for filename in gpx_files:
            source_path = os.path.join(source_dir, filename)
            preview = BatchMatcher.preview_file(source_path, self.baseline_waypoints, threshold)
            total_waypoints += preview.matched + preview.removed
            total_matched += preview.matched
            total_removed += preview.removed

        self.global_stats.config(
            text=f"文件总数: {total_files} | 航点总数: {total_waypoints} | 匹配: {total_matched} | 删除: {total_removed}",
            foreground="darkgreen"
        )

    def _validate_inputs(self) -> bool:
        """验证输入"""
        if not self.baseline_path.get():
            messagebox.showwarning("提示", "请选择基线GPX文件")
            return False
        if not self.source_dir.get():
            messagebox.showwarning("提示", "请选择源文件目录")
            return False
        if not self.output_dir.get():
            messagebox.showwarning("提示", "请选择输出目录")
            return False
        try:
            threshold = float(self.threshold.get())
            if threshold <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("提示", "请输入有效的距离阈值（正数）")
            return False
        return True

    def _start_process(self):
        """开始处理"""
        if self.is_processing:
            return
        if not self._validate_inputs():
            return

        self.is_processing = True
        self.start_btn.config(state=DISABLED)
        self.progress_var.set(0)

        thread = threading.Thread(target=self._process_thread, daemon=True)
        thread.start()

    def _process_thread(self):
        """处理线程"""
        try:
            threshold = float(self.threshold.get())
            prefix = self.prefix.get()

            def update_progress(filename, current, total):
                progress = (current / total) * 100
                self.after(0, self._update_progress_ui, filename, progress, current, total)

            result = BatchMatcher.batch_process(
                self.baseline_path.get(),
                self.source_dir.get(),
                self.output_dir.get(),
                threshold,
                prefix=prefix,
                callback=update_progress
            )

            self.after(0, self._show_result, result)

        except Exception as e:
            self.after(0, self._show_error, str(e))

        finally:
            self.after(0, self._process_complete)

    def _update_progress_ui(self, filename: str, progress: float, current: int, total: int):
        """更新进度UI"""
        self.progress_var.set(progress)
        self.progress_label.config(text=f"处理中: {filename} ({current}/{total})")

    def _show_result(self, result):
        """显示处理结果"""
        msg = (
            f"处理完成!\n\n"
            f"处理文件数: {result.processed_files}\n"
            f"失败文件数: {result.failed_files}\n"
            f"匹配航点数: {result.total_matched}\n"
            f"删除航点数: {result.total_removed}"
        )
        messagebox.showinfo("处理结果", msg)
        self.progress_label.config(text="处理完成")

    def _show_error(self, error_msg):
        """显示错误"""
        messagebox.showerror("错误", f"处理过程中发生错误:\n{error_msg}")
        self.progress_label.config(text="处理失败")

    def _process_complete(self):
        """处理完成"""
        self.is_processing = False
        self.start_btn.config(state=NORMAL)

    def _on_close(self):
        """关闭对话框"""
        if self.is_processing:
            if messagebox.askyesno("确认", "正在处理中，确定要关闭吗？"):
                self.destroy()
        else:
            self.destroy()
