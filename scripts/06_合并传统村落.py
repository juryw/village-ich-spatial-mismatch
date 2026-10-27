# -*- coding: utf-8 -*-
"""
06_合并传统村落.py
作用：把三份传统村落数据集合并成一个统一文件（CSV + GeoJSON），
     统一字段：村名、省、市、县、镇、村、经度、纬度、批次来源。
     同时做质检：总数、去重、坐标范围、分省统计。
注意：坐标存在 .shp 几何文件里（DBF 属性表里没有 X/Y），需要两边的顺序一一对应。
"""
import csv
import json
import struct
from pathlib import Path

ROOT = Path(r"E:\GLM\非遗论文\02_数据\02_传统村落")
OUT_CSV = ROOT / "合并_传统村落_前五批.csv"
OUT_GEOJSON = ROOT / "合并_传统村落_前五批.geojson"

# (标签, dbf路径, 全名中文字段名)
DATASETS = [
    ("1-3批(2012-2014)", ROOT / "VillagesChina2555" / "Villages2555.dbf", "NameCN"),
    ("4批(2017)",         ROOT / "VillagesChina1598" / "VillagesChina1598.dbf", "Name"),
    ("5批(2019)",         ROOT / "VillagesChina2666" / "VillagesChina2666.dbf", "Name_1"),
]


def read_dbf(path):
    """读 DBF 属性表：先严格按 UTF-8 解，失败（说明是 GBK）再退回 GBK"""
    raw = path.read_bytes()
    n_records = struct.unpack("<I", raw[4:8])[0]
    header_size = struct.unpack("<H", raw[8:10])[0]
    record_size = struct.unpack("<H", raw[10:12])[0]
    fields, pos = [], 32
    while raw[pos] != 0x0D:
        name = raw[pos:pos + 11].split(b"\x00")[0].decode("ascii", errors="replace")
        fields.append((name, raw[pos + 16]))
        pos += 32

    def parse(encoding):
        rows = []
        for i in range(n_records):
            start = header_size + i * record_size
            if raw[start] == 0x2A:
                continue
            vals, p = {}, start + 1
            for name, flen in fields:
                chunk = raw[p:p + flen]
                vals[name] = chunk.decode(encoding).strip("\x00 \r\n").strip()  # 严格模式：解不动会抛异常
                p += flen
            rows.append(vals)
        return rows

    try:
        return parse("UTF-8"), "UTF-8"
    except UnicodeDecodeError:
        return parse("GBK"), "GBK"


def read_points(shp_path):
    """按记录头逐条读点坐标（与 DBF 记录顺序一一对应）"""
    data = shp_path.read_bytes()
    pos, pts = 100, []
    while pos + 8 <= len(data):
        content_len = struct.unpack(">I", data[pos + 4:pos + 8])[0] * 2  # 记录头里长度单位是"字"（2字节）
        content = data[pos + 8:pos + 8 + content_len]
        stype = struct.unpack("<I", content[0:4])[0]
        if stype in (1, 11, 21):                         # 1=点 11=带高程点 21=带度量点，X/Y 位置相同
            x, y = struct.unpack("<2d", content[4:20])
            pts.append((x, y))
        else:
            raise ValueError(f"遇到非点要素类型 {stype}，请告知 GLM")
        pos += 8 + content_len
    return pts


# ---------- 合并 ----------
all_rows = []
for label, dbf_path, name_field in DATASETS:
    records, enc = read_dbf(dbf_path)
    points = read_points(dbf_path.with_suffix(".shp"))
    assert len(records) == len(points), f"{label}：属性 {len(records)} 条与几何 {len(points)} 个不一致！"
    print(f"◆ {label}：{len(records)} 条，编码 {enc}")
    for r, (x, y) in zip(records, points):
        all_rows.append({
            "NameCN": r[name_field],
            "ProvinceCN": r["ProvinceCN"], "CityCN": r["CItyCN"],     # 源数据字段名拼写就是 CItyCN
            "DistrictCN": r["DistrictCN"], "TownCN": r["TownCN"], "VillageCN": r["VillageCN"],
            "X": x, "Y": y, "Batch": label,
        })

# ---------- 质检 ----------
print(f"\n合并总数：{len(all_rows)}（应为 6819）")
names = [row["NameCN"] for row in all_rows]
dup = len(names) - len(set(names))
print(f"按全名去重后相差：{dup} 条（0 = 无重复）")

# 源数据里有个别村被重复收录（坐标完全相同或同一村两个落点），
# 按"全名首次出现保留"去重，去重明细记录在 数据说明_传统村落.md
seen, deduped, dropped = set(), [], []
for row in all_rows:
    if row["NameCN"] in seen:
        dropped.append(row["NameCN"])
    else:
        seen.add(row["NameCN"])
        deduped.append(row)
for name in dropped:
    print(f"  去重删除：{name}")
all_rows = deduped
print(f"去重后总数：{len(all_rows)}")

xs, ys = [r["X"] for r in all_rows], [r["Y"] for r in all_rows]
print(f"坐标范围：经度 {min(xs):.2f}~{max(xs):.2f}，纬度 {min(ys):.2f}~{max(ys):.2f}")
bad = sum(1 for r in all_rows if not (73 < r["X"] < 136 and 18 < r["Y"] < 54))
print(f"坐标越界记录：{bad} 条")

from collections import Counter
prov_counter = Counter(r["ProvinceCN"] for r in all_rows)
print("\n分省统计（前 10）：")
for prov, num in prov_counter.most_common(10):
    print(f"  {prov}: {num}")

# ---------- 输出 CSV（utf-8-sig 让 Excel 直接打开不乱码） ----------
with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
    writer.writeheader()
    writer.writerows(all_rows)

# ---------- 输出 GeoJSON（点要素，WGS-84） ----------
features = [{
    "type": "Feature",
    "properties": {k: v for k, v in row.items() if k not in ("X", "Y")},
    "geometry": {"type": "Point", "coordinates": [row["X"], row["Y"]]},
} for row in all_rows]
OUT_GEOJSON.write_text(
    json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False),
    encoding="utf-8")

print(f"\n已保存：\n  {OUT_CSV}\n  {OUT_GEOJSON}")
