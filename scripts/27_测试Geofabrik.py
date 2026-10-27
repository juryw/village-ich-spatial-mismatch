# -*- coding: utf-8 -*-
"""27_测试Geofabrik.py：诊断路网源连通性（系统代理 / 直连 / 常见本地端口）"""
import urllib.request

URL = "https://download.geofabrik.de/asia/china-latest.osm.pbf"

print("Windows 系统代理设置:", urllib.request.getproxies())

for label, opener in (
    ("系统默认（含TUN/全局）", urllib.request.build_opener()),
    ("显式 127.0.0.1:7890", urllib.request.build_opener(urllib.request.ProxyHandler({"https": "http://127.0.0.1:7890", "http": "http://127.0.0.1:7890"}))),
    ("显式 127.0.0.1:10809", urllib.request.build_opener(urllib.request.ProxyHandler({"https": "http://127.0.0.1:10809", "http": "http://127.0.0.1:10809"}))),
    ("显式 127.0.0.1:1080", urllib.request.build_opener(urllib.request.ProxyHandler({"https": "http://127.0.0.1:1080", "http": "http://127.0.0.1:1080"}))),
):
    try:
        req = urllib.request.Request(URL, method="HEAD")
        with opener.open(req, timeout=20) as r:
            print(f"[{label}] ✓ 状态 {r.status}，大小 {int(r.headers.get('Content-Length', 0)) / 1e9:.2f} GB")
            break
    except Exception as e:
        print(f"[{label}] ✗ {type(e).__name__}: {e}")
