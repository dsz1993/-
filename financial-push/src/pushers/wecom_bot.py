"""企业微信机器人推送器"""

import os
import asyncio
import aiohttp
from typing import Optional

# 企业微信 Markdown 消息字节上限（4096）
WECOM_MARKDOWN_MAX_BYTES = 4000
# 末尾落款（为分片逻辑共享常量）
_FOOTER = '\n<font color="comment">'


def _get_webhook_url() -> Optional[str]:
    url = os.environ.get("WECOM_WEBHOOK", "").strip()
    if not url:
        print("[企微推送] 未配置 WECOM_WEBHOOK 环境变量，跳过推送")
        return None
    return url


def _format_message(news_items: list[dict]) -> str:
    if not news_items:
        return ""

    lines = ["## 📰 金融重大信息速报\n"]

    for item in news_items:
        title = item.get("title", "无标题")
        source = item.get("source", "未知来源")
        url = item.get("url", "")
        direction = item.get("direction", "neutral")
        summary = item.get("summary", "")

        dir_icon = {"positive": "🟢", "negative": "🔴", "neutral": "⚪"}.get(direction, "⚪")

        line = f"{dir_icon} **{title}**"
        if summary:
            line += f"\n> {summary}"
        line += f"\n> 来源: {source}"
        if url:
            line += f"\n> [查看详情]({url})"
        line += "\n"

        lines.append(line)

    lines.append(f"{_FOOTER}共 {len(news_items)} 条 · 自动推送</font>")
    return "\n".join(lines)


def _chunk_by_stock_blocks(content: str, max_bytes: int) -> list[str]:
    """
    按新闻条目智能分片。
    如果整体不超限直接返回单条；超限则合并多条但不拆散单条新闻。
    末尾 footer（以 _FOOTER 开头的一行）会被识别并附加到每个分片末尾。
    """
    content_bytes = len(content.encode("utf-8"))
    if content_bytes <= max_bytes:
        return [content]

    # 按空行分块，每个块是一条完整新闻（或 header / footer）
    raw_blocks = content.split("\n\n")

    # 识别 header（第一个非空块以 ## 开头）
    header = ""
    body_start = 0
    if raw_blocks and raw_blocks[0].strip().startswith("##"):
        header = raw_blocks[0]
        body_start = 1
    else:
        # 如果第一个块不以 ## 开头，尝试找到头
        for i, b in enumerate(raw_blocks):
            if b.strip().startswith("##"):
                header = b
                body_start = i + 1
                break

    # 识别 footer（以 _FOOTER 开头的块）
    footer = ""
    body_blocks = []
    for b in raw_blocks[body_start:]:
        if b.startswith(_FOOTER):
            footer = b
        elif b.strip():
            body_blocks.append(b)

    if not body_blocks:
        return [content]

    def _make_chunk(news_parts: list[str]) -> str:
        return "\n\n".join([header] + news_parts + ([footer] if footer else []))

    chunks = []
    current = []

    for block in body_blocks:
        # 尝试把当前块加入
        trial = _make_chunk(current + [block])
        if len(trial.encode("utf-8")) <= max_bytes:
            current.append(block)
        else:
            # 当前批次满
            if current:
                chunks.append(_make_chunk(current))
            else:
                # 单条就超限的情况：截断显示
                truncated = block[:100] + "…"
                chunks.append(_make_chunk([truncated]))
                continue
            current = [block]

    if current:
        chunks.append(_make_chunk(current))

    return chunks if chunks else [content]


async def push_to_wecom(
    news_items: list[dict],
    session: Optional[aiohttp.ClientSession] = None,
) -> bool:
    webhook_url = _get_webhook_url()
    if not webhook_url:
        return False

    message = _format_message(news_items)
    if not message:
        print("[企微推送] 消息为空，跳过")
        return False

    chunks = _chunk_by_stock_blocks(message, WECOM_MARKDOWN_MAX_BYTES)
    print(f"[企微推送] 消息 {len(message.encode('utf-8'))} 字节 → {len(chunks)} 批次")

    close_session = False
    if session is None:
        session = aiohttp.ClientSession()
        close_session = True

    try:
        all_ok = True
        for i, chunk in enumerate(chunks):
            payload = {"msgtype": "markdown", "markdown": {"content": chunk}}
            try:
                async with session.post(
                    webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("errcode") == 0:
                            print(f"[企微推送] 第 {i+1}/{len(chunks)} 批发送成功")
                        else:
                            print(f"[企微推送] 第 {i+1}/{len(chunks)} 批错误: {data}")
                            all_ok = False
                    else:
                        print(f"[企微推送] 第 {i+1}/{len(chunks)} 批 HTTP {resp.status}")
                        all_ok = False
            except Exception as e:
                print(f"[企微推送] 第 {i+1}/{len(chunks)} 批请求失败: {e}")
                all_ok = False

            if i < len(chunks) - 1:
                await asyncio.sleep(1)

        return all_ok
    finally:
        if close_session:
            await session.close()
