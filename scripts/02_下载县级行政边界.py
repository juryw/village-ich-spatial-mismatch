# -*- coding: utf-8 -*-
"""
02_下载县级行政边界.py
作用：从阿里云 DataV GeoAtlas（免登录、免费公开接口）下载全国县级行政区边界，
     合并成一个 GeoJSON 文件，供 QGIS 做县域统计单元使用。
原理：DataV 的 areas_v3 接口按行政层级返回：全国(100000)→省→市→县。
     先取省列表，再逐省取市列表，再逐市取县列表，最后合并保存。
运行：python 02_下载县级行政边界.py（约 3~5 分钟，370 多次小请求）
来源合规：阿里云 DataV 地理选点/边界公开服务，论文注明来源即可。
注意：DataV 边界存在 GCJ-02 偏移（数百米级），县域尺度统计可忽略，
     投稿终版图如需严格 WGS-84 可换用国家基础地理信息中心 1:100 万数据。
"""
import json
import time
import urllib.request
from pathlib import Path

BASE = "https://geo.datav.aliyun.com/areas_v3/bound/{}_full.json"
OUT_DIR = Path(r"E:\GLM\非遗论文\02_数据\03_基础地理")
OUT_DIR.mkdir(parents=True, exist_ok=True)
HEADERS = {"User-Agent": "Mozilla/5.0 (research use)"}
SLEEP = 0.3          # 每次请求间隔，礼貌抓取
failures = []        # 记录失败的请求，最后统一补试


def fetch(code: str):
    """下载某个行政区的下一级边界 GeoJSON，返回解析后的字典；失败返回 None"""
    url = BASE.format(code)
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"  ! 请求失败 {code}: {e}")
        return None


def features_of(geojson):
    return geojson.get("features", []) if geojson else []


# ---------- 第 1 步：全国 → 省级 ----------
print("第 1 步：下载省级行政区列表 ...")
national = fetch("100000")
provinces = features_of(national)
(OUT_DIR / "中国_省级边界.geojson").write_text(
    json.dumps(national, ensure_ascii=False), encoding="utf-8")
print(f"  省级要素 {len(provinces)} 个，已保存 中国_省级边界.geojson")

# ---------- 第 2、3 步：省 → 市 → 县，逐级抓取并收集县级要素 ----------
counties = []
for prov in provinces:
    p_code = prov["properties"].get("adcode")
    p_name = prov["properties"].get("name", "")
    print(f"第 2 步：{p_name}({p_code}) 取市级列表 ...")
    for city in features_of(fetch(p_code)):
        c_props = city["properties"]
        c_code, c_name, c_level = c_props.get("adcode"), c_props.get("name", ""), c_props.get("level")
        if c_level == "district":          # 直辖市下直接就是区县
            counties.append(city)
            print(f"    [县级·直辖] {p_name}-{c_name}")
        else:                              # 普通地级市 → 再取区县
            for dist in features_of(fetch(c_code)):
                d_props = dist["properties"]
                print(f"    [县级] {c_name}-{d_props.get('name', '')}")
                counties.append(dist)
        time.sleep(SLEEP)
    time.sleep(SLEEP)

# ---------- 第 4 步：合并保存 ----------
merged = {"type": "FeatureCollection", "features": counties}
out_path = OUT_DIR / "中国_县级边界.geojson"
out_path.write_text(json.dumps(merged, ensure_ascii=False), encoding="utf-8")
print(f"\n完成：共 {len(counties)} 个县级要素，已保存至 {out_path}")
if failures:
    print(f"失败请求 {len(failures)} 个：{failures}（重跑本脚本可自动补齐）")
