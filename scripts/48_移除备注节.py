# -*- coding: utf-8 -*-
"""48_移除备注节.py：从正稿 md 中删除"写作状态备注"节（内容已迁移至投稿前检查清单.md）"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = Path(r"E:\GLM\非遗论文\05_稿件\论文初稿_v1.md")
t = p.read_text(encoding="utf-8")
start = t.find("## 写作状态备注")
assert start > 0, "未找到备注节"
t = t[:start].rstrip() + "\n"
p.write_text(t, encoding="utf-8")
print("备注节已移除；正稿现以参考文献表结尾")
print("末尾 80 字符预览：", t[-80:])
