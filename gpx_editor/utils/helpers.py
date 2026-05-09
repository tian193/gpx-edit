# -*- coding: utf-8 -*-
"""
工具函数模块
功能: 通用辅助函数
"""

import os
from typing import List, Tuple
from math import radians, sin, cos, sqrt, atan2


def format_distance(meters: float) -> str:
    """格式化距离显示"""
    if meters < 1000:
        return f"{meters:.1f}米"
    else:
        return f"{meters/1000:.2f}公里"


def format_elevation(meters: float) -> str:
    """格式化海拔显示"""
    return f"{meters:.1f}米"


def format_coordinate(lat: float, lon: float) -> str:
    """格式化坐标显示"""
    lat_dir = "N" if lat >= 0 else "S"
    lon_dir = "E" if lon >= 0 else "W"
    return f"{abs(lat):.6f}°{lat_dir}, {abs(lon):.6f}°{lon_dir}"


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """计算两点间距离(米)"""
    R = 6371000
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))


def get_file_list(directory: str, extension: str = '.gpx') -> List[str]:
    """获取目录下指定扩展名的文件列表"""
    files = []
    for filename in os.listdir(directory):
        if filename.lower().endswith(extension.lower()):
            files.append(os.path.join(directory, filename))
    return sorted(files)


def ensure_directory(path: str):
    """确保目录存在"""
    os.makedirs(path, exist_ok=True)


def get_filename_without_extension(filepath: str) -> str:
    """获取不含扩展名的文件名"""
    return os.path.splitext(os.path.basename(filepath))[0]
