import os, hashlib, gpxpy
from gpx_editor.core.exporter import GdbExporter

test_gpx = 'F:/gpx edit/test_original.gpx'

# 创建测试GPX
with open(test_gpx, 'w', encoding='utf-8') as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    f.write('<gpx version="1.1">\n')
    f.write('<wpt lat="39.9" lon="74.2"><name>BL3216C1</name></wpt>\n')
    f.write('<wpt lat="39.8" lon="74.1"><name>BL3216A1</name></wpt>\n')
    f.write('</gpx>')

# 记录原始hash
with open(test_gpx, 'rb') as f:
    h1 = hashlib.md5(f.read()).hexdigest()

# 读取并导出
with open(test_gpx, 'r', encoding='utf-8') as f:
    gpx = gpxpy.parse(f)

print(f'航点数: {len(gpx.waypoints)}')
for w in gpx.waypoints:
    print(f'  {w.name}: {w.latitude}, {w.longitude}')

GdbExporter.export(gpx, 'F:/gpx edit/test_export.gdb')

# 检查原始文件是否被修改
with open(test_gpx, 'rb') as f:
    h2 = hashlib.md5(f.read()).hexdigest()

print(f'\nhash before: {h1}')
print(f'hash after:  {h2}')
print(f'文件被修改: {h1 != h2}')

# 清理
os.remove(test_gpx)
os.remove('F:/gpx edit/test_export.gdb')
