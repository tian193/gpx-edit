# 批量航点Excel导出功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 改造现有ExcelExportDialog，支持批量添加GPX文件、跨文件选择航点导出

**Architecture:** 重构ExcelExportDialog，使用OrderedDict按文件分组存储航点，Treeview树形显示，支持文件/文件夹添加

**Tech Stack:** tkinter, ttkbootstrap, gpxpy, openpyxl

---

## 文件结构

- `gpx_editor/gui/excel_export_dialog.py` - 主要改造：构造函数、文件管理、树形显示、勾选逻辑
- `gpx_editor/gui/main_window.py` - 修改入口调用方式（第994-1000行）
- `gpx_editor/core/excel_exporter.py` - 增加source_file字段支持

---

### Task 1: 扩展ExcelExporter支持来源文件字段

**Files:**
- Modify: `gpx_editor/core/excel_exporter.py:13-20`

- [ ] **Step 1: 修改FIELD_CONFIG增加source_file字段**

```python
# gpx_editor/core/excel_exporter.py
# 字段配置：代码名 -> 中文表头
FIELD_CONFIG = {
    "source_file": "来源文件",  # 新增
    "name": "名称",
    "latitude": "纬度",
    "longitude": "经度",
    "elevation": "海拔",
    "description": "描述",
    "time": "时间",
}
```

- [ ] **Step 2: 修改_get_waypoint_value支持source_file**

```python
def _get_waypoint_value(waypoint, field: str, source_file: str = None):
    """从航点对象获取指定字段值"""
    if field == "source_file":
        if source_file:
            import os
            return os.path.basename(source_file)
        return None
    if field == "time":
        if waypoint.time:
            return waypoint.time.strftime("%Y-%m-%d %H:%M:%S")
        return None
    return getattr(waypoint, field, None)
```

- [ ] **Step 3: 修改export方法签名支持source_files参数**

```python
@staticmethod
def export(waypoints: list, selected_fields: List[str], output_path: str, source_files: dict = None):
    """
    导出航点到Excel
    Args:
        waypoints: gpxpy GPXWaypoint列表
        selected_fields: 选中的字段代码列表
        output_path: 输出文件路径(.xlsx)
        source_files: 航点来源文件映射 {waypoint_id: file_path}，可选
    """
```

- [ ] **Step 4: 修改数据写入逻辑使用source_files**

```python
# 写数据
for row_idx, wp in enumerate(waypoints, 2):
    for col_idx, field in enumerate(selected_fields, 1):
        if field in FIELD_CONFIG:
            source_file = source_files.get(id(wp)) if source_files else None
            value = _get_waypoint_value(wp, field, source_file)
            ws.cell(row=row_idx, column=col_idx, value=value)
```

- [ ] **Step 5: 提交改动**

```bash
git add gpx_editor/core/excel_exporter.py
git commit -m "feat: ExcelExporter增加来源文件字段支持"
```

---

### Task 2: 重构ExcelExportDialog构造函数和数据结构

**Files:**
- Modify: `gpx_editor/gui/excel_export_dialog.py:18-48`

- [ ] **Step 1: 添加OrderedDict导入**

```python
# gpx_editor/gui/excel_export_dialog.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
import os
import subprocess
import platform
from collections import OrderedDict

from ..core.excel_exporter import ExcelExporter, FIELD_CONFIG
```

- [ ] **Step 2: 重构构造函数**

```python
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

        self._update_export_state()
```

- [ ] **Step 3: 提交改动**

```bash
git add gpx_editor/gui/excel_export_dialog.py
git commit -m "refactor: ExcelExportDialog构造函数支持多文件"
```

---

### Task 3: 实现文件管理功能（添加/移除）

**Files:**
- Modify: `gpx_editor/gui/excel_export_dialog.py` (新增方法)

- [ ] **Step 1: 实现_load_gpx_file方法**

```python
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
        self._update_export_state()
    except Exception as e:
        messagebox.showerror("错误", f"加载文件失败:\n{file_path}\n{e}")
```

- [ ] **Step 2: 实现_add_files方法**

```python
def _add_files(self):
    """添加GPX文件（支持多选）"""
    files = filedialog.askopenfilenames(
        filetypes=[("GPX文件", "*.gpx"), ("所有文件", "*.*")]
    )
    for f in files:
        if f not in self.file_data:
            self._load_gpx_file(f)
```

- [ ] **Step 3: 实现_add_folder方法**

```python
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
```

- [ ] **Step 4: 实现_remove_selected方法**

```python
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
```

- [ ] **Step 5: 提交改动**

```bash
git add gpx_editor/gui/excel_export_dialog.py
git commit -m "feat: 实现文件管理功能（添加/移除GPX文件）"
```

---

### Task 4: 实现树形显示和勾选逻辑

**Files:**
- Modify: `gpx_editor/gui/excel_export_dialog.py` (新增方法)

- [ ] **Step 1: 实现_add_file_to_tree方法**

```python
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
```

- [ ] **Step 2: 实现_refresh_file_node方法**

```python
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
```

- [ ] **Step 3: 实现_on_tree_click方法**

```python
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
```

- [ ] **Step 4: 实现_toggle_file_waypoints方法**

```python
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
```

- [ ] **Step 5: 实现_toggle_single_waypoint方法**

```python
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
```

- [ ] **Step 6: 提交改动**

```bash
git add gpx_editor/gui/excel_export_dialog.py
git commit -m "feat: 实现树形显示和勾选逻辑"
```

---

### Task 5: 重构_create_widgets方法

**Files:**
- Modify: `gpx_editor/gui/excel_export_dialog.py:59-136`

- [ ] **Step 1: 重写_create_widgets方法**

```python
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

    # 文件操作按钮
    file_btn_row = ttk.Frame(right_frame)
    file_btn_row.pack(fill=X, pady=(0, 5))
    ttk.Button(file_btn_row, text="添加文件", command=self._add_files, bootstyle=INFO).pack(side=LEFT, padx=2)
    ttk.Button(file_btn_row, text="添加文件夹", command=self._add_folder, bootstyle=INFO).pack(side=LEFT, padx=2)
    ttk.Button(file_btn_row, text="移除", command=self._remove_selected, bootstyle=WARNING).pack(side=LEFT, padx=2)
    ttk.Button(file_btn_row, text="全选", command=self._select_all_waypoints, bootstyle=INFO).pack(side=RIGHT, padx=2)
    ttk.Button(file_btn_row, text="取消全选", command=self._deselect_all_waypoints, bootstyle=INFO).pack(side=RIGHT, padx=2)

    # 航点Treeview（树形结构）
    tree_frame = ttk.Frame(right_frame)
    tree_frame.pack(fill=BOTH, expand=True)

    columns = ("file_path", "check", "index", "name", "lat", "lon")
    self.tree = ttk.Treeview(tree_frame, columns=columns, show="tree headings", height=15)
    self.tree.heading("#0", text="文件")
    self.tree.heading("check", text="✓")
    self.tree.heading("index", text="序号")
    self.tree.heading("name", text="名称")
    self.tree.heading("lat", text="纬度")
    self.tree.heading("lon", text="经度")

    self.tree.column("#0", width=200)
    self.tree.column("file_path", width=0, stretch=False)  # 隐藏列
    self.tree.column("check", width=30, anchor=CENTER)
    self.tree.column("index", width=50, anchor=CENTER)
    self.tree.column("name", width=120)
    self.tree.column("lat", width=80)
    self.tree.column("lon", width=80)

    scrollbar = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.tree.yview)
    self.tree.configure(yscrollcommand=scrollbar.set)
    self.tree.pack(side=LEFT, fill=BOTH, expand=True)
    scrollbar.pack(side=RIGHT, fill=Y)

    # 点击切换勾选
    self.tree.bind("<ButtonRelease-1>", self._on_tree_click)

    # ===== 底部按钮 =====
    btn_frame = ttk.Frame(main_frame)
    btn_frame.pack(fill=X, pady=10)

    self.export_btn = ttk.Button(btn_frame, text="导出", command=self._do_export, bootstyle=SUCCESS)
    self.export_btn.pack(side=LEFT, padx=5)
    ttk.Button(btn_frame, text="取消", command=self.destroy, bootstyle=SECONDARY).pack(side=RIGHT, padx=5)

    # 状态标签
    self.status_label = ttk.Label(btn_frame, text="", foreground="gray")
    self.status_label.pack(side=LEFT, padx=15)
```

- [ ] **Step 2: 提交改动**

```bash
git add gpx_editor/gui/excel_export_dialog.py
git commit -m "refactor: 重构_create_widgets支持树形显示"
```

---

### Task 6: 重构导出逻辑和状态更新

**Files:**
- Modify: `gpx_editor/gui/excel_export_dialog.py` (修改方法)

- [ ] **Step 1: 重写_update_export_state方法**

```python
def _update_export_state(self):
    """更新导出按钮状态"""
    has_fields = any(v.get() for v in self.field_vars.values())
    has_waypoints = any(
        wp_info['checked'].get()
        for waypoints in self.file_data.values()
        for wp_info in waypoints
    )

    if has_fields and has_waypoints:
        self.export_btn.config(state=NORMAL)
        selected_count = sum(
            1 for waypoints in self.file_data.values()
            for wp_info in waypoints if wp_info['checked'].get()
        )
        total_count = sum(len(waypoints) for waypoints in self.file_data.values())
        self.status_label.config(text=f"已选 {selected_count}/{total_count} 条航点")
    else:
        self.export_btn.config(state=DISABLED)
        if not has_fields:
            self.status_label.config(text="请至少选择一个属性")
        elif not self.file_data:
            self.status_label.config(text="请添加GPX文件")
        else:
            self.status_label.config(text="请至少选择一条航点")
```

- [ ] **Step 2: 重写_do_export方法**

```python
def _do_export(self):
    """执行导出"""
    # 收集所有勾选的航点及其来源文件
    selected_waypoints = []
    source_files = {}
    for file_path, waypoints in self.file_data.items():
        for wp_info in waypoints:
            if wp_info['checked'].get():
                wp = wp_info['waypoint']
                selected_waypoints.append(wp)
                source_files[id(wp)] = file_path

    if not selected_waypoints:
        messagebox.showwarning("提示", "请至少选择一条航点")
        return

    selected_fields = [f for f, v in self.field_vars.items() if v.get()]
    if not selected_fields:
        messagebox.showwarning("提示", "请至少选择一个导出属性")
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
        ExcelExporter.export(selected_waypoints, selected_fields, filepath, source_files)
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
```

- [ ] **Step 3: 实现_select_all_waypoints方法**

```python
def _select_all_waypoints(self):
    """全选所有航点"""
    for file_path, waypoints in self.file_data.items():
        for wp_info in waypoints:
            wp_info['checked'].set(True)
    # 刷新所有文件节点
    for child in self.tree.get_children(""):
        file_path = self.tree.item(child, "values")[0]
        self._refresh_file_node(child, file_path)
    self._update_export_state()
```

- [ ] **Step 4: 实现_deselect_all_waypoints方法**

```python
def _deselect_all_waypoints(self):
    """取消全选所有航点"""
    for file_path, waypoints in self.file_data.items():
        for wp_info in waypoints:
            wp_info['checked'].set(False)
    # 刷新所有文件节点
    for child in self.tree.get_children(""):
        file_path = self.tree.item(child, "values")[0]
        self._refresh_file_node(child, file_path)
    self._update_export_state()
```

- [ ] **Step 5: 提交改动**

```bash
git add gpx_editor/gui/excel_export_dialog.py
git commit -m "feat: 重构导出逻辑支持跨文件选择"
```

---

### Task 7: 修改main_window.py入口调用

**Files:**
- Modify: `gpx_editor/gui/main_window.py:994-1000`

- [ ] **Step 1: 修改export_waypoints_to_excel方法**

```python
def export_waypoints_to_excel(self):
    """导出航点到Excel"""
    current_file = getattr(self, 'current_file', None)
    ExcelExportDialog(self, initial_file=current_file)
```

- [ ] **Step 2: 提交改动**

```bash
git add gpx_editor/gui/main_window.py
git commit -m "refactor: 修改Excel导出入口支持多文件模式"
```

---

### Task 8: 删除不再需要的旧方法

**Files:**
- Modify: `gpx_editor/gui/excel_export_dialog.py` (删除方法)

- [ ] **Step 1: 删除_load_waypoints方法**

删除以下方法（如果存在）：
```python
def _load_waypoints(self):
    """加载航点到列表"""
    # ... 旧代码
```

- [ ] **Step 2: 删除旧的_on_waypoint_click方法**

删除以下方法（如果存在）：
```python
def _on_waypoint_click(self, event):
    """点击航点行切换勾选状态"""
    # ... 旧代码
```

- [ ] **Step 3: 提交改动**

```bash
git add gpx_editor/gui/excel_export_dialog.py
git commit -m "refactor: 清理不再需要的旧方法"
```

---

### Task 9: 功能验证测试

- [ ] **Step 1: 运行程序验证基本功能**

```bash
python main.py
```

- [ ] **Step 2: 测试单文件加载**

1. 打开一个GPX文件
2. 点击"工具" → "导出航点到Excel"
3. 验证对话框自动加载当前文件的航点

- [ ] **Step 3: 测试添加文件功能**

1. 点击"添加文件"按钮
2. 选择一个或多个GPX文件
3. 验证文件正确加载到树形列表

- [ ] **Step 4: 测试添加文件夹功能**

1. 点击"添加文件夹"按钮
2. 选择包含GPX文件的文件夹
3. 验证文件夹中所有GPX文件正确加载

- [ ] **Step 5: 测试勾选功能**

1. 点击文件节点，验证该文件所有航点勾选状态切换
2. 点击单个航点，验证勾选状态切换
3. 使用"全选"/"取消全选"按钮

- [ ] **Step 6: 测试导出功能**

1. 选择部分航点
2. 点击"导出"按钮
3. 验证Excel文件正确生成，包含来源文件列

- [ ] **Step 7: 提交最终版本**

```bash
git add -A
git commit -m "feat: 完成批量航点Excel导出功能"
```
