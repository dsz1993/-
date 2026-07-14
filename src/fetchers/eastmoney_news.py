"""东方财富要闻与公告抓取器"""

import aiohttp
import asyncio
from typing import Optional


# 东方财富要闻接口（公共 JSONP → JSON）
EASTMONEY_NEWS_URL = (
    "https://np-listapi.eastmoney.com/comm/news/getNews?"
    "client=web&biz=finance&pagesize={pagesize}&pageindex=1"
)


async def fetch_eastmoney_news(
    session: aiohttp.ClientSession,
    pagesize: int = 30,
) -> list[dict]:
    """
    抓取东方财富财经要闻。
    返回格式: [{"id": str, "title": str, "content": str, "ctime": int, "url": str}, ...]
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://finance.eastmoney.com/",
    }

    url = EASTMONEY_NEWS_URL.format(pagesize=pagesize)

    try:
        async with session.get(
            url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status != 200:
                print(f"[东方财富] HTTP {resp.status}")
                return []

            data = await resp.json(content_type=None)

            if not isinstance(data, dict) or data.get("code") != 0:
                print(f"[东方财富] API 返回异常: {data.get('message', 'unknown')}")
                return []

            news_list = data.get("data", {}).get("list", [])
            items = []

            for item in news_list:
                title = item.get("title", "")
                if not title:
                    continue

                items.append({
                    "id": str(item.get("title_id", item.get("code", ""))),
                    "title": title,
                    "content": item.get("digest", ""),
                    "ctime": int(item.get("show_time", item.get("publish_time", 0))),
                    "url": f"https://finance.eastmoney.com/a/{item.get('code', '')}.html",
                    "source": "东方财富",
                })

            return items

    except asyncio.TimeoutError:
        print("[东方财富] 请求超时")
    except aiohttp.ClientError as e:
        print(f"[东方财富] 网络错误: {e}")
    except Exception as e:
        print(f"[东方财富] 未知错误: {e}")

    return []


# 东方财富公告接口（备用，自选股阶段使用）
EASTMONEY_ANNOUNCE_URL = (
    "https://np-anotice-stock.eastmoney.com/api/security/ann?"
    "sr=-1&page_size=20&page_index=1&ann_type=A"
    "&client_source=web&stock_list={stock_code}"
)


async def fetch_stock_announcements(
    session: aiohttp.ClientSession,
    stock_code: str,  # 如 "000858"（不含 sh/sz 前缀）
) -> list[dict]:
    """抓取指定股票公告（Phase 2 用）"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://data.eastmoney.com/",
    }

    url = EASTMONEY_ANNOUNCE_URL.format(stock_code=stock_code)

    try:
        async with session.get(
            url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status != 200:
                return []

            data = await resp.json(content_type=None)
            if not isinstance(data, dict) or not data.get("success"):
                return []

            items = []
            for item in data.get("data", {}).get("list", []):
                items.append({
                    "id": str(item.get("art_code", "")),
                    "title": item.get("title", ""),
                    "ctime": int(item.get("notice_date", 0)),
                    "url": f"https://data.eastmoney.com/notices/detail/{stock_code}/{item.get('art_code', '')}.html",
                    "source": "巨潮公告",
                })
            return items

    except Exception as e:
        print(f"[东方财富公告] 错误: {e}")
        return []
