# -*- coding: utf-8 -*-
"""
13_敏感性检验.py
作用：识别并剔除"保护单位注册地型"非遗点，重算县域格局，检验结论是否稳健。
剔除规则（v1，待导师确认）：
  S1 地域标准：申报地属于北京/上海/天津三个直辖市（国家级协会、院团总部聚集地）
  S2 机构标准：保护单位名称含 机构型关键词（协会/学会/研究院/剧院/剧团/公司……）
口径 A = 全量 3610；口径 B = 剔除 S1∪S2。
输出：剔除点位清单 CSV、县域 A/B 对比 CSV、新旧 r 值与前列县对比。
"""
import csv
import json
import math
import struct
from pathlib import Path

DATA = Path(r"E:\GLM\非遗论文\02_数据")
OUT_LIST = DATA / "01_非遗名录" / "敏感性_剔除点位清单.csv"
OUT_CMP = DATA / "03_基础地理" / "县域统计_敏感性对比.csv"

ORG_KEYWORDS = ["协会", "学会", "研究会", "促进会", "联合会", "公司", "集团",
                "剧院", "剧团", "演艺", "大学", "学院", "研究所", "研究院"]
METRO = ("北京市", "上海市", "天津市")

# ---------- 1. 读非遗 DBF（沿用之前的读法） ----------
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
                "unit": vals[idx["Unit_CN"]], "x": float(vals[idx["X"]]), "y": float(vals[idx["Y"]])})

# ---------- 2. 规则打标 ----------
s1 = lambda r: r["place"].startswith(METRO)
s2 = lambda r: any(k in r["unit"] for k in ORG_KEYWORDS)
flagged = [r for r in ich if s1(r) or s2(r)]
only_s1 = sum(1 for r in ich if s1(r) and not s2(r))
only_s2 = sum(1 for r in ich if s2(r) and not s1(r))
both = sum(1 for r in ich if s1(r) and s2(r))
print(f"S1 地域（北上津）：{only_s1 + both} 条；S2 机构关键词：{only_s2 + both} 条；并集剔除：{len(flagged)} 条")
print(f"口径 B = {len(ich) - len(flagged)} 条")

with open(OUT_LIST, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["项目名称", "申报地区", "保护单位", "触发规则"])
    for r in sorted(flagged, key=lambda r: r["place"]):
        rule = ("S1+S2" if s1(r) and s2(r) else "S1" if s1(r) else "S2")
        w.writerow([r["name"], r["place"], r["unit"], rule])

# ---------- 3. 归县（与 09 相同的网格索引 + 射线法，代码自包含） ----------
geo = json.loads((DATA / "03_基础地理" / "中国_县级边界_修复.geojson").read_text(encoding="utf-8"))
counties = []
for f_ in geo["features"]:
    g = f_.get("geometry")
    if not g:
        continue
    parts = [g["coordinates"][0]] if g["type"] == "Polygon" else [p[0] for p in g["coordinates"]]
    xs = [x for part in parts for x, _ in part]
    ys = [y for part in parts for _, y in part]
    counties.append({"adcode": f_["properties"]["adcode"], "name": f_["properties"].get("name", ""),
                     "parts": parts, "bbox": (min(xs), min(ys), max(xs), max(ys)),
                     "cx": (min(xs) + max(xs)) / 2, "cy": (min(ys) + max(ys)) / 2})
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

for c in counties:
    c["A"], c["B"] = 0, 0
vill = json.loads((DATA / "02_传统村落" / "合并_传统村落_前五批.geojson").read_text(encoding="utf-8"))
for f_ in vill["features"]:
    i = assign(*f_["geometry"]["coordinates"])
    if i is not None:
        counties[i]["A"] = counties[i]["A"]  # 占位：村落数从上次的 CSV 读更稳
# 村落数直接沿用 09 的结果
prev = {r["adcode"]: int(r["村落数"]) for r in csv.DictReader(open(
    DATA / "03_基础地理" / "县域统计_村落非遗.csv", encoding="utf-8-sig"))}
for c in counties:
    c["village"] = prev.get(str(c["adcode"]), 0)

for r in ich:
    i = assign(r["x"], r["y"])
    if i is None:
        continue
    counties[i]["A"] += 1
    if not (s1(r) or s2(r)):
        counties[i]["B"] += 1

# ---------- 4. 对比输出 ----------
with open(OUT_CMP, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["adcode", "县名", "村落数", "非遗A全量", "非遗B剔除后"])
    for c in counties:
        w.writerow([c["adcode"], c["name"], c["village"], c["A"], c["B"]])

def pearson(xs, ys):
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return num / den

vs = [c["village"] for c in counties]
print(f"\n村落-非遗 相关：A 口径 r = {pearson(vs, [c['A'] for c in counties]):.3f}"
      f" ｜ B 口径 r = {pearson(vs, [c['B'] for c in counties]):.3f}")
print(f"有非遗的县：A {sum(1 for c in counties if c['A'] > 0)} → B {sum(1 for c in counties if c['B'] > 0)}")
print("非遗前十县（A → B）：")
for ca, cb in zip(sorted(counties, key=lambda c: -c["A"])[:10], sorted(counties, key=lambda c: -c["B"])[:10]):
    print(f"  {ca['name']} {ca['A']:>3}  →  {cb['name']} {cb['B']:>3}")
print(f"\n已保存：{OUT_LIST}\n已保存：{OUT_CMP}")
