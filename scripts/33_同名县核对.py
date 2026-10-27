# -*- coding: utf-8 -*-
"""33_同名县核对.py：核对城关区/朝阳区等同名县的身份与数量"""
import csv

rows = list(csv.DictReader(open(
    r"E:\GLM\非遗论文\02_数据\03_基础地理\县域统计_敏感性对比.csv", encoding="utf-8-sig")))
targets = ("城关区", "朝阳区", "越城区", "宁江区", "姑苏区")
for r in rows:
    if r["县名"] in targets and (int(r["非遗A全量"]) >= 5 or int(r["非遗B剔除后"]) >= 5):
        print(r["adcode"], r["县名"],
              "村落", r["村落数"], "| A", r["非遗A全量"], "| B", r["非遗B剔除后"])
