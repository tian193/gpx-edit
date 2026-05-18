# 导出航点到Excel 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增功能，将GPX文件中的航点属性导出为Excel文件，支持选择导出字段和航点。

**Architecture:** 新增两个文件：`excel_exporter.py`（核心导出逻辑）和 `excel_export_dialog.py`（GUI对话框）。在 `main_window.py` 工具菜单中添加入口。

**Tech Stack:** Python 3.10+ / openpyxl / tkinter + ttkbootstrap

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `gpx_editor/core/excel_exporter.py` | 新建 | 核心导出逻辑，接收航点列表和字段列表，生成Excel |
| `gpx_editor/gui/excel_export_dialog.py` | 新建 | 导出对话框，属性勾选 + 航点勾选 |
| `gpx_editor/gui/main_window.py:96-103` | 修改 | 工具菜单添加入口 |
| `tests/test_excel_exporter.py` | 新建 | 核心导出逻辑的单元测试 |

---

### Task 1: 核心导出逻辑 + 测试

**Files:**
- Create: `gpx_editor/core/excel_exporter.py`
- Create: `tests/test_excel_exporter.py`

- [ ] **Step 1: 编写单元测试**

```python
# tests/test_excel_exporter.py
# -*- coding: utf-8 -*-
"""Excel导出模块测试"""

import os
import tempfile
import pytest
import gpxpy.gpx
from openpyxl import load_workbook
from gpx_editor.core.excel_exporter import ExcelExporter


def _make_waypoint(name, lat, lon, ele=None, desc=None, time=None):
    """创建测试用航点"""
    wp = gpxpy.gpx.GPXWaypoint(latitude=lat, longitude=lon, elevation=ele, name=name, description=desc)
    if time:
        from datetime import datetime
        wp.time = datetime(2026, 5, 16, 10, 30, 0)
    return wp


class TestExcelExporter:
    """ExcelExporter 测试"""

    def test_export_all_fields(self):
        """测试导出全部字段"""
        waypoints = [_make_waypoint("航点A", 39.9, 116.3, ele=100.5, desc="测试描述")]
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            path = f.name
        try:
            fields = ["name", "latitude", "longitude", "elevation", "description", "time"]
            result = ExcelExporter.export(waypoints, fields, path)
            assert result is True
            wb = load_workbook(path)
            ws = wb.active
            # 表头
            headers = [cell.value for cell in ws[1]]
            assert headers == ["名称", "纬度", "经度", "海拔", "描述", "时间"]
            # 数据
            assert ws.cell(2, 1).value == "航点A"
            assert ws.cell(2, 2).value == 39.9
            assert ws.cell(2, 3).value == 116.3
            assert ws.cell(2, 4).value == 100.5
            assert ws.cell(2, 5).value == "测试描述"
            wb.close()
        finally:
            os.unlink(path)

    def test_export_selected_fields(self):
        """测试导出部分字段"""
        waypoints = [_make_waypoint("航点A", 39.9, 116.3)]
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            path = f.name
        try:
            fields = ["name", "latitude", "longitude"]
            result = ExcelExporter.export(waypoints, fields, path)
            assert result is True
            wb = load_workbook(path)
            ws = wb.active
            headers = [cell.value for cell in ws[1]]
            assert headers == ["名称", "纬度", "经度"]
            assert ws.cell(2, 1).value == "航点A"
            wb.close()
        finally:
            os.unlink(path)

    def test_export_empty_values(self):
        """测试空值处理"""
        waypoints = [_make_waypoint("航点A", 39.9, 116.3)]
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            path = f.name
        try:
            fields = ["name", "elevation", "description"]
            result = ExcelExporter.export(waypoints, fields, path)
            assert result is True
            wb = load_workbook(path)
            ws = wb.active
            assert ws.cell(2, 1).value == "航点A"
            assert ws.cell(2, 2).value is None  # 海拔为空
            assert ws.cell(2, 3).value is None  # 描述为空
            wb.close()
        finally:
            os.unlink(path)

    def test_export_multiple_waypoints(self):
        """测试多条航点导出"""
        waypoints = [
            _make_waypoint("航点A", 39.9, 116.3),
            _make_waypoint("航点B", 40.0, 116.4),
            _make_waypoint("航点C", 40.1, 116.5),
        ]
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            path = f.name
        try:
            fields = ["name", "latitude", "longitude"]
            result = ExcelExporter.export(waypoints, fields, path)
            assert result is True
            wb = load_workbook(path)
            ws = wb.active
            # 1行表头 + 3行数据
            assert ws.max_row == 4
            assert ws.cell(2, 1).value == "航点A"
            assert ws.cell(3, 1).value == "航点B"
            assert ws.cell(4, 1).value == "航点C"
            wb.close()
        finally:
            os.unlink(path)

    def test_export_empty_waypoints(self):
        """测试空列表"""
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            path = f.name
        try:
            fields = ["name"]
            result = ExcelExporter.export([], fields, path)
            assert result is True
            wb = load_workbook(path)
            ws = wb.active
            assert ws.max_row == 1  # 只有表头
            wb.close()
        finally:
            os.unlink(path)
```

- [ ] **Step 2: 运行测试确认失败**

运行: `cd "F:/gpx edit" && python -m pytest tests/test_excel_exporter.py -v`
预期: FAIL（模块不存在）

- [ ] **Step 3: 实现 ExcelExporter**

```python
# gpx_editor/core/excel_exporter.py
# -*- coding: utf-8 -*-
"""
Excel导出模块
功能: 将航点数据导出为Excel格式
"""

from typing import List
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment


# 字段配置：代码名 -> 中文表头
FIELD_CONFIG = {
    "name": "名称",
    "latitude": "纬度",
    "longitude": "经度",
    "elevation": "海拔",
    "description": "描述",
    "time": "时间",
}


def _get_waypoint_value(waypoint, field: str):
    """从航点对象获取指定字段值"""
    if field == "name":
        return waypoint.name
    elif field == "latitude":
        return waypoint.latitude
    elif field == "longitude":
        return waypoint.longitude
    elif field == "elevation":
        return waypoint.elevation
    elif field == "description":
        return waypoint.description
    elif field == "time":
        if waypoint.time:
            return waypoint.time.strftime("%Y-%m-%d %H:%M:%S")
        return None
    return None


class ExcelExporter:
    """Excel导出器"""

    @staticmethod
    def export(waypoints: list, selected_fields: List[str], output_path: str) -> bool:
        """
        导出航点到Excel
        Args:
            waypoints: gpxpy GPXWaypoint列表
            selected_fields: 选中的字段代码列表，如 ["name", "latitude", "longitude"]
            output_path: 输出文件路径(.xlsx)
        Returns:
            是否成功
        """
        wb = Workbook()
        ws = wb.active
        ws.title = "航点数据"

        # 写表头
        headers = [FIELD_CONFIG[f] for f in selected_fields if f in FIELD_CONFIG]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center")

        # 写数据
        for row_idx, wp in enumerate(waypoints, 2):
            for col_idx, field in enumerate(selected_fields, 1):
                if field in FIELD_CONFIG:
                    value = _get_waypoint_value(wp, field)
                    ws.cell(row=row_idx, column=col_idx, value=value)

        # 自动调整列宽
        for col_idx, field in enumerate(selected_fields, 1):
            if field in FIELD_CONFIG:
                max_len = len(FIELD_CONFIG[field])
                for row in ws.iter_rows(min_row=2, min_col=col_idx, max_col=col_idx):
                    for cell in row:
                        if cell.value:
                            max_len = max(max_len, len(str(cell.value)))
                ws.column_dimensions[ws.cell(1, col_idx).column_letter].width = min(max_len + 4, 50)

        wb.save(output_path)
        return True
```

- [ ] **Step 4: 运行测试确认通过**

运行: `cd "F:/gpx edit" && python -m pytest tests/test_excel_exporter.py -v`
预期: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git add gpx_editor/core/excel_exporter.py tests/test_excel_exporter.py
git commit -m "feat: 新增航点Excel导出核心逻辑"
```

---

### Task 2: 导出对话框

**Files:**
- Create: `gpx_editor/gui/excel_export_dialog.py`

- [ ] **Step 1: 实现对话框**

```python
# gpx_editor/gui/excel_export_dialog.py
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

from ..core.excel_exporter import ExcelExporter, FIELD_CONFIG


class ExcelExportDialog(tk.Toplevel):
    """航点Excel导出对话框"""

    def __init__(self, parent, waypoints):
        """
        初始化对话框
        Args:
            parent: 父窗口
            waypoints: gpxpy GPXWaypoint列表
        """
        super().__init__(parent)

        self.waypoints = waypoints
        self.title("导出航点到Excel")
        self.geometry("700x500")
        self.resizable(True, True)

        self.transient(parent)
        self.grab_set()

        # 字段勾选变量（中文 -> BooleanVar）
        self.field_vars = {}
        for field_code, field_name in FIELD_CONFIG.items():
            self.field_vars[field_code] = tk.BooleanVar(value=True)

        # 航点勾选数据
        self.waypoint_checks = []  # [(BooleanVar, waypoint)]

        self._create_widgets()
        self._center_window()
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

        # 全选按钮
        wp_btn_row = ttk.Frame(right_frame)
        wp_btn_row.pack(fill=X, pady=(0, 5))
        ttk.Button(wp_btn_row, text="全选", command=self._select_all_waypoints, bootstyle=INFO).pack(side=LEFT, padx=2)
        ttk.Button(wp_btn_row, text="取消全选", command=self._deselect_all_waypoints, bootstyle=INFO).pack(side=LEFT, padx=2)

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

        # 点击切换勾选
        self.waypoint_tree.bind("<ButtonRelease-1>", self._on_waypoint_click)

        # 填充航点数据
        self._load_waypoints()

        # ===== 底部按钮 =====
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=X, pady=10)

        self.export_btn = ttk.Button(btn_frame, text="导出", command=self._do_export, bootstyle=SUCCESS)
        self.export_btn.pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self.destroy, bootstyle=SECONDARY).pack(side=RIGHT, padx=5)

        # 状态标签
        self.status_label = ttk.Label(btn_frame, text="", foreground="gray")
        self.status_label.pack(side=LEFT, padx=15)

    def _load_waypoints(self):
        """加载航点到列表"""
        for i, wp in enumerate(self.waypoints):
            var = tk.BooleanVar(value=True)
            self.waypoint_checks.append((var, wp))
            check_text = "✓"
            self.waypoint_tree.insert("", tk.END, iid=str(i), values=(
                check_text,
                i + 1,
                wp.name or "",
                f"{wp.latitude:.6f}",
                f"{wp.longitude:.6f}"
            ))

    def _on_waypoint_click(self, event):
        """点击航点行切换勾选状态"""
        region = self.waypoint_tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        item = self.waypoint_tree.identify_row(event.y)
        if not item:
            return
        idx = int(item)
        var, _ = self.waypoint_checks[idx]
        var.set(not var.get())
        check_text = "✓" if var.get() else ""
        values = list(self.waypoint_tree.item(item, "values"))
        values[0] = check_text
        self.waypoint_tree.item(item, values=values)
        self._update_export_state()

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

    def _select_all_waypoints(self):
        """全选航点"""
        for i, (var, wp) in enumerate(self.waypoint_checks):
            var.set(True)
            values = list(self.waypoint_tree.item(str(i), "values"))
            values[0] = "✓"
            self.waypoint_tree.item(str(i), values=values)
        self._update_export_state()

    def _deselect_all_waypoints(self):
        """取消全选航点"""
        for i, (var, wp) in enumerate(self.waypoint_checks):
            var.set(False)
            values = list(self.waypoint_tree.item(str(i), "values"))
            values[0] = ""
            self.waypoint_tree.item(str(i), values=values)
        self._update_export_state()

    def _update_export_state(self):
        """更新导出按钮状态"""
        has_fields = any(v.get() for v in self.field_vars.values())
        has_waypoints = any(v.get() for v, _ in self.waypoint_checks)
        if has_fields and has_waypoints:
            self.export_btn.config(state=NORMAL)
            selected_count = sum(1 for v, _ in self.waypoint_checks if v.get())
            self.status_label.config(text=f"已选 {selected_count} 条航点")
        else:
            self.export_btn.config(state=DISABLED)
            if not has_fields:
                self.status_label.config(text="请至少选择一个属性")
            else:
                self.status_label.config(text="请至少选择一条航点")

    def _do_export(self):
        """执行导出"""
        selected_fields = [f for f, v in self.field_vars.items() if v.get()]
        selected_waypoints = [wp for var, wp in self.waypoint_checks if var.get()]

        if not selected_fields:
            messagebox.showwarning("提示", "请至少选择一个导出属性")
            return
        if not selected_waypoints:
            messagebox.showwarning("提示", "请至少选择一条航点")
            return

        # 选择保存路径
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel文件", "*.xlsx"), ("所有文件", "*.*")],
            title="保存Excel文件"
        )
        if not filepath:
            return

        try:
            ExcelExporter.export(selected_waypoints, selected_fields, filepath)
            result = messagebox.askyesno(
                "导出成功",
                f"导出成功！共 {len(selected_waypoints)} 条航点\n\n是否打开文件所在目录？"
            )
            if result:
                self._open_file_directory(filepath)
            self.destroy()
        except PermissionError:
            messagebox.showerror("错误", "文件被占用或无写入权限，请关闭已打开的Excel文件后重试")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败:\n{e}")

    def _open_file_directory(self, filepath):
        """打开文件所在目录"""
        directory = os.path.dirname(os.path.abspath(filepath))
        if platform.system() == "Windows":
            subprocess.Popen(["explorer", directory])
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", directory])
        else:
            subprocess.Popen(["xdg-open", directory])
```

- [ ] **Step 2: 运行确认无语法错误**

运行: `cd "F:/gpx edit" && python -c "from gpx_editor.gui.excel_export_dialog import ExcelExportDialog; print('OK')"`
预期: OK

- [ ] **Step 3: 提交**

```bash
git add gpx_editor/gui/excel_export_dialog.py
git commit -m "feat: 新增航点Excel导出对话框"
```

---

### Task 3: 集成到主窗口

**Files:**
- Modify: `gpx_editor/gui/main_window.py:96-103`

- [ ] **Step 1: 添加菜单入口**

在 `main_window.py` 的 `_create_menu` 方法中，工具菜单部分（约第103行后）添加：

```python
        tools_menu.add_separator()
        tools_menu.add_command(label="导出航点到Excel", command=self.export_waypoints_to_excel)
```

- [ ] **Step 2: 添加 import**

在 `main_window.py` 顶部 import 区域添加：

```python
from .excel_export_dialog import ExcelExportDialog
```

- [ ] **Step 3: 添加菜单处理方法**

在 `main_window.py` 的工具菜单相关方法区域添加：

```python
    def export_waypoints_to_excel(self):
        """导出航点到Excel"""
        waypoints = self.gpx_handler.get_waypoints()
        if not waypoints:
            messagebox.showwarning("提示", "当前文件无航点")
            return
        ExcelExportDialog(self, waypoints)
```

- [ ] **Step 4: 运行程序确认功能正常**

运行: `cd "F:/gpx edit" && python main.py`
手动验证：
1. 打开一个含航点的GPX文件
2. 工具菜单 → 导出航点到Excel
3. 对话框正常显示，属性和航点列表正确
4. 取消部分勾选，导出按钮状态正确
5. 点击导出，选择保存路径，Excel文件生成正确

- [ ] **Step 5: 提交**

```bash
git add gpx_editor/gui/main_window.py
git commit -m "feat: 工具菜单集成航点Excel导出功能"
```
