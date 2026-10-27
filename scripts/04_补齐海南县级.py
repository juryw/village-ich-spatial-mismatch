# -*- coding: utf-8 -*-
"""
04_补齐海南县级.py
作用：DataV 的省级响应不含"海南省直辖县级市"（469001~469030），
     但单单元端点 bound/{code}.json 可以逐个取到。逐个尝试，存在的并入。
     同时补新疆兵团第 10 市（659010 胡杨河）。
"""
import json
import time
import urllib.request
from pathlib import Path

GEO_DIR = Path(r"E:\GLM\非遗论文\02_数据\03_基础地理")
MERGED = GEO_DIR / "中国_县级边界.geojson"
HEADERS = {"User-Agent": "Mozilla/5.0 (research use)"}

merged = json.loads(MERGED.read_text(encoding="utf-8"))
have = {str(f["properties"].get("adcode")) for f in merged["features"]}
print(f"现有县级要素：{len(merged['features'])} 个")

candidates = [f"4690{i:02d}" for i in range(1, 31)] + ["659010"]  # 海南省直辖县市 + 胡杨河市
added = []
for code in candidates:
    url = f"https://geo.datav.aliyun.com/areas_v3/bound/{code}.json"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        continue                      # 不存在的代码直接跳过（404）
    time.sleep(0.2)
    # 该端点可能返回单个 Feature，也可能返回 FeatureCollection，做兼容处理
    feats = data["features"] if data.get("type") == "FeatureCollection" else [data]
    for feat in feats:
        ac = str(feat["properties"].get("adcode"))
        if ac not in have and feat.get("geometry"):
            merged["features"].append(feat)
            have.add(ac)
            added.append(f"{ac} {feat['properties'].get('name', '')}")

MERGED.write_text(json.dumps(merged, ensure_ascii=False), encoding="utf-8")
print(f"本次补入 {len(added)} 个：")
for line in added:
    print(f"  {line}")
print(f"\n最终县级要素总数：{len(merged['features'])} 个")
