# -*- coding: utf-8 -*-
"""
导出模块
功能: 导出GPX为TXT和GDB格式
"""

import os
from typing import List, Optional
from datetime import datetime
import gpxpy.gpx


class TxtExporter:
    """TXT格式导出器"""

    @staticmethod
    def export(gpx: gpxpy.gpx.GPX, filepath: str):
        """导出GPX为TXT格式
        按GPX 1.1字段结构导出
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            # 写入文件头
            f.write("# GPX 1.1 数据导出\n")
            f.write(f"# 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("#" + "=" * 60 + "\n\n")

            # 写入航点
            if gpx.waypoints:
                f.write("[航点]\n")
                f.write("序号,名称,经度,纬度,海拔,描述\n")
                for i, wpt in enumerate(gpx.waypoints, 1):
                    desc = wpt.description or ""
                    ele = f"{wpt.elevation:.2f}" if wpt.elevation else ""
                    f.write(f"{i},{wpt.name},{wpt.longitude:.6f},{wpt.latitude:.6f},{ele},{desc}\n")
                f.write("\n")

            # 写入航迹
            if gpx.tracks:
                for ti, track in enumerate(gpx.tracks, 1):
                    f.write(f"[航迹 {ti}] {track.name or '未命名'}\n")
                    f.write("段号,点序号,经度,纬度,海拔,时间\n")

                    for si, segment in enumerate(track.segments, 1):
                        for pi, point in enumerate(segment.points, 1):
                            ele = f"{point.elevation:.2f}" if point.elevation else ""
                            time_str = point.time.strftime("%Y-%m-%d %H:%M:%S") if point.time else ""
                            f.write(f"{si},{pi},{point.longitude:.6f},{point.latitude:.6f},{ele},{time_str}\n")
                    f.write("\n")

    @staticmethod
    def batch_export(input_dir: str, output_dir: str) -> List[str]:
        """批量导出目录下所有GPX文件"""
        exported = []
        for filename in os.listdir(input_dir):
            if filename.lower().endswith('.gpx'):
                input_path = os.path.join(input_dir, filename)
                output_path = os.path.join(output_dir, os.path.splitext(filename)[0] + '.txt')

                try:
                    import gpxpy
                    with open(input_path, 'r', encoding='utf-8') as f:
                        gpx = gpxpy.parse(f)
                    TxtExporter.export(gpx, output_path)
                    exported.append(filename)
                except Exception as e:
                    print(f"导出失败 {filename}: {e}")

        return exported


class GdbExporter:
    """Garmin GDB格式导出器"""

    @staticmethod
    def export(gpx: gpxpy.gpx.GPX, filepath: str):
        """导出GPX为Garmin GDB格式
        GDB是Garmin设备的数据库格式
        """
        # GDB文件头结构
        GDB_HEADER = b'MsRcd\x00\x00\x00'
        GDB_VERSION = b'\x02\x00'

        with open(filepath, 'wb') as f:
            # 写入文件头
            f.write(GDB_HEADER)
            f.write(GDB_VERSION)

            # 写入数据记录
            # 航点记录
            for wpt in gpx.waypoints:
                GdbExporter._write_waypoint(f, wpt)

            # 航迹记录
            for track in gpx.tracks:
                GdbExporter._write_track(f, track)

    @staticmethod
    def _write_waypoint(f, waypoint: gpxpy.gpx.GPXWaypoint):
        """写入航点记录"""
        # 记录类型: 航点 (0x01)
        record_type = b'\x01'
        f.write(record_type)

        # 航点名称 (最多10字节)
        name = (waypoint.name or "")[:10].encode('ascii', errors='ignore')
        name = name.ljust(10, b'\x00')
        f.write(name)

        # 坐标 (度转为Garmin格式: 0x80000000 = 180度)
        lat = int(waypoint.latitude * 0x80000000 / 180)
        lon = int(waypoint.longitude * 0x80000000 / 180)
        f.write(lat.to_bytes(4, 'little', signed=True))
        f.write(lon.to_bytes(4, 'little', signed=True))

        # 海拔 (米转英尺, 偏移量1000)
        if waypoint.elevation is not None:
            alt = int(waypoint.elevation * 3.28084 + 1000)
        else:
            alt = 1000
        f.write(alt.to_bytes(2, 'little'))

        # 符号 (默认0)
        f.write(b'\x00\x00')

        # 显示选项
        f.write(b'\x00')

        # 颜色
        f.write(b'\x00')

        # 属性掩码
        f.write(b'\x00\x00\x00\x00')

        # 空终止
        f.write(b'\x00')

    @staticmethod
    def _write_track(f, track: gpxpy.gpx.GPXTrack):
        """写入航迹记录"""
        # 记录类型: 航迹 (0x06)
        record_type = b'\x06'
        f.write(record_type)

        # 航迹名称
        name = (track.name or "")[:10].encode('ascii', errors='ignore')
        name = name.ljust(10, b'\x00')
        f.write(name)

        # 航迹点数量
        point_count = sum(len(seg.points) for seg in track.segments)
        f.write(point_count.to_bytes(4, 'little'))

        # 写入航迹点
        for segment in track.segments:
            for point in segment.points:
                lat = int(point.latitude * 0x80000000 / 180)
                lon = int(point.longitude * 0x80000000 / 180)
                f.write(lat.to_bytes(4, 'little', signed=True))
                f.write(lon.to_bytes(4, 'little', signed=True))

                if point.elevation is not None:
                    alt = int(point.elevation * 3.28084 + 1000)
                else:
                    alt = 1000
                f.write(alt.to_bytes(2, 'little'))

    @staticmethod
    def batch_export(input_dir: str, output_dir: str) -> List[str]:
        """批量导出目录下所有GPX文件"""
        exported = []
        for filename in os.listdir(input_dir):
            if filename.lower().endswith('.gpx'):
                input_path = os.path.join(input_dir, filename)
                output_path = os.path.join(output_dir, os.path.splitext(filename)[0] + '.gdb')

                try:
                    import gpxpy
                    with open(input_path, 'r', encoding='utf-8') as f:
                        gpx = gpxpy.parse(f)
                    GdbExporter.export(gpx, output_path)
                    exported.append(filename)
                except Exception as e:
                    print(f"导出失败 {filename}: {e}")

        return exported
