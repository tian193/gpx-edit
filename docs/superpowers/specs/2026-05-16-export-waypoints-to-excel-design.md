# 导出航点到Excel - 设计文档

> 日期: 2026-05-16

## 概述

新增功能：将GPX文件中的航点属性导出为Excel文件，支持选择导出哪些属性字段和哪些航点。

## 架构

新增两个文件：
- `gpx_editor/core/excel_exporter.py` — 核心导出逻辑（纯数据层，无GUI依赖）
- `gpx_editor/gui/excel_export_dialog.py` — 导出对话框

在 `main_window.py` 的"工具"菜单下新增入口"导出航点到Excel"。

## 对话框设计

标题："导出航点到Excel"，大小约700x500，可调整。

### 左侧 — 属性选择区

- 分组框"选择导出属性"
- 6个勾选框，全部中文显示：名称、纬度、经度、海拔、描述、时间
- 默认全部勾选
- "全选/取消全选"快捷按钮

### 右侧 — 航点列表区

- 分组框"选择航点"
- Treeview表格，带勾选框，显示：序号、名称、纬度、经度
- 顶部"全选/取消全选"按钮
- 默认全部勾选

### 底部

- "导出"按钮 → 弹出文件保存对话框（.xlsx）
- "取消"按钮

## 核心导出逻辑

`excel_exporter.py` 提供函数：

```python
def export_waypoints_to_excel(
    waypoints: List[WaypointData],
    selected_fields: List[str],
    output_path: str
) -> bool
```

### 字段映射

| 代码字段 | Excel表头 |
|---------|----------|
| name | 名称 |
| latitude | 纬度 |
| longitude | 经度 |
| elevation | 海拔 |
| description | 描述 |
| time | 时间 |

### Excel格式

- 第1行表头（中文），加粗
- 数据从第2行开始
- 列宽自动适配内容
- 空值（海拔、描述、时间为空时）留空单元格

## 边界处理

- 无航点：提示"当前文件无航点"，禁用导出按钮
- 未选属性：导出按钮置灰不可点
- 未选航点：导出按钮置灰不可点
- 导出成功：弹出提示"导出成功，共N条航点"，询问是否打开文件所在目录
- 导出失败：弹出错误提示（如文件被占用、权限不足等）

## 集成方式

- main_window.py：在"工具"菜单添加"导出航点到Excel"，点击打开对话框
- 依赖：复用已有 openpyxl、WaypointData
- 不改动现有核心模块逻辑
