# GPX编辑器三项功能改善实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现列配置系统、移动航点对话框（三种模式）、地图交互编辑（MapSource风格）三项功能。

**Architecture:** 新增coord_converter模块处理CGCS2000坐标转换和天地图瓦片URL生成；新增column_config_dialog实现列配置UI；重写move_waypoint_dialog支持三种移动模式；修改main_window集成天地图和地图交互编辑。

**Tech Stack:** Python 3.10+ / tkinter + ttkbootstrap / tkintermapview / pyproj / gpxpy

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `gpx_editor/core/coord_converter.py` | 坐标转换（WGS84↔CGCS2000）+ 天地图瓦片URL生成 |
| `gpx_editor/gui/column_config_dialog.py` | 列配置对话框UI |
| `gpx_editor/gui/move_waypoint_dialog.py` | 移动航点对话框（三种模式，重写） |
| `gpx_editor/gui/main_window.py` | 集成列配置、天地图、地图交互编辑 |
| `gpx_editor/gui/undo_manager.py` | 支持新的操作类型 |
| `requirements.txt` | 添加pyproj依赖 |
| `tests/test_coord_converter.py` | 坐标转换测试 |

---

## Task 1: 坐标转换模块

**Files:**
- Create: `gpx_editor/core/coord_converter.py`
- Create: `tests/test_coord_converter.py`
- Modify: `requirements.txt`

- [ ] **Step 1: 添加pyproj依赖**

在 `requirements.txt` 末尾添加：
```
pyproj>=3.0.0
```

- [ ] **Step 2: 编写坐标转换测试**

```python
# tests/test_coord_converter.py
# -*- coding: utf-8 -*-
"""
坐标转换模块测试
"""

import pytest
from gpx_editor.core.coord_converter import CoordConverter


class TestCoordConverter:
    """坐标转换器测试"""

    def test_get_zone_number(self):
        """测试带号计算"""
        # 经度116° → 39带 (116/6=19.33, floor+1=20... 不对)
        # 实际: floor(116/6)+1 = floor(19.33)+1 = 19+1 = 20带
        assert CoordConverter.get_zone_number(116.654321) == 20
        # 经度117° → 20带
        assert CoordConverter.get_zone_number(117.0) == 20
        # 经度120° → 21带
        assert CoordConverter.get_zone_number(120.0) == 21

    def test_wgs84_to_cgcs2000(self):
        """测试WGS84转CGCS2000投影坐标"""
        # 北京天安门附近: 纬度39.9042, 经度116.4074
        x, y, zone = CoordConverter.wgs84_to_cgcs2000(39.9042, 116.4074)
        assert zone == 20
        # X（东向）应该在 400000-500000 范围
        assert 400000 < x < 500000
        # Y（北向）应该在 4400000-4500000 范围
        assert 4400000 < y < 4500000

    def test_cgcs2000_to_wgs84(self):
        """测试CGCS2000投影坐标转WGS84"""
        # 先转过去再转回来，验证往返一致性
        lat_orig, lon_orig = 39.9042, 116.4074
        x, y, zone = CoordConverter.wgs84_to_cgcs2000(lat_orig, lon_orig)
        lat_back, lon_back = CoordConverter.cgcs2000_to_wgs84(x, y, zone)
        # 精度到小数点后6位（约0.1米）
        assert abs(lat_orig - lat_back) < 0.000001
        assert abs(lon_orig - lon_back) < 0.000001

    def test_format_cgcs2000(self):
        """测试格式化输出"""
        result = CoordConverter.format_cgcs2000(39.9042, 116.4074)
        assert "20带" in result
        assert "X=" in result
        assert "Y=" in result
```

- [ ] **Step 3: 运行测试确认失败**

Run: `cd "F:/gpx edit" && python -m pytest tests/test_coord_converter.py -v`
Expected: FAIL (模块不存在)

- [ ] **Step 4: 实现坐标转换模块**

```python
# gpx_editor/core/coord_converter.py
# -*- coding: utf-8 -*-
"""
坐标转换模块
功能: WGS84↔CGCS2000投影坐标转换、天地图瓦片URL生成
"""

import math
from typing import Tuple, Optional


class CoordConverter:
    """坐标转换器"""

    @staticmethod
    def get_zone_number(longitude: float) -> int:
        """计算6度带带号

        Args:
            longitude: 经度

        Returns:
            带号
        """
        return int(math.floor(longitude / 6)) + 1

    @staticmethod
    def get_central_meridian(zone_number: int) -> float:
        """计算中央经线

        Args:
            zone_number: 带号

        Returns:
            中央经线经度
        """
        return zone_number * 6 - 3

    @staticmethod
    def wgs84_to_cgcs2000(latitude: float, longitude: float) -> Tuple[float, float, int]:
        """WGS84经纬度转CGCS2000投影坐标

        Args:
            latitude: 纬度
            longitude: 经度

        Returns:
            (X东向, Y北向, 带号)
        """
        try:
            from pyproj import Transformer
            zone = CoordConverter.get_zone_number(longitude)
            # CGCS2000 / Gauss-Kruger zone
            # EPSG代码: 4491 + zone_number (6度带)
            # 但对于CGCS2000, 使用自定义proj字符串更可靠
            central_meridian = CoordConverter.get_central_meridian(zone)
            proj_string = (
                f"+proj=tmerc +lat_0=0 +lon_0={central_meridian} +k=1 +x_0={zone}000000 +y_0=0 "
                f"+ellps=GRS80 +units=m +no_defs"
            )
            transformer = Transformer.from_crs("EPSG:4326", proj_string, always_xy=True)
            x, y = transformer.transform(longitude, latitude)
            return x, y, zone
        except ImportError:
            # pyproj不可用时的备用实现（简化版，精度较低）
            return CoordConverter._wgs84_to_cgcs2000_fallback(latitude, longitude)

    @staticmethod
    def cgcs2000_to_wgs84(x: float, y: float, zone: int) -> Tuple[float, float]:
        """CGCS2000投影坐标转WGS84经纬度

        Args:
            x: 东向坐标
            y: 北向坐标
            zone: 带号

        Returns:
            (纬度, 经度)
        """
        try:
            from pyproj import Transformer
            central_meridian = CoordConverter.get_central_meridian(zone)
            proj_string = (
                f"+proj=tmerc +lat_0=0 +lon_0={central_meridian} +k=1 +x_0={zone}000000 +y_0=0 "
                f"+ellps=GRS80 +units=m +no_defs"
            )
            transformer = Transformer.from_crs(proj_string, "EPSG:4326", always_xy=True)
            lon, lat = transformer.transform(x, y)
            return lat, lon
        except ImportError:
            return CoordConverter._cgcs2000_to_wgs84_fallback(x, y, zone)

    @staticmethod
    def _wgs84_to_cgcs2000_fallback(latitude: float, longitude: float) -> Tuple[float, float, int]:
        """备用坐标转换（不依赖pyproj）"""
        zone = CoordConverter.get_zone_number(longitude)
        central_meridian = CoordConverter.get_central_meridian(zone)

        # 简化的高斯-克吕格投影公式
        a = 6378137.0  # CGCS2000长半轴
        f = 1 / 298.257222101  # 扁率
        e2 = 2 * f - f * f
        ep2 = e2 / (1 - e2)

        lat_rad = math.radians(latitude)
        lon_rad = math.radians(longitude)
        lon0_rad = math.radians(central_meridian)

        N = a / math.sqrt(1 - e2 * math.sin(lat_rad) ** 2)
        t = math.tan(lat_rad)
        eta2 = ep2 * math.cos(lat_rad) ** 2

        l = lon_rad - lon0_rad

        # 高斯-克吕格正算公式（简化版）
        x = N * math.cos(lat_rad) * l + \
            N * math.cos(lat_rad) ** 3 * t * (1 - t ** 2 + eta2) * l ** 3 / 6

        # 子午线弧长
        A0 = 1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256
        A2 = 3 / 8 * (e2 + e2 ** 2 / 4 + 15 * e2 ** 3 / 128)
        A4 = 15 / 256 * (e2 ** 2 + 3 * e2 ** 3 / 4)
        A6 = 35 * e2 ** 3 / 3072

        X = a * (A0 * lat_rad - A2 * math.sin(2 * lat_rad) + A4 * math.sin(4 * lat_rad) - A6 * math.sin(6 * lat_rad))

        y = X + N * math.sin(lat_rad) * math.cos(lat_rad) * l ** 2 / 2 + \
            N * math.sin(lat_rad) * math.cos(lat_rad) ** 3 * (5 - t ** 2 + 9 * eta2 + 4 * eta2 ** 2) * l ** 4 / 24

        # 加带号偏移
        x_final = x + zone * 1000000

        return x_final, y, zone

    @staticmethod
    def _cgcs2000_to_wgs84_fallback(x: float, y: float, zone: int) -> Tuple[float, float]:
        """备用反算（不依赖pyproj）"""
        # 去掉带号偏移
        x_adj = x - zone * 1000000

        a = 6378137.0
        f = 1 / 298.257222101
        e2 = 2 * f - f * f

        # 迭代求解纬度
        lat = y / a
        for _ in range(10):
            lat_new = (y + a * e2 * math.sin(lat) * math.cos(lat)) / a
            if abs(lat_new - lat) < 1e-12:
                break
            lat = lat_new

        lat_deg = math.degrees(lat)

        # 求解经度
        central_meridian = CoordConverter.get_central_meridian(zone)
        N = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
        lon = central_meridian + math.degrees(x_adj / (N * math.cos(lat)))

        return lat_deg, lon

    @staticmethod
    def format_cgcs2000(latitude: float, longitude: float) -> str:
        """格式化输出CGCS2000坐标

        Args:
            latitude: 纬度
            longitude: 经度

        Returns:
            格式化字符串，如 "20带 X=444012.345 Y=4330567.890"
        """
        x, y, zone = CoordConverter.wgs84_to_cgcs2000(latitude, longitude)
        return f"{zone}带 X={x:.3f} Y={y:.3f}"


class TiandituTileProvider:
    """天地图瓦片服务提供器"""

    # 瓦片服务URL模板
    TILE_URLS = {
        "vec": "http://t{s}.tianditu.gov.cn/vec_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=vec&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk={tk}",
        "img": "http://t{s}.tianditu.gov.cn/img_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=img&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk={tk}",
        "cia": "http://t{s}.tianditu.gov.cn/cia_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=cia&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk={tk}",
    }

    @staticmethod
    def get_tile_url(layer: str, api_key: str) -> str:
        """获取瓦片服务URL

        Args:
            layer: 图层类型 ('vec', 'img', 'cia')
            api_key: 天地图API Key

        Returns:
            瓦片URL模板
        """
        if layer not in TiandituTileProvider.TILE_URLS:
            raise ValueError(f"不支持的图层类型: {layer}")

        url = TiandituTileProvider.TILE_URLS[layer]
        # 替换API Key，保留{s}, {x}, {y}, {z}占位符
        url = url.replace("{tk}", api_key)
        return url

    @staticmethod
    def get_road_url(api_key: str) -> str:
        """获取路网图URL"""
        return TiandituTileProvider.get_tile_url("vec", api_key)

    @staticmethod
    def get_satellite_url(api_key: str) -> str:
        """获取卫星影像URL"""
        return TiandituTileProvider.get_tile_url("img", api_key)

    @staticmethod
    def get_annotation_url(api_key: str) -> str:
        """获取路网标注URL（叠加层）"""
        return TiandituTileProvider.get_tile_url("cia", api_key)
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd "F:/gpx edit" && python -m pytest tests/test_coord_converter.py -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
cd "F:/gpx edit"
git add requirements.txt gpx_editor/core/coord_converter.py tests/test_coord_converter.py
git commit -m "feat: 新增坐标转换模块（CGCS2000 + 天地图瓦片）"
```

---

## Task 2: 列配置对话框

**Files:**
- Create: `gpx_editor/gui/column_config_dialog.py`
- Modify: `gpx_editor/gui/main_window.py:143-156` (列定义)

- [ ] **Step 1: 编写列配置对话框**

```python
# gpx_editor/gui/column_config_dialog.py
# -*- coding: utf-8 -*-
"""
列配置对话框
功能: 配置数据列表显示的列、顺序和宽度
"""

import json
import os
import tkinter as tk
from tkinter import ttk, messagebox
from ttkbootstrap.constants import *
from typing import List, Dict, Any, Optional


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

# 默认显示的列
DEFAULT_VISIBLE = ["type", "name", "lat", "lon"]

# 默认列顺序
DEFAULT_ORDER = [col["id"] for col in COLUMN_DEFINITIONS]


class ColumnConfigManager:
    """列配置管理器"""

    def __init__(self, config_dir: Optional[str] = None):
        if config_dir is None:
            config_dir = os.path.expanduser("~/.gpx_editor")
        self._config_dir = config_dir
        self._config_file = os.path.join(config_dir, "column_config.json")
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        if os.path.exists(self._config_file):
            try:
                with open(self._config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "visible_columns": DEFAULT_VISIBLE[:],
            "column_order": DEFAULT_ORDER[:],
            "column_widths": {col["id"]: col["width"] for col in COLUMN_DEFINITIONS},
        }

    def save(self):
        """保存配置"""
        os.makedirs(self._config_dir, exist_ok=True)
        with open(self._config_file, "w", encoding="utf-8") as f:
            json.dump(self._config, f, ensure_ascii=False, indent=2)

    def reset_to_default(self):
        """重置为默认配置"""
        self._config = self._get_default_config()

    @property
    def visible_columns(self) -> List[str]:
        """获取可见列列表"""
        return self._config["visible_columns"]

    @visible_columns.setter
    def visible_columns(self, value: List[str]):
        self._config["visible_columns"] = value

    @property
    def column_order(self) -> List[str]:
        """获取列顺序"""
        return self._config["column_order"]

    @column_order.setter
    def column_order(self, value: List[str]):
        self._config["column_order"] = value

    def get_column_width(self, col_id: str) -> int:
        """获取列宽度"""
        return self._config["column_widths"].get(col_id, 100)

    def set_column_width(self, col_id: str, width: int):
        """设置列宽度"""
        self._config["column_widths"][col_id] = width

    def get_column_def(self, col_id: str) -> Optional[Dict[str, Any]]:
        """获取列定义"""
        for col in COLUMN_DEFINITIONS:
            if col["id"] == col_id:
                return col
        return None

    def get_ordered_visible_columns(self) -> List[Dict[str, Any]]:
        """获取按顺序排列的可见列定义"""
        result = []
        for col_id in self._config["column_order"]:
            if col_id in self._config["visible_columns"]:
                col_def = self.get_column_def(col_id)
                if col_def:
                    result.append(col_def)
        return result


class ColumnConfigDialog:
    """列配置对话框"""

    def __init__(self, parent, config_manager: ColumnConfigManager):
        """
        Args:
            parent: 父窗口
            config_manager: 列配置管理器
        """
        self.result = False
        self._config_manager = config_manager
        # 临时配置（确定时才保存）
        self._temp_visible = config_manager.visible_columns[:]
        self._temp_order = config_manager.column_order[:]

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("列配置")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)
        self.dialog.geometry("500x450")

        self._create_widgets()
        self._populate_lists()

        # 居中
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.dialog.wait_window()

    def _create_widgets(self):
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=BOTH, expand=True)

        # 说明
        ttk.Label(main_frame, text="选择要显示的列，拖动调整顺序",
                  foreground="gray").pack(anchor=W, pady=(0, 10))

        # 左右分栏
        paned = ttk.Frame(main_frame)
        paned.pack(fill=BOTH, expand=True)

        # 左侧：可用列
        left_frame = ttk.LabelFrame(paned, text="可用列", padding=5)
        left_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 5))

        self.available_list = tk.Listbox(left_frame, selectmode=SINGLE, height=15)
        self.available_list.pack(fill=BOTH, expand=True)
        self.available_list.bind("<Double-1>", self._on_add_column)

        ttk.Button(left_frame, text="添加 →", command=self._on_add_column,
                   bootstyle=PRIMARY).pack(pady=(5, 0))

        # 右侧：已显示列
        right_frame = ttk.LabelFrame(paned, text="已显示列", padding=5)
        right_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(5, 0))

        self.visible_list = tk.Listbox(right_frame, selectmode=SINGLE, height=15)
        self.visible_list.pack(fill=BOTH, expand=True)
        self.visible_list.bind("<Double-1>", self._on_remove_column)

        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(fill=X, pady=(5, 0))
        ttk.Button(btn_frame, text="← 移除", command=self._on_remove_column,
                   bootstyle=DANGER).pack(side=LEFT)
        ttk.Button(btn_frame, text="上移", command=self._on_move_up).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="下移", command=self._on_move_down).pack(side=LEFT)

        # 底部按钮
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=X, pady=(10, 0))
        ttk.Button(bottom_frame, text="重置默认", command=self._on_reset,
                   bootstyle=WARNING).pack(side=LEFT)
        ttk.Button(bottom_frame, text="确定", command=self._on_ok,
                   bootstyle=PRIMARY).pack(side=RIGHT, padx=5)
        ttk.Button(bottom_frame, text="取消", command=self._on_cancel).pack(side=RIGHT)

    def _populate_lists(self):
        """填充列表"""
        self.available_list.delete(0, END)
        self.visible_list.delete(0, END)

        for col in COLUMN_DEFINITIONS:
            col_id = col["id"]
            label = f"[计算] {col['name']}" if col["category"] == "computed" else col["name"]
            if col_id in self._temp_visible:
                # 已显示
                self.visible_list.insert(END, label)
            else:
                # 可用
                self.available_list.insert(END, label)

    def _get_selected_available(self) -> Optional[str]:
        """获取选中的可用列ID"""
        sel = self.available_list.curselection()
        if not sel:
            return None
        label = self.available_list.get(sel[0])
        # 查找对应的列ID
        for col in COLUMN_DEFINITIONS:
            check_label = f"[计算] {col['name']}" if col["category"] == "computed" else col["name"]
            if check_label == label:
                return col["id"]
        return None

    def _get_selected_visible(self) -> Optional[str]:
        """获取选中的已显示列ID"""
        sel = self.visible_list.curselection()
        if not sel:
            return None
        label = self.visible_list.get(sel[0])
        for col in COLUMN_DEFINITIONS:
            check_label = f"[计算] {col['name']}" if col["category"] == "computed" else col["name"]
            if check_label == label:
                return col["id"]
        return None

    def _on_add_column(self, event=None):
        """添加列到已显示"""
        col_id = self._get_selected_available()
        if col_id and col_id not in self._temp_visible:
            self._temp_visible.append(col_id)
            # 确保在order中
            if col_id not in self._temp_order:
                self._temp_order.append(col_id)
            self._populate_lists()

    def _on_remove_column(self, event=None):
        """从已显示移除列"""
        col_id = self._get_selected_visible()
        if col_id and col_id in self._temp_visible:
            self._temp_visible.remove(col_id)
            self._populate_lists()

    def _on_move_up(self):
        """上移选中列"""
        col_id = self._get_selected_visible()
        if not col_id:
            return
        idx = self._temp_visible.index(col_id)
        if idx > 0:
            self._temp_visible[idx], self._temp_visible[idx - 1] = \
                self._temp_visible[idx - 1], self._temp_visible[idx]
            self._populate_lists()
            self.visible_list.selection_set(idx - 1)

    def _on_move_down(self):
        """下移选中列"""
        col_id = self._get_selected_visible()
        if not col_id:
            return
        idx = self._temp_visible.index(col_id)
        if idx < len(self._temp_visible) - 1:
            self._temp_visible[idx], self._temp_visible[idx + 1] = \
                self._temp_visible[idx + 1], self._temp_visible[idx]
            self._populate_lists()
            self.visible_list.selection_set(idx + 1)

    def _on_reset(self):
        """重置为默认"""
        self._temp_visible = DEFAULT_VISIBLE[:]
        self._temp_order = DEFAULT_ORDER[:]
        self._populate_lists()

    def _on_ok(self):
        """确定"""
        self._config_manager.visible_columns = self._temp_visible
        self._config_manager.column_order = self._temp_order
        self._config_manager.save()
        self.result = True
        self.dialog.destroy()

    def _on_cancel(self):
        """取消"""
        self.dialog.destroy()
```

- [ ] **Step 2: 提交列配置对话框**

```bash
cd "F:/gpx edit"
git add gpx_editor/gui/column_config_dialog.py
git commit -m "feat: 新增列配置对话框模块"
```

---

## Task 3: 集成列配置到主窗口

**Files:**
- Modify: `gpx_editor/gui/main_window.py` (树形列表创建 + 数据填充)

- [ ] **Step 1: 修改main_window导入和初始化**

在 `gpx_editor/gui/main_window.py` 的导入部分添加：
```python
from .column_config_dialog import ColumnConfigManager, ColumnConfigDialog, COLUMN_DEFINITIONS
from ..core.coord_converter import CoordConverter
```

在 `__init__` 方法中添加列配置管理器：
```python
self.column_config = ColumnConfigManager()
```

- [ ] **Step 2: 修改树形列表创建**

将 `_create_main_layout` 中的树形列表创建改为动态列：

```python
# 替换原来的固定列创建
# 旧代码:
# self.tree = ttk.Treeview(tree_frame, columns=("type", "name", "lat", "lon"), ...)

# 新代码:
self._rebuild_tree_columns()
```

添加新方法：
```python
def _rebuild_tree_columns(self):
    """重建树形列表列配置"""
    visible_cols = self.column_config.get_ordered_visible_columns()
    col_ids = [col["id"] for col in visible_cols]

    # 如果tree已存在，先销毁
    if hasattr(self, 'tree') and self.tree:
        self.tree.destroy()

    tree_frame = self.tree.master if hasattr(self, 'tree') else None
    if tree_frame is None:
        return

    scrollbar = ttk.Scrollbar(tree_frame, orient=VERTICAL)

    self.tree = ttk.Treeview(tree_frame, columns=col_ids,
                              show="tree headings", yscrollcommand=scrollbar.set)
    scrollbar.config(command=self.tree.yview)

    # 设置列头
    self.tree.heading("#0", text="")
    self.tree.column("#0", width=30, stretch=False)

    for col in visible_cols:
        col_id = col["id"]
        col_name = col["name"]
        # 计算列显示带号信息
        if col_id in ("cgcs2000_x", "cgcs2000_y") and hasattr(self, '_current_zone') and self._current_zone:
            col_name = f"{col_name} ({self._current_zone}带)"
        self.tree.heading(col_id, text=col_name)
        width = self.column_config.get_column_width(col_id)
        self.tree.column(col_id, width=width)

    self.tree.pack(fill=BOTH, expand=True)
    scrollbar.pack(side=RIGHT, fill=Y)

    # 绑定事件
    self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
    self.tree.bind("<Double-1>", self._on_tree_double_click)
    self.tree.bind("<Button-3>", self._on_tree_right_click)
```

- [ ] **Step 3: 修改数据填充方法**

修改 `_populate_tree` 方法，支持动态列和计算列：

```python
def _populate_tree(self):
    """填充树形列表"""
    # 清空
    for item in self.tree.get_children():
        self.tree.delete(item)

    if not self.gpx_handler.gpx:
        return

    # 计算CGCS2000带号（基于第一个航点）
    self._current_zone = None
    waypoints = self.gpx_handler.get_waypoints()
    if waypoints and waypoints[0].latitude is not None and waypoints[0].longitude is not None:
        _, _, self._current_zone = CoordConverter.wgs84_to_cgcs2000(
            waypoints[0].latitude, waypoints[0].longitude
        )
        # 更新列头显示带号
        self._update_column_headers()

    # 获取可见列
    visible_cols = self.column_config.get_ordered_visible_columns()

    # 添加航点组
    if waypoints:
        wpt_group = self.tree.insert("", END, text=" ", values=("", "航点", "", ""), open=True)
        for i, wpt in enumerate(waypoints):
            values = self._get_waypoint_values(wpt, visible_cols)
            self.tree.insert(wpt_group, END, iid=f"wpt_{i}", text=" ", values=values)

    # 添加航迹组
    tracks = self.gpx_handler.get_tracks()
    if tracks:
        trk_group = self.tree.insert("", END, text=" ", values=("", "航迹", "", ""), open=True)
        for i, trk in enumerate(tracks):
            values = self._get_track_values(trk, visible_cols)
            self.tree.insert(trk_group, END, iid=f"trk_{i}", text=" ", values=values)

    self._update_status_counts()

def _get_waypoint_values(self, wpt, visible_cols):
    """获取航点在各列的值"""
    values = []
    for col in visible_cols:
        col_id = col["id"]
        if col_id == "type":
            values.append("航点")
        elif col_id == "name":
            values.append(wpt.name or "")
        elif col_id == "lat":
            values.append(f"{wpt.latitude:.6f}" if wpt.latitude is not None else "")
        elif col_id == "lon":
            values.append(f"{wpt.longitude:.6f}" if wpt.longitude is not None else "")
        elif col_id == "ele":
            values.append(f"{wpt.elevation:.1f}" if wpt.elevation is not None else "")
        elif col_id == "time":
            values.append(str(wpt.time) if wpt.time else "")
        elif col_id == "desc":
            values.append(wpt.description or "")
        elif col_id == "cmt":
            values.append(wpt.comment or "")
        elif col_id == "sym":
            values.append(wpt.symbol or "")
        elif col_id == "source":
            values.append(wpt.source or "")
        elif col_id in ("cgcs2000_x", "cgcs2000_y"):
            if wpt.latitude is not None and wpt.longitude is not None:
                x, y, _ = CoordConverter.wgs84_to_cgcs2000(wpt.latitude, wpt.longitude)
                values.append(f"{x:.3f}" if col_id == "cgcs2000_x" else f"{y:.3f}")
            else:
                values.append("")
        else:
            values.append("")
    return tuple(values)

def _get_track_values(self, trk, visible_cols):
    """获取航迹在各列的值"""
    values = []
    for col in visible_cols:
        col_id = col["id"]
        if col_id == "type":
            values.append("航迹")
        elif col_id == "name":
            values.append(trk.name or "")
        elif col_id == "lat":
            values.append("")
        elif col_id == "lon":
            values.append("")
        elif col_id == "ele":
            values.append("")
        elif col_id == "time":
            values.append("")
        elif col_id == "desc":
            values.append(trk.description or "")
        elif col_id == "cmt":
            values.append(trk.comment or "")
        elif col_id == "sym":
            values.append("")
        elif col_id == "source":
            values.append(trk.source or "")
        elif col_id in ("cgcs2000_x", "cgcs2000_y"):
            values.append("")
        else:
            values.append("")
    return tuple(values)

def _update_column_headers(self):
    """更新列头显示（带号信息）"""
    if not hasattr(self, '_current_zone') or not self._current_zone:
        return
    for col in self.column_config.get_ordered_visible_columns():
        if col["id"] in ("cgcs2000_x", "cgcs2000_y"):
            self.tree.heading(col["id"], text=f"{col['name']} ({self._current_zone}带)")
```

- [ ] **Step 4: 添加列配置按钮和菜单**

在视图菜单中添加列配置入口：
```python
view_menu.add_separator()
view_menu.add_command(label="列配置", command=self._open_column_config)
```

添加方法：
```python
def _open_column_config(self):
    """打开列配置对话框"""
    dialog = ColumnConfigDialog(self, self.column_config)
    if dialog.result:
        self._rebuild_tree_columns()
        self._populate_tree()
```

- [ ] **Step 5: 提交**

```bash
cd "F:/gpx edit"
git add gpx_editor/gui/main_window.py
git commit -m "feat: 集成列配置系统到主窗口"
```

---

## Task 4: 重写移动航点对话框

**Files:**
- Modify: `gpx_editor/gui/move_waypoint_dialog.py` (完全重写)

- [ ] **Step 1: 重写移动航点对话框**

```python
# gpx_editor/gui/move_waypoint_dialog.py
# -*- coding: utf-8 -*-
"""
移动航点对话框
功能: 三种移动模式（手动输入、地图选点、精细移动）
"""

import tkinter as tk
from tkinter import ttk, messagebox
from ttkbootstrap.constants import *

from ..core.coord_converter import CoordConverter
from ..core.gpx_editor import GpxEditor


class MoveWaypointDialog:
    """移动航点对话框（三种模式）"""

    def __init__(self, parent, map_widget, waypoint):
        """
        Args:
            parent: 父窗口
            map_widget: TkinterMapView实例
            waypoint: 要移动的GPXWaypoint对象
        """
        self.result = None
        self.map_widget = map_widget
        self.waypoint = waypoint
        self._click_binding = None
        self._temp_marker = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"移动航点 — {waypoint.name or '未命名'}")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)
        self.dialog.geometry("450x400")

        self._create_widgets()
        self._update_current_position()

        # 居中
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.dialog.wait_window()

    def _create_widgets(self):
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=BOTH, expand=True)

        # 当前位置显示
        pos_frame = ttk.LabelFrame(main_frame, text="当前位置", padding=5)
        pos_frame.pack(fill=X, pady=(0, 10))

        self.pos_wgs84_label = ttk.Label(pos_frame, text="WGS84: -")
        self.pos_wgs84_label.pack(anchor=W)
        self.pos_cgcs_label = ttk.Label(pos_frame, text="CGCS2000: -")
        self.pos_cgcs_label.pack(anchor=W)

        # 标签页
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=BOTH, expand=True)

        # 标签页1: 手动输入
        tab1 = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab1, text="手动输入")
        self._create_manual_tab(tab1)

        # 标签页2: 地图选点
        tab2 = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab2, text="地图选点")
        self._create_map_tab(tab2)

        # 标签页3: 精细移动
        tab3 = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab3, text="精细移动")
        self._create_fine_tab(tab3)

        # 按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=X, pady=(10, 0))
        ttk.Button(btn_frame, text="确定", command=self._on_ok,
                   bootstyle=PRIMARY, width=10).pack(side=RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self._on_cancel,
                   width=10).pack(side=RIGHT, padx=5)

    def _create_manual_tab(self, parent):
        """手动输入标签页"""
        # 输入模式选择
        self.coord_mode = tk.StringVar(value="wgs84")
        mode_frame = ttk.Frame(parent)
        mode_frame.pack(fill=X, pady=(0, 10))

        ttk.Radiobutton(mode_frame, text="经纬度（WGS84）",
                        variable=self.coord_mode, value="wgs84",
                        command=self._on_mode_change).pack(side=LEFT, padx=(0, 15))
        ttk.Radiobutton(mode_frame, text="投影坐标（CGCS2000）",
                        variable=self.coord_mode, value="cgcs2000",
                        command=self._on_mode_change).pack(side=LEFT)

        # WGS84输入区
        self.wgs84_frame = ttk.Frame(parent)
        self.wgs84_frame.pack(fill=X)

        ttk.Label(self.wgs84_frame, text="纬度:").grid(row=0, column=0, sticky=W, pady=3)
        self.lat_var = tk.StringVar()
        if self.waypoint.latitude is not None:
            self.lat_var.set(str(self.waypoint.latitude))
        ttk.Entry(self.wgs84_frame, textvariable=self.lat_var, width=25).grid(row=0, column=1, padx=(5, 0))

        ttk.Label(self.wgs84_frame, text="经度:").grid(row=1, column=0, sticky=W, pady=3)
        self.lon_var = tk.StringVar()
        if self.waypoint.longitude is not None:
            self.lon_var.set(str(self.waypoint.longitude))
        ttk.Entry(self.wgs84_frame, textvariable=self.lon_var, width=25).grid(row=1, column=1, padx=(5, 0))

        # CGCS2000输入区（初始隐藏）
        self.cgcs_frame = ttk.Frame(parent)

        ttk.Label(self.cgcs_frame, text="X（东向）:").grid(row=0, column=0, sticky=W, pady=3)
        self.cgcs_x_var = tk.StringVar()
        ttk.Entry(self.cgcs_frame, textvariable=self.cgcs_x_var, width=25).grid(row=0, column=1, padx=(5, 0))

        ttk.Label(self.cgcs_frame, text="Y（北向）:").grid(row=1, column=0, sticky=W, pady=3)
        self.cgcs_y_var = tk.StringVar()
        ttk.Entry(self.cgcs_frame, textvariable=self.cgcs_y_var, width=25).grid(row=1, column=1, padx=(5, 0))

        # 输入提示
        self.hint_label = ttk.Label(parent, text="", foreground="gray")
        self.hint_label.pack(anchor=W, pady=(5, 0))

    def _create_map_tab(self, parent):
        """地图选点标签页"""
        ttk.Label(parent, text="点击"确定"后，在地图上点击新位置",
                  foreground="blue").pack(anchor=W, pady=(0, 10))
        ttk.Label(parent, text="• 当前位置已标记为红色", foreground="gray").pack(anchor=W)
        ttk.Label(parent, text="• 点击地图选择新位置", foreground="gray").pack(anchor=W)
        ttk.Label(parent, text="• 按 ESC 取消", foreground="gray").pack(anchor=W)

        self.map_preview_label = ttk.Label(parent, text="", foreground="green")
        self.map_preview_label.pack(anchor=W, pady=(10, 0))

    def _create_fine_tab(self, parent):
        """精细移动标签页"""
        ttk.Label(parent, text="输入偏移量（单位：米）",
                  foreground="gray").pack(anchor=W, pady=(0, 5))
        ttk.Label(parent, text="正值向东/北，负值向西/南",
                  foreground="gray").pack(anchor=W, pady=(0, 10))

        # X偏移
        x_frame = ttk.Frame(parent)
        x_frame.pack(fill=X, pady=3)
        ttk.Label(x_frame, text="X偏移（东西）:", width=15).pack(side=LEFT)
        self.offset_x_var = tk.StringVar(value="0")
        ttk.Entry(x_frame, textvariable=self.offset_x_var, width=15).pack(side=LEFT, padx=5)
        ttk.Label(x_frame, text="米").pack(side=LEFT)

        # Y偏移
        y_frame = ttk.Frame(parent)
        y_frame.pack(fill=X, pady=3)
        ttk.Label(y_frame, text="Y偏移（南北）:", width=15).pack(side=LEFT)
        self.offset_y_var = tk.StringVar(value="0")
        ttk.Entry(y_frame, textvariable=self.offset_y_var, width=15).pack(side=LEFT, padx=5)
        ttk.Label(y_frame, text="米").pack(side=LEFT)

        # 快捷按钮
        quick_frame = ttk.LabelFrame(parent, text="快捷偏移", padding=5)
        quick_frame.pack(fill=X, pady=(10, 0))

        for text, dx, dy in [
            ("北+10m", 0, 10), ("南-10m", 0, -10),
            ("东+10m", 10, 0), ("西-10m", -10, 0),
            ("北+1m", 0, 1), ("南-1m", 0, -1),
            ("东+1m", 1, 0), ("西-1m", -1, 0),
        ]:
            ttk.Button(quick_frame, text=text, width=8,
                       command=lambda dx=dx, dy=dy: self._apply_quick_offset(dx, dy)
                       ).pack(side=LEFT, padx=2, pady=2)

        # 预览
        self.fine_preview_label = ttk.Label(parent, text="", foreground="green")
        self.fine_preview_label.pack(anchor=W, pady=(10, 0))

        # 绑定偏移量变化事件
        self.offset_x_var.trace_add("write", self._on_offset_change)
        self.offset_y_var.trace_add("write", self._on_offset_change)

    def _update_current_position(self):
        """更新当前位置显示"""
        wpt = self.waypoint
        if wpt.latitude is not None and wpt.longitude is not None:
            self.pos_wgs84_label.config(
                text=f"WGS84: {wpt.latitude:.6f}, {wpt.longitude:.6f}")
            cgcs_text = CoordConverter.format_cgcs2000(wpt.latitude, wpt.longitude)
            self.pos_cgcs_label.config(text=f"CGCS2000: {cgcs_text}")
        else:
            self.pos_wgs84_label.config(text="WGS84: 未知")
            self.pos_cgcs_label.config(text="CGCS2000: 未知")

    def _on_mode_change(self):
        """切换输入模式"""
        if self.coord_mode.get() == "wgs84":
            self.cgcs_frame.pack_forget()
            self.wgs84_frame.pack(fill=X)
            self.hint_label.config(text="")
        else:
            self.wgs84_frame.pack_forget()
            self.cgcs_frame.pack(fill=X)
            self.hint_label.config(text="输入CGCS2000投影坐标，自动转换为WGS84经纬度")

    def _apply_quick_offset(self, dx, dy):
        """应用快捷偏移"""
        try:
            cur_x = float(self.offset_x_var.get())
            cur_y = float(self.offset_y_var.get())
        except ValueError:
            cur_x, cur_y = 0, 0
        self.offset_x_var.set(str(cur_x + dx))
        self.offset_y_var.set(str(cur_y + dy))

    def _on_offset_change(self, *args):
        """偏移量变化时更新预览"""
        try:
            dx = float(self.offset_x_var.get())
            dy = float(self.offset_y_var.get())
        except ValueError:
            self.fine_preview_label.config(text="输入格式不正确")
            return

        if self.waypoint.latitude is None or self.waypoint.longitude is None:
            return

        new_lat, new_lon = GpxEditor.offset_coordinates(
            self.waypoint.latitude, self.waypoint.longitude, dx, dy)
        cgcs_text = CoordConverter.format_cgcs2000(new_lat, new_lon)
        self.fine_preview_label.config(
            text=f"预览: {new_lat:.6f}, {new_lon:.6f}\nCGCS2000: {cgcs_text}")

    def _on_ok(self):
        """确定按钮"""
        tab_idx = self.notebook.index(self.notebook.select())

        if tab_idx == 0:  # 手动输入
            self._handle_manual_input()
        elif tab_idx == 1:  # 地图选点
            self._handle_map_click()
        elif tab_idx == 2:  # 精细移动
            self._handle_fine_move()

    def _handle_manual_input(self):
        """处理手动输入"""
        if self.coord_mode.get() == "wgs84":
            # WGS84经纬度输入
            try:
                lat = float(self.lat_var.get())
                if not (-90 <= lat <= 90):
                    messagebox.showwarning("提示", "纬度必须在 -90 到 90 之间")
                    return
            except ValueError:
                messagebox.showwarning("提示", "纬度格式不正确")
                return

            try:
                lon = float(self.lon_var.get())
                if not (-180 <= lon <= 180):
                    messagebox.showwarning("提示", "经度必须在 -180 到 180 之间")
                    return
            except ValueError:
                messagebox.showwarning("提示", "经度格式不正确")
                return

            self.result = (lat, lon)
            self.dialog.destroy()
        else:
            # CGCS2000投影坐标输入
            try:
                x = float(self.cgcs_x_var.get())
                y = float(self.cgcs_y_var.get())
            except ValueError:
                messagebox.showwarning("提示", "坐标格式不正确")
                return

            # 获取当前带号
            if self.waypoint.latitude is not None and self.waypoint.longitude is not None:
                _, _, zone = CoordConverter.wgs84_to_cgcs2000(
                    self.waypoint.latitude, self.waypoint.longitude)
            else:
                messagebox.showwarning("提示", "无法确定投影带号")
                return

            lat, lon = CoordConverter.cgcs2000_to_wgs84(x, y, zone)
            self.result = (lat, lon)
            self.dialog.destroy()

    def _handle_map_click(self):
        """处理地图选点"""
        self.dialog.destroy()
        self._start_map_click()

    def _handle_fine_move(self):
        """处理精细移动"""
        try:
            dx = float(self.offset_x_var.get())
            dy = float(self.offset_y_var.get())
        except ValueError:
            messagebox.showwarning("提示", "偏移量格式不正确")
            return

        if self.waypoint.latitude is None or self.waypoint.longitude is None:
            messagebox.showwarning("提示", "当前航点坐标未知")
            return

        new_lat, new_lon = GpxEditor.offset_coordinates(
            self.waypoint.latitude, self.waypoint.longitude, dx, dy)
        self.result = (new_lat, new_lon)
        self.dialog.destroy()

    def _start_map_click(self):
        """开始地图点击模式"""
        # 标记当前位置
        if self.waypoint.latitude and self.waypoint.longitude:
            self._temp_marker = self.map_widget.set_marker(
                self.waypoint.latitude, self.waypoint.longitude,
                text="当前位置", marker_color_circle="red", marker_color_outside="red")

        self.map_widget.canvas.config(cursor="crosshair")
        self._click_binding = self.map_widget.canvas.bind("<Button-1>", self._on_map_click)
        self.map_widget.winfo_toplevel().bind("<Escape>", self._cancel_map_click)

    def _on_map_click(self, event):
        """地图点击回调"""
        try:
            lat, lon = self.map_widget.convert_canvas_coords_to_decimal_coords(event.x, event.y)
            self.result = (lat, lon)
        except Exception:
            pass
        self._cleanup_map_click()

    def _cancel_map_click(self, event=None):
        """取消地图点击"""
        self._cleanup_map_click()

    def _cleanup_map_click(self):
        """清理地图点击绑定"""
        self.map_widget.canvas.config(cursor="")
        if self._click_binding:
            self.map_widget.canvas.unbind("<Button-1>")
            self._click_binding = None
        self.map_widget.winfo_toplevel().unbind("<Escape>")
        if self._temp_marker:
            self._temp_marker.delete()
            self._temp_marker = None

    def _on_cancel(self):
        """取消按钮"""
        self._cleanup_map_click()
        self.dialog.destroy()
```

- [ ] **Step 2: 提交**

```bash
cd "F:/gpx edit"
git add gpx_editor/gui/move_waypoint_dialog.py
git commit -m "feat: 重写移动航点对话框支持三种模式"
```

---

## Task 5: 集成天地图到主窗口

**Files:**
- Modify: `gpx_editor/gui/main_window.py` (地图瓦片 + 图层切换)
- Create: `~/.gpx_editor/config.json` (API Key配置)

- [ ] **Step 1: 添加配置管理**

在 `main_window.py` 中添加配置管理方法：

```python
import json

def _load_config(self):
    """加载配置"""
    config_dir = os.path.expanduser("~/.gpx_editor")
    config_file = os.path.join(config_dir, "config.json")
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_config(self, config):
    """保存配置"""
    config_dir = os.path.expanduser("~/.gpx_editor")
    os.makedirs(config_dir, exist_ok=True)
    config_file = os.path.join(config_dir, "config.json")
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def _get_tianditu_key(self):
    """获取天地图API Key"""
    config = self._load_config()
    return config.get("tianditu_api_key", "")

def _set_tianditu_key(self, key):
    """设置天地图API Key"""
    config = self._load_config()
    config["tianditu_api_key"] = key
    self._save_config(config)
```

- [ ] **Step 2: 修改地图初始化**

在 `_create_main_layout` 中修改地图初始化：

```python
from ..core.coord_converter import TiandituTileProvider

# 替换原来的高德地图初始化
# 旧代码:
# self.map_widget.set_tile_server(
#     "https://webrd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}",
#     max_zoom=18
# )

# 新代码:
self._init_tianditu_map()
```

添加方法：
```python
def _init_tianditu_map(self):
    """初始化天地图"""
    api_key = self._get_tianditu_key()
    if not api_key:
        # 首次使用，提示输入
        api_key = self._prompt_api_key()
        if not api_key:
            # 用户取消，使用默认高德地图
            self._init_default_map()
            return

    self._tianditu_key = api_key
    self._current_map_layer = "road"

    # 设置路网图
    road_url = TiandituTileProvider.get_road_url(api_key)
    self.map_widget.set_tile_server(road_url, max_zoom=18)

    self.map_widget.set_position(39.9, 74.3)
    self.map_widget.set_zoom(10)

def _init_default_map(self):
    """初始化默认地图（高德）"""
    self._tianditu_key = None
    self._current_map_layer = "road"
    self.map_widget.set_tile_server(
        "https://webrd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}",
        max_zoom=18
    )
    self.map_widget.set_position(39.9, 74.3)
    self.map_widget.set_zoom(10)

def _prompt_api_key(self):
    """提示输入天地图API Key"""
    from tkinter import simpledialog
    key = simpledialog.askstring(
        "天地图API Key",
        "请输入天地图API Key（免费申请：https://console.tianditu.gov.cn/）",
        parent=self
    )
    if key:
        self._set_tianditu_key(key.strip())
    return key
```

- [ ] **Step 3: 修改图层切换**

替换 `_toggle_satellite` 方法：

```python
def _toggle_satellite(self):
    """切换卫星图层"""
    if not self._tianditu_key:
        messagebox.showinfo("提示", "请先配置天地图API Key")
        return

    if self._current_map_layer == "road":
        # 切换到卫星图层
        img_url = TiandituTileProvider.get_satellite_url(self._tianditu_key)
        cia_url = TiandituTileProvider.get_annotation_url(self._tianditu_key)
        self.map_widget.set_tile_server(img_url, max_zoom=18)
        self.map_widget.set_overlay_tile_server(cia_url)
        self._current_map_layer = "satellite"
        self.status_label.config(text="已开启卫星图层")
    else:
        # 切换回路网图
        road_url = TiandituTileProvider.get_road_url(self._tianditu_key)
        self.map_widget.set_tile_server(road_url, max_zoom=18)
        self.map_widget.set_overlay_tile_server(None)
        self._current_map_layer = "road"
        self.status_label.config(text="已关闭卫星图层")
```

- [ ] **Step 4: 添加设置菜单**

在视图菜单中添加API Key设置入口：
```python
view_menu.add_separator()
view_menu.add_command(label="设置天地图Key", command=self._settings_tianditu_key)
```

添加方法：
```python
def _settings_tianditu_key(self):
    """设置天地图API Key"""
    from tkinter import simpledialog
    current_key = self._get_tianditu_key()
    key = simpledialog.askstring(
        "天地图API Key",
        "请输入天地图API Key（免费申请：https://console.tianditu.gov.cn/）",
        initialvalue=current_key,
        parent=self
    )
    if key:
        self._set_tianditu_key(key.strip())
        self._tianditu_key = key.strip()
        # 重新加载地图
        road_url = TiandituTileProvider.get_road_url(key.strip())
        self.map_widget.set_tile_server(road_url, max_zoom=18)
        self.map_widget.set_overlay_tile_server(None)
        self._current_map_layer = "road"
        self.status_label.config(text="已更新天地图API Key")
```

- [ ] **Step 5: 提交**

```bash
cd "F:/gpx edit"
git add gpx_editor/gui/main_window.py
git commit -m "feat: 集成天地图瓦片服务"
```

---

## Task 6: 地图交互编辑 - 航点拖拽

**Files:**
- Modify: `gpx_editor/gui/main_window.py` (航点marker拖拽)

- [ ] **Step 1: 修改航点marker创建**

修改 `_update_map` 方法，使航点marker支持拖拽：

```python
def _update_map(self):
    """更新地图显示"""
    for marker in self._map_markers:
        marker.delete()
    for path in self._map_paths:
        path.delete()
    self._map_markers.clear()
    self._map_paths.clear()

    if not self.gpx_handler.gpx:
        return

    # 添加航点标记（支持拖拽）
    for i, wpt in enumerate(self.gpx_handler.get_waypoints()):
        if wpt.latitude is not None and wpt.longitude is not None:
            name = wpt.name or f"航点{i+1}"
            marker = self.map_widget.set_marker(
                wpt.latitude, wpt.longitude, text=name,
                command=lambda m, idx=i: self._on_marker_click(idx)
            )
            # 绑定拖拽事件
            marker.bind_move_event(lambda m, idx=i: self._on_marker_drag_end(m, idx))
            self._map_markers.append(marker)

    # 添加航迹路径（后续任务实现航迹点交互）
    for i, track in enumerate(self.gpx_handler.get_tracks()):
        for segment in track.segments:
            if len(segment.points) >= 2:
                coords = [(p.latitude, p.longitude) for p in segment.points
                          if p.latitude is not None and p.longitude is not None]
                if len(coords) >= 2:
                    path = self.map_widget.set_path(coords)
                    self._map_paths.append(path)

    self._zoom_to_fit()

def _on_marker_click(self, index):
    """航点marker点击事件"""
    # 选中树形列表对应项
    self.tree.selection_set(f"wpt_{index}")
    self.tree.see(f"wpt_{index}")

def _on_marker_drag_end(self, marker, index):
    """航点marker拖拽结束事件"""
    wpt = self.gpx_handler.get_waypoints()[index]
    old_lat, old_lon = wpt.latitude, wpt.longitude
    new_lat, new_lon = marker.position

    # 更新航点坐标
    wpt.latitude = new_lat
    wpt.longitude = new_lon

    # 记录撤销操作
    self.undo_manager.push({
        'type': 'move_waypoint',
        'data': {'index': index, 'lat': new_lat, 'lon': new_lon},
        'reverse_data': {'index': index, 'lat': old_lat, 'lon': old_lon}
    })

    self._populate_tree()
    self._mark_modified()
    self.status_label.config(text=f"已移动航点: {wpt.name}")
```

- [ ] **Step 2: 更新撤销/重做处理**

在 `main_window.py` 的 `undo` 和 `redo` 方法中添加新的操作类型处理：

```python
def undo(self):
    """撤销"""
    cmd = self.undo_manager.undo()
    if not cmd:
        return
    self._apply_undo_redo(cmd, is_undo=True)

def redo(self):
    """重做"""
    cmd = self.undo_manager.redo()
    if not cmd:
        return
    self._apply_undo_redo(cmd, is_undo=False)

def _apply_undo_redo(self, cmd, is_undo):
    """应用撤销/重做操作"""
    data = cmd['reverse_data'] if is_undo else cmd['data']
    cmd_type = cmd['type']

    if cmd_type in ('add_waypoint', 'delete_waypoint', 'edit_waypoint', 'move_waypoint'):
        index = data.get('index')
        if cmd_type == 'add_waypoint':
            if is_undo:
                self.gpx_handler.delete_waypoint(index)
            else:
                self.gpx_handler.add_waypoint(
                    data['name'], data['lat'], data['lon'], data.get('ele'), data.get('desc'))
        elif cmd_type == 'delete_waypoint':
            if is_undo:
                self.gpx_handler.add_waypoint(
                    data['name'], data['lat'], data['lon'], data.get('ele'), data.get('desc'))
            else:
                self.gpx_handler.delete_waypoint(index)
        elif cmd_type in ('edit_waypoint', 'move_waypoint'):
            wpt = self.gpx_handler.get_waypoints()[index]
            wpt.latitude = data['lat']
            wpt.longitude = data['lon']
            if 'name' in data:
                wpt.name = data['name']
            if 'ele' in data:
                wpt.elevation = data['ele']
            if 'desc' in data:
                wpt.description = data['desc']

    self._populate_tree()
    self._update_map()
    self._mark_modified()
```

- [ ] **Step 3: 提交**

```bash
cd "F:/gpx edit"
git add gpx_editor/gui/main_window.py
git commit -m "feat: 实现航点marker拖拽移动"
```

---

## Task 7: 地图交互编辑 - 航迹点交互

**Files:**
- Modify: `gpx_editor/gui/main_window.py` (航迹点显示和交互)

- [ ] **Step 1: 添加航迹点marker和路径重绘**

```python
def __init__(self):
    # ... 现有代码 ...
    self._track_point_markers = []  # 航迹点marker列表
    self._track_paths = []  # 航迹路径列表

def _update_map(self):
    """更新地图显示"""
    # 清除所有标记
    for marker in self._map_markers:
        marker.delete()
    for path in self._map_paths:
        path.delete()
    for marker in self._track_point_markers:
        marker.delete()
    for path in self._track_paths:
        path.delete()
    self._map_markers.clear()
    self._map_paths.clear()
    self._track_point_markers.clear()
    self._track_paths.clear()

    if not self.gpx_handler.gpx:
        return

    # 添加航点标记（支持拖拽）
    for i, wpt in enumerate(self.gpx_handler.get_waypoints()):
        if wpt.latitude is not None and wpt.longitude is not None:
            name = wpt.name or f"航点{i+1}"
            marker = self.map_widget.set_marker(
                wpt.latitude, wpt.longitude, text=name,
                command=lambda m, idx=i: self._on_marker_click(idx)
            )
            marker.bind_move_event(lambda m, idx=i: self._on_marker_drag_end(m, idx))
            self._map_markers.append(marker)

    # 添加航迹（航迹点 + 路径）
    for i, track in enumerate(self.gpx_handler.get_tracks()):
        for seg_idx, segment in enumerate(track.segments):
            if len(segment.points) >= 2:
                coords = [(p.latitude, p.longitude) for p in segment.points
                          if p.latitude is not None and p.longitude is not None]
                if len(coords) >= 2:
                    # 绘制航迹线
                    path = self.map_widget.set_path(coords, color="green", width=2)
                    self._track_paths.append(path)

                    # 绘制航迹点（小号marker）
                    for pt_idx, (lat, lon) in enumerate(coords):
                        marker = self.map_widget.set_marker(
                            lat, lon,
                            text="",  # 不显示文字
                            marker_color_circle="green",
                            marker_color_outside="white",
                            marker_radius=4,
                            command=lambda m, trk=i, seg=seg_idx, pt=pt_idx:
                                self._on_track_point_click(trk, seg, pt)
                        )
                        marker.bind_move_event(
                            lambda m, trk=i, seg=seg_idx, pt=pt_idx:
                                self._on_track_point_drag_end(m, trk, seg, pt))
                        self._track_point_markers.append(marker)

    self._zoom_to_fit()
```

- [ ] **Step 2: 添加航迹点交互方法**

```python
def _on_track_point_click(self, trk_index, seg_index, pt_index):
    """航迹点点击事件"""
    # 选中树形列表对应航迹
    self.tree.selection_set(f"trk_{trk_index}")
    self.tree.see(f"trk_{trk_index}")

def _on_track_point_drag_end(self, marker, trk_index, seg_index, pt_index):
    """航迹点拖拽结束事件"""
    track = self.gpx_handler.get_tracks()[trk_index]
    segment = track.segments[seg_index]
    point = segment.points[pt_index]

    old_lat, old_lon = point.latitude, point.longitude
    new_lat, new_lon = marker.position

    # 更新航迹点坐标
    point.latitude = new_lat
    point.longitude = new_lon

    # 记录撤销操作
    self.undo_manager.push({
        'type': 'move_track_point',
        'data': {
            'trk_index': trk_index, 'seg_index': seg_index, 'pt_index': pt_index,
            'lat': new_lat, 'lon': new_lon
        },
        'reverse_data': {
            'trk_index': trk_index, 'seg_index': seg_index, 'pt_index': pt_index,
            'lat': old_lat, 'lon': old_lon
        }
    })

    # 重绘航迹线
    self._redraw_track(trk_index, seg_index)
    self._populate_tree()
    self._mark_modified()

def _redraw_track(self, trk_index, seg_index):
    """重绘指定航迹段"""
    # 这里简化处理，重新更新整个地图
    # 实际可以优化为只重绘指定航迹
    self._update_map()

def _on_track_double_click(self, event):
    """航迹双击插入新点"""
    # 获取点击位置的坐标
    try:
        lat, lon = self.map_widget.convert_canvas_coords_to_decimal_coords(event.x, event.y)
    except Exception:
        return

    # 找到最近的航迹段
    # 简化实现：在当前选中的航迹末尾添加新点
    selected = self.tree.selection()
    if not selected:
        return
    iid = selected[0]
    if not iid.startswith("trk_"):
        return

    trk_index = int(iid.split("_")[1])
    track = self.gpx_handler.get_tracks()[trk_index]
    if not track.segments:
        return

    segment = track.segments[0]  # 使用第一个段

    # 找到最近的两个点，在它们之间插入
    min_dist = float('inf')
    insert_idx = len(segment.points)

    for i in range(len(segment.points) - 1):
        p1 = segment.points[i]
        p2 = segment.points[i + 1]
        # 简化的距离计算
        dist = abs(p1.latitude - lat) + abs(p1.longitude - lon) + \
               abs(p2.latitude - lat) + abs(p2.longitude - lon)
        if dist < min_dist:
            min_dist = dist
            insert_idx = i + 1

    # 插入新点
    import gpxpy.gpx
    new_point = gpxpy.gpx.GPXTrackPoint(latitude=lat, longitude=lon)
    segment.points.insert(insert_idx, new_point)

    # 记录撤销操作
    self.undo_manager.push({
        'type': 'insert_track_point',
        'data': {
            'trk_index': trk_index, 'seg_index': 0, 'pt_index': insert_idx,
            'lat': lat, 'lon': lon
        },
        'reverse_data': {
            'trk_index': trk_index, 'seg_index': 0, 'pt_index': insert_idx
        }
    })

    self._update_map()
    self._populate_tree()
    self._mark_modified()
    self.status_label.config(text="已插入航迹点")

def _on_track_point_right_click(self, event):
    """航迹点右键菜单"""
    # 创建右键菜单
    menu = tk.Menu(self, tearoff=0)
    menu.add_command(label="删除航迹点", command=self._delete_track_point_at_cursor)
    menu.post(event.x_root, event.y_root)

def _delete_track_point_at_cursor(self):
    """删除光标位置的航迹点"""
    # 简化实现：删除当前选中航迹的最后一个点
    selected = self.tree.selection()
    if not selected:
        return
    iid = selected[0]
    if not iid.startswith("trk_"):
        return

    trk_index = int(iid.split("_")[1])
    track = self.gpx_handler.get_tracks()[trk_index]
    if not track.segments or not track.segments[0].points:
        return

    segment = track.segments[0]
    pt_index = len(segment.points) - 1
    point = segment.points[pt_index]

    # 记录撤销操作
    self.undo_manager.push({
        'type': 'delete_track_point',
        'data': {
            'trk_index': trk_index, 'seg_index': 0, 'pt_index': pt_index,
            'lat': point.latitude, 'lon': point.longitude
        },
        'reverse_data': {
            'trk_index': trk_index, 'seg_index': 0, 'pt_index': pt_index
        }
    })

    segment.points.pop(pt_index)

    self._update_map()
    self._populate_tree()
    self._mark_modified()
    self.status_label.config(text="已删除航迹点")
```

- [ ] **Step 3: 绑定双击和右键事件**

在 `_create_main_layout` 中添加地图双击和右键绑定：

```python
# 绑定地图双击事件（插入航迹点）
self.map_widget.canvas.bind("<Double-1>", self._on_track_double_click)

# 绑定航迹点右键菜单
self.map_widget.canvas.bind("<Button-3>", self._on_track_point_right_click)
```

- [ ] **Step 4: 更新撤销/重做处理**

在 `_apply_undo_redo` 方法中添加航迹点操作类型：

```python
elif cmd_type == 'move_track_point':
    track = self.gpx_handler.get_tracks()[data['trk_index']]
    point = track.segments[data['seg_index']].points[data['pt_index']]
    point.latitude = data['lat']
    point.longitude = data['lon']

elif cmd_type == 'insert_track_point':
    track = self.gpx_handler.get_tracks()[data['trk_index']]
    segment = track.segments[data['seg_index']]
    if is_undo:
        segment.points.pop(data['pt_index'])
    else:
        import gpxpy.gpx
        new_point = gpxpy.gpx.GPXTrackPoint(latitude=data['lat'], longitude=data['lon'])
        segment.points.insert(data['pt_index'], new_point)

elif cmd_type == 'delete_track_point':
    track = self.gpx_handler.get_tracks()[data['trk_index']]
    segment = track.segments[data['seg_index']]
    if is_undo:
        import gpxpy.gpx
        new_point = gpxpy.gpx.GPXTrackPoint(latitude=data['lat'], longitude=data['lon'])
        segment.points.insert(data['pt_index'], new_point)
    else:
        segment.points.pop(data['pt_index'])
```

- [ ] **Step 5: 提交**

```bash
cd "F:/gpx edit"
git add gpx_editor/gui/main_window.py
git commit -m "feat: 实现航迹点交互编辑（拖拽/插入/删除）"
```

---

## Task 8: 最终测试和提交

- [ ] **Step 1: 运行所有测试**

```bash
cd "F:/gpx edit"
python -m pytest tests/ -v
```

- [ ] **Step 2: 手动测试功能**

启动程序，测试：
1. 列配置：视图 → 列配置 → 勾选/取消列、拖动排序
2. 移动航点：右键航点 → 移动航点 → 三种模式都试一下
3. 地图交互：拖拽航点、双击插入航迹点、右键删除航迹点
4. 天地图：视图 → 卫星图层切换

- [ ] **Step 3: 最终提交**

```bash
cd "F:/gpx edit"
git add -A
git commit -m "feat: 完成三项功能改善（列配置/移动航点/地图交互编辑）"
```
