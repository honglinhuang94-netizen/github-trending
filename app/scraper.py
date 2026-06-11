"""GitHub Trending 抓取模块

抓取 https://github.com/trending 的 daily / weekly / monthly 列表,
解析出仓库名、描述、编程语言、star 总数、本期新增 star、fork 数等信息。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import List, Optional

import httpx
from bs4 import BeautifulSoup

TRENDING_URL = "https://github.com/trending"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


@dataclass
class TrendingRepo:
    """单个热门仓库的解析结果。"""

    rank: int
    name: str               # "owner/repo"
    url: str                # 完整 URL
    description: str        # 原始英文描述
    language: Optional[str] # 编程语言
    stars_total: int        # 累计 star
    stars_period: int       # 本期新增 star
    forks: int              # fork 数
    contributors: List[str] # 本期主要贡献者头像 url

    def to_dict(self) -> dict:
        return asdict(self)


def _parse_int(text: str) -> int:
    """把 '1,234' / '1.2k' / '12' 这样的字符串解析成整数。"""
    if not text:
        return 0
    text = text.strip().replace(",", "")
    match = re.match(r"^([\d.]+)\s*([kKmM]?)$", text)
    if not match:
        return 0
    value = float(match.group(1))
    suffix = match.group(2).lower()
    if suffix == "k":
        value *= 1_000
    elif suffix == "m":
        value *= 1_000_000
    return int(value)


def _extract_owner_repo(href: str) -> str:
    """从形如 '/owner/repo' 的路径里取出 'owner/repo'。"""
    href = href.strip().strip("/")
    parts = href.split("/")
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return href


def _parse_period_stars(text: str) -> int:
    """解析 '1,234 stars today' / '1.2k stars this week' 这类字符串里的数字。"""
    if not text:
        return 0
    match = re.search(r"([\d.,]+)\s*([kKmM]?)\s*stars", text)
    if not match:
        return 0
    raw = match.group(1).replace(",", "")
    suffix = match.group(2).lower()
    try:
        value = float(raw)
    except ValueError:
        return 0
    if suffix == "k":
        value *= 1_000
    elif suffix == "m":
        value *= 1_000_000
    return int(value)


def parse_trending_html(html: str) -> List[TrendingRepo]:
    """把 trending 页面的 HTML 解析成 TrendingRepo 列表。"""
    soup = BeautifulSoup(html, "html.parser")
    articles = soup.select("article.Box-row")
    repos: List[TrendingRepo] = []

    for idx, article in enumerate(articles, start=1):
        # 仓库名: 第一个 h2 里的 a 标签
        title_link = article.select_one("h2 a")
        if not title_link or not title_link.get("href"):
            continue
        name = _extract_owner_repo(title_link["href"])
        url = f"https://github.com{title_link['href']}"

        # 描述
        desc_tag = article.select_one("p")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        # 编程语言
        lang_tag = article.select_one("[itemprop='programmingLanguage']")
        language = lang_tag.get_text(strip=True) if lang_tag else None

        # star / fork 链接
        stars_total = 0
        forks = 0
        for a in article.select("a[href$='/stargazers']"):
            stars_total = _parse_int(a.get_text(strip=True))
            break
        for a in article.select("a[href$='/network/members'], a[href$='/forks']"):
            forks = _parse_int(a.get_text(strip=True))
            break

        # 本期新增 star
        period_tag = article.select_one("span.d-inline-block.float-sm-right")
        stars_period = _parse_period_stars(period_tag.get_text()) if period_tag else 0

        # 贡献者头像 (本期热门贡献者)
        contributors: List[str] = []
        for img in article.select("img[src*='avatars']"):
            src = img.get("src", "")
            if src and src not in contributors:
                contributors.append(src)
                if len(contributors) >= 5:
                    break

        repos.append(
            TrendingRepo(
                rank=idx,
                name=name,
                url=url,
                description=description,
                language=language,
                stars_total=stars_total,
                stars_period=stars_period,
                forks=forks,
                contributors=contributors,
            )
        )

    return repos


async def fetch_trending(period: str = "daily") -> List[TrendingRepo]:
    """异步抓取指定周期的 trending 列表。

    period: daily | weekly | monthly
    """
    period = period.lower()
    if period not in {"daily", "weekly", "monthly"}:
        period = "daily"

    params = {"since": period}
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        resp = await client.get(TRENDING_URL, params=params, headers=HEADERS)
        resp.raise_for_status()
        return parse_trending_html(resp.text)
