# 批量航点Excel导出功能设计

**日期**: 2026-05-16

**状态**: 已批准

## 1. 概述

### 1.1 目标
增强现有的航点Excel导出功能，支持：
- 批量添加GPX文件（文件夹或手选多个文件）
- 跨GPX文件选择航点
- 按文件分组显示航点
- 支持全部导出或选中部分导出

### 1.2 范围
改造现有的 `ExcelExportDialog` 对话框，不新建独立对话框。

## 2. 架构设计

### 2.1 改动文件
- `gpx_editor/gui/excel_export_dialog.py` - 主要改造
- `gpx_editor/gui/main_window.py` - 修改入口调用方式
- `gpx_editor/core/excel_exporter.py` - 可选：增加来源文件字段

### 2.2 数据流
```
用户添加文件/文件夹 → 解析GPX → 按文件分组存储航点 → 树形展示 → 用户勾选 → 导出Excel
```

### 2.3 核心数据结构
```python
from collections import OrderedDict

# 文件数据存储
self.file_data = OrderedDict()  # {文件路径: [waypoint_info, ...]}

# 航点信息结构
waypoint_info = {
    'waypoint': gpxpy.gpx.GPXWaypoint,  # 原始航点对象
    'checked': BooleanVar,               # 勾选状态
    'file_path': str                     # 来源文件路径
}
```

## 3. 界面设计

### 3.1 布局
```
┌─────────────────────────────────────────────────────────────┐
│  导出航点到Excel                                    [X]     │
├─────────────────────────────────────────────────────────────┤
│  ┌─ 选择导出属性 ──────┐  ┌─ 选择航点 ────────────────────┐ │
│  │ [全选] [取消全选]    │  │ [添加文件] [添加文件夹] [移除] │ │
│  │ ☑ 名称              │  │                               │ │
│  │ ☑ 纬度              │  │ ▼ 📄 航迹942214.gpx (3)      │ │
│  │ ☑ 经度              │  │   ☑ 序号  名称    纬度    经度│ │
│  │ ☑ 海拔              │  │   ☑  1    WP001   39.xxx  ...│ │
│  │ ☑ 描述              │  │   ☑  2    WP002   39.xxx  ...│ │
│  │ ☑ 时间              │  │   ☑  3    WP003   39.xxx  ...│ │
│  │                     │  │ ▼ 📄 水系设计点.gpx (2)       │ │
│  │                     │  │   ☑  1    WP001   39.xxx  ...│ │
│  │                     │  │   ☐  2    WP002   39.xxx  ...│ │
│  └─────────────────────┘  └───────────────────────────────┘ │
│                                                             │
│  [导出]                              已选 4 条航点     [取消]│
└─────────────────────────────────────────────────────────────┘
```

### 3.2 交互逻辑

#### 文件节点操作
- 点击文件行 → 切换该文件下所有航点的勾选状态
- 文件节点显示格式：`▼ 📄 文件名.gpx (已选数/总数)`

#### 航点节点操作
- 点击航点行 → 切换单个航点的勾选状态
- 航点显示：勾选标记、序号、名称、纬度、经度

#### 状态栏
- 实时显示已选航点总数
- 导出按钮状态随勾选变化

## 4. 功能设计

### 4.1 文件管理

#### 添加文件
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

#### 添加文件夹
```python
def _add_folder(self):
    """添加文件夹，自动扫描所有GPX文件"""
    folder = filedialog.askdirectory()
    if folder:
        for f in os.listdir(folder):
            if f.lower().endswith('.gpx'):
                full_path = os.path.join(folder, f)
                if full_path not in self.file_data:
                    self._load_gpx_file(full_path)
```

#### 移除文件
```python
def _remove_selected(self):
    """移除选中的文件及其航点"""
    selected_item = self.tree.selection()
    if selected_item:
        # 获取文件节点（如果是航点节点则获取其父节点）
        item = selected_item[0]
        parent = self.tree.parent(item)
        file_item = parent if parent else item
        
        # 从file_data中移除
        file_path = self.tree.item(file_item, "values")[0]
        if file_path in self.file_data:
            del self.file_data[file_path]
        
        # 从树中移除
        self.tree.delete(file_item)
        self._update_status()
```

### 4.2 GPX文件加载

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
        self._update_status()
    except Exception as e:
        messagebox.showerror("错误", f"加载文件失败:\n{file_path}\n{e}")
```

### 4.3 树形显示

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

### 4.4 勾选逻辑

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
    self._update_status()

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
        self._update_status()
```

### 4.5 导出逻辑

```python
def _do_export(self):
    """执行导出"""
    # 收集所有勾选的航点
    selected_waypoints = []
    for file_path, waypoints in self.file_data.items():
        for wp_info in waypoints:
            if wp_info['checked'].get():
                selected_waypoints.append(wp_info['waypoint'])
    
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
```

## 5. 入口调用改造

### 5.1 main_window.py

```python
# 原来：传递当前文件的航点
def _export_waypoints_excel(self):
    waypoints = self._get_current_waypoints()
    ExcelExportDialog(self, waypoints)

# 改为：传递当前文件路径（如果有）
def _export_waypoints_excel(self):
    current_file = getattr(self, 'current_file', None)
    ExcelExportDialog(self, initial_file=current_file)
```

### 5.2 ExcelExportDialog 构造函数

```python
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
    
    # 文件数据存储
    self.file_data = OrderedDict()  # {文件路径: [waypoint_info, ...]}
    
    self._create_widgets()
    self._center_window()
    
    # 自动加载初始文件
    if initial_file and os.path.exists(initial_file):
        self._load_gpx_file(initial_file)
    
    self._update_export_state()
```

## 6. ExcelExporter 扩展

为支持跨文件导出时区分来源，增加"来源文件"字段：

```python
# gpx_editor/core/excel_exporter.py
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

## 7. 测试要点

### 7.1 功能测试
- [ ] 添加单个GPX文件
- [ ] 添加多个GPX文件
- [ ] 添加文件夹
- [ ] 移除文件
- [ ] 文件节点全选/取消全选
- [ ] 单个航点勾选/取消
- [ ] 跨文件选择航点导出
- [ ] 导出Excel文件

### 7.2 边界测试
- [ ] 空GPX文件处理
- [ ] 重复添加同一文件
- [ ] 无航点时导出提示
- [ ] 文件被占用时的错误处理

## 8. 实施计划

1. 改造 `ExcelExportDialog` 构造函数和数据结构
2. 实现文件管理功能（添加/移除）
3. 实现树形显示和勾选逻辑
4. 修改 `main_window.py` 入口调用
5. 测试验证
