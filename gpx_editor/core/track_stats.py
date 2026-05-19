# -*- coding: utf-8 -*-
"""
航迹统计计算模块
功能: 航迹点级别的详细统计数据（距离、速度、方向等）
"""

import math
from typing import List, Optional, Tuple
from ..utils.helpers import haversine_distance


def get_all_points(track) -> list:
    """获取航迹的所有点（跨航段展平）"""
    points = []
    for seg in track.segments:
        points.extend(seg.points)
    return points


def segment_distance(p1, p2) -> float:
    """计算两点间距离(米)"""
    if p1.latitude is None or p1.longitude is None:
        return 0.0
    if p2.latitude is None or p2.longitude is None:
        return 0.0
    return haversine_distance(p1.latitude, p1.longitude, p2.latitude, p2.longitude)


def segment_time(p1, p2) -> Optional[float]:
    """计算两点间时间差(秒)，无时间数据返回None"""
    if p1.time is None or p2.time is None:
        return None
    try:
        dt = p2.time - p1.time
        return dt.total_seconds()
    except Exception:
        return None


def segment_speed(dist_m: float, time_s: Optional[float]) -> Optional[float]:
    """计算航段速度(km/h)，无时间数据返回None"""
    if time_s is None or time_s <= 0:
        return None
    return (dist_m / time_s) * 3.6


def bearing(p1, p2) -> Optional[float]:
    """计算从p1到p2的方位角(0-360度，N=0)"""
    if p1.latitude is None or p1.longitude is None:
        return None
    if p2.latitude is None or p2.longitude is None:
        return None
    lat1 = math.radians(p1.latitude)
    lat2 = math.radians(p2.latitude)
    dlon = math.radians(p2.longitude - p1.longitude)
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    brng = math.degrees(math.atan2(x, y))
    return (brng + 360) % 360


def format_time_delta(seconds: float) -> str:
    """格式化时间差为 MM:SS 或 HH:MM:SS"""
    if seconds < 0:
        seconds = -seconds
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def format_direction(degrees: float) -> str:
    """格式化方位角为方向文字"""
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = round(degrees / 45) % 8
    return directions[idx]


def get_point_details(track) -> List[dict]:
    """获取每个航迹点的详细信息列表

    返回列表，每个元素为字典：
    {
        'index': int,           # 全局序号
        'time': datetime|None,
        'elevation': float|None,
        'latitude': float,
        'longitude': float,
        'seg_distance': float,  # 到下一点的距离(m)，最后一点为0
        'seg_time': float|None, # 到下一点的时间差(秒)
        'seg_speed': float|None,# 航段速度(km/h)
        'seg_bearing': float|None, # 方位角
    }
    """
    all_points = get_all_points(track)
    details = []
    for i, pt in enumerate(all_points):
        detail = {
            'index': i,
            'time': pt.time,
            'elevation': pt.elevation,
            'latitude': pt.latitude,
            'longitude': pt.longitude,
            'seg_distance': 0.0,
            'seg_time': None,
            'seg_speed': None,
            'seg_bearing': None,
        }
        if i < len(all_points) - 1:
            next_pt = all_points[i + 1]
            dist = segment_distance(pt, next_pt)
            t = segment_time(pt, next_pt)
            detail['seg_distance'] = dist
            detail['seg_time'] = t
            detail['seg_speed'] = segment_speed(dist, t)
            detail['seg_bearing'] = bearing(pt, next_pt)
        details.append(detail)
    return details


def get_track_statistics(track) -> dict:
    """获取航迹的汇总统计数据

    返回字典：
    {
        'total_points': int,
        'total_distance': float,      # 米
        'total_time': float|None,     # 秒
        'avg_speed': float|None,      # km/h
        'max_elevation': float|None,
        'min_elevation': float|None,
        'elevation_gain': float,      # 米
        'elevation_loss': float,      # 米
    }
    """
    all_points = get_all_points(track)
    total_points = len(all_points)

    # 总距离
    total_distance = 0.0
    for i in range(1, total_points):
        total_distance += segment_distance(all_points[i - 1], all_points[i])

    # 总时间（第一个有点时间的点到最后一个有点时间的点）
    total_time = None
    times = [p.time for p in all_points if p.time is not None]
    if len(times) >= 2:
        total_time = (times[-1] - times[0]).total_seconds()

    # 平均速度
    avg_speed = None
    if total_time and total_time > 0:
        avg_speed = (total_distance / total_time) * 3.6

    # 海拔统计
    elevations = [p.elevation for p in all_points if p.elevation is not None]
    max_elevation = max(elevations) if elevations else None
    min_elevation = min(elevations) if elevations else None

    # 累计爬升/下降
    elevation_gain = 0.0
    elevation_loss = 0.0
    for i in range(1, total_points):
        e1 = all_points[i - 1].elevation
        e2 = all_points[i].elevation
        if e1 is not None and e2 is not None:
            diff = e2 - e1
            if diff > 0:
                elevation_gain += diff
            else:
                elevation_loss += abs(diff)

    return {
        'total_points': total_points,
        'total_distance': total_distance,
        'total_time': total_time,
        'avg_speed': avg_speed,
        'max_elevation': max_elevation,
        'min_elevation': min_elevation,
        'elevation_gain': elevation_gain,
        'elevation_loss': elevation_loss,
    }


def get_elevation_profile_data(track) -> List[Tuple[float, float, object]]:
    """获取海拔剖面图数据

    返回列表，每个元素为 (累计距离m, 海拔m, 时间)
    """
    all_points = get_all_points(track)
    if not all_points:
        return []

    profile = []
    cumulative_dist = 0.0
    for i, pt in enumerate(all_points):
        if i > 0:
            cumulative_dist += segment_distance(all_points[i - 1], pt)
        ele = pt.elevation if pt.elevation is not None else 0.0
        profile.append((cumulative_dist, ele, pt.time))
    return profile
