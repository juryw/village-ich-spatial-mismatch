# -*- coding: utf-8 -*-
"""
43_口径v3主口径与多规则稳健性.py（新的权威敏感性脚本，取代39号）
背景（审稿自查发现）：旧 S2 规则存在系统性类别偏差——文艺院团转企改制后
     在地剧团/老字号企业名含"公司/剧院"被误删（技艺1.67x、医药2.40x），
     396 条非北上津在地单位被连坐。
新口径设计：
  A 主分析口径 = 全量 3610
  B 主口径     = v3：仅剔"全国性机构"（单位名含 中国/国家/中华/全国 或
                 协会/学会/研究会/研究院/研究所/促进会/联合会/大学/学院），434 条
  C 严格下界   = S1∪S2（旧口径），1115 条
  D 备选       = 仅 S2（1001 条）——留档供审稿人对照
产出：县域统计_敏感性对比.csv（B=v3）、县域LISA结果.csv、
     图4 双联图（A / B-v3）、全局双变量 I 的 计数/密度 双口径数字。
"""
import csv
import json
import math
import random
import struct
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
random.seed(42)
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import ListedColormap, BoundaryNorm
import matplotlib.patches as mpatches

plt.rcParams["font.family"] = "Microsoft YaHei"

DATA = Path(r"E:\GLM\非遗论文\02_数据")
OUT_PNG = Path(r"E:\GLM\非遗论文\04_图表") / "图4_双变量LISA集聚图_预览.png"

KW_V3 = ["中国", "国家", "中华", "全国", "协会", "学会", "研究会", "研究院",
         "研究所", "促进会", "联合会", "大学", "学院"]
KW_S2 = KW_V3 + ["公司", "集团", "剧院", "剧团", "演艺"]
METRO = ("北京市", "上海市", "天津市")

# ---------- 1. 读非遗 DBF ----------
raw = (DATA / "01_非遗名录" / "IhChina_2006-2021" / "IhChina_2006-2021.dbf").read_bytes()
n_rec = struct.unpack("<I", raw[4:8])[0]
h_size, r_size = struct.unpack("<H", raw[8:10])[0], struct.unpack("<H", raw[10:12])[0]
fields, pos = [], 32
while raw[pos] != 0x0D:
    fields.append((raw[pos:pos + 11].split(b"\x00")[0].decode("ascii"), raw[pos + 16]))
    pos += 32
widths = [w for _, w in fields]
idx = {nm: k for k, (nm, _) in enumerate(fields)}
ich = []
for i in range(n_rec):
    start = h_size + i * r_size + 1
    p, vals = start, []
    for w in widths:
        vals.append(raw[p:p + w].decode("utf-8", errors="replace").strip())
        p += w
    ich.append({"name": vals[idx["Name_CN"]], "place": vals[idx["Place_CN"]],
                "unit": vals[idx["Unit_CN"]], "cat": vals[idx["CategoryCN"]],
                "x": float(vals[idx["X"]]), "y": float(vals[idx["Y"]])})

s1 = lambda r: r["place"].startswith(METRO)
v3 = lambda r: any(k in r["unit"] for k in KW_V3)
s2 = lambda r: any(k in r["unit"] for k in KW_S2)
n_v3 = sum(1 for r in ich if v3(r))
n_s2 = sum(1 for r in ich if s2(r))
n_strict = sum(1 for r in ich if s1(r) or s2(r))
print(f"口径：A 全量 {len(ich)}｜B v3 剔 {n_v3}｜C S1∪S2 剔 {n_strict}｜D 仅S2 剔 {n_s2}")

# ---------- 2. 县级边界 + 网格索引（与 09 一致） ----------
geo = json.loads((DATA / "03_基础地理" / "中国_县级边界_修复.geojson").read_text(encoding="utf-8"))
counties = []
for f_ in geo["features"]:
    g = f_.get("geometry")
    if not g:
        continue
    parts = [g["coordinates"][0]] if g["type"] == "Polygon" else [p[0] for p in g["coordinates"]]
    xs = [x for part in parts for x, _ in part]
    ys = [y for part in parts for _, y in part]
    counties.append({"adcode": str(f_["properties"]["adcode"]), "name": f_["properties"].get("name", ""),
                     "parts": parts, "bbox": (min(xs), min(ys), max(xs), max(ys)),
                     "cx": (min(xs) + max(xs)) / 2, "cy": (min(ys) + max(ys)) / 2,
                     "B": 0, "C": 0, "D": 0})
GRID = {}
for i, c in enumerate(counties):
    x0, y0, x1, y1 = c["bbox"]
    for gx in range(math.floor(x0), math.floor(x1) + 1):
        for gy in range(math.floor(y0), math.floor(y1) + 1):
            GRID.setdefault((gx, gy), []).append(i)

def pip(x, y, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x1 + (y - y1) * (x2 - x1) / (y2 - y1) > x:
            inside = not inside
    return inside

def assign(x, y):
    for i in GRID.get((math.floor(x), math.floor(y)), []):
        if any(pip(x, y, part) for part in counties[i]["parts"]):
            return i
    best, bd = None, 1e9
    for i in GRID.get((math.floor(x), math.floor(y)), []):
        d = (counties[i]["cx"] - x) ** 2 + (counties[i]["cy"] - y) ** 2
        if d < bd:
            best, bd = i, d
    return best

for r in ich:
    i = assign(r["x"], r["y"])
    if i is None:
        continue
    if not v3(r):
        counties[i]["B"] += 1
    if not (s1(r) or s2(r)):
        counties[i]["C"] += 1
    if not s2(r):
        counties[i]["D"] += 1

# ---------- 3. 更新敏感性对比 CSV（B=v3 主口径） ----------
_prev = list(csv.DictReader(open(DATA / "03_基础地理" / "县域统计_敏感性对比.csv", encoding="utf-8-sig")))
_old = {r["adcode"]: r for r in _prev}
with open(DATA / "03_基础地理" / "县域统计_敏感性对比.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.writer(fh)
    w.writerow(["adcode", "县名", "村落数", "非遗A全量", "非遗B剔除后", "非遗C严格(S1∪S2)", "非遗D仅S2"])
    for c in counties:
        old = _old.get(c["adcode"], {})
        v = int(old.get("村落数", 0))
        a = int(old.get("非遗A全量", 0))
        w.writerow([c["adcode"], c["name"], v, a, c["B"], c["C"], c["D"]])
print(f"敏感性对比表已更新（B=v3 主口径）")

# ---------- 4. LISA（Queen 邻接，A 与 B 双口径，计数+密度） ----------
from shapely.geometry import shape
from shapely import STRtree
import libpysal
from esda.moran import Moran, Moran_BV, Moran_Local_BV

feats = [f for f in json.loads((DATA / "03_基础地理" / "中国_县级边界_统计.geojson")
        .read_text(encoding="utf-8"))["features"]
        if f.get("geometry") and str(f["properties"]["adcode"]) < "810000"]
geoms = [shape(f["geometry"]).buffer(0) for f in feats]
area_map = {r["adcode"]: float(r["area_km2"]) for r in csv.DictReader(
    open(DATA / "03_基础地理" / "县域驱动因子表.csv", encoding="utf-8-sig"))}
vc = np.array([f["properties"]["VILLAGE_N"] for f in feats], dtype=float)
ic = np.array([f["properties"]["ICH_N"] for f in feats], dtype=float)
area = np.array([area_map.get(str(f["properties"]["adcode"]), 1.0) for f in feats])
b_map = {str(f["properties"]["adcode"]): None for f in feats}
for c in counties:
    if c["adcode"] in b_map:
        b_map[c["adcode"]] = c["B"]
ib = np.array([b_map[str(f["properties"]["adcode"])] or 0 for f in feats], dtype=float)

tree = STRtree(geoms)
pairs = tree.query(geoms, predicate="touches")
neighbors = {k: set() for k in range(len(geoms))}
for a, b in zip(pairs[0], pairs[1]):
    if a != b:
        neighbors[int(a)].add(int(b))
wq = libpysal.weights.W(neighbors, silence_warnings=True)

vd, id_ = vc / area * 1000, ic / area * 1000
bd = ib / area * 1000
print(f"\n全局双变量 I（村落→非遗）：")
print(f"  A 计数 {Moran_BV(vc, ic, wq).I:.4f}｜A 密度 {Moran_BV(vd, id_, wq).I:.4f}")
print(f"  B 计数 {Moran_BV(vc, ib, wq).I:.4f}｜B 密度 {Moran_BV(vd, bd, wq).I:.4f}")
print(f"  C 计数 {Moran_BV(vc, np.array([next((c['C'] for c in counties if c['adcode']==str(f['properties']['adcode'])), 0) for f in feats]), wq).I:.4f}")

lisa = Moran_Local_BV(vc, ib, wq, permutations=199)
q, p = lisa.q, lisa.p_sim
cls = np.zeros(len(vc), dtype=int)
for qq in (1, 2, 3, 4):
    cls[(q == qq) & (p <= 0.05)] = qq
NAMES = {0: "不显著", 1: "高-高 协同", 3: "低-低 低值连片", 4: "高-低 错位(村落富集·非遗稀缺)", 2: "低-高 错位(非遗富集·村落稀缺)"}
print("\nB 口径（v3）局部 LISA：")
for qq in (1, 2, 3, 4, 0):
    print(f"  {NAMES[qq]}：{int((cls == qq).sum())} 个县")
hh = [feats[k]["properties"]["name"] for k in np.where(cls == 1)[0]]
print("B 口径高-高前列：", "、".join(hh[:24]))

with open(DATA / "03_基础地理" / "县域LISA结果.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.writer(fh)
    w.writerow(["adcode", "县名", "村落数", "非遗B(v3)", "象限", "p值", "分类"])
    for k, feat in enumerate(feats):
        w.writerow([feat["properties"]["adcode"], feat["properties"]["name"],
                    int(vc[k]), int(ib[k]), int(q[k]), f"{p[k]:.4f}", NAMES[cls[k]]])

# ---------- 5. 图4 双联（A / B-v3） ----------
COLORS = {1: "#d7191c", 3: "#2c7bb6", 4: "#fdae61", 2: "#abd9e9", 0: "#e8e8e8"}
cls_map_a = {str(feats[k]["properties"]["adcode"]): 0 for k in range(len(feats))}
# A 口径局部 LISA 也算一遍（用于左图）
lisa_a = Moran_Local_BV(vc, ic, wq, permutations=199)
qa, pa_ = lisa_a.q, lisa_a.p_sim
cls_a = np.zeros(len(vc), dtype=int)
for qq in (1, 2, 3, 4):
    cls_a[(qa == qq) & (pa_ <= 0.05)] = qq
for k in range(len(feats)):
    cls_map_a[str(feats[k]["properties"]["adcode"])] = cls_a[k]
cls_map_b = {str(feats[k]["properties"]["adcode"]): cls[k] for k in range(len(feats))}

polys, fa, fb = [], [], []
for feat in json.loads((DATA / "03_基础地理" / "中国_县级边界_统计.geojson").read_text(encoding="utf-8"))["features"]:
    g = feat.get("geometry")
    if not g:
        continue
    parts = [g["coordinates"][0]] if g["type"] == "Polygon" else [p[0] for p in g["coordinates"]]
    ac = str(feat["properties"]["adcode"])
    for part in parts:
        polys.append(part)
        fa.append(cls_map_a.get(ac, 0))
        fb.append(cls_map_b.get(ac, 0))

fig, axes = plt.subplots(1, 2, figsize=(15, 7.5), dpi=200, sharex=True, sharey=True)
cmap = ListedColormap([COLORS[0], COLORS[1], COLORS[2], COLORS[3], COLORS[4]])
norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5, 4.5], cmap.N)
for ax, face, title in (
    (axes[0], fa, "A 全量口径（n=3610）"),
    (axes[1], fb, "B 剔除全国性机构点位（n=3176）"),
):
    ax.add_collection(PolyCollection(polys, array=np.array(face), cmap=cmap, norm=norm,
                                     edgecolor="#999999", linewidths=0.06))
    ax.set_xlim(73, 135.5); ax.set_ylim(15, 54); ax.set_aspect(1.18)
    ax.set_title(title, fontsize=12)
    ax.set_xticks([]); ax.set_yticks([])
fig.suptitle("传统村落与非遗的双变量LISA集聚格局：机构注册效应清洗前后对比（p≤0.05，预览图）", fontsize=14)
handles = [mpatches.Patch(color=COLORS[k], label=NAMES[k]) for k in (1, 3, 4, 2, 0)]
axes[0].legend(handles=handles, loc="lower left", fontsize=8, frameon=True)
fig.savefig(OUT_PNG, bbox_inches="tight", facecolor="white")
print(f"图4 已更新：{OUT_PNG}")

# ---------- 6. 剔除清单（含规则标记） ----------
with open(DATA / "01_非遗名录" / "敏感性_剔除点位清单.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.writer(fh)
    w.writerow(["项目名称", "申报地区", "保护单位", "B主口径(v3)", "C严格(S1∪S2)"])
    for r in sorted(ich, key=lambda r: r["place"]):
        if v3(r) or (s1(r) or s2(r)):
            w.writerow([r["name"], r["place"], r["unit"],
                        "是" if v3(r) else "", "是" if (s1(r) or s2(r)) else ""])
print("剔除清单已更新")
