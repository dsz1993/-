"""自选股行情与公告抓取器

数据源：东方财富公开 API（免费，无需 Key）
"""

import aiohttp
import asyncio
import json
from typing import Optional


async def fetch_realtime_quotes(
    session: aiohttp.ClientSession,
    stock_codes: list[str],
) -> list[dict]:
    """
    批量获取自选股实时行情。

    stock_codes: ["sh600519", "sz000858", ...] 格式
    返回: [{"code":..., "name":..., "price":..., "change_pct":..., "volume":..., "volume_ratio":..., "high":..., "low":..., "open":..., "pre_close":...}, ...]
    """
    if not stock_codes:
        return []

    # 东方财富批量行情接口
    codes_str = ",".join(stock_codes)
    url = (
        "https://push2.eastmoney.com/api/qt/ulist.np/get"
        f"?fltt=2&fields=f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f14,f15,f16,f17,f18"
        f"&secids={codes_str}"
    )

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://quote.eastmoney.com/",
    }

    try:
        async with session.get(
            url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            if resp.status != 200:
                print(f"[自选股行情] HTTP {resp.status}")
                return []

            data = await resp.json(content_type=None)
            if not isinstance(data, dict) or not data.get("data"):
                print(f"[自选股行情] 无数据返回")
                return []

            items = []
            for item in data["data"].get("diff", []):
                items.append({
                    "code": item.get("f12", ""),
                    "name": item.get("f14", ""),
                    "price": item.get("f2", 0),
                    "change_pct": item.get("f3", 0),
                    "change_amount": item.get("f4", 0),
                    "volume": item.get("f5", 0),
                    "turnover": item.get("f6", 0),
                    "amplitude": item.get("f7", 0),
                    "high": item.get("f15", 0),
                    "low": item.get("f16", 0),
                    "open": item.get("f17", 0),
                    "pre_close": item.get("f18", 0),
                    "volume_ratio": item.get("f10", 0),
                })
            return items

    except asyncio.TimeoutError:
        print("[自选股行情] 请求超时")
    except Exception as e:
        print(f"[自选股行情] 错误: {e}")

    return []


async def fetch_stock_news(
    session: aiohttp.ClientSession,
    stock_code: str,  # 纯数字，如 "000858"
    limit: int = 10,
) -> list[dict]:
    """
    抓取指定股票的新闻。

    返回: [{"title":..., "url":..., "ctime":...}, ...]
    """
    url = (
        "https://np-anotice-stock.eastmoney.com/api/security/ann"
        f"?sr=-1&page_size={limit}&page_index=1&ann_type=SHA"
        f"&client_source=web&stock_list={stock_code}"
    )

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://data.eastmoney.com/",
    }

    try:
        async with session.get(
            url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            if resp.status != 200:
                return []

            data = await resp.json(content_type=None)
            if not isinstance(data, dict) or not data.get("success"):
                return []

            items = []
            for item in data.get("data", {}).get("list", []):
                items.append({
                    "title": item.get("title", ""),
                    "code": stock_code,
                    "ctime": int(item.get("notice_date", 0)),
                    "url": f"https://data.eastmoney.com/notices/detail/{stock_code}/{item.get('art_code', '')}.html",
                    "source": "公司公告",
                })
            return items

    except Exception as e:
        print(f"[自选股公告] {stock_code} 错误: {e}")
        return []


def check_alerts(
    quotes: list[dict],
    watchlist: list[dict],
) -> list[dict]:
    """
    检查自选股是否有异动，生成告警列表。

    返回: [{"code":..., "name":..., "reason":..., "direction":..., "price":..., "change_pct":...}, ...]
    """
    alerts = []

    # 构建告警阈值字典
    alert_configs = {}
    for stock in watchlist:
        code = stock["code"]
        alert_configs[code] = stock.get("alerts", {})

    for quote in quotes:
        code = quote["code"]
        config = alert_configs.get(code, {})
        if not config:
            continue

        threshold = config.get("price_change_pct", 5)
        vol_threshold = config.get("volume_surge", 3)
        change_pct = quote.get("change_pct", 0) or 0

        reasons = []

        # 涨跌幅告警
        if abs(change_pct) >= threshold:
            direction = "positive" if change_pct > 0 else "negative"
            reasons.append(
                f"{'大涨' if change_pct > 0 else '大跌'} {abs(change_pct):.2f}%"
            )

        # 量比告警
        vol_ratio = quote.get("volume_ratio", 0) or 0
        if vol_ratio >= vol_threshold and change_pct > 0:
            reasons.append(f"放量 {vol_ratio:.1f}倍")
        elif vol_ratio >= vol_threshold and change_pct < 0:
            reasons.append(f"放量下跌 {vol_ratio:.1f}倍")

        if reasons:
            alerts.append({
                "code": code,
                "name": quote.get("name", code),
                "price": quote.get("price", 0),
                "change_pct": change_pct,
                "volume_ratio": vol_ratio,
                "reason": "；".join(reasons),
                "direction": "positive" if change_pct > 0 else "negative",
                "type": "price_alert",
            })

    return alerts
