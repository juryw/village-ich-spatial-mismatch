# -*- coding: utf-8 -*-
"""
16_双变量LISA.py
作用：县域"村落密度 × 非遗密度"的双变量空间自相关分析（论文核心图）。
  1) 用县级边界构建 Queen 邻接空间权重矩阵（相邻=共享边界）
  2) 全局双变量 Moran's I（村落 → 非遗，及反向）
  3) 局部双变量 LISA：把每个县归为 高-高/低-低/高-低/低-高/不显著 五类
     （高-高 = 村落多且周边非遗多 → 协同区；高-低 = 村落多但周边非遗少 → 错位区）
范围：大陆县级单元（不含港澳；港澳与大陆不接壤，空间权重接不上）。
工具：libpysal（权重）+ esda（Moran），随机种子固定保证可复现。
"""
import json
import random
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import ListedColormap, BoundaryNorm
import matplotlib.patches as mpatches
from shapely.geometry import shape
from shapely import STRtree
import libpysal
from esda.moran import Moran, Moran_BV, Moran_Local_BV

random.seed(42)
np.random.seed(42)
plt.rcParams["font.family"] = "Microsoft YaHei"

DATA = Path(r"E:\GLM\非遗论文\02_数据")
OUT_CSV = DATA / "03_基础地理" / "县域LISA结果.csv"
OUT_PNG = Path(r"E:\GLM\非遗论文\04_图表") / "图4_双变量LISA集聚图_预览.png"

# ---------- 1. 大陆县级单元（不含港澳台） ----------
geo = json.loads((DATA / "03_基础地理" / "中国_县级边界_统计.geojson").read_text(encoding="utf-8"))
feats = [f for f in geo["features"]
         if f.get("geometry") and str(f["properties"]["adcode"]) < "810000"]
print(f"大陆县级单元：{len(feats)} 个")

geoms = [shape(f["geometry"]).buffer(0) for f in feats]
v = np.array([f["properties"]["VILLAGE_N"] for f in feats], dtype=float)
i = np.array([f["properties"]["ICH_N"] for f in feats], dtype=float)

# ---------- 2. Queen 邻接（STRtree 加速的 touches 判定） ----------
tree = STRtree(geoms)
pairs = tree.query(geoms, predicate="touches")     # 2×N，含 (a,b) 与 (b,a) 两个方向
neighbors = {k: set() for k in range(len(geoms))}
for a, b in zip(pairs[0], pairs[1]):
    if a != b:
        neighbors[int(a)].add(int(b))
n_island = sum(1 for k, ns in neighbors.items() if not ns)
print(f"邻接构建完成；孤立单元（无陆上邻居）：{n_island} 个（多为岛屿区县）")
w = libpysal.weights.W(neighbors, silence_warnings=True)

# ---------- 3. 全局空间自相关 ----------
mv = Moran(v, w)
mi = Moran(i, w)
mvbi = Moran_BV(v, i, w)
mibv = Moran_BV(i, v, w)
print(f"全局 Moran's I：村落 {mv.I:.3f} (p={mv.p_sim:.3f})｜非遗 {mi.I:.3f} (p={mi.p_sim:.3f})")
print(f"双变量 I：村落→非遗 {mvbi.I:.3f}｜非遗→村落 {mibv.I:.3f}")

# ---------- 4. 局部双变量 LISA ----------
lisa = Moran_Local_BV(v, i, w, permutations=199)
q, p = lisa.q, lisa.p_sim
sig = p <= 0.05

# 四象限含义（x=村落中心化，W·y=周边非遗拉格中心化）：
# 1=HH 2=LH 3=LL 4=HL（esda 约定）
cls = np.zeros(len(v), dtype=int)                  # 0=不显著
for qq in (1, 2, 3, 4):
    cls[(q == qq) & sig] = qq
NAMES = {0: "不显著", 1: "高-高 协同", 3: "低-低 低值连片", 4: "高-低 错位(村落富集·非遗稀缺)", 2: "低-高 错位(非遗富集·村落稀缺)"}
for qq in (1, 2, 3, 4, 0):
    print(f"  {NAMES[qq]}：{int((cls == qq).sum())} 个县")

hh = [feats[k]["properties"]["name"] for k in np.where(cls == 1)[0]]
print("高-高协同区（前20）：", "、".join(hh[:20]))

with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
    import csv as _csv
    wcsv = _csv.writer(f)
    wcsv.writerow(["adcode", "县名", "村落数", "非遗数", "象限", "p值", "分类"])
    for k, feat in enumerate(feats):
        wcsv.writerow([feat["properties"]["adcode"], feat["properties"]["name"],
                       int(v[k]), int(i[k]), int(q[k]), f"{p[k]:.4f}", NAMES[cls[k]]])
print(f"已保存：{OUT_CSV}")

# ---------- 4b. 敏感性：B 口径（仅剔机构型保护单位）再算一遍 ----------
import csv as _csv2
_sens_rows = list(_csv2.DictReader(
    open(DATA / "03_基础地理" / "县域统计_敏感性对比.csv", encoding="utf-8-sig")))
_b_key = "非遗B剔除后(仅S2)" if "非遗B剔除后(仅S2)" in _sens_rows[0] else "非遗B剔除后"
b_map = {r["adcode"]: int(r[_b_key]) for r in _sens_rows}
ib = np.array([b_map.get(str(f["properties"]["adcode"]), 0) for f in feats], dtype=float)
lisa_b = Moran_Local_BV(v, ib, w, permutations=199)
qb, pb = lisa_b.q, lisa_b.p_sim
cls_b = np.zeros(len(v), dtype=int)
for qq in (1, 2, 3, 4):
    cls_b[(qb == qq) & (pb <= 0.05)] = qq
print(f"\nB 口径（剔除1115条注册地型）双变量 I = {Moran_BV(v, ib, w).I:.3f}")
for qq in (1, 2, 3, 4, 0):
    print(f"  {NAMES[qq]}：{int((cls_b == qq).sum())} 个县（A 口径为 {int((cls == qq).sum())}）")
hh_b = [feats[k]["properties"]["name"] for k in np.where(cls_b == 1)[0]]
print("B 口径高-高协同区（前20）：", "、".join(hh_b[:20]))

# ---------- 5. 集聚图（A/B 双联对比：主图版式） ----------
COLORS = {1: "#d7191c", 3: "#2c7bb6", 4: "#fdae61", 2: "#abd9e9", 0: "#e8e8e8"}

all_geo = json.loads((DATA / "03_基础地理" / "中国_县级边界_统计.geojson").read_text(encoding="utf-8"))
cls_map_a = {str(feats[k]["properties"]["adcode"]): cls[k] for k in range(len(feats))}
cls_map_b = {str(feats[k]["properties"]["adcode"]): cls_b[k] for k in range(len(feats))}

polys = []
face_a, face_b = [], []
for feat in all_geo["features"]:
    g = feat.get("geometry")
    if not g:
        continue
    parts = [g["coordinates"][0]] if g["type"] == "Polygon" else [p[0] for p in g["coordinates"]]
    acode = str(feat["properties"]["adcode"])
    for part in parts:
        polys.append(part)
        face_a.append(cls_map_a.get(acode, 0))
        face_b.append(cls_map_b.get(acode, 0))

fig, axes = plt.subplots(1, 2, figsize=(15, 7.5), dpi=200, sharex=True, sharey=True)
cmap = ListedColormap([COLORS[0], COLORS[1], COLORS[2], COLORS[3], COLORS[4]])
norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5, 4.5], cmap.N)
for ax, face, title in (
    (axes[0], face_a, "A 全量口径（n=3610）"),
    (axes[1], face_b, "B 剔除注册地型（n=2495）"),
):
    ax.add_collection(PolyCollection(polys, array=np.array(face), cmap=cmap, norm=norm,
                                     edgecolor="#999999", linewidths=0.06))
    ax.set_xlim(73, 135.5); ax.set_ylim(15, 54); ax.set_aspect(1.18)
    ax.set_title(title, fontsize=12)
    ax.set_xticks([]); ax.set_yticks([])
fig.suptitle("传统村落与非遗的双变量LISA集聚格局：注册地效应清洗前后对比（p≤0.05，预览图）", fontsize=14)
handles = [mpatches.Patch(color=COLORS[k], label=NAMES[k]) for k in (1, 3, 4, 2, 0)]
axes[0].legend(handles=handles, loc="lower left", fontsize=8, frameon=True)
fig.savefig(OUT_PNG, bbox_inches="tight", facecolor="white")
print(f"已保存（A/B 双联版）：{OUT_PNG}")
