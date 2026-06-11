"""翻译模块

把仓库的英文描述翻译成简体中文,使用 Google Translate 的非官方接口
(经由 deep-translator)。翻译失败时降级为原文,不会让整页崩掉。
"""
from __future__ import annotations

import asyncio
import time
from typing import Iterable, List, Optional, Tuple

from deep_translator import GoogleTranslator
from deep_translator.exceptions import (
    NotValidPayload,
    RequestError,
    TooManyRequests,
    TranslationNotFound,
)


# 进程级缓存: 描述原文 -> 中文译文
_TRANSLATION_CACHE: dict[str, str] = {}
_LAST_REQUEST_TS: float = 0.0
_MIN_INTERVAL = 0.05  # 同一进程内两次请求的最小间隔,降低被限流的概率


async def _translate_one(text: str) -> str:
    """单条描述 -> 中文。失败时返回原文。"""
    if not text or not text.strip():
        return ""

    text = text.strip()
    if text in _TRANSLATION_CACHE:
        return _TRANSLATION_CACHE[text]

    def _do() -> str:
        global _LAST_REQUEST_TS
        # 简单节流
        gap = time.time() - _LAST_REQUEST_TS
        if gap < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - gap)
        _LAST_REQUEST_TS = time.time()
        return GoogleTranslator(source="auto", target="zh-CN").translate(text)

    try:
        translated = await asyncio.to_thread(_do)
        if translated and translated.strip():
            _TRANSLATION_CACHE[text] = translated
            return translated
        return text
    except (TooManyRequests, RequestError, TranslationNotFound, NotValidPayload):
        # 翻译失败,降级原文
        return text
    except Exception:
        return text


async def translate_descriptions(descriptions: Iterable[str]) -> List[str]:
    """并发翻译一组描述,保持输入顺序。"""
    items: List[Tuple[int, str]] = [(i, d) for i, d in enumerate(descriptions)]
    results: List[Optional[str]] = [None] * len(items)

    # 用信号量限制并发,避免一次性打爆翻译服务
    sem = asyncio.Semaphore(5)

    async def _worker(idx: int, text: str) -> None:
        async with sem:
            results[idx] = await _translate_one(text)

    await asyncio.gather(*[_worker(i, t) for i, t in items])
    return [r if r is not None else "" for r in results]


def clear_cache() -> None:
    """清空翻译缓存 (测试用)。"""
    _TRANSLATION_CACHE.clear()
