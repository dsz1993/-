"""Telegram 推送器（备选渠道）"""

import os
import asyncio
import aiohttp
from typing import Optional


TELEGRAM_API_BASE = "https://api.telegram.org"


def _get_bot_token() -> Optional[str]:
    return os.environ.get("TELEGRAM_BOT_TOKEN", "").strip() or None


def _get_chat_id() -> Optional[str]:
    return os.environ.get("TELEGRAM_CHAT_ID", "").strip() or None


def _format_telegram_message(news_items: list[dict]) -> str:
    if not news_items:
        return ""

    lines = ["📰 <b>金融重大信息速报</b>\n"]

    for item in news_items:
        title = item.get("title", "无标题")
        source = item.get("source", "未知来源")
        url = item.get("url", "")
        direction = item.get("direction", "neutral")
        summary = item.get("summary", "")

        dir_icon = {"positive": "🟢", "negative": "🔴", "neutral": "⚪"}.get(direction, "⚪")

        line = f"{dir_icon} <b>{title}</b>"
        if summary:
            line += f"\n<i>{summary}</i>"
        line += f"\n来源: {source}"
        if url:
            line += f'\n<a href="{url}">查看详情</a>'
        lines.append(line)

    lines.append(f"\n共 {len(news_items)} 条 · 自动推送")
    return "\n\n".join(lines)


async def push_to_telegram(
    news_items: list[dict],
    session: Optional[aiohttp.ClientSession] = None,
) -> bool:
    bot_token = _get_bot_token()
    chat_id = _get_chat_id()

    if not bot_token or not chat_id:
        print("[Telegram] 未配置 TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID，跳过")
        return False

    message = _format_telegram_message(news_items)
    if not message:
        return False

    url = f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage"

    close_session = False
    if session is None:
        session = aiohttp.ClientSession()
        close_session = True

    try:
        async with session.post(
            url,
            json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status == 200:
                print(f"[Telegram] 成功推送 {len(news_items)} 条新闻")
                return True
            else:
                body = await resp.text()
                print(f"[Telegram] HTTP {resp.status}: {body[:200]}")
                return False
    except Exception as e:
        print(f"[Telegram] 请求失败: {e}")
        return False
    finally:
        if close_session:
            await session.close()
