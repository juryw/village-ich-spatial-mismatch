# -*- coding: utf-8 -*-
"""
14_空间分布格局.py
作用：计算并绘制论文"分布格局"一节的核心内容：
  1) 最邻近指数 NNI（聚集/随机/均匀 判定 + Z 检验）
  2) 核密度分析（KDE，图2 左村落右非遗）
  3) 标准差椭圆 SDE（方向与展布，叠加在图2上）
  4) 县级规模的基尼系数（分布均衡度）
坐标：Albers 等积圆锥投影（中央经线105°，标准纬线25/47），面积与距离才可靠。
KDE 实现：先栅格化计数，再高斯滤波平滑——与ArcGIS核密度原理一致且快得多。
⚠ 权威数字提示：本脚本早期版本的 NNI-Z 公式有误（SE 误用 √(A/n)）、VMR 网格随点集
   漂移；论文采用的权威 NNI-Z 与 VMR 见 51_整改_M1_M3_M4.py（Z=−86.4/−78.0，
   统一 700 格网格 VMR=145.9/45.0）。本脚本保留用于绘图流程复现。
"""
import csv
import json
import struct
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
from scipy import ndimage
from scipy.spatial import cKDTree
from shapely.geometry import shape
from shapely.ops import transform, unary_union
from shapely import contains_xy
import pyproj

plt.rcParams["font.family"] = "Microsoft YaHei"
plt.rcParams["axes.unicode_minus"] = False

DATA = Path(r"E:\GLM\非遗论文\02_数据")
OUT = Path(r"E:\GLM\非遗论文\04_图表") / "图2_核密度与标准差椭圆_预览.png"

PROJ = pyproj.Transformer.from_crs("EPSG:4326",
    "+proj=aea +lat_1=25 +lat_2=47 +lon_0=105 +datum=WGS84 +units=m", always_xy=True).transform

def to_xy(lon, lat):
    return PROJ(lon, lat)

# ---------- 1. 数据 ----------
vill = json.loads((DATA / "02_传统村落" / "合并_传统村落_前五批.geojson").read_text(encoding="utf-8"))
vxy = np.array([to_xy(*f["geometry"]["coordinates"]) for f in vill["features"]]) / 1000.0  # km

raw = (DATA / "01_非遗名录" / "IhChina_2006-2021" / "IhChina_2006-2021.dbf").read_bytes()
n_rec = struct.unpack("<I", raw[4:8])[0]
h_size, r_size = struct.unpack("<H", raw[8:10])[0], struct.unpack("<H", raw[10:12])[0]
fields, pos = [], 32
while raw[pos] != 0x0D:
    fields.append((raw[pos:pos + 11].split(b"\x00")[0].decode("ascii"), raw[pos + 16]))
    pos += 32
widths = [w for _, w in fields]
idx = {nm: k for k, (nm, _) in enumerate(fields)}
ixy = np.empty((n_rec, 2))
for i in range(n_rec):
    start = h_size + i * r_size + 1
    p, vals = start, []
    for w in widths:
        vals.append(raw[p:p + w].decode("utf-8", errors="replace").strip())
        p += w
    ixy[i] = to_xy(float(vals[idx["X"]]), float(vals[idx["Y"]]))
ixy /= 1000.0

# ---------- 2. 研究区面积（县级边界投影后求和，互不重叠） ----------
geo = json.loads((DATA / "03_基础地理" / "中国_县级边界_修复.geojson").read_text(encoding="utf-8"))
polys = [transform(PROJ, shape(f["geometry"])) for f in geo["features"] if f.get("geometry")]
AREA_KM2 = sum(p.area for p in polys) / 1e6
print(f"研究区面积（县级边界合计）：{AREA_KM2:,.0f} km²")

# 投影后的整体范围（VMR 样方与 KDE 网格都要用，单位 km）
all_bounds = np.array([p.bounds for p in polys])
xmin0, ymin0 = all_bounds[:, 0].min() / 1000, all_bounds[:, 1].min() / 1000

# ---------- 3. 最邻近指数 ----------
def nni(pts, label):
    n = len(pts)
    tree = cKDTree(pts)
    d, _ = tree.query(pts, k=2)          # k=2 的第 2 列才是"最近邻"（第 1 列是自己）
    obs = d[:, 1].mean()
    exp = 0.5 * np.sqrt(AREA_KM2 / n)
    z = (obs - exp) / (0.26136 * np.sqrt(AREA_KM2 / n))
    print(f"{label}: NNI = {obs / exp:.3f}（观测 {obs:.1f} km / 期望 {exp:.1f} km），Z = {z:.1f}")
    return obs / exp

def vmr(pts, label, cell_km=200):
    """方差均值比（样方法）：VMR>1 且卡方显著 → 集聚分布。对大范围稀疏点比 NNI 的 Z 更稳健。"""
    from collections import Counter
    qx = ((pts[:, 0] - xmin0) // cell_km).astype(int)
    qy = ((pts[:, 1] - ymin0) // cell_km).astype(int)
    nq_x, nq_y = qx.max() + 1, qy.max() + 1
    grid = np.zeros(nq_x * nq_y)
    for (a, b), c in Counter(zip(qx.tolist(), qy.tolist())).items():
        grid[b * nq_x + a] = c
    m = grid.mean()
    vmr_v = grid.var() / m
    chi2 = (len(grid) - 1) * vmr_v
    crit = 1.64 * np.sqrt(2 * (len(grid) - 1)) + (len(grid) - 1)   # χ² 近似：均值+1.64σ
    print(f"{label}: 样方{cell_km}km，方格数 {len(grid)}，VMR = {vmr_v:.2f}，χ² = {chi2:,.0f} > 临界 {crit:,.0f} → "
          f"{'显著集聚 (α=0.05)' if chi2 > crit else '未达显著'}")
    return vmr_v

nni(vxy, "传统村落")
nni(ixy, "国家级非遗")
vmr(vxy, "传统村落")
vmr(ixy, "国家级非遗")

# ---------- 4. 标准差椭圆（1σ） ----------
def sde(pts, label):
    cx, cy = pts.mean(axis=0)
    cov = np.cov(pts.T)
    vals, vecs = np.linalg.eigh(cov)     # eigh 升序
    ax1, ax2 = np.sqrt(vals[1]), np.sqrt(vals[0])   # 半轴 = sqrt(特征值)
    ang = np.degrees(np.arctan2(vecs[1, 1], vecs[0, 1]))
    print(f"{label}: 中心({cx:.0f},{cy:.0f})km 半轴 {ax1:.0f}×{ax2:.0f} km 方位 {ang:.1f}°")
    return cx, cy, ax1, ax2, ang

v_ell = sde(vxy, "村落椭圆")
i_ell = sde(ixy, "非遗椭圆")

# ---------- 5. 基尼系数（县级数量分布） ----------
def gini(counts):
    counts = np.sort(np.asarray(counts, dtype=float))
    n = len(counts)
    cum = np.cumsum(counts)
    return (n + 1 - 2 * np.sum(cum) / cum[-1]) / n

stats = list(csv.DictReader(open(DATA / "03_基础地理" / "县域统计_村落非遗.csv", encoding="utf-8-sig")))
print(f"基尼系数：村落 {gini([int(r['村落数']) for r in stats]):.3f}｜非遗 {gini([int(r['非遗数']) for r in stats]):.3f}")

# ---------- 6. 核密度图（栅格化 + 高斯滤波） ----------
unified = unary_union(polys)
xmin, ymin, xmax, ymax = unified.bounds
xmin, ymin, xmax, ymax = xmin / 1000, ymin / 1000, xmax / 1000, ymax / 1000
NB = 600
xe = np.linspace(xmin, xmax, NB)      # 格网边界
ye = np.linspace(ymin, ymax, NB)
cell = (xmax - xmin) / (NB - 1)
xc = (xe[:-1] + xe[1:]) / 2           # 格心（用于边界掩膜）
yc = (ye[:-1] + ye[1:]) / 2

def kde_grid(pts):
    H, _, _ = np.histogram2d(pts[:, 1], pts[:, 0], bins=[ye, xe])  # 行=y 列=x
    bw = pts.std() * len(pts) ** (-1 / 6)          # Scott 带宽（2维）
    return ndimage.gaussian_filter(H, sigma=bw / cell)

HXc, HYc = np.meshgrid(xc, yc)
mask = contains_xy(unified, HXc * 1000, HYc * 1000)   # x、y 作为两个参数传入

v_grid = np.where(mask, kde_grid(vxy), np.nan) / cell ** 2 * 1000   # 换算为 处/千km²
i_grid = np.where(mask, kde_grid(ixy), np.nan) / cell ** 2 * 1000

fig, axes = plt.subplots(1, 2, figsize=(15, 7.5), dpi=200)
vmax_common = float(np.nanmax(v_grid))          # 两幅共用同一色标上限，便于目视比较
for ax, grid, pts, ell, title, cmap in (
    (axes[0], v_grid, vxy, v_ell, "传统村落核密度（处/千km²）", "Blues"),
    (axes[1], i_grid, ixy, i_ell, "国家级非遗核密度（处/千km²）", "Reds"),
):
    im = ax.imshow(grid, origin="lower", extent=[xmin, xmax, ymin, ymax],
                   cmap=cmap, aspect="equal", vmin=0, vmax=vmax_common)
    cx, cy, a1, a2, ang = ell
    ax.add_patch(Ellipse((cx, cy), 2 * a1, 2 * a2, angle=ang,
                         fill=False, ls="--", ec="#333333", lw=1.4))
    ax.plot(cx, cy, "*", ms=14, mec="k", mfc="#ffdf00")
    ax.set_title(title, fontsize=13)
    ax.set_xticks([]); ax.set_yticks([])
    fig.colorbar(im, ax=ax, shrink=0.7, pad=0.01)

fig.suptitle("中国传统村落与国家级非遗的核密度与标准差椭圆", fontsize=15)
OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, bbox_inches="tight", facecolor="white")
print(f"已保存：{OUT}（统一色标上限 {vmax_common:.2f} 处/千km²）")
