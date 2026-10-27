# -*- coding: utf-8 -*-
"""
01_检查非遗数据.py
作用：在不装任何第三方库的情况下，直接读取下载的 shapefile 文件，
     检查字段、记录数、坐标范围和数据完整度。
数据：《中国五批3610个国家级非物质文化遗产空间分布数据集》(geodoi.ac.cn)
运行方法：python 01_检查非遗数据.py
"""
import struct  # Python 自带模块，用来按字节解析二进制文件
from collections import Counter
from pathlib import Path

# ---------- 0. 文件路径（以后换电脑只改这里） ----------
folder = Path(r"E:\GLM\非遗论文\02_数据\01_非遗名录\IhChina_2006-2021")
dbf_path = folder / "IhChina_2006-2021.dbf"   # 属性表：字段和每条记录的信息
shp_path = folder / "IhChina_2006-2021.shp"   # 几何：点的经纬度坐标
shx_path = folder / "IhChina_2006-2021.shx"   # 索引：可用来数要素个数
prj_path = folder / "IhChina_2006-2021.prj"   # 坐标系定义（纯文本）
cpg_path = folder / "IhChina_2006-2021.cpg"   # 属性表文字编码说明

# ---------- 1. 确定中文编码（GBK 或 UTF-8） ----------
encoding = cpg_path.read_text().strip() if cpg_path.exists() else "GBK"
if encoding in ("936", "cp936"):
    encoding = "GBK"
print(f"【文字编码】{encoding}")

# ---------- 2. 解析 DBF 属性表头：字段名、字段类型、记录条数 ----------
raw = dbf_path.read_bytes()
n_records = struct.unpack("<I", raw[4:8])[0]      # 记录总数（<I = 小端 32 位整数）
header_size = struct.unpack("<H", raw[8:10])[0]   # 表头字节数
record_size = struct.unpack("<H", raw[10:12])[0]  # 每条记录的字节数
print(f"【DBF 表头】记录总数 = {n_records}，表头 {header_size} 字节，每条记录 {record_size} 字节")

fields = []  # 每个元素是 (字段名, 类型字母, 字段长度)
pos = 32
while raw[pos] != 0x0D:                           # 0x0D 是字段描述区的结束标志
    name = raw[pos:pos + 11].split(b"\x00")[0].decode(encoding)
    ftype = chr(raw[pos + 11])                    # C=文本 N=数字 D=日期
    flen = raw[pos + 16]
    fields.append((name, ftype, flen))
    pos += 32
print("【字段清单】" + "，".join(f"{n}({t})" for n, t, _ in fields))

# ---------- 3. 逐条读出记录，存成字典列表 ----------
records = []
for i in range(n_records):
    start = header_size + i * record_size
    flag = raw[start]                             # 删除标记：32(空格)=正常
    if flag == 0x2A:                              # '*' 表示已删除的记录，跳过
        continue
    vals, p = {}, start + 1
    for name, ftype, flen in fields:
        chunk = raw[p:p + flen]
        text = chunk.decode(encoding, errors="replace").strip("\x00 ").strip()
        vals[name] = text
        p += flen
    records.append(vals)
print(f"【有效记录】{len(records)} 条")

# ---------- 4. 打印前 3 条记录看看内容 ----------
print("\n【前 3 条记录示例】")
for r in records[:3]:
    print("  " + " | ".join(f"{k}={v}" for k, v in r.items()))

# ---------- 5. 对取值不多的字段做统计（比如非遗门类、公布批次） ----------
print("\n【分类字段分布】")
for name, ftype, flen in fields:
    counter = Counter(r[name] for r in records)
    if ftype == "N":  # 数字字段（如公布年份）先转成整数再统计
        counter = Counter(
            (str(int(float(v))) if v not in ("", ".") else "缺失" for v in (r[name] for r in records))
        )
    if not 1 < len(counter) <= 25:                # 取值 2~25 种的视为分类字段
        continue
    print(f"  ◆ {name}（{len(counter)} 类）:")
    for value, num in sorted(counter.items()):
        print(f"     {value}: {num} 条")

# ---------- 6. 读 SHP 文件头，检查坐标范围是否落在中国范围 ----------
shp = shp_path.read_bytes()
xmin, ymin, xmax, ymax = struct.unpack("<4d", shp[36:68])
print(f"\n【坐标范围】经度 {xmin:.2f} ~ {xmax:.2f}，纬度 {ymin:.2f} ~ {ymax:.2f}")
china_ok = 73 <= xmin and xmax <= 136 and 18 <= ymin and ymax <= 54
print(f"【范围校验】{'✓ 落在中国境内范围，坐标正常' if china_ok else '✗ 超出中国范围，需要检查坐标系！'}")

# ---------- 7. 读 PRJ 坐标系和 SHX 索引，交叉核对要素个数 ----------
prj_text = prj_path.read_text(errors="replace")
print(f"【坐标系】{prj_text[:90]} ...")
n_shx = (shx_path.stat().st_size - 100) // 8
print(f"【要素数核对】SHP 索引显示 {n_shx} 个要素，DBF 属性 {n_records} 条"
      f"{' —— 一致 ✓' if n_shx == n_records else ' —— 不一致，需检查！'}")
