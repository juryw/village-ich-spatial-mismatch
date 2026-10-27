# -*- coding: utf-8 -*-
"""
42_审稿自查_密度LISA.py
审稿人视角自查二：正文 LISA 用的是"绝对计数"，而探测器用的是"密度"——
     方法不一致；且计数存在"面积暴露偏差"（大县天然点多）。
本脚本用密度（处/千km²）重算全局双变量 Moran's I，与计数版对比。
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import numpy as np
from shapely.geometry import shape
from shapely import STRtree
import libpysal
from esda.moran import Moran_BV

DATA = Path(r"E:\GLM\非遗论文\02_数据\03_基础地理")
geo = json.loads((DATA / "中国_县级边界_统计.geojson").read_text(encoding="utf-8"))
feats = [f for f in geo["features"] if f.get("geometry") and str(f["properties"]["adcode"]) < "810000"]
geoms = [shape(f["geometry"]).buffer(0) for f in feats]
vc = np.array([f["properties"]["VILLAGE_N"] for f in feats], dtype=float)
ic = np.array([f["properties"]["ICH_N"] for f in feats], dtype=float)
print(f"县数 {len(feats)}")

tree = STRtree(geoms)
pairs = tree.query(geoms, predicate="touches")
neighbors = {k: set() for k in range(len(geoms))}
for a, b in zip(pairs[0], pairs[1]):
    if a != b:
        neighbors[int(a)].add(int(b))
w = libpysal.weights.W(neighbors, silence_warnings=True)

# 面积：从驱动因子表读
import csv as _csv
area_map = {r["adcode"]: float(r["area_km2"]) for r in _csv.DictReader(
    open(DATA / "县域驱动因子表.csv", encoding="utf-8-sig"))}
area = np.array([area_map.get(str(f["properties"]["adcode"]), 1.0) for f in feats])

vd = vc / area * 1000
id_ = ic / area * 1000
print(f"计数版 双变量 I（村落→非遗）: {Moran_BV(vc, ic, w).I:.4f}")
print(f"密度版 双变量 I（村落→非遗）: {Moran_BV(vd, id_, w).I:.4f}")
mv_c = __import__('esda.moran', fromlist=['Moran']).Moran(vc, w)
mv_d = __import__('esda.moran', fromlist=['Moran']).Moran(vd, w)
print(f"计数版 村落单变量 I: {mv_c.I:.3f}｜密度版: {mv_d.I:.3f}")
