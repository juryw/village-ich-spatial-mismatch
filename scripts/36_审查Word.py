# -*- coding: utf-8 -*-
"""
36_审查Word.py：全面检查导出的 docx——乱码字符、残留Markdown符号、空段、字体一致性
"""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from docx import Document

d = Document(r"E:\GLM\非遗论文\05_稿件\论文初稿_v1.docx")

issues = []
md_residue = []      # 残留 ** 或 # 等符号
garbled = []         # 乱码/替换字符
sup_issues = []      # 上标引文问题（[数字] 应为上标，现在是正文文本）

for i, p in enumerate(d.paragraphs):
    t = p.text
    if not t.strip():
        continue
    if "**" in t or t.strip().startswith("#"):
        md_residue.append((i, t[:50]))
    if "\ufffd" in t or "□" in t:
        garbled.append((i, t[:50]))
    # Markdown 上标 <sup>[数字]</sup> 转换残留
    if "<sup>" in t or "</sup>" in t:
        sup_issues.append((i, t[:60]))

print("== 残留Markdown符号:", len(md_residue))
for i, t in md_residue[:8]:
    print(f"  段{i}: {t}")
print("== 乱码字符:", len(garbled))
for i, t in garbled[:8]:
    print(f"  段{i}: {t}")
print("== <sup>残留:", len(sup_issues))
for i, t in sup_issues[:10]:
    print(f"  段{i}: {t}")

# 检查上标数字的现状：正文引用 [9] 等是否作为普通文本
plain_cites = [p.text[:50] for p in d.paragraphs if re.search(r"\[\d+\]", p.text) and not p.text.strip().startswith("[")]
print("== 含行内引文编号的段落数:", len(plain_cites))
for t in plain_cites[:5]:
    print("  ", t)

# 空表格单元格 + 表格内残留标记
for ti, t in enumerate(d.tables):
    for ri, row in enumerate(t.rows):
        for ci, c in enumerate(row.cells):
            if not c.text.strip():
                issues.append(f"表{ti} 第{ri}行第{ci}列 为空")
            if "<sup>" in c.text or "**" in c.text:
                issues.append(f"表{ti} 第{ri}行第{ci}列 有残留标记: {c.text[:40]}")
print("== 表格问题:", len(issues))
for x in issues[:10]:
    print("  ", x)
