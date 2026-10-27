# -*- coding: utf-8 -*-
"""
51_整改_M1_M3_M4.py（DeepSeek 审稿意见·确认有误项整改）
M3：NNI 的 Z 公式更正（SE=0.26136·√A/n）
M4：VMR 改用统一网格（研究区外包框锚定、两套点集同一格网），并报告格数
M1：CCD 改在 758 个双要素县上计算分级；1217 个单要素县拆分为"纯村落/纯非遗"单列
    并重算 B(v3) 口径在 758 县上的 Spearman 秩相关
输出：全部新数字（供正文与表 2/表 3 改写）
"""
import csv
import json
import math
import struct
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import numpy as np
import pyproj
from shapely.geometry import Point, shape as shp_shape
from shapely.ops import transform as shp_tr

DATA = Path(r"E:\GLM\非遗论文\02_数据")
PROJ = pyproj.Transformer.from_crs("EPSG:4326",
    "+proj=aea +lat_1=25 +lat_2=47 +lon_0=105 +datum=WGS84 +units=m", always_xy=True).transform

# ---------- 点集 ----------
vill = json.loads((DATA / "02_传统村落" / "合并_传统村落_前五批.geojson").read_text(encoding="utf-8"))
vxy = np.array([[*shp_tr(PROJ, Point(f["geometry"]["coordinates"])).coords][0] for f in vill["features"]]) / 1000.0
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
    ixy[i] = PROJ(float(vals[idx["X"]]), float(vals[idx["Y"]]))
ixy /= 1000.0

# ---------- M4：统一网格 VMR ----------
GEO = json.loads((DATA / "03_基础地理" / "中国_县级边界_修复.geojson").read_text(encoding="utf-8"))
allb = np.array([shp_tr(PROJ, shp_shape(f_["geometry"])).bounds for f_ in GEO["features"] if f_.get("geometry")]) / 1000.0  # →km
xmin0, ymin0 = allb[:, 0].min(), allb[:, 1].min()
xmax0, ymax0 = allb[:, 2].max(), allb[:, 3].max()

def vmr_fixed(pts, cell_km, label):
    nx = int(math.ceil((xmax0 - xmin0) / cell_km))
    ny = int(math.ceil((ymax0 - ymin0) / cell_km))
    qx = np.clip(((pts[:, 0] - xmin0) // cell_km).astype(int), 0, nx - 1)
    qy = np.clip(((pts[:, 1] - ymin0) // cell_km).astype(int), 0, ny - 1)
    grid = np.zeros(nx * ny)
    for a, b in zip(qx.tolist(), qy.tolist()):
        grid[b * nx + a] += 1
    m = grid.mean()
    v = grid.var()
    chi2 = (len(grid) - 1) * v / m
    print(f"  {label}: 格网 {nx}×{ny}={len(grid)} 格（cell={cell_km}km），"
          f"VMR={v/m:.2f}，χ²={chi2:,.0f}（df={len(grid)-1}）")
    return v / m, chi2, len(grid)

print("【M4 整改】统一网格 VMR（同一格网、可比较）：")
v200, c200, n200 = vmr_fixed(vxy, 200, "村落")
i200, ci200, _ = vmr_fixed(ixy, 200, "非遗")
print("  尺度敏感性（补充，供审稿人）：")
for cell in (100, 150, 300):
    vmr_fixed(vxy, cell, f"村落{cell}km")
    vmr_fixed(ixy, cell, f"非遗{cell}km")

# ---------- M3：NNI 正确 Z ----------
A_km2 = 9489084.0  # 县级多边形真面积之和（脚本 14 已验证），bbox 求和会因重叠高估
print(f"\n【M3 整改】NNI 的 Z（正确公式 SE=0.26136·√A/n，A={A_km2:,.0f} km²）：")
for label, n, obs, exp in (("村落", 6817, 8.5, 18.7), ("非遗", 3610, 8.2, 25.6)):
    se = 0.26136 * math.sqrt(A_km2) / n
    print(f"  {label}: Z = {(obs - exp) / se:.1f}")

# ---------- M1：CCD 改在 758 双要素县上 ----------
sens = list(csv.DictReader(open(DATA / "03_基础地理" / "县域统计_敏感性对比.csv", encoding="utf-8-sig")))
ccd = {r["adcode"]: float(r["D_A主口径"]) for r in csv.DictReader(
    open(DATA / "03_基础地理" / "县域耦合协调度.csv", encoding="utf-8-sig"))}
dual = [r for r in sens if int(r["村落数"]) > 0 and int(r["非遗A全量"]) > 0]
pure_v = [r for r in sens if int(r["村落数"]) > 0 and int(r["非遗A全量"]) == 0]
pure_i = [r for r in sens if int(r["村落数"]) == 0 and int(r["非遗A全量"]) > 0]
print(f"\n【M1 整改】双要素县 {len(dual)}｜纯村落县 {len(pure_v)}｜纯非遗县 {len(pure_i)}"
      f"（合计 {len(dual)+len(pure_v)+len(pure_i)} = 大陆 2848）")
d_dual = np.array([ccd[r["adcode"]] for r in dual])
BREAKS = [0, 0.10, 0.20, 0.30, 0.40, 1.01]
LBL = ["<0.10", "0.10~0.20", "0.20~0.30", "0.30~0.40", "≥0.40"]
print("  双要素县 D 分级：")
for k in range(5):
    n_k = int(((d_dual >= BREAKS[k]) & (d_dual < BREAKS[k + 1])).sum())
    print(f"    {LBL[k]}: {n_k} 县（{100*n_k/len(dual):.1f}%）")
print(f"  中位 {np.median(d_dual):.3f}｜P25 {np.percentile(d_dual,25):.3f}｜"
      f"P75 {np.percentile(d_dual,75):.3f}｜最小 {d_dual.min():.3f}｜最大 {d_dual.max():.3f}")

# B(v3) 口径在 758 县上的 CCD 与 Spearman
b_map = {r["adcode"]: int(r["非遗B剔除后"]) for r in sens}
vs = np.array([int(r["村落数"]) for r in dual], dtype=float)
isb = np.array([b_map[r["adcode"]] for r in dual], dtype=float)
u1 = (vs - vs.min()) / (vs.max() - vs.min() + 1e-12)
u2 = (isb - isb.min()) / (isb.max() - isb.min() + 1e-12)
Cb = 2 * np.sqrt(u1 * u2) / (u1 + u2 + 1e-12)
Tb = 0.5 * u1 + 0.5 * u2
Db = np.sqrt(Cb * Tb)
ia = np.array([int(r["非遗A全量"]) for r in dual], dtype=float)
u2a = (ia - ia.min()) / (ia.max() - ia.min() + 1e-12)
Ca = 2 * np.sqrt(u1 * u2a) / (u1 + u2a + 1e-12)
Da = np.sqrt(Ca * (0.5 * u1 + 0.5 * u2a))

def spearman(x, y):
    rx = np.argsort(np.argsort(x))
    ry = np.argsort(np.argsort(y))
    return 1 - 6 * np.sum((rx - ry) ** 2) / (len(x) * (len(x) ** 2 - 1))

print(f"\n  758 县上 A vs B(v3) 协调度的 Spearman 秩相关 = {spearman(Da, Db):.3f}")
top_a = [dual[k]["县名"] for k in np.argsort(-Da)[:10]]
top_b = [dual[k]["县名"] for k in np.argsort(-Db)[:10]]
print(f"  A 前十：{'、'.join(top_a)}")
print(f"  B 前十：{'、'.join(top_b)}")
print(f"  前十重合：{len(set(top_a) & set(top_b))}/10")
print(f"  B 口径下 ≥0.4 的县：{int((Db >= 0.4).sum())} 个")
