# -*- coding: utf-8 -*-
"""
23_探测器v1.py
作用：合并 驱动因子表 + GDP + 人口 + 海拔（+路网，若有）为 v2 因子表，
     跑地理探测器正式版：因子探测（q + F 检验）与交互探测。
因变量：县域村落密度、非遗密度（处/千km²）；口径 A/B 双版本（B 用敏感性对比表的非遗B）。
"""
import csv
import json
from pathlib import Path

import numpy as np
from scipy import stats as sps

DATA = Path(r"E:\GLM\非遗论文\02_数据\03_基础地理")

def load(path, key="adcode"):
    return {str(r[key]): r for r in csv.DictReader(open(path, encoding="utf-8-sig"))}

drv = load(DATA / "县域驱动因子表.csv")
gdp = load(DATA / "县域GDP_2020.csv")
pop = load(DATA / "县域人口_2020.csv")
try:
    dem = load(DATA / "县域海拔.csv")
except FileNotFoundError:
    dem = {}
try:
    road = load(DATA / "县域路网.csv")          # 夜班5若完成则自动纳入
except FileNotFoundError:
    road = {}
cmp_ = load(DATA / "县域统计_敏感性对比.csv")
_b_key = "非遗B剔除后(仅S2)" if "非遗B剔除后(仅S2)" in next(iter(cmp_.values())) else "非遗B剔除后"

common = [c for c in drv if c in gdp and c in pop]
print(f"因子表县数：{len(common)}（海拔 {sum(1 for c in common if c in dem)}，路网 {sum(1 for c in common if c in road)}）")

def col(src, key, cast=float, default=0.0):
    def cv(c):
        v = src.get(c, {}).get(key, default)
        if v == "" or v is None:
            return np.nan
        return cast(v)
    return np.array([cv(c) for c in common])

def qc(x, m=5):
    edges = np.quantile(x[~np.isnan(x)], np.linspace(0, 1, m + 1)[1:-1])
    out = np.searchsorted(edges, x, side="right").astype(float)
    out[np.isnan(x)] = np.nan        # 缺失县不参与该因子
    return out

area = col(drv, "area_km2")
Y_v = col(drv, "village") / area * 1000
Y_a = col(drv, "ich") / area * 1000
Y_b = np.array([float(cmp_.get(c, {}).get(_b_key, 0)) for c in common]) / area * 1000

X = {
    "GDP密度": qc(col(gdp, "GDP密度_万元每km2")),
    "人口密度": qc(col(pop, "人口密度_人每km2")),
    "距省会距离": qc(col(drv, "d_capital")),
    "县域面积": qc(area),
    "民族自治地方": col(drv, "ethnic").astype(int),
    "经度位置": qc(col(drv, "lon")),
    "纬度位置": qc(col(drv, "lat")),
}
if dem:
    X["平均海拔"] = qc(col(dem, "平均海拔_m", default=np.nan))
if dem:
    X["地形起伏度"] = qc(col(dem, "地形起伏度_m(像元std)", default=np.nan))
if road:
    X["路网密度"] = qc(col(road, "路网密度_km每km2"))

def q_stat(y, x):
    ok = ~np.isnan(y) & ~np.isnan(x.astype(float))
    y, x = y[ok], x[ok]
    sst = ((y - y.mean()) ** 2).sum()
    ssw = sum(len(y[x == h]) * y[x == h].var() for h in np.unique(x))
    q = 1 - ssw / sst
    L, N = len(np.unique(x)), len(y)
    f = (ssw / (L - 1)) / ((sst - ssw) / (N - L)) if L > 1 and sst > ssw else np.inf
    return q, 1 - sps.f.cdf(f, L - 1, N - L)

rows_out = []
print("\n【因子探测 q（p：*** <0.01，** <0.05）】")
for yn, y in (("村落密度", Y_v), ("非遗A", Y_a), ("非遗B", Y_b)):
    line = f"  {yn}: "
    for xn, x in X.items():
        q, p = q_stat(y, x)
        line += f"{xn} {q:.3f}{'***' if p < 0.01 else '**' if p < 0.05 else ''}｜"
        rows_out.append({"因变量": yn, "因子": xn, "q": f"{q:.4f}", "p": f"{p:.4g}"})
    print(line)

print("\n【交互探测（村落密度主表；其余表存CSV）】")
names = list(X)
with open(DATA / "探测器结果_v1.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["因变量", "因子对", "q交互", "q1", "q2", "类型"])
    for yn, y in (("村落密度", Y_v), ("非遗A", Y_a), ("非遗B", Y_b)):
        for a in range(len(names)):
            for b in range(a + 1, len(names)):
                inter = X[names[a]] * 100 + X[names[b]]
                q_ab, _ = q_stat(y, inter)
                q_a, _ = q_stat(y, X[names[a]])
                q_b, _ = q_stat(y, X[names[b]])
                kind = ("非线性增强" if q_ab > q_a + q_b else "双因子增强" if q_ab > max(q_a, q_b) else "减弱")
                w.writerow([yn, f"{names[a]}×{names[b]}", f"{q_ab:.4f}", f"{q_a:.4f}", f"{q_b:.4f}", kind])
                if yn == "村落密度":
                    print(f"    {names[a]}×{names[b]} q={q_ab:.3f} → {kind}")
print(f"\n已保存：{DATA / '探测器结果_v1.csv'}")
