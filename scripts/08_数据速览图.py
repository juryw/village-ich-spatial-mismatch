# -*- coding: utf-8 -*-
"""
08_数据速览图.py
作用：用 matplotlib 画一张"传统村落 × 国家级非遗"全国分布预览图，
     让我们对数据的第一印象可视化。正式论文图件后续用 QGIS 精做。
说明：本图为数据预览示意，非标准地图；正式图件将采用自然资源部
     标准地图服务底图（含南海诸岛和九段线）。
"""
import json
import struct
from pathlib import Path

import matplotlib
matplotlib.use("Agg")                     # 不弹窗口，直接存文件
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.lines import Line2D

plt.rcParams["font.family"] = "Microsoft YaHei"   # 中文字体
plt.rcParams["axes.unicode_minus"] = False

DATA = Path(r"E:\GLM\非遗论文\02_数据")
OUT = Path(r"E:\GLM\非遗论文\04_图表") / "图0_数据速览_预览.png"

# ---------- 1. 读县级行政边界（面） ----------
counties = json.loads((DATA / "03_基础地理" / "中国_县级边界.geojson").read_text(encoding="utf-8"))
polygons = []
for feat in counties["features"]:
    geom = feat.get("geometry")
    if not geom:
        continue
    if geom["type"] == "Polygon":
        polygons.append(geom["coordinates"][0])                 # 只取外环
    elif geom["type"] == "MultiPolygon":
        polygons.extend(part[0] for part in geom["coordinates"])

# ---------- 2. 读传统村落（点，GeoJSON） ----------
villages = json.loads((DATA / "02_传统村落" / "合并_传统村落_前五批.geojson").read_text(encoding="utf-8"))
vx = [f["geometry"]["coordinates"][0] for f in villages["features"]]
vy = [f["geometry"]["coordinates"][1] for f in villages["features"]]

# ---------- 3. 读国家级非遗（点，直接从 DBF 属性表取 X/Y） ----------
def read_dbf_xy(path):
    raw = path.read_bytes()
    n = struct.unpack("<I", raw[4:8])[0]
    header_size = struct.unpack("<H", raw[8:10])[0]
    record_size = struct.unpack("<H", raw[10:12])[0]
    fields, pos = [], 32
    while raw[pos] != 0x0D:
        name = raw[pos:pos + 11].split(b"\x00")[0].decode("ascii")
        fields.append((name, raw[pos + 16]))
        pos += 32
    idx = {name: i for i, (name, _) in enumerate(fields)}
    widths = [flen for _, flen in fields]
    xs, ys = [], []
    for i in range(n):
        start = header_size + i * record_size + 1
        vals, p = {}, start
        for (name, _), w in zip(fields, widths):
            vals[name] = raw[p:p + w].decode("utf-8", errors="replace").strip()
            p += w
        xs.append(float(vals["X"]))
        ys.append(float(vals["Y"]))
    return xs, ys

ix, iy = read_dbf_xy(DATA / "01_非遗名录" / "IhChina_2006-2021" / "IhChina_2006-2021.dbf")

# ---------- 4. 画图 ----------
fig, ax = plt.subplots(figsize=(11, 8.5), dpi=200)
ax.add_collection(PolyCollection(
    polygons, facecolor="#f2f2f2", edgecolor="#b0b0b0", linewidths=0.08, zorder=1))
ax.scatter(vx, vy, s=2.2, c="#1f77b4", alpha=0.55, linewidths=0, zorder=2, label=f"传统村落（n={len(vx)}）")
ax.scatter(ix, iy, s=2.2, c="#d62728", alpha=0.5, linewidths=0, zorder=3, label=f"国家级非遗（n={len(ix)}）")

ax.set_xlim(73, 135.5)
ax.set_ylim(15, 54)
ax.set_aspect(1.18)                       # 近似中纬度经纬度比例
ax.set_title("中国传统村落与国家级非物质文化遗产空间分布（数据预览图）", fontsize=14)
ax.legend(loc="lower left", frameon=True, fontsize=10)
ax.text(0.99, 0.01,
        "数据预览示意图，非标准地图；正式图件将采用自然资源部标准地图底图（含南海诸岛）",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=7, color="#666666")
ax.set_xticks([])
ax.set_yticks([])

OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, bbox_inches="tight", facecolor="white")
print(f"已保存：{OUT}")
print(f"图中要素：县级行政区 {len(counties['features'])} 个，传统村落 {len(vx)} 个，非遗点 {len(ix)} 个")
