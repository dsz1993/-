"""财联社电报快讯抓取器"""

import aiohttp
import asyncio
from datetime import datetime
from typing import Optional


CLS_TELEGRAPH_URL = "https://www.cls.cn/nodeapi/telegraphList"


async def fetch_cls_telegraph(
    session: aiohttp.ClientSession,
    limit: int = 30,
) -> list[dict]:
    """
    抓取财联社电报快讯。
    返回格式: [{"id": str, "title": str, "content": str, "ctime": int, "url": str}, ...]
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.cls.cn/telegraph",
        "Content-Type": "application/json",
    }

    payload = {
        "app": "CailianpressWeb",
        "os": "web",
        "sv": "8.4.7",
        "rn": limit,
        "type": "telegraph",
    }

    try:
        async with session.post(
            CLS_TELEGRAPH_URL,
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status != 200:
                print(f"[财联社] HTTP {resp.status}")
                return []

            data = await resp.json()

            # cls 返回结构: {"error": 0, "data": {"roll_data": [...]}}
            # 字段随版本变化，做兼容处理
            if isinstance(data, dict) and data.get("error") == 0:
                roll_data = data.get("data", {}).get("roll_data", [])
            elif isinstance(data, list):
                roll_data = data
            else:
                print(f"[财联社] 非预期数据结构")
                return []

            items = []
            for item in roll_data:
                items.append({
                    "id": str(item.get("id", "")),
                    "title": item.get("title", ""),
                    "content": item.get("content", item.get("brief", "")),
                    "ctime": item.get("ctime", 0),
                    "url": f"https://www.cls.cn/detail/{item.get('id', '')}",
                    "source": "财联社",
                })

            return items

    except asyncio.TimeoutError:
        print("[财联社] 请求超时")
    except aiohttp.ClientError as e:
        print(f"[财联社] 网络错误: {e}")
    except Exception as e:
        print(f"[财联社] 未知错误: {e}")

    return []
