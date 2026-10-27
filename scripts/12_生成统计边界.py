# -*- coding: utf-8 -*-
"""
12_生成统计边界.py（用系统 Python 运行）
背景：PyQGIS 直接编辑 GeoJSON 属性报 Invalid index，改为在 Python 里
     直接生成一份"边界 + 统计字段"的副本，QGIS 只读不写，最稳。
作用：检查修复版边界文件是否完好 → 生成 中国_县级边界_统计.geojson
     （在 properties 里追加 VILLAGE_N 村落数、ICH_N 非遗数）
"""
import csv
import json
from pathlib import Path

DATA = Path(r"E:\GLM\非遗论文\02_数据")
SRC = DATA / "03_基础地理" / "中国_县级边界_修复.geojson"
DST = DATA / "03_基础地理" / "中国_县级边界_统计.geojson"
STATS = DATA / "03_基础地理" / "县域统计_村落非遗.csv"

geo = json.loads(SRC.read_text(encoding="utf-8"))
print(f"修复版边界要素数：{len(geo['features'])}（应为 2874）")
print(f"首要素属性键：{sorted(geo['features'][0]['properties'].keys())}")

counts = {str(r["adcode"]): (int(r["村落数"]), int(r["非遗数"]))
          for r in csv.DictReader(open(STATS, encoding="utf-8-sig"))}

miss = 0
for feat in geo["features"]:
    p = feat["properties"]
    v, i = counts.get(str(p.get("adcode")), (0, 0))
    if str(p.get("adcode")) not in counts:
        miss += 1
    p["VILLAGE_N"] = v
    p["ICH_N"] = i

DST.write_text(json.dumps(geo, ensure_ascii=False), encoding="utf-8")
tv = sum(f["properties"]["VILLAGE_N"] for f in geo["features"])
ti = sum(f["properties"]["ICH_N"] for f in geo["features"])
print(f"未匹配县：{miss} 个；村落合计 {tv}（应 6817），非遗合计 {ti}（应 3610）")
print(f"已保存：{DST}")
