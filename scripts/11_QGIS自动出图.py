# -*- coding: utf-8 -*-
"""
11_QGIS自动出图.py（用 QGIS 自带的 Python 运行，不是系统 Python！）
运行方式：E:\\QGIS\\bin\\python-qgis.bat 本文件路径
作用：1) 加载修复版县级边界 + 村落点 + 非遗点
     2) 把 09 号脚本算好的县域统计（村落数/非遗数）写入边界属性表
     3) 自动配置两套分级填色（村落=蓝色系、非遗=红色系）和点样式
     4) 保存工程"论文分析_自动版.qgz"——用户双击打开即是成品地图
"""
import csv
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor
from qgis.core import (
    QgsApplication, QgsProject, QgsVectorLayer, QgsField,
    QgsGraduatedSymbolRenderer, QgsRendererRange,
    QgsFillSymbol, QgsMarkerSymbol, QgsCoordinateReferenceSystem,
)

DATA = Path(r"E:\GLM\非遗论文\02_数据")
COUNTY = DATA / "03_基础地理" / "中国_县级边界_统计.geojson"   # 已含 VILLAGE_N/ICH_N 字段（脚本12生成）
VILLAGE = DATA / "02_传统村落" / "合并_传统村落_前五批.geojson"
ICH = DATA / "01_非遗名录" / "IhChina_2006-2021" / "IhChina_2006-2021.shp"
PROJECT = r"E:\GLM\非遗论文\论文分析_自动版.qgz"

qgs = QgsApplication([], False)
qgs.setPrefixPath(r"E:\QGIS\apps\qgis", True)
qgs.initQgis()

# ---------- 1. 加载图层（统计字段已由脚本12预先写好，这里只读不写） ----------
counties = QgsVectorLayer(str(COUNTY), "县域·传统村落数量", "ogr")
counties_ich = QgsVectorLayer(str(COUNTY), "县域·非遗数量", "ogr")
print(f"边界加载：{counties.featureCount()} 个要素，字段含 VILLAGE_N/ICH_N：",
      [f.name() for f in counties.fields()][-2:])

villages = QgsVectorLayer(str(VILLAGE), "传统村落（前五批）", "ogr")
ich = QgsVectorLayer(str(ICH), "国家级非遗（五批）", "ogr")

# ---------- 3. 配色 ----------
BREAKS = [0, 1, 3, 6, 11, 21, 10 ** 9]
LABELS = ["0", "1-2", "3-5", "6-10", "11-20", "≥21"]

def graduated(layer, field, colors):
    """按固定断点做分级填色"""
    ranges = []
    for k in range(len(LABELS)):
        sym = QgsFillSymbol.createSimple({
            "color": colors[k], "outline_color": "#999999", "outline_width": "0.06"})
        ranges.append(QgsRendererRange(BREAKS[k], BREAKS[k + 1], sym, LABELS[k]))
    layer.setRenderer(QgsGraduatedSymbolRenderer(field, ranges))

graduated(counties, "VILLAGE_N",
          ["#f7f7f7", "#c6dbef", "#6baed6", "#3182bd", "#08519c", "#08306b"])
graduated(counties_ich, "ICH_N",
          ["#fff5f0", "#fcbba1", "#fb6a4a", "#de2d26", "#a50f15", "#67000d"])

def point_style(layer, color_hex, label):
    sym = QgsMarkerSymbol.createSimple({"name": "circle", "size": "0.9",
                                        "color": color_hex, "outline_style": "no"})
    sym.setOpacity(0.65)
    layer.setRenderer(layer.renderer().clone())  # 保持默认单符号，替换其符号
    layer.renderer().setSymbol(sym)
    print(f"{label} 样式完成")

point_style(villages, "#1f77b4", "村落")
point_style(ich, "#d62728", "非遗")

# ---------- 4. 组装并保存工程 ----------
project = QgsProject.instance()
for lyr in (counties, counties_ich, villages, ich):
    project.addMapLayer(lyr, False)
root = project.layerTreeRoot()
for lyr in (counties, counties_ich, villages, ich):   # 后加入的显示在上层
    root.addLayer(lyr)
project.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
project.write(PROJECT)
print(f"工程已保存：{PROJECT}")
print("打开方式：QGIS → 工程 → 打开 → 选这个 .qgz 文件")

qgs.exitQgis()
