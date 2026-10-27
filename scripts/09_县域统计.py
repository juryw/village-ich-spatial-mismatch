# -*- coding: utf-8 -*-
"""
09_县域统计.py
作用：统计每个县级行政区里的传统村落数和国家级非遗数，
     输出 CSV 统计表 + 一张双联分级填色图（choropleth 预览）。
     这是后续耦合协调度分析的直接输入。
原理：点在多边形内判断（射线法）+ 网格空间索引加速；
     落不进任何县（边界偏移等极少数情况）的点按"最近的县"兜底归入。
"""
import csv
import json
import math
import struct
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import BoundaryNorm, ListedColormap

plt.rcParams["font.family"] = "Microsoft YaHei"
plt.rcParams["axes.unicode_minus"] = False

DATA = Path(r"E:\GLM\非遗论文\02_数据")
OUT_DIR = Path(r"E:\GLM\非遗论文\04_图表")
OUT_CSV = DATA / "03_基础地理" / "县域统计_村落非遗.csv"
OUT_PNG = OUT_DIR / "图1_县域统计choropleth_预览.png"

# ---------- 1. 读县级行政边界，提取多边形与属性 ----------
geo = json.loads((DATA / "03_基础地理" / "中国_县级边界_修复.geojson").read_text(encoding="utf-8"))
provinces = json.loads((DATA / "03_基础地理" / "中国_省级边界.geojson").read_text(encoding="utf-8"))
prov_name = {f["properties"]["adcode"]: f["properties"].get("name", "") for f in provinces["features"]}

counties = []  # 每项：{adcode,name,prov,parts:[外环坐标列表],bbox}
for f in geo["features"]:
    geom = f.get("geometry")
    if not geom:
        continue
    parts = ([geom["coordinates"][0]] if geom["type"] == "Polygon"
             else [p[0] for p in geom["coordinates"]])
    xs = [x for part in parts for x, _ in part]
    ys = [y for part in parts for _, y in part]
    props = f["properties"]
    route = props.get("acroutes") or []          # 如 [320000, 320500, 320582]
    prov = prov_name.get(route[0], "") if route else ""
    counties.append({
        "adcode": props["adcode"], "name": props.get("name", ""), "prov": prov,
        "parts": parts, "bbox": (min(xs), min(ys), max(xs), max(ys)),
        "cx": (min(xs) + max(xs)) / 2, "cy": (min(ys) + max(ys)) / 2,
        "village": 0, "ich": 0,
    })

# ---------- 2. 建 1°×1° 网格空间索引（不然 2874 县 × 上万点会慢） ----------
GRID = {}
for i, c in enumerate(counties):
    x0, y0, x1, y1 = c["bbox"]
    for gx in range(math.floor(x0), math.floor(x1) + 1):
        for gy in range(math.floor(y0), math.floor(y1) + 1):
            GRID.setdefault((gx, gy), []).append(i)

def point_in_poly(x, y, poly):
    """射线法：从 (x,y) 向右引一条线，穿过多边形边界奇数次则在内"""
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xin = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if xin > x:
                inside = not inside
    return inside

def assign(x, y):
    """返回点所属县的序号；找不到就兜底到中心最近的县"""
    hits = GRID.get((math.floor(x), math.floor(y)), [])
    for i in hits:
        for part in counties[i]["parts"]:
            if point_in_poly(x, y, part):
                return i
    best, best_d = None, 1e9      # 兜底：几乎不会发生（边界偏移个例）
    for i in hits:
        d = (counties[i]["cx"] - x) ** 2 + (counties[i]["cy"] - y) ** 2
        if d < best_d:
            best, best_d = i, d
    return best

# ---------- 3. 读两类点并归县 ----------
villages = json.loads((DATA / "02_传统村落" / "合并_传统村落_前五批.geojson").read_text(encoding="utf-8"))

raw = (DATA / "01_非遗名录" / "IhChina_2006-2021" / "IhChina_2006-2021.dbf").read_bytes()
n_rec = struct.unpack("<I", raw[4:8])[0]
h_size, r_size = struct.unpack("<H", raw[8:10])[0], struct.unpack("<H", raw[10:12])[0]
fields, pos = [], 32
while raw[pos] != 0x0D:
    fields.append((raw[pos:pos + 11].split(b"\x00")[0].decode("ascii"), raw[pos + 16]))
    pos += 32
widths = [w for _, w in fields]
idx = {nm: k for k, (nm, _) in enumerate(fields)}
ich_xy = []
for i in range(n_rec):
    start = h_size + i * r_size + 1
    p = start
    vals = []
    for w in widths:
        vals.append(raw[p:p + w].decode("utf-8", errors="replace").strip())
        p += w
    ich_xy.append((float(vals[idx["X"]]), float(vals[idx["Y"]])))

fallback = 0
for f in villages["features"]:
    x, y = f["geometry"]["coordinates"]
    i = assign(x, y)
    if i is None:
        continue
    if not any(point_in_poly(x, y, part) for part in counties[i]["parts"]):
        fallback += 1
    counties[i]["village"] += 1
for x, y in ich_xy:
    i = assign(x, y)
    if i is None:
        continue
    if not any(point_in_poly(x, y, part) for part in counties[i]["parts"]):
        fallback += 1
    counties[i]["ich"] += 1

# ---------- 4. 输出 CSV 与摘要 ----------
with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.writer(fh)
    w.writerow(["adcode", "县名", "省份", "村落数", "非遗数"])
    for c in counties:
        w.writerow([c["adcode"], c["name"], c["prov"], c["village"], c["ich"]])

n_v = sum(c["village"] for c in counties)
n_i = sum(c["ich"] for c in counties)
print(f"归县结果：村落 {n_v}/6817，非遗 {n_i}/3610（兜底归入 {fallback} 个点）")
print(f"有村落的县：{sum(1 for c in counties if c['village'] > 0)} 个；有非遗的县：{sum(1 for c in counties if c['ich'] > 0)} 个")
print("村落最多的10个县：", [(c['name'], c['village']) for c in sorted(counties, key=lambda c: -c['village'])[:10]])
print("非遗最多的10个县：", [(c['name'], c['ich']) for c in sorted(counties, key=lambda c: -c['ich'])[:10]])
vs = [c["village"] for c in counties]
is_ = [c["ich"] for c in counties]
mv, mi = sum(vs) / len(vs), sum(is_) / len(is_)
cov = sum((v - mv) * (i - mi) for v, i in zip(vs, is_)) / math.sqrt(
    sum((v - mv) ** 2 for v in vs) * sum((i - mi) ** 2 for i in is_))
print(f"县域村落-非遗计数皮尔逊相关 r = {cov:.3f}（后面做双变量空间自相关会再细分）")

# ---------- 5. 双联 choropleth 预览图 ----------
breaks = [0, 1, 3, 6, 11, 21, 10 ** 9]
labels = ["0", "1-2", "3-5", "6-10", "11-20", "≥21"]

def color_of(v):
    for k in range(len(breaks) - 1):
        if breaks[k] <= v < breaks[k + 1]:
            return k
    return len(breaks) - 2

fig, axes = plt.subplots(1, 2, figsize=(15, 7.5), dpi=200)
for ax, key, title, cmap_colors in (
    (axes[0], "village", "传统村落数量（县级）", ["#f7f7f7", "#c6dbef", "#6baed6", "#3182bd", "#08519c", "#08306b"]),
    (axes[1], "ich", "国家级非遗数量（县级）", ["#fff5f0", "#fcbba1", "#fb6a4a", "#de2d26", "#a50f15", "#67000d"]),
):
    cmap = ListedColormap(cmap_colors)
    norm = BoundaryNorm(range(len(labels) + 1), cmap.N)
    polys, face = [], []
    for c in counties:
        for part in c["parts"]:
            polys.append(part)
            face.append(color_of(c[key]))
    ax.add_collection(PolyCollection(polys, array=face, cmap=cmap, norm=norm,
                                     edgecolor="#bbbbbb", linewidths=0.06, zorder=1))
    ax.set_xlim(73, 135.5)
    ax.set_ylim(15, 54)
    ax.set_aspect(1.18)
    ax.set_title(title, fontsize=13)
    ax.set_xticks([])
    ax.set_yticks([])
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    cbar = fig.colorbar(sm, ax=ax, shrink=0.7, pad=0.01, ticks=range(len(labels)))
    cbar.ax.set_yticklabels(labels)
    cbar.set_label("处/个")

fig.suptitle("中国传统村落与国家级非遗的县域分布（预览图，非标准地图）", fontsize=15)
OUT_DIR.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT_PNG, bbox_inches="tight", facecolor="white")
print(f"已保存：{OUT_PNG}")
print(f"已保存：{OUT_CSV}")
