# -*- coding: utf-8 -*-
"""
05_检查传统村落数据.py
作用：分别读取三份传统村落数据集（前三批2555 / 第四批1598 / 第五批2666），
     查看字段、条数、坐标范围、文字编码，为下一步合并成统一数据做准备。
"""
import struct
from pathlib import Path

ROOT = Path(r"E:\GLM\非遗论文\02_数据\02_传统村落")
DATASETS = [
    ("前三批", ROOT / "VillagesChina2555" / "Villages2555.dbf"),
    ("第四批", ROOT / "VillagesChina1598" / "VillagesChina1598.dbf"),
    ("第五批", ROOT / "VillagesChina2666" / "VillagesChina2666.dbf"),
]


def looks_chinese(text):
    """统计字符串里中日韩字符数量，用来判断编码猜得对不对"""
    return sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")


def read_dbf(path, encoding):
    raw = path.read_bytes()
    n_records = struct.unpack("<I", raw[4:8])[0]
    header_size = struct.unpack("<H", raw[8:10])[0]
    record_size = struct.unpack("<H", raw[10:12])[0]
    fields, pos = [], 32
    while raw[pos] != 0x0D:
        name = raw[pos:pos + 11].split(b"\x00")[0].decode("ascii", errors="replace")
        fields.append((name, chr(raw[pos + 11]), raw[pos + 16]))
        pos += 32
    records = []
    for i in range(n_records):
        start = header_size + i * record_size
        if raw[start] == 0x2A:
            continue
        vals, p = {}, start + 1
        for name, ftype, flen in fields:
            text = raw[p:p + flen].decode(encoding, errors="replace").strip("\x00 ").strip()
            vals[name] = text
            p += flen
        records.append(vals)
    return fields, records


def shp_bbox(shp_path):
    shp = shp_path.read_bytes()
    return struct.unpack("<4d", shp[36:68])


for label, dbf_path in DATASETS:
    print("=" * 60)
    print(f"◆ {label}：{dbf_path.parent.name}")
    # 2555/1598 没有 .cpg，需要自动判断编码：分别用 GBK 和 UTF-8 试解同一段内容
    encodings = ["GBK", "UTF-8"]
    best, best_score = "GBK", -1
    for enc in encodings:
        try:
            fields, records = read_dbf(dbf_path, enc)
            sample = " ".join(str(v) for r in records[:20] for v in r.values())
            score = looks_chinese(sample)
            if score > best_score:
                best, best_score = enc, score
        except Exception:
            continue
    fields, records = read_dbf(dbf_path, best)
    print(f"  编码：{best}（中文得分 {best_score}）｜记录数：{len(records)}")
    print(f"  字段：{'，'.join(f'{n}({t},{l})' for n, t, l in fields)}")
    for r in records[:2]:
        print("  示例：" + " | ".join(f"{k}={v}" for k, v in r.items()))
    shp_path = dbf_path.with_suffix(".shp")
    xmin, ymin, xmax, ymax = shp_bbox(shp_path)
    print(f"  坐标范围：经度 {xmin:.2f}~{xmax:.2f}，纬度 {ymin:.2f}~{ymax:.2f}")
    prj = dbf_path.with_suffix(".prj").read_text(errors="replace")[:80]
    print(f"  坐标系：{prj} ...")
