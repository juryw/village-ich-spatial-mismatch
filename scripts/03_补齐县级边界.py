# -*- coding: utf-8 -*-
"""
03_补齐县级边界.py
作用：补齐 02_下载县级行政边界.py 漏掉的县级单元：
     - 省直辖县级市（济源、仙桃、潜江、天门、神农架、海南各省辖县市、新疆兵团市）
     - 不设区的地级市（东莞、中山、嘉峪关）——直接用市域范围作为一个统计单元
原理：这些单元在"省级_full"响应里本来就带有边界（作为省的直下级要素），
     只是它们的"_full"（取下一级）不存在，所以之前 404。从省级响应里捞即可。
"""
import json
import time
import urllib.request
from pathlib import Path

BASE = "https://geo.datav.aliyun.com/areas_v3/bound/{}_full.json"
GEO_DIR = Path(r"E:\GLM\非遗论文\02_数据\03_基础地理")
MERGED = GEO_DIR / "中国_县级边界.geojson"
HEADERS = {"User-Agent": "Mozilla/5.0 (research use)"}

# 需要补的省份（省级 adcode）
PARENTS = ["410000", "420000", "440000", "460000", "620000", "650000"]
# 省直辖县级单元：直接取其自身要素（含边界）
PROV_DIRECT = (
    {f"41900{i}" for i in (1,)}            # 河南济源
    | {"429004", "429005", "429006", "429021"}   # 湖北仙桃/潜江/天门/神农架
    | {f"46900{i:02d}" for i in range(1, 31)}    # 海南省直辖县市
    | {f"65900{i}" for i in range(1, 11)}        # 新疆兵团市
    | {"460400"}                                 # 海南儋州
)
# 不设区地级市：取市本身范围作为一个县级单元
NO_DISTRICT_CITIES = {"441900", "442000", "620200"}  # 东莞/中山/嘉峪关


def fetch(code):
    try:
        req = urllib.request.Request(BASE.format(code), headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"  ! 请求失败 {code}: {e}")
        return None


# 读入已合并的县级边界，建立 adcode 索引防止重复
merged = json.loads(MERGED.read_text(encoding="utf-8"))
have = {str(f["properties"].get("adcode")) for f in merged["features"]}  # adcode 是整数，统一转成字符串再比较
print(f"现有县级要素：{len(merged['features'])} 个")

added = []
for prov_code in PARENTS:
    data = fetch(prov_code)
    time.sleep(0.3)
    if not data:
        continue
    for feat in data.get("features", []):
        code = str(feat["properties"].get("adcode"))
        name = feat["properties"].get("name", "")
        if code in have:
            continue
        if code in PROV_DIRECT:
            added.append((code, name, "省直辖县级"))
            merged["features"].append(feat)
        elif code in NO_DISTRICT_CITIES:
            added.append((code, name, "不设区市（整市作为一个单元）"))
            merged["features"].append(feat)

MERGED.write_text(json.dumps(merged, ensure_ascii=False), encoding="utf-8")
print(f"\n本次补入 {len(added)} 个单元：")
for code, name, kind in added:
    print(f"  {code} {name}（{kind}）")
print(f"\n最终县级要素总数：{len(merged['features'])} 个，已覆盖写回 {MERGED}")

# 简单质检：确认关键县区在列
codes = {str(f["properties"].get("adcode")) for f in merged["features"]}
for must in ("419001", "441900", "469001", "429004", "620200"):
    print(f"  校验 {must}：{'✓' if must in codes else '✗ 仍缺失'}")
