#!/usr/bin/env python3
"""批量导入归档文件中列出的缺失 Notion 页面。

从 ARCHIVED_20260508-105811_商业管理_汇总版已拆分.md 中提取的 19 个 relation 链接页面。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# 工作区根目录
ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "Earth_Library" / "scripts" / "notion_atomic_ingest.py"

# 需要导入的页面列表 (标题, page_id, 分类)
PAGES_TO_IMPORT = [
    ("5W2H分析法", "7ae299d05ba8832c8f9f012b22f39ff4", "产品方法论"),
    ("KANO模型", "ac4299d05ba883bbbfad01e6abf592dc", "产品方法论"),
    ("B端产品的演进路线", "088299d05ba8830eb4490160db7c1a35", "B端产品"),
    ("B端整体方案设计", "e04299d05ba88322ac4d011bce774978", "B端产品"),
    ("B端产品市场分析与业务调研", "f8a299d05ba88271a5a1011dd494ab7b", "B端产品"),
    ("好产品的评价标准", "0cd299d05ba8829dbc640157b46bb664", "产品设计"),
    ("从产品到产品矩阵", "c01299d05ba8837b9a2e8177f9da6a9e", "产品战略"),
    ("产品各阶段的关键指标", "25d299d05ba882f2985801c52e218926", "数据指标"),
    ("产品起步的逻辑", "fe4299d05ba883ea98ef01fc68874033", "产品战略"),
    ("产品生命周期", "186299d05ba882adbc3301e767682302", "产品管理"),
    ("产品服务系统", "4fa299d05ba8836285fa81ba5ccb2c0a", "产品设计"),
    ("如何理性评价产品设计的好坏", "3b8299d05ba8830abf138170b1169447", "设计评估"),
    ("用户体验旅程图", "090299d05ba883129bb781276269aa8f", "用户研究"),
    ("同理心地图", "65c299d05ba882f1bcb60129afdb7715", "用户研究"),
    ("5MVVP框架", "efc299d05ba88305846f81d76c2ba3e7", "产品方法论"),
    ("竞品生态", "893299d05ba88296ba0801a930a16727", "竞品分析"),
    ("需求分析的十三要素五步法", "594299d05ba88241a2508187d8884b43", "需求分析"),
    ("B端产品需求管理与迭代", "3f5299d05ba8828381ce810a7cc08af9", "B端产品"),
    ("支付的基础概念与会计基础", "116299d05ba8839f8540012349cfe0b0", "支付金融"),
]


def import_single_page(title: str, page_id: str, category: str, index: int, total: int) -> dict:
    """导入单个页面并返回结果。"""
    print(f"\n[{index}/{total}] 导入: {title}...", file=sys.stderr)
    
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--page-id", page_id,
        "--book-title", f"《{category}》",
        "--depth", "1",
    ]
    
    try:
        proc = subprocess.run(cmd, capture_output=True, cwd=str(ROOT), timeout=90)
        stdout = proc.stdout.decode('utf-8', errors='ignore')
        stderr = proc.stderr.decode('utf-8', errors='ignore')
        
        if proc.returncode != 0:
            return {"ok": False, "error": stderr[:200] or f"exit code {proc.returncode}", "title": title}
        
        # 从输出中提取最后一行的 JSON
        lines = stdout.strip().split('\n')
        json_line = None
        for line in reversed(lines):
            line = line.strip()
            if line.startswith('{') and line.endswith('}'):
                json_line = line
                break
        
        if not json_line:
            return {"ok": False, "error": "no JSON found in output", "title": title}
        
        result = json.loads(json_line)
        result["title"] = title
        return result
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "title": title}
    except Exception as e:
        return {"ok": False, "error": str(e), "title": title}


def main() -> int:
    results = []
    total = len(PAGES_TO_IMPORT)
    
    print(f"开始批量导入 {total} 个页面...", file=sys.stderr)
    
    for i, (title, page_id, category) in enumerate(PAGES_TO_IMPORT, 1):
        result = import_single_page(title, page_id, category, i, total)
        results.append(result)
        
        if result.get("ok"):
            print(f"  ✓ 成功: {title}", file=sys.stderr)
        else:
            print(f"  ✗ 失败: {title} - {result.get('error', 'unknown')}", file=sys.stderr)
    
    # 汇总
    success_count = sum(1 for r in results if r.get("ok"))
    print(f"\n{'='*50}", file=sys.stderr)
    print(f"导入完成: {success_count}/{total} 成功", file=sys.stderr)
    
    # 输出 JSON 结果
    output = {
        "ok": True,
        "total": total,
        "success_count": success_count,
        "results": results,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if success_count == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
