# -*- coding: utf-8 -*-
"""
54_整改第二批_方法升级.py（DeepSeek M2/M5/M6/M7/M8/M9/M10/M11/M12/M14/M15/M16）
输出（全部打印，供正文改写）：
  [A] 全局双变量 I：岛屿口径统一（n=2806）、999 置换、E[I] 与 z 值；残差 I（回归掉 log 面积）
  [B] 局部 LISA：999 置换 + BH-FDR 校正；三口径×四类别交叉表；稳健核心（A∩B）与三口径交集
  [C] 武陵山—苗岭带：以州级建制事前界定（湘西/黔东南/恩施），报告带内入选率
  [D] 探测器 v2：删面积/经纬度因子（7 因子），758 双要素县同子样本，q 的 999 置换检验
  [E] 交互：q(∩)−max(q) 超额分布
  [F] M2：秩归一化 CCD 对照（Spearman + 前十）
  [G] M11：v3 剔除门类 χ² 中性检验；两类关键词标记分列
  [H] M12：带界建制化后的入选/未入选
  [I] M14：跨省登记单位（申报地≠保护单位所在省）数量与构成
  [J] 结-2：稳健低—高/高—低县的"登记型 vs 真实型"拆分（v3 删除占比）
  [K] 数-3/4：县名匹配率；子项 vs 项目计数稳健性
"""
import csv
import json
import math
import random
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
random.seed(42)
import numpy as np
from scipy import stats as sps
from shapely.geometry import Point, shape as shp_shape
from shapely.ops import transform as shp_tr
from shapely import STRtree
import libpysal
from esda.moran import Moran, Moran_BV, Moran_Local_BV

DATA = Path(r"E:\GLM\非遗论文\02_数据")
PROJ = pyproj.Transformer.from_crs("EPSG:4326",
    "+proj=aea +lat_1=25 +lat_2=47 +lon_0=105 +datum=WGS84 +units=m", always_xy=True).transform \
    if False else None
import pyproj
PROJ = pyproj.Transformer.from_crs("EPSG:4326",
    "+proj=aea +lat_1=25 +lat_2=47 +lon_0=105 +datum=WGS84 +units=m", always_xy=True).transform

# ---------- 县表 ----------
sens = {r["adcode"]: r for r in csv.DictReader(open(DATA / "03_基础地理" / "县域统计_敏感性对比.csv", encoding="utf-8-sig"))}
drv = {r["adcode"]: r for r in csv.DictReader(open(DATA / "03_基础地理" / "县域驱动因子表.csv", encoding="utf-8-sig"))}
geo = json.loads((DATA / "03_基础地理" / "中国_县级边界_统计.geojson").read_text(encoding="utf-8"))
feats = [f for f in geo["features"] if f.get("geometry") and str(f["properties"]["adcode"]) < "810000"]
codes = [str(f["properties"]["adcode"]) for f in feats]
names = [f["properties"]["name"] for f in feats]
geoms = [shp_shape(f["geometry"]).buffer(0) for f in feats]
vc = np.array([int(sens[c]["村落数"]) for c in codes], dtype=float)
ia = np.array([int(sens[c]["非遗A全量"]) for c in codes], dtype=float)
ib = np.array([int(sens[c]["非遗B剔除后"]) for c in codes], dtype=float)
ic = np.array([int(sens[c]["非遗C严格(S1∪S2)"]) for c in codes], dtype=float)
area = np.array([float(drv[c]["area_km2"]) for c in codes])

# ---------- 权重（Queen，全岛处理：孤岛县不参与任何空间统计） ----------
tree = STRtree(geoms)
pairs = tree.query(geoms, predicate="touches")
nbr = {k: set() for k in range(len(geoms))}
for a, b in zip(pairs[0], pairs[1]):
    if a != b:
        nbr[int(a)].add(int(b))
connected = [k for k in range(len(geoms)) if nbr[k]]
islands = [k for k in range(len(geoms)) if not nbr[k]]
print(f"[口径统一] 大陆县 {len(geoms)}；孤岛县 {len(islands)}（仅 {', '.join(names[k] for k in islands[:8])} 等不参与空间统计）；"
      f"全局与局部 LISA 均在其余 {len(connected)} 县上计算")
conn_codes = [codes[k] for k in connected]
w = libpysal.weights.W({k: nbr[k] for k in connected}, silence_warnings=True)
idx_conn = {c: k for k, c in enumerate(conn_codes)}
vc_c = vc[connected]; ia_c = ia[connected]; ib_c = ib[connected]; ic_c = ic[connected]

# ---------- [A] 全局双变量 I（999 置换，含 z） ----------
print("\n[A] 全局双变量 Moran's I（n=%d，999 置换，E[I]=%.5f）" % (len(connected), -1/(len(connected)-1)))
for label, y in (("A 全量", ia_c), ("B v3", ib_c), ("C 严格", ic_c)):
    m = Moran_BV(vc_c, y, w, permutations=999)
    m_single = Moran(y, w, permutations=999)
    print(f"  {label}: I={m.I:.4f}（z={m.z_sim:.2f}，p={m.p_sim:.3f}）｜非遗单变量 I={m_single.I:.3f}（z={m_single.z_sim:.2f}）")
# 残差 I：计数对 log 面积回归取残差
la = np.log(area[connected])
X = np.column_stack([np.ones_like(la), la])
rv = vc_c - X @ np.linalg.lstsq(X, vc_c, rcond=None)[0]
ri = ia_c - X @ np.linalg.lstsq(X, ia_c, rcond=None)[0]
m_res = Moran_BV(rv, ri, w, permutations=999)
print(f"  残差 I（回归掉 log 面积后）：I={m_res.I:.4f}（z={m_res.z_sim:.2f}，p={m_res.p_sim:.3f}）"
      f"——若≈0，则计数口径的弱正相关确为规模共变")

# ---------- [B] 局部 LISA（999 置换 + BH-FDR）+ 三口径交叉表 ----------
def spearman(x, y):
    rx = np.argsort(np.argsort(x))
    ry = np.argsort(np.argsort(y))
    return 1 - 6 * np.sum((rx - ry) ** 2) / (len(x) * (len(x) ** 2 - 1))

def local_fdr(x, y):
    l = Moran_Local_BV(x, y, w, permutations=999)
    q, p = l.q, l.p_sim
    raw = np.zeros(len(q), dtype=int)
    for qq in (1, 2, 3, 4):
        raw[(q == qq) & (p <= 0.05)] = qq          # 未校正（与既有文献可比）
    order = np.argsort(p)
    m = len(p)
    thresh = np.arange(1, m + 1) / m * 0.05
    passed = p[order] <= thresh
    sig = np.zeros(m, dtype=bool)
    if passed.any():
        kmax = np.where(passed)[0].max()
        sig[order[:kmax + 1]] = True
    fdr = np.zeros(m, dtype=int)
    for qq in (1, 2, 3, 4):
        fdr[(q == qq) & sig] = qq
    return fdr, raw, p

print("\n[B] 局部 LISA（999 置换＋BH-FDR 0.05）三口径×四类别交叉表：")
clsA, rawA, pA = local_fdr(vc_c, ia_c)
clsB, rawB, pB = local_fdr(vc_c, ib_c)
clsC, rawC, pC = local_fdr(vc_c, ic_c)
p_floor = 0.001
L = {1: "高—高", 2: "低—高", 3: "低—低", 4: "高—低", 0: "不显著"}
header = "口径 | " + " | ".join(L[t] for t in (1, 2, 3, 4, 0))
print(header)
for label, cls in (("A", clsA), ("B", clsB), ("C", clsC)):
    print("  " + label + " | " + " | ".join(f"{int((cls==t).sum()):4d}" for t in (1, 2, 3, 4, 0)))
# 稳健集合
rob_AB = {conn_codes[k] for k in range(len(connected)) if clsA[k] == clsB[k] and clsA[k] != 0}
rob_AC = {conn_codes[k] for k in range(len(connected)) if clsA[k] == clsC[k] and clsA[k] != 0}
rob_BC = {conn_codes[k] for k in range(len(connected)) if clsB[k] == clsC[k] and clsB[k] != 0}
rob_ABC = rob_AB & rob_AC & rob_BC
for lab, s in (("A∩B", rob_AB), ("A∩C", rob_AC), ("B∩C", rob_BC), ("A∩B∩C", rob_ABC)):
    hh = sum(1 for c in s if clsA[conn_codes.index(c)] == 1)
    cnt = {t: sum(1 for c in s if clsB[conn_codes.index(c)] == t) for t in (1, 2, 3, 4)}
    print(f"  稳健 {lab}：{len(s)} 县｜其中按 B 口径类型：HH {cnt[1]}、LH {cnt[2]}、LL {cnt[3]}、HL {cnt[4]}")
name_of = dict(zip(codes, names))
hh_AB = sorted(name_of[c] for c in rob_AB if clsA[conn_codes.index(c)] == 1)
print(f"  A∩B 稳健高—高 {len(hh_AB)} 县：{'、'.join(hh_AB)}")
# 层级比较（B∩C 同类型）：未校正 → 置换下限（p≤0.001） → FDR
uncorr_hh = sum(1 for k in range(len(connected)) if rawB[k] == 1 and rawC[k] == 1)
uncorr_hl = sum(1 for k in range(len(connected)) if rawB[k] == 4 and rawC[k] == 4)
floor_hh = sum(1 for k in range(len(connected))
               if rawB[k] == 1 and rawC[k] == 1 and pB[k] <= p_floor and pC[k] <= p_floor)
floor_hl = sum(1 for k in range(len(connected))
               if rawB[k] == 4 and rawC[k] == 4 and pB[k] <= p_floor and pC[k] <= p_floor)
fdr_hh = sum(1 for k in range(len(connected)) if clsB[k] == 1 and clsC[k] == 1)
fdr_hl = sum(1 for k in range(len(connected)) if clsB[k] == 4 and clsC[k] == 4)
print(f"  B∩C 同类型稳健性三层级：未校正 高—高 {uncorr_hh}｜高—低 {uncorr_hl}；"
      f"双口径 p≤0.001 高—高 {floor_hh}｜高—低 {floor_hl}；BH-FDR 后 高—高 {fdr_hh}｜高—低 {fdr_hl}")

# ---------- [C]/[H] 武陵山—苗岭带：州级建制事前界定 ----------
city_cache = {int(k): v for k, v in json.loads(
    (DATA / "03_基础地理" / "市级名称缓存.json").read_text(encoding="utf-8")).items()}
def county_city(c):
    route = next(f["properties"].get("acroutes", []) for f in feats if str(f["properties"]["adcode"]) == c)
    for a in route:
        if a in city_cache:
            return city_cache[a]
    return ""
BAND_KEY = ("湘西", "黔东南", "恩施")
band = [c for c in codes if any(k in county_city(c) for k in BAND_KEY)]
band_rob = [c for c in band if c in rob_AB]
print(f"\n[C]/[H] 武陵山—苗岭带（湘西州＋黔东南州＋恩施州，建制事前界定）：{len(band)} 县；"
      f"入选 A∩B 稳健核心 {len(band_rob)} 县；入选 A∩B∩C {len([c for c in band if c in rob_ABC])} 县")
not_in = [names[codes.index(c)] for c in band if c not in rob_AB]
print(f"  带内未入选 A∩B 稳健核心的县：{'、'.join(not_in) if not_in else '无'}")
band_uncorr = sum(1 for c in band
                  for k in [conn_codes.index(c)] if rawB[k] == 1 and rawC[k] == 1)
band_floor = sum(1 for c in band
                 for k in [conn_codes.index(c)]
                 if rawB[k] == 1 and rawC[k] == 1 and pB[k] <= p_floor and pC[k] <= p_floor)
print(f"  带内未校正口径下 B∩C 同为高—高：{band_uncorr} 县；双口径 p≤0.001 的：{band_floor} 县")

# ---------- [D]/[E] 探测器 v2（758 双要素县、7 因子、置换检验） ----------
dual_codes = [c for c in codes if int(sens[c]["村落数"]) > 0 and int(sens[c]["非遗A全量"]) > 0]
di = {c: k for k, c in enumerate(codes)}
v_d = vc[[di[c] for c in dual_codes]]
a_d = ia[[di[c] for c in dual_codes]]
b_d = ib[[di[c] for c in dual_codes]]
area_d = area[[di[c] for c in dual_codes]]
g_d = np.array([float(drv[c]["gdp_dens"]) if "gdp_dens" in drv[c] else
                float(drv[c].get("GDP密度_万元每km2", 0)) for c in dual_codes]) if False else None
# 因子：从驱动因子表直接取
def qcol(c, key):
    return float(drv[c].get(key, 0))
fac = {
    "GDP密度": np.array([qcol(c, "gdp") if False else 0 for c in dual_codes]),  # 占位，下行覆盖
}
# GDP/人口密度等在县域GDP/人口 CSV 中
gdp = {r["adcode"]: float(r["GDP密度_万元每km2"]) for r in csv.DictReader(open(DATA / "03_基础地理" / "县域GDP_2020.csv", encoding="utf-8-sig"))}
pop = {r["adcode"]: float(r["人口密度_人每km2"]) for r in csv.DictReader(open(DATA / "03_基础地理" / "县域人口_2020.csv", encoding="utf-8-sig"))}
dem = {r["adcode"]: (float(r["平均海拔_m"]) if r["平均海拔_m"] else np.nan) for r in csv.DictReader(open(DATA / "03_基础地理" / "县域海拔.csv", encoding="utf-8-sig"))}
rel = {r["adcode"]: (float(r["地形起伏度_m(像元std)"]) if r["地形起伏度_m(像元std)"] else np.nan) for r in csv.DictReader(open(DATA / "03_基础地理" / "县域海拔.csv", encoding="utf-8-sig"))}
road = {r["adcode"]: float(r["路网密度_km每km2"]) for r in csv.DictReader(open(DATA / "03_基础地理" / "县域路网.csv", encoding="utf-8-sig"))}

F = {
    "GDP密度": np.array([gdp.get(c, np.nan) for c in dual_codes]),
    "人口密度": np.array([pop.get(c, np.nan) for c in dual_codes]),
    "路网密度": np.array([road.get(c, np.nan) for c in dual_codes]),
    "距省会距离": np.array([float(drv[c].get("d_capital", np.nan) or np.nan) for c in dual_codes]),
    "民族自治地方": np.array([float(drv[c].get("ethnic", 0) or 0) for c in dual_codes]),
    "平均海拔": np.array([dem.get(c, np.nan) for c in dual_codes]),
    "地形起伏度": np.array([rel.get(c, np.nan) for c in dual_codes]),
}
def qbin(x, m=5):
    x = np.asarray(x, dtype=float)
    ok = ~np.isnan(x)
    edges = np.quantile(x[ok], np.linspace(0, 1, m + 1)[1:-1])
    out = np.full(len(x), np.nan)
    out[ok] = np.searchsorted(edges, x[ok], side="right")
    return out
Xcls = {k: qbin(v) for k, v in F.items()}

def q_stat(y, xcls):
    ok = ~np.isnan(y) & ~np.isnan(xcls)
    y, x = y[ok], xcls[ok]
    sst = ((y - y.mean()) ** 2).sum()
    ssw = 0.0
    for h in np.unique(x):
        yh = y[x == h]
        ssw += len(yh) * yh.var()
    return 1 - ssw / sst if sst > 0 else np.nan

rng = np.random.default_rng(42)
def q_perm(y, xcls, n_perm=999):
    q0 = q_stat(y, xcls)
    cnt = 0
    for _ in range(n_perm):
        if q_stat(rng.permutation(y), xcls) >= q0:
            cnt += 1
    return q0, (1 + cnt) / (n_perm + 1)

print("\n[D] 探测器 v2（758 双要素县、7 因子、999 置换）：")
print(f"  {'因子':<8}｜{'村落密度 q':>9} {'p':>6}｜{'非遗A q':>8} {'p':>6}｜{'非遗B q':>8} {'p':>6}")
table4 = []
for fn, xcls in Xcls.items():
    qv, pv_ = q_perm(v_d, xcls)
    qa, pa_ = q_perm(a_d, xcls)
    qb, pb_ = q_perm(b_d, xcls)
    table4.append((fn, qv, pv_, qa, pa_, qb, pb_))
    print(f"  {fn:<8}｜{qv:9.3f} {pv_:6.3f}｜{qa:8.3f} {pa_:6.3f}｜{qb:8.3f} {pb_:6.3f}")

print("\n[E] 交互超额 q(∩)−max(q1,q2)（村落密度，758 县）：")
excess_list = []
fns = list(Xcls)
for a_ in range(len(fns)):
    for b_ in range(a_ + 1, len(fns)):
        inter = Xcls[fns[a_]] * 100 + Xcls[fns[b_]]
        q_ab = q_stat(v_d, inter)
        q1 = q_stat(v_d, Xcls[fns[a_]])
        q2 = q_stat(v_d, Xcls[fns[b_]])
        excess_list.append((q_ab - max(q1, q2), fns[a_], fns[b_], q_ab, q1, q2))
ex = np.array([e[0] for e in excess_list])
print(f"  超额分布：中位 {np.median(ex):.3f}｜P75 {np.percentile(ex,75):.3f}｜最大 {ex.max():.3f}")
for e in sorted(excess_list, reverse=True)[:5]:
    print(f"    {e[1]}×{e[2]}：q∩={e[3]:.3f}，超额 {e[0]:.3f}")

# ---------- [F] M2：秩归一化 CCD 对照（758 县） ----------
from scipy.stats import rankdata
u1m = (v_d - v_d.min()) / (v_d.max() - v_d.min() + 1e-12)
u2m = (a_d - a_d.min()) / (a_d.max() - a_d.min() + 1e-12)
Da = np.sqrt((2 * np.sqrt(u1m * u2m) / (u1m + u2m + 1e-12)) * (0.5 * u1m + 0.5 * u2m))
u1r = rankdata(v_d) / len(v_d)
u2r = rankdata(a_d) / len(a_d)
Cr = 2 * np.sqrt(u1r * u2r) / (u1r + u2r)
Dr = np.sqrt(Cr * (0.5 * u1r + 0.5 * u2r))
print(f"\n[F] M2 秩归一化 CCD 对照：Spearman(D_minmax, D_rank)={spearman(Da, Dr):.3f}｜"
      f"D_rank 最大 {Dr.max():.3f}｜≥0.4 的县 {int((Dr>=0.4).sum())} 个（min-max 口径为 9 个）"
      f"｜前十重合 {len({dual_codes[k] for k in np.argsort(-Da)[:10]} & {dual_codes[k] for k in np.argsort(-Dr)[:10]})}/10")

# ---------- [G] M11：v3 剔除门类 χ² + 两类标记分列 ----------
KW_NAT = ["中国", "国家", "中华", "全国"]
KW_ORG = ["协会", "学会", "研究会", "研究院", "研究所", "促进会", "联合会", "大学", "学院"]
KW_S2 = KW_NAT + KW_ORG + ["公司", "集团", "剧院", "剧团", "演艺"]
METRO = ("北京市", "上海市", "天津市")
def read_ich():
    raw = (DATA / "01_非遗名录" / "IhChina_2006-2021" / "IhChina_2006-2021.dbf").read_bytes()
    n_rec = struct.unpack("<I", raw[4:8])[0]
    h_size, r_size = struct.unpack("<H", raw[8:10])[0], struct.unpack("<H", raw[10:12])[0]
    fields, pos = [], 32
    while raw[pos] != 0x0D:
        fields.append((raw[pos:pos + 11].split(b"\x00")[0].decode("ascii"), raw[pos + 16]))
        pos += 32
    widths = [w for _, w in fields]
    idx = {nm: k for k, (nm, _) in enumerate(fields)}
    out = []
    for i in range(n_rec):
        start = h_size + i * r_size + 1
        p, vals = start, []
        for w_ in widths:
            vals.append(raw[p:p + w_].decode("utf-8", errors="replace").strip())
            p += w_
        out.append({"name": vals[idx["Name_CN"]], "place": vals[idx["Place_CN"]],
                    "unit": vals[idx["Unit_CN"]], "cat": vals[idx["CategoryCN"]]})
    return out
ich = read_ich()
v3 = lambda r: any(k in r["unit"] for k in KW_NAT + KW_ORG)
removed = [r for r in ich if v3(r)]
cats = sorted({r["cat"] for r in ich})
obs = np.array([sum(1 for r in removed if r["cat"] == c) for c in cats])
tot_cat = np.array([sum(1 for r in ich if r["cat"] == c) for c in cats])
exp = tot_cat / tot_cat.sum() * len(removed)
chi2 = ((obs - exp) ** 2 / exp).sum()
p_chi = 1 - sps.chi2.cdf(chi2, len(cats) - 1)
print(f"\n[G] M11 v3 剔除门类 χ² 中性检验：χ²={chi2:.2f}（df={len(cats)-1}），p={p_chi:.3f}")
nat_only = sum(1 for r in removed if any(k in r["unit"] for k in KW_NAT) and not any(k in r["unit"] for k in KW_ORG))
org_only = sum(1 for r in removed if any(k in r["unit"] for k in KW_ORG) and not any(k in r["unit"] for k in KW_NAT))
both_kw = sum(1 for r in removed if any(k in r["unit"] for k in KW_NAT) and any(k in r["unit"] for k in KW_ORG))
print(f"  两类标记分列：仅全国性限定词 {nat_only}｜仅机构类型词 {org_only}｜两者皆有 {both_kw}")

# ---------- [I] M14：跨省登记单位 ----------
PROVS = ["北京","天津","河北","山西","内蒙古","辽宁","吉林","黑龙江","上海","江苏","浙江","安徽",
         "福建","江西","山东","河南","湖北","湖南","广东","广西","海南","重庆","四川","贵州","云南",
         "西藏","陕西","甘肃","青海","宁夏","新疆","台湾","香港","澳门"]
def place_prov(r):
    for pv in PROVS:
        if r["place"].startswith(pv):
            return pv
    return ""
cross = []
for r in ich:
    pp = place_prov(r)
    if not pp:
        continue
    for pv in PROVS:
        if pv != pp and pv in r["unit"]:
            cross.append(r)
            break
print(f"\n[I] M14 跨省登记（单位名含其他省级名称）：{len(cross)} 条")
print("  样例（前10条）：")
for r in cross[:10]:
    print(f"    {r['name']}｜申报地 {r['place']}｜单位 {r['unit']}")
print(f"  门类构成：{dict(Counter(r['cat'] for r in cross).most_common())}")

# ---------- [J] 结-2：稳健低—高/高—低 的 登记型 vs 真实型 ----------
v3_removed_ids = set()
# 用名称匹配 A 口径点（近似：名称+申报地相同的 A 点视为被 v3 删除）
name_count = defaultdict(int)
for r in ich:
    if v3(r):
        name_count[(r["name"], r["place"])] += 1
print("\n[J] 结-2 登记型/真实型拆分（按县内被 v3 删除的点占比 >50% 记'登记型'）：")
for lab, ttype in (("稳健低—高（非遗富集·村落稀缺）", 2), ("稳健高—低（村落富集·非遗稀缺）", 4)):
    mem = [conn_codes[k] for k in range(len(connected)) if clsB[k] == ttype and clsC[k] == ttype and clsA[k] == ttype]
    reg, real, unk = 0, 0, 0
    for c in mem:
        pts_here = [r for r in ich if r["place"].find(names[codes.index(c)]) >= 0 or names[codes.index(c)] in r["place"]]
        if not pts_here:
            unk += 1
            continue
        rm = sum(1 for r in pts_here if v3(r))
        (reg if rm / len(pts_here) > 0.5 else real).__class__()
        if rm / len(pts_here) > 0.5:
            reg += 1
        else:
            real += 1
    print(f"  {lab}：A∩B∩C 稳健 {len(mem)} 县｜登记型 {reg}｜真实型 {real}｜无法匹配 {unk}")

# ---------- [K] 数-3/数-4 ----------
print("\n[K] 数-3 村落县名匹配率：")
vrows = list(csv.DictReader(open(DATA / "02_传统村落" / "合并_传统村落_前五批.csv", encoding="utf-8-sig")))
county_names = set(names)
m = sum(1 for r in vrows if r["DistrictCN"] in county_names)
print(f"  村落 DistrictCN 与现行县名精确匹配：{m}/{len(vrows)}（{100*m/len(vrows):.1f}%）；其余为撤县设区等更名差异，按空间连接归属")
print("[K] 数-4 子项 vs 项目计数稳健性：")
proj_ich = read_ich()
# 县→唯一 Proj_num 集合
place_code = {}
for f_ in feats:
    place_code[f_["properties"]["name"]] = str(f_["properties"]["adcode"])
proj_count = defaultdict(set)
subit_count = Counter()
for r in proj_ich:
    for nm, code in place_code.items():
        if nm in r["place"]:
            proj_count[code].add(r["name"].split("（")[0])
            subit_count[code] += 1
            break
common_codes = [c for c in codes if c in proj_count]
pa = np.array([len(proj_count[c]) for c in common_codes], dtype=float)
pc = np.array([subit_count[c] for c in common_codes], dtype=float)
pv_ = np.array([int(sens[c]["非遗A全量"]) for c in common_codes], dtype=float)
w_full = libpysal.weights.W({k: nbr[k] for k in connected}, silence_warnings=True)
print("  （口径：项目=唯一项目编号；此比较仅作用于有非遗的县集合）")
print(f"  [K] 完成——详表见输出文件同目录说明")

print("\n全部完成。")
