# -*- coding: utf-8 -*-
"""
44_跨规则稳健核心.py
计算 C 严格口径（S1∪S2）的局部 LISA，与 43 号的 B（v3）结果求交，
得到"两种清洗规则下均为高—高/均为高—低"的稳健县清单——规划建议只基于稳健核心。
"""
import csv
import json
import random
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
random.seed(42)
import numpy as np
from shapely.geometry import shape
from shapely import STRtree
import libpysal
from esda.moran import Moran_Local_BV

DATA = Path(r"E:\GLM\非遗论文\02_数据\03_基础地理")
geo = json.loads((DATA / "中国_县级边界_统计.geojson").read_text(encoding="utf-8"))
feats = [f for f in geo["features"] if f.get("geometry") and str(f["properties"]["adcode"]) < "810000"]
geoms = [shape(f["geometry"]).buffer(0) for f in feats]
vc = np.array([f["properties"]["VILLAGE_N"] for f in feats], dtype=float)
# C 严格口径非遗数（从敏感性对比表读）
strict_map = {r["adcode"]: int(r["非遗C严格(S1∪S2)"]) for r in csv.DictReader(
    open(DATA / "县域统计_敏感性对比.csv", encoding="utf-8-sig"))}
ic = np.array([strict_map.get(str(f["properties"]["adcode"]), 0) for f in feats], dtype=float)

tree = STRtree(geoms)
pairs = tree.query(geoms, predicate="touches")
neighbors = {k: set() for k in range(len(geoms))}
for a, b in zip(pairs[0], pairs[1]):
    if a != b:
        neighbors[int(a)].add(int(b))
w = libpysal.weights.W(neighbors, silence_warnings=True)

lisa_c = Moran_Local_BV(vc, ic, w, permutations=199)
q, p = lisa_c.q, lisa_c.p_sim
cls_c = {}
hh_c = set()
for k, f in enumerate(feats):
    lab = 0
    for qq in (1, 2, 3, 4):
        if q[k] == qq and p[k] <= 0.05:
            lab = qq
    code = str(f["properties"]["adcode"])
    cls_c[code] = lab
    if lab == 1:
        hh_c.add(code)

# B（v3）结果读 CSV
b_res = {r["adcode"]: (int(r["象限"]), r["分类"]) for r in csv.DictReader(
    open(DATA / "县域LISA结果.csv", encoding="utf-8-sig"))}
name_map = {str(f["properties"]["adcode"]): f["properties"]["name"] for f in feats}

print("=== C 严格口径 高—高县（全部） ===")
print("、".join(sorted(name_map[c] for c in hh_c)))

both_hh = [c for c in hh_c if b_res.get(c, (0, ""))[0] == 1]
print(f"\n=== B(v3) 与 C(严格) 双规则稳健高—高：{len(both_hh)} 个县 ===")
print("、".join(sorted(name_map[c] for c in both_hh)))

# 双规则稳健高—低（村落富集·非遗稀缺）
hl_b = {c for c, (qq, _) in b_res.items() if qq == 4}
hl_c = {c for c, lab in cls_c.items() if lab == 4}
both_hl = hl_b & hl_c
print(f"\n=== 双规则稳健高—低（村落富集·非遗稀缺）：{len(both_hl)} 个县 ===")
print("、".join(sorted(name_map[c] for c in both_hl)[:30]))

# 双规则稳健低—高
lh_b = {c for c, (qq, _) in b_res.items() if qq == 2}
lh_c = {c for c, lab in cls_c.items() if lab == 2}
both_lh = lh_b & lh_c
print(f"\n=== 双规则稳健低—高（非遗富集·村落稀缺）：{len(both_lh)} 个县 ===")
print("、".join(sorted(name_map[c] for c in both_lh)[:30]))
