# -*- coding: utf-8 -*-
"""
航点操作模块
功能: 航点数据处理和操作
"""

from typing import List, Optional, Tuple
from dataclasses import dataclass
from ..utils.helpers import haversine_distance


@dataclass
class WaypointData:
    """航点数据"""
    name: str
    latitude: float
    longitude: float
    elevation: Optional[float] = None
    description: Optional[str] = None
    time: Optional[str] = None

    def validate(self) -> bool:
        """验证航点数据"""
        if not (-90 <= self.latitude <= 90):
            return False
        if not (-180 <= self.longitude <= 180):
            return False
        return True

    def to_tuple(self) -> Tuple[float, float, Optional[float]]:
        """转换为元组"""
        return (self.latitude, self.longitude, self.elevation)


class WaypointManager:
    """航点管理器"""

    @staticmethod
    def sort_by_name(waypoints: List[WaypointData], reverse: bool = False) -> List[WaypointData]:
        """按名称排序"""
        return sorted(waypoints, key=lambda w: w.name, reverse=reverse)

    @staticmethod
    def sort_by_distance(waypoints: List[WaypointData],
                         center: Tuple[float, float]) -> List[WaypointData]:
        """按距离中心点排序"""
        center_lat, center_lon = center
        return sorted(waypoints,
                      key=lambda w: haversine_distance(w.latitude, w.longitude, center_lat, center_lon))

    @staticmethod
    def filter_by_bounds(waypoints: List[WaypointData],
                         min_lat: float, min_lon: float,
                         max_lat: float, max_lon: float) -> List[WaypointData]:
        """按边界过滤航点"""
        return [w for w in waypoints
                if min_lat <= w.latitude <= max_lat
                and min_lon <= w.longitude <= max_lon]

    @staticmethod
    def calculate_distance(wp1: WaypointData, wp2: WaypointData) -> float:
        """计算两点间距离(米)"""
        return haversine_distance(wp1.latitude, wp1.longitude, wp2.latitude, wp2.longitude)
