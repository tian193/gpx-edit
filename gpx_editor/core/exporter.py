# -*- coding: utf-8 -*-
"""
导出模块
功能: 导出GPX为TXT和GDB格式
GDB格式基于GPSBabel逆向工程规范实现
"""

import os
import struct
from typing import List, Optional
from datetime import datetime, timezone
import gpxpy.gpx


class TxtExporter:
    """TXT格式导出器 - MapSource兼容格式"""

    @staticmethod
    def _format_coord_dms(decimal_degrees, is_lat=True):
        """将十进制度转换为度分格式
        例如: 39.879295 -> N39 52.758
        """
        if decimal_degrees is None:
            return ""

        abs_deg = abs(decimal_degrees)
        degrees = int(abs_deg)
        minutes = (abs_deg - degrees) * 60

        if is_lat:
            hemisphere = 'N' if decimal_degrees >= 0 else 'S'
        else:
            hemisphere = 'E' if decimal_degrees >= 0 else 'W'

        return f"{hemisphere}{degrees} {minutes:06.3f}"

    @staticmethod
    def _format_time(time_obj):
        """格式化时间为MapSource格式
        例如: 2026-04-16 12:43:11 -> 4/16/2026 12:43:11 PM
        """
        if time_obj is None:
            return ""

        month = time_obj.month
        day = time_obj.day
        year = time_obj.year
        hour = time_obj.hour
        minute = time_obj.minute
        second = time_obj.second

        ampm = "AM" if hour < 12 else "PM"
        display_hour = hour % 12
        if display_hour == 0:
            display_hour = 12

        return f"{month}/{day}/{year} {display_hour}:{minute:02d}:{second:02d} {ampm}"

    @staticmethod
    def export(gpx: gpxpy.gpx.GPX, filepath: str):
        """导出GPX为MapSource TXT格式"""
        with open(filepath, 'w', encoding='gbk') as f:
            # 写入Grid和Datum头部
            f.write("Grid\t经纬度/度分 hddd°mm.mmm'\n")
            f.write("Datum\tWGS 84\n")
            f.write("\n")

            # 写入Header行
            f.write("Header\tName\tDescription\tType\tPosition\tAltitude\tDepth\tProximity\tTemperature\tDisplay Mode\tColor\tSymbol\tFacility\tCity\tState\tCountry\tDate Modified\tLink\tCategories\n")
            f.write("\n")

            # 写入航点
            if gpx.waypoints:
                for wpt in gpx.waypoints:
                    name = wpt.name or ""
                    desc = wpt.description or ""
                    time_str = TxtExporter._format_time(wpt.time) if wpt.time else ""
                    position = f"{TxtExporter._format_coord_dms(wpt.latitude, True)} {TxtExporter._format_coord_dms(wpt.longitude, False)}"
                    altitude = f"{int(wpt.elevation)} m" if wpt.elevation is not None else ""

                    f.write(f"Waypoint\t{name}\t{time_str}\tUser Waypoint\t{position}\t{altitude}\t\t\t\tSymbol & Name\tUnknown\tFlag, Blue\t\t\t\t\t{time_str}\t\t\n")

            # 写入航迹
            if gpx.tracks:
                for track in gpx.tracks:
                    track_name = track.name or ""

                    # 写入航迹头
                    f.write(f"Track\t{track_name}\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\n")

                    # 写入航迹点
                    for segment in track.segments:
                        for point in segment.points:
                            position = f"{TxtExporter._format_coord_dms(point.latitude, True)} {TxtExporter._format_coord_dms(point.longitude, False)}"
                            altitude = f"{int(point.elevation)} m" if point.elevation is not None else ""
                            time_str = TxtExporter._format_time(point.time) if point.time else ""

                            f.write(f"Trackpoint\t\t{time_str}\t\t{position}\t{altitude}\t\t\t\t\t\t\t\t\t\t\t\t\t\n")

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
    """Garmin GDB v3格式导出器 - 基于GPSBabel逆向工程规范"""

    # GDB版本常量
    _GDB_VER = 3
    _FILE_FORMAT = _GDB_VER + 0x6a  # 0x6d = 109
    _PROGRAM_VERSION = 605  # 6.5 -> 6*100 + 5

    # 未知高度的哨兵值
    _UNKNOWN_ALT = -1e25

    # 默认图标: Flag, Blue (141)
    _DEFAULT_ICON = 141

    # GPX符号名称到Garmin MapSource图标编号的映射表
    # 基于GPSBabel garmin_icon_tables.h
    _ICON_MAP = {
        # 常用符号
        "airport": 107,
        "amusement park": 73,
        "ball park": 55,
        "bank": 6,
        "bar": 13,
        "beach": 104,
        "bell": 1,
        "boat ramp": 37,
        "bowling": 74,
        "bridge": 93,
        "building": 94,
        "campground": 38,
        "car": 56,
        "car rental": 75,
        "car repair": 76,
        "cemetery": 95,
        "church": 96,
        "circle with x": 65,
        "city (capitol)": 72,
        "city (large)": 71,
        "city (medium)": 70,
        "city (small)": 69,
        "small city": 69,
        "civil": 97,
        "controlled area": 52,
        "convenience store": 89,
        "crossing": 98,
        "dam": 51,
        "danger area": 53,
        "department store": 87,
        "diver down flag 1": 4,
        "diver down flag 2": 5,
        "drinking water": 41,
        "exit": 63,
        "fast food": 77,
        "fishing area": 7,
        "fitness center": 78,
        "flag": 64,
        "flag, blue": 141,
        "flag, green": 142,
        "flag, red": 140,
        "forest": 105,
        "gas station": 8,
        "geocache": 117,
        "geocache found": 118,
        "golf course": 79,
        "ground transportation": 80,
        "heliport": 108,
        "horn": 2,
        "hunting area": 9,
        "information": 109,
        "levee": 99,
        "light": 10,
        "live theater": 81,
        "lodging": 82,
        "man overboard": 11,
        "marina": 12,
        "mile marker": 66,
        "movie theater": 83,
        "museum": 84,
        "navaid, amber": 16389,
        "navaid, black": 16390,
        "navaid, blue": 16391,
        "navaid, green": 16392,
        "navaid, green/red": 16393,
        "navaid, green/white": 16394,
        "navaid, orange": 16395,
        "navaid, red": 16396,
        "navaid, red/green": 16397,
        "navaid, red/white": 16398,
        "navaid, white": 16400,
        "navaid, white/green": 16401,
        "navaid, white/red": 16402,
        "park": 85,
        "parking": 14,
        "pharmacy": 110,
        "picnic area": 15,
        "pizza": 86,
        "police station": 16,
        "post office": 111,
        "rv park": 39,
        "restroom": 17,
        "restaurant": 88,
        "scenic area": 112,
        "school": 113,
        "shipwreck": 100,
        "shopping center": 114,
        "short tower": 101,
        "ski resort": 115,
        "stadium": 116,
        "summit": 102,
        "swimming area": 18,
        "tall tower": 103,
        "telephone": 19,
        "toll booth": 20,
        "trail head": 21,
        "truck stop": 22,
        "tunnel": 100,
        "water hydrant": 40,
        "waypoint": 18,
        "wrecker": 23,
        "zoo": 106,
        # 中文符号名称映射
        "航点": 18,
        "旗": 64,
        "蓝旗": 141,
        "红旗": 140,
        "绿旗": 142,
        "机场": 107,
        "加油站": 8,
        "餐厅": 88,
        "住宿": 82,
        "停车场": 14,
        "医院": 109,
        "学校": 113,
        "银行": 6,
        "商店": 89,
        "厕所": 17,
        "营地": 38,
        "钓鱼": 7,
        "露营": 38,
        "船": 37,
        "桥": 93,
        "教堂": 96,
        "墓地": 95,
        "危险": 53,
        "信息": 109,
        "公园": 85,
        "加油站": 8,
        " summit": 102,
        "山顶": 102,
    }

    @staticmethod
    def _write_cstr(buf: bytearray, s: str):
        """写入null结尾的C字符串"""
        if s:
            buf.extend(s.encode('ascii', errors='ignore'))
        buf.append(0)

    @staticmethod
    def _write_int16(buf: bytearray, val: int):
        """写入16位小端整数"""
        buf.extend(struct.pack('<h', val))

    @staticmethod
    def _write_uint16(buf: bytearray, val: int):
        """写入16位小端无符号整数"""
        buf.extend(struct.pack('<H', val))

    @staticmethod
    def _write_int32(buf: bytearray, val: int):
        """写入32位小端整数"""
        buf.extend(struct.pack('<i', val))

    @staticmethod
    def _write_dbl(buf: bytearray, value: float, default: float):
        """写入双精度浮点数（带标志字节）
        如果值等于默认值，只写0x00；否则写0x01+8字节double
        """
        if value == default or value is None:
            buf.append(0)
        else:
            buf.append(1)
            buf.extend(struct.pack('<d', value))

    @staticmethod
    def _write_time(buf: bytearray, time_obj):
        """写入时间（带标志字节）
        如果有时间，写0x01+4字节Unix时间戳；否则写0x00
        """
        if time_obj is not None:
            # 转换为Unix时间戳
            if time_obj.tzinfo is None:
                ts = int(time_obj.replace(tzinfo=timezone.utc).timestamp())
            else:
                ts = int(time_obj.timestamp())
            buf.append(1)
            buf.extend(struct.pack('<i', ts))
        else:
            buf.append(0)

    @staticmethod
    def _write_latlon(buf: bytearray, degrees: float):
        """写入坐标（半圆格式）
        semicircles = degrees * 2^31 / 180
        """
        semicircles = int(degrees * 0x80000000 / 180)
        buf.extend(struct.pack('<i', semicircles))

    @staticmethod
    def _format_name(name_str: str) -> str:
        """格式化航点名称, 最多10字符"""
        name = name_str or "WPT"
        # 截断到10字符
        return name[:10]

    @staticmethod
    def _get_icon_number(symbol_name: str) -> int:
        """根据GPX符号名称获取Garmin图标编号
        如果找不到匹配，返回默认图标(Flag, Blue=141)
        """
        if not symbol_name:
            return GdbExporter._DEFAULT_ICON

        # 尝试精确匹配（不区分大小写）
        key = symbol_name.strip().lower()
        if key in GdbExporter._ICON_MAP:
            return GdbExporter._ICON_MAP[key]

        # 尝试部分匹配
        for map_key, icon_num in GdbExporter._ICON_MAP.items():
            if map_key in key or key in map_key:
                return icon_num

        return GdbExporter._DEFAULT_ICON

    @staticmethod
    def _build_record_data(name_str: str, lat: float, lon: float,
                           altitude: float = None, time_obj=None,
                           symbol: str = None,
                           wpt_class: int = 0, display: int = 1) -> bytearray:
        """构建一条航点记录的数据部分（不含长度和类型前缀）"""
        buf = bytearray()

        # 1. 航点名称
        GdbExporter._write_cstr(buf, GdbExporter._format_name(name_str))

        # 2. 航点类别 (0=用户航点)
        GdbExporter._write_int32(buf, wpt_class)

        # 3. 国家代码（空）
        GdbExporter._write_cstr(buf, "")

        # 4. 子类数据 (4+12+2=18字节)
        buf.extend(b'\x00' * 4)   # subclass part 1
        buf.extend(b'\xff' * 12)  # subclass part 2
        buf.extend(b'\x00' * 2)   # subclass part 3

        # 5. 未知字段 (4字节)
        buf.extend(b'\xff' * 4)

        # 6. 纬度
        GdbExporter._write_latlon(buf, lat)

        # 7. 经度
        GdbExporter._write_latlon(buf, lon)

        # 8. 高度
        alt = altitude if altitude is not None else GdbExporter._UNKNOWN_ALT
        GdbExporter._write_dbl(buf, alt, GdbExporter._UNKNOWN_ALT)

        # 9. 备注/描述（空）
        GdbExporter._write_cstr(buf, "")

        # 10. 接近距离
        GdbExporter._write_dbl(buf, GdbExporter._UNKNOWN_ALT, GdbExporter._UNKNOWN_ALT)

        # 11. 显示模式 (0=仅符号, 1=符号和名称, 2=符号和注释)
        GdbExporter._write_int32(buf, display)

        # 12. 颜色 (0=默认)
        GdbExporter._write_int32(buf, 0)

        # 13. 图标
        icon_num = GdbExporter._get_icon_number(symbol)
        GdbExporter._write_int32(buf, icon_num)

        # 14. 城市（空）
        GdbExporter._write_cstr(buf, "")

        # 15. 州/省（空）
        GdbExporter._write_cstr(buf, "")

        # 16. 设施（空）
        GdbExporter._write_cstr(buf, "")

        # 17. 未知字节
        buf.append(0)

        # 18. 深度
        GdbExporter._write_dbl(buf, GdbExporter._UNKNOWN_ALT, GdbExporter._UNKNOWN_ALT)

        # 19. GDB v3: 地址（空字符串）
        GdbExporter._write_cstr(buf, "")

        # 20. 指令相关 (5字节)
        buf.extend(b'\x00' * 5)

        # 21. 指令/描述（空）
        GdbExporter._write_cstr(buf, "")

        # 22. URL数量 (0)
        GdbExporter._write_int32(buf, 0)

        # 23. 类别 (默认类别)
        GdbExporter._write_uint16(buf, 1)

        # 24. 温度
        GdbExporter._write_dbl(buf, 0, 0)

        # 25. 时间
        GdbExporter._write_time(buf, time_obj)

        # 26. GDB v3: 电话号码数量 (0)
        GdbExporter._write_int32(buf, 0)

        # 27. GDB v3: 国家（空）
        GdbExporter._write_cstr(buf, "")

        # 28. GDB v3: 邮政编码（空）
        GdbExporter._write_cstr(buf, "")

        return buf

    @staticmethod
    def _build_header() -> bytearray:
        """构建文件头部（含'D'记录和'A'记录）"""
        buf = bytearray()

        # 文件签名
        buf.extend(b'MsRc')

        # 主文件格式 (0x66)
        GdbExporter._write_uint16(buf, 0x66)

        # 'D'记录：记录长度=2，类型='D'，数据=文件格式版本
        GdbExporter._write_int32(buf, 2)  # 记录长度
        buf.append(ord('D'))  # 记录类型
        GdbExporter._write_uint16(buf, GdbExporter._FILE_FORMAT)  # 文件格式版本

        # 'A'记录：创建器信息
        # 先构建数据部分
        a_data = bytearray()
        GdbExporter._write_uint16(a_data, GdbExporter._PROGRAM_VERSION)
        GdbExporter._write_cstr(a_data, "GPXEditor")
        GdbExporter._write_cstr(a_data, "May 11 2026")
        GdbExporter._write_cstr(a_data, "00:00:00")

        # 写入记录长度和类型
        GdbExporter._write_int32(buf, len(a_data))
        buf.append(ord('A'))
        buf.extend(a_data)

        # "MapSource"标识（在记录之外）
        GdbExporter._write_cstr(buf, "MapSource")

        return buf

    @staticmethod
    def _build_waypoint_record(name_str: str, lat: float, lon: float,
                               altitude: float = None, time_obj=None,
                               symbol: str = None) -> bytearray:
        """构建一条完整的航点记录（含长度和类型前缀）"""
        # 构建数据部分
        data = GdbExporter._build_record_data(
            name_str=name_str,
            lat=lat,
            lon=lon,
            altitude=altitude,
            time_obj=time_obj,
            symbol=symbol
        )

        # 构建完整记录：长度 + 类型 + 数据
        buf = bytearray()
        GdbExporter._write_int32(buf, len(data))
        buf.append(ord('W'))  # 航点记录类型
        buf.extend(data)

        return buf

    @staticmethod
    def export(gpx: gpxpy.gpx.GPX, filepath: str):
        """导出GPX为Garmin GDB v3格式"""
        with open(filepath, 'wb') as f:
            # 写入文件头部
            f.write(GdbExporter._build_header())

            # 写入航点记录
            if gpx.waypoints:
                for wpt in gpx.waypoints:
                    record = GdbExporter._build_waypoint_record(
                        name_str=wpt.name,
                        lat=wpt.latitude,
                        lon=wpt.longitude,
                        altitude=wpt.elevation,
                        time_obj=wpt.time,
                        symbol=wpt.symbol
                    )
                    f.write(record)

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
