# GPX编辑器

GPX航点航迹编辑处理工具，支持GUI界面操作，提供航点/航迹基础操作和TXT/GDB格式导出功能。

## 功能特性

- **文件操作**: 打开、保存、新建GPX文件
- **航点管理**: 添加、删除、编辑航点
- **航迹管理**: 添加、删除、编辑航迹，航迹简化
- **导出功能**: 导出为TXT和GDB格式，支持批量导出
- **地图显示**: 在地图上显示航点和航迹

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行程序

```bash
python main.py
```

## 打包为可执行文件

```bash
pyinstaller --onefile --windowed main.py
```

## 技术栈

- Python 3.10+
- tkinter + ttkbootstrap
- gpxpy
- tkintermapview

## 目录结构

```
gpx_editor/
├── main.py              # 程序入口
├── gui/                 # GUI模块
│   ├── main_window.py   # 主窗口
│   ├── map_view.py      # 地图组件
│   ├── tree_view.py     # 树形列表
│   └── dialogs.py       # 对话框
├── core/                # 核心处理
│   ├── gpx_handler.py   # GPX读写
│   ├── waypoint.py      # 航点操作
│   ├── track.py         # 航迹操作
│   └── exporter.py      # 导出模块
└── utils/               # 工具函数
    └── helpers.py
```
