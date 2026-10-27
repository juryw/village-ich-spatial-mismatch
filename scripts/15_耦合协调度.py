# -*- coding: utf-8 -*-
"""
15_耦合协调度.py
作用：县域"传统村落系统 × 非遗系统"的耦合协调度（CCD）测算与制图。
模型（标准公式，参考文献见研究备忘）：
  功效值 u1、u2 = min-max 归一化（分析单元内）
  耦合度 C = 2√(u1·u2) / (u1+u2)
  综合协调指数 T = a·u1 + b·u2（a=b=0.5，两类要素同等重要）
  耦合协调度 D = √(C·T)
分析单元：村落数>0 或 非遗数>0 的县（两类要素至少有其一）。
口径：A=全量非遗（主分析）；B=剔除注册地型（敏感性，只出数字不出图）。
"""
import csv
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import ListedColormap, BoundaryNorm

plt.rcParams["font.family"] = "Microsoft YaHei"
plt.rcParams["axes.unicode_minus"] = False

DATA = Path(r"E:\GLM\非遗论文\02_数据")
OUT_CSV = DATA / "03_基础地理" / "县域耦合协调度.csv"
OUT_PNG = Path(r"E:\GLM\非遗论文\04_图表") / "图3_县域耦合协调度_预览.png"

# ---------- 1. 读数 ----------
rows = list(csv.DictReader(open(DATA / "03_基础地理" / "县域统计_敏感性对比.csv", encoding="utf-8-sig")))
_b_key = "非遗B剔除后" if "非遗B剔除后" in rows[0] else next(
    k for k in rows[0] if k.startswith("非遗B"))
for r in rows:
    r["v"] = int(r["村落数"]); r["a"] = int(r["非遗A全量"]); r["b"] = int(r[_b_key])

def ccd(values):
    """输入 [(village, ich), ...]，返回 D 值列表"""
    v = np.array([x[0] for x in values], dtype=float)
    i = np.array([x[1] for x in values], dtype=float)
    u1 = (v - v.min()) / (v.max() - v.min() + 1e-12)
    u2 = (i - i.min()) / (i.max() - i.min() + 1e-12)
    C = 2 * np.sqrt(u1 * u2) / (u1 + u2 + 1e-12)
    T = 0.5 * u1 + 0.5 * u2
    return np.sqrt(C * T), C, T

subset = [r for r in rows if r["v"] > 0 or r["a"] > 0]        # A 口径分析单元
D_a, C_a, T_a = ccd([(r["v"], r["a"]) for r in subset])
D_b, _, _ = ccd([(r["v"], r["b"]) for r in subset])           # B 口径敏感性
for r, d in zip(subset, D_a):
    r["D_a"] = d
for r, d in zip(subset, D_b):
    r["D_b"] = d

print(f"分析单元：{len(subset)} 个县（A 口径）")
for q in (10, 25, 50, 75, 90, 98, 100):
    print(f"  D 的 P{q} = {np.percentile(D_a, q):.3f}")

# 分级（数据驱动 + 常用四档语义）
BREAKS = [0, 0.10, 0.20, 0.30, 0.40, 1.01]
LABELS = ["低度耦合协调 (D<0.10)", "较低 (0.10-0.20)", "中等 (0.20-0.30)", "较高 (0.30-0.40)", "高 (D≥0.40)"]
COLORS = ["#ffffd9", "#edf8b1", "#7fcdbb", "#2c7fb8", "#0c2c84"]

def klass(d):
    for k in range(5):
        if BREAKS[k] <= d < BREAKS[k + 1]:
            return k
    return 4

# D 最高的前 10 县
top = sorted(subset, key=lambda r: -r["D_a"])[:10]
print("耦合协调度最高的 10 个县（A 口径）：")
for r in top:
    print(f"  {r['县名']}：村落 {r['v']}｜非遗 {r['a']}｜D = {r['D_a']:.3f}")

# B 口径 CCD 敏感性：秩相关 + 前十县对比
def spearman(x, y):
    rx = {v: k for k, v in enumerate(sorted(range(len(x)), key=lambda k: x[k]))}
    ry = {v: k for k, v in enumerate(sorted(range(len(y)), key=lambda k: y[k]))}
    n = len(x)
    d2 = sum((rx[i] - ry[i]) ** 2 for i in range(n))
    return 1 - 6 * d2 / (n * (n * n - 1))

rho = spearman(D_a, D_b)
print(f"\nA 与 B 口径 D 值的 Spearman 秩相关 = {rho:.3f}")
top_b = sorted(subset, key=lambda r: -r["D_b"])[:10]
print("B 口径最高的 10 个县：")
for r in top_b:
    print(f"  {r['县名']}：村落 {r['v']}｜非遗B {r['b']}｜D = {r['D_b']:.3f}")
top_a_set = {r["县名"] for r in top}
top_b_set = {r["县名"] for r in top_b}
print(f"两个前十名单的重叠：{len(top_a_set & top_b_set)}/10")

with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["adcode", "县名", "村落数", "非遗A", "非遗B", "D_A主口径", "D_B敏感性"])
    for r in subset:
        w.writerow([r["adcode"], r["县名"], r["v"], r["a"], r["b"],
                    f"{r['D_a']:.4f}", f"{r['D_b']:.4f}"])
print(f"已保存：{OUT_CSV}")

# ---------- 2. 制图 ----------
geo = json.loads((DATA / "03_基础地理" / "中国_县级边界_统计.geojson").read_text(encoding="utf-8"))
d_map = {str(r["adcode"]): klass(r["D_a"]) for r in subset}

polys, face = [], []
for feat in geo["features"]:
    g = feat.get("geometry")
    if not g:
        continue
    parts = [g["coordinates"][0]] if g["type"] == "Polygon" else [p[0] for p in g["coordinates"]]
    k = d_map.get(str(feat["properties"]["adcode"]))
    if k is None:
        k = -1                                  # 无要素县
    for part in parts:
        polys.append(part)
        face.append(k)

fig, ax = plt.subplots(figsize=(11, 8.5), dpi=200)
cmap = ListedColormap(["#eeeeee"] + COLORS)
norm = BoundaryNorm(range(-1, 6), cmap.N)
ax.add_collection(PolyCollection(polys, array=np.array(face), cmap=cmap, norm=norm,
                                 edgecolor="#aaaaaa", linewidths=0.06))
ax.set_xlim(73, 135.5); ax.set_ylim(15, 54); ax.set_aspect(1.18)
ax.set_title("县域传统村落与非遗耦合协调度（D，全量口径，预览图）", fontsize=14)
ax.set_xticks([]); ax.set_yticks([])
import matplotlib.patches as mpatches
handles = [mpatches.Patch(color="#eeeeee", label="无要素县")] + [
    mpatches.Patch(color=COLORS[k], label=LABELS[k]) for k in range(5)]
ax.legend(handles=handles, loc="lower left", fontsize=9, frameon=True)
fig.savefig(OUT_PNG, bbox_inches="tight", facecolor="white")
print(f"已保存：{OUT_PNG}")
