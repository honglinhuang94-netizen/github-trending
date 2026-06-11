"""FastAPI 主服务

- /                       静态前端页面
- /api/trending/{period}  返回 daily / weekly / monthly 列表
- /api/health             健康检查
"""
from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .cache import TTLCache
from .scraper import TrendingRepo, fetch_trending
from .translator import translate_descriptions

logger = logging.getLogger("github-trending")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")

# 1 小时缓存: trending 数据本身更新不快,且翻译是耗时操作
_cache: TTLCache[dict] = TTLCache(ttl_seconds=3600)
# 同一周期并发请求时,只让一个真正去抓
_inflight: dict[str, asyncio.Event] = {}


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("GitHub Trending 服务启动, static=%s", STATIC_DIR)
    yield
    logger.info("GitHub Trending 服务关闭")


app = FastAPI(
    title="GitHub Trending Viewer",
    description="按 daily / weekly / monthly 查看 GitHub 热门项目,带中文翻译。",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ---- API --------------------------------------------------------------------


async def _build_payload(period: str) -> dict:
    """抓取 + 翻译,返回给前端的 payload。"""
    cached = _cache.get(period)
    if cached:
        return cached

    # 同一周期并发请求时合并: 后到的等前面的结果
    event = _inflight.get(period)
    if event:
        await event.wait()
        cached = _cache.get(period)
        if cached:
            return cached
        # 兜底: 前面的请求如果崩了,继续往下走

    event = asyncio.Event()
    _inflight[period] = event
    try:
        logger.info("开始抓取 trending period=%s", period)
        t0 = time.time()
        repos: List[TrendingRepo] = await fetch_trending(period)
        logger.info("抓取完成 period=%s count=%d 耗时=%.2fs", period, len(repos), time.time() - t0)

        descriptions = [r.description for r in repos]
        t0 = time.time()
        translated = await translate_descriptions(descriptions)
        logger.info("翻译完成 period=%s 耗时=%.2fs", period, time.time() - t0)

        items: List[dict] = []
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
        _cache.set(period, payload)
        return payload
    except Exception as e:
        logger.exception("抓取 trending 失败 period=%s: %s", period, e)
        raise
    finally:
        event.set()
        _inflight.pop(period, None)


@app.get("/api/trending/{period}")
async def api_trending(period: str) -> dict:
    period = period.lower()
    if period not in {"daily", "weekly", "monthly"}:
        raise HTTPException(status_code=400, detail="period must be daily/weekly/monthly")
    return await _build_payload(period)


@app.get("/api/health")
async def api_health() -> dict:
    return {
        "status": "ok",
        "cache": _cache.stats(),
    }


# ---- 静态文件 ---------------------------------------------------------------

# 挂载 /static 路径,便于 CSS / JS 引用
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index() -> FileResponse:
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=500, detail="frontend not built")
    return FileResponse(str(index_file))
