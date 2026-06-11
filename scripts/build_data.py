"""离线数据生成脚本

跑一次会抓取 daily/weekly/monthly 三份 trending,翻译后写到
docs/data/trending-*.json,给静态前端使用。

本地运行:
    python scripts/build_data.py

GitHub Actions 也会调用本脚本 (见 .github/workflows/update.yml)。
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

# 把项目根目录加到 sys.path,这样可以 import app.*
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.scraper import fetch_trending            # noqa: E402
from app.translator import translate_descriptions  # noqa: E402

OUT_DIR = ROOT / "docs" / "data"
PERIODS = ("daily", "weekly", "monthly")


async def build_one(period: str) -> dict:
    """抓取 + 翻译单个周期,返回 payload 并写入文件。"""
    print(f"[{period}] 抓取中...", flush=True)
    t0 = time.time()
    repos = await fetch_trending(period)
    print(f"[{period}] 抓到 {len(repos)} 个仓库, 耗时 {time.time() - t0:.1f}s", flush=True)

    descriptions = [r.description for r in repos]
    t0 = time.time()
    translated = await translate_descriptions(descriptions)
    print(f"[{period}] 翻译完成, 耗时 {time.time() - t0:.1f}s", flush=True)

    items: list[dict] = []
    for repo, zh in zip(repos, translated):
        data = repo.to_dict()
        data["description_zh"] = zh
        items.append(data)

    payload = {
        "period": period,
        "count": len(items),
        "items": items,
        "generated_at": int(time.time()),
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUT_DIR / f"trending-{period}.json"
    out_file.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[{period}] 写入 {out_file.relative_to(ROOT)}", flush=True)
    return payload


async def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    has_error = False
    for period in PERIODS:
        try:
            await build_one(period)
        except Exception as e:
            # 单个周期失败不阻塞其他周期
            print(f"[{period}] 失败: {e}", flush=True)
            has_error = True
    # 写一个 index 文件,前端可以用来判断数据是否已生成
    manifest = {
        "generated_at": int(time.time()),
        "periods": list(PERIODS),
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 1 if has_error else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
