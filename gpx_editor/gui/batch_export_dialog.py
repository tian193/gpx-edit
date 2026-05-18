# -*- coding: utf-8 -*-
"""
批量导出对话框
功能: 批量导出GPX为TXT/GDB格式的GUI界面
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
import threading
import os

from ..core.exporter import TxtExporter, GdbExporter


class BatchExportDialog(tk.Toplevel):
    """批量导出对话框"""

    def __init__(self, parent, export_type="txt"):
        """
        初始化对话框
        Args:
            parent: 父窗口
            export_type: 导出类型，"txt" 或 "gdb"
        """
        super().__init__(parent)

        self.export_type = export_type
        self.title(f"批量导出{export_type.upper()}")
        self.geometry("600x400")
        self.resizable(True, True)

        self.transient(parent)
        self.grab_set()

        # 变量
        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()

        # 处理状态
        self.is_processing = False

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
        file_frame = ttk.LabelFrame(main_frame, text="目录设置", padding=10)
        file_frame.pack(fill=X, pady=(0, 10))

        ttk.Label(file_frame, text="输入目录:").grid(row=0, column=0, sticky=W, pady=5)
        ttk.Entry(file_frame, textvariable=self.input_dir, width=45).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="选择", command=self._select_input_dir, bootstyle=INFO).grid(row=0, column=2, pady=5)

        ttk.Label(file_frame, text="输出目录:").grid(row=1, column=0, sticky=W, pady=5)
        ttk.Entry(file_frame, textvariable=self.output_dir, width=45).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="选择", command=self._select_output_dir, bootstyle=INFO).grid(row=1, column=2, pady=5)

        # ===== 文件列表预览 =====
        list_frame = ttk.LabelFrame(main_frame, text="待导出文件", padding=10)
        list_frame.pack(fill=BOTH, expand=True, pady=(0, 10))

        # 文件列表
        self.file_listbox = tk.Listbox(list_frame, height=8)
        scrollbar = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.file_listbox.yview)
        self.file_listbox.configure(yscrollcommand=scrollbar.set)
        self.file_listbox.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        # 统计信息
        self.stats_label = ttk.Label(list_frame, text="未选择目录", foreground="gray")
        self.stats_label.pack(fill=X, pady=(5, 0))

        # ===== 按钮和进度区域 =====
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=X, pady=10)

        self.start_btn = ttk.Button(btn_frame, text="开始导出", command=self._start_export, bootstyle=SUCCESS)
        self.start_btn.pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="刷新列表", command=self._refresh_file_list, bootstyle=INFO).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="关闭", command=self._on_close, bootstyle=SECONDARY).pack(side=RIGHT, padx=5)

        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=X)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=X, pady=(0, 5))

        self.progress_label = ttk.Label(progress_frame, text="就绪")
        self.progress_label.pack(fill=X)

    def _select_input_dir(self):
        """选择输入目录"""
        path = filedialog.askdirectory()
        if path:
            self.input_dir.set(path)
            self._refresh_file_list()

    def _select_output_dir(self):
        """选择输出目录"""
        path = filedialog.askdirectory()
        if path:
            self.output_dir.set(path)

    def _refresh_file_list(self):
        """刷新文件列表"""
        input_dir = self.input_dir.get()
        if not input_dir or not os.path.isdir(input_dir):
            self.stats_label.config(text="请选择有效的输入目录", foreground="gray")
            return

        gpx_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.gpx')]

        self.file_listbox.delete(0, tk.END)
        for f in gpx_files:
            self.file_listbox.insert(tk.END, f)

        self.stats_label.config(text=f"找到 {len(gpx_files)} 个GPX文件", foreground="blue")

    def _validate_inputs(self) -> bool:
        """验证输入"""
        if not self.input_dir.get():
            messagebox.showwarning("提示", "请选择输入目录")
            return False
        if not os.path.isdir(self.input_dir.get()):
            messagebox.showwarning("提示", "输入目录不存在")
            return False
        if not self.output_dir.get():
            messagebox.showwarning("提示", "请选择输出目录")
            return False
        if not os.path.isdir(self.output_dir.get()):
            messagebox.showwarning("提示", "输出目录不存在")
            return False
        return True

    def _start_export(self):
        """开始导出"""
        if self.is_processing:
            return
        if not self._validate_inputs():
            return

        self.is_processing = True
        self.start_btn.config(state=DISABLED)
        self.progress_var.set(0)

        thread = threading.Thread(target=self._export_thread, daemon=True)
        thread.start()

    def _export_thread(self):
        """导出线程"""
        try:
            input_dir = self.input_dir.get()
            output_dir = self.output_dir.get()

            # 获取GPX文件列表
            gpx_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.gpx')]
            total = len(gpx_files)

            if total == 0:
                self.after(0, lambda: messagebox.showinfo("提示", "输入目录中没有GPX文件"))
                return

            exported = []
            failed = []

            for i, filename in enumerate(gpx_files, 1):
                # 更新进度
                progress = (i / total) * 100
                self.after(0, self._update_progress_ui, filename, progress, i, total)

                input_path = os.path.join(input_dir, filename)

                try:
                    import gpxpy
                    with open(input_path, 'r', encoding='utf-8') as f:
                        gpx = gpxpy.parse(f)

                    if self.export_type == "txt":
                        output_path = os.path.join(output_dir, os.path.splitext(filename)[0] + '.txt')
                        TxtExporter.export(gpx, output_path)
                    else:
                        output_path = os.path.join(output_dir, os.path.splitext(filename)[0] + '.gdb')
                        GdbExporter.export(gpx, output_path)

                    exported.append(filename)
                except Exception as e:
                    failed.append((filename, str(e)))

            # 显示结果
            self.after(0, self._show_result, exported, failed)

        except Exception as e:
            self.after(0, self._show_error, str(e))

        finally:
            self.after(0, self._export_complete)

    def _update_progress_ui(self, filename: str, progress: float, current: int, total: int):
        """更新进度UI"""
        self.progress_var.set(progress)
        self.progress_label.config(text=f"导出中: {filename} ({current}/{total})")

    def _show_result(self, exported: list, failed: list):
        """显示导出结果"""
        msg = (
            f"导出完成!\n\n"
            f"成功: {len(exported)} 个文件\n"
            f"失败: {len(failed)} 个文件"
        )
        if failed:
            msg += "\n\n失败文件:\n"
            for filename, error in failed[:5]:  # 最多显示5个
                msg += f"  - {filename}: {error}\n"
            if len(failed) > 5:
                msg += f"  ... 还有 {len(failed) - 5} 个文件"

        messagebox.showinfo("导出结果", msg)
        self.progress_label.config(text="导出完成")

    def _show_error(self, error_msg):
        """显示错误"""
        messagebox.showerror("错误", f"导出过程中发生错误:\n{error_msg}")
        self.progress_label.config(text="导出失败")

    def _export_complete(self):
        """导出完成"""
        self.is_processing = False
        self.start_btn.config(state=NORMAL)

    def _on_close(self):
        """关闭对话框"""
        if self.is_processing:
            if messagebox.askyesno("确认", "正在导出中，确定要关闭吗？"):
                self.destroy()
        else:
            self.destroy()


class SingleExportDialog:
    """单文件导出处理类"""

    @staticmethod
    def export_txt(parent):
        """导出当前GPX为TXT"""
        # 检查是否有打开的文件
        if not hasattr(parent, 'current_file') or not parent.current_file:
            messagebox.showwarning("提示", "请先打开一个GPX文件")
            return

        # 选择输出文件
        filetypes = [("TXT文件", "*.txt"), ("所有文件", "*.*")]
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=filetypes,
            initialfile=os.path.splitext(os.path.basename(parent.current_file))[0] + '.txt'
        )
        if not filepath:
            return

        try:
            import gpxpy
            with open(parent.current_file, 'r', encoding='utf-8') as f:
                gpx = gpxpy.parse(f)

            TxtExporter.export(gpx, filepath)
            messagebox.showinfo("成功", f"已导出为TXT:\n{filepath}")
            parent.status_label.config(text="TXT导出完成")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败:\n{e}")

    @staticmethod
    def export_gdb(parent):
        """导出当前GPX为GDB"""
        # 检查是否有打开的文件
        if not hasattr(parent, 'current_file') or not parent.current_file:
            messagebox.showwarning("提示", "请先打开一个GPX文件")
            return

        # 选择输出文件
        filetypes = [("GDB文件", "*.gdb"), ("所有文件", "*.*")]
        filepath = filedialog.asksaveasfilename(
            defaultextension=".gdb",
            filetypes=filetypes,
            initialfile=os.path.splitext(os.path.basename(parent.current_file))[0] + '.gdb'
        )
        if not filepath:
            return

        try:
            import gpxpy
            with open(parent.current_file, 'r', encoding='utf-8') as f:
                gpx = gpxpy.parse(f)

            GdbExporter.export(gpx, filepath)
            messagebox.showinfo("成功", f"已导出为GDB:\n{filepath}")
            parent.status_label.config(text="GDB导出完成")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败:\n{e}")
