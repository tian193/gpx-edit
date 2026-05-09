# GPX Editor - 项目规范

## 项目概述
GPX航点航迹编辑处理工具，支持GUI界面操作，提供航点/航迹基础操作和TXT/GDB格式导出功能。

## 技术栈
- **语言**: Python 3.10+
- **GUI**: tkinter + ttkbootstrap
- **GPX处理**: gpxpy
- **地图显示**: tkintermapview
- **打包**: PyInstaller

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

## 开发规则

### 代码规范
- 使用中文注释和文档字符串
- 遵循PEP 8编码规范
- 函数和变量使用snake_case命名
- 类名使用PascalCase命名
- 每个模块文件顶部添加模块说明注释

### GUI规范
- 所有界面文字使用中文
- 窗口标题格式: "GPX编辑器 - [功能名]"
- 按钮文字简洁明了
- 操作结果提供明确反馈

### 提交规范
- feat: 新功能
- fix: 修复bug
- refactor: 重构
- docs: 文档更新
- test: 测试相关

## 常用命令

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行程序
```bash
python main.py
```

### 运行测试
```bash
pytest tests/
```

### 打包
```bash
pyinstaller --onefile --windowed main.py
```

## Skills使用说明
项目已安装以下skills到 `.agents/skills/` 目录：
- brainstorm: 方案设计讨论
- implement-task: 任务实现
- plan-task: 任务规划
- kaizen: 代码优化重构
- test-driven-development: 测试驱动开发
- write-tests: 编写测试
- update-docs: 更新文档
- create-rule: 创建开发规范
