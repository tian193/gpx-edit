# -*- coding: utf-8 -*-
"""
GPX编辑器 - 程序入口
功能: GPX航点航迹编辑处理工具
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gpx_editor.gui.main_window import MainWindow


def main():
    """程序主入口"""
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
