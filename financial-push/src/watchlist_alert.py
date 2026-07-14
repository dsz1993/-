"""自选股异动监控 — 独立入口
编排：自选股行情 → 异动检测 → 公告抓取 → 去重 → 推送
"""

import sys
import os
import json
import asyncio
import aiohttp
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from fetchers.watchlist import fetch_realtime_quotes, fetch_stock_news, check_alerts
from filters.dedup import is_duplicate, mark_sent, cleanup_expired
from filters.scorer import ai_score, keyword_score
from pushers.wecom_bot import push_to_wecom
from pushers.telegram_bot import push_to_telegram


WATCHLIST_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "config",
    "watchlist.json",
)


def load_watchlist() -> list[dict]:
    try:
        with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[自选股] 配置加载失败: {e}")
        return []


async def main():
    print("=" * 50)
    print("自选股异动监控 v1.0")
    print("=" * 50)

    watchlist = load_watchlist()
    if not watchlist:
        print("❌ 自选股列表为空，退出")
        return

    stock_codes = [s["code"] for s in watchlist]
    print(f"📋 监控 {len(stock_codes)} 只股票: {', '.join(s['name'] for s in watchlist)}")

    async with aiohttp.ClientSession() as session:
        # ── 第一步：抓取实时行情 ──
        print("\n📡 [1/4] 实时行情...")
        quotes = await fetch_realtime_quotes(session, stock_codes)
        print(f"  获取到 {len(quotes)} 只股票行情")

        if not quotes:
            print("❌ 无行情数据，退出")
            return

        # ── 第二步：异动检测 ──
        print("\n🔔 [2/4] 异动检测...")
        alerts = check_alerts(quotes, watchlist)

        if alerts:
            for a in alerts:
                print(f"  ⚡ {a['name']}({a['code']}): {a['reason']} 价格: {a['price']}")
        else:
            print("  无异动")

        # ── 第三步：公告抓取（仅限开启了 monitor_announcements 的股票） ──
        print("\n📄 [3/4] 公告抓取...")
        announcement_stocks = [
            s for s in watchlist
            if s.get("alerts", {}).get("monitor_announcements", False)
        ]

        announcement_items = []
        if announcement_stocks:
            ann_tasks = []
            for stock in announcement_stocks:
                # 去掉 sh/sz 前缀
                code_num = stock["code"][2:]
                ann_tasks.append(fetch_stock_news(session, code_num, limit=5))

            ann_results = await asyncio.gather(*ann_tasks, return_exceptions=True)

            for stock, result in zip(announcement_stocks, ann_results):
                if isinstance(result, Exception):
                    print(f"  ⚠ {stock['name']} 公告抓取异常: {result}")
                else:
                    # 去重 + 加入告警
                    new_ann = []
                    for item in result:
                        if not is_duplicate(item["title"], "公司公告"):
                            new_ann.append(item)
                    if new_ann:
                        print(f"  📢 {stock['name']}: {len(new_ann)} 条新公告")
                        for ann in new_ann:
                            alerts.append({
                                "code": stock["code"],
                                "name": stock["name"],
                                "reason": f"新公告: {ann['title'][:30]}",
                                "direction": "neutral",
                                "type": "announcement",
                                **ann,
                            })
        else:
            print("  未配置公告监控")

        # 合并所有告警
        if not alerts:
            print("\n✅ 无告警，退出")
            cleanup_expired()
            return

        # ── 第四步：格式化 + 推送 ──
        print(f"\n📤 [4/4] 推送 {len(alerts)} 条告警...")

        # 组装推送消息
        news_items = []
        for alert in alerts:
            title = alert.get("title") or f"{alert['name']}: {alert['reason']}"
            news_items.append({
                "title": title,
                "source": "自选股监控",
                "url": alert.get("url", ""),
                "direction": alert.get("direction", "neutral"),
                "summary": f"{alert.get('name', '')} {alert.get('reason', '')}",
                "score": 8,  # 异动告警默认高优先级
            })

        push_tasks = [
            push_to_wecom(news_items, session),
            push_to_telegram(news_items, session),
        ]
        results = await asyncio.gather(*push_tasks, return_exceptions=True)

        wecom_ok = results[0] if not isinstance(results[0], Exception) else False
        telegram_ok = results[1] if not isinstance(results[1], Exception) else False

        if wecom_ok:
            print("  ✅ 企业微信推送成功")
        if telegram_ok:
            print("  ✅ Telegram 推送成功")

        if wecom_ok or telegram_ok:
            for item in news_items:
                mark_sent(item["title"], "自选股监控")
            print("✅ 完成")
        else:
            print("⚠️ 所有通道推送失败")

        cleanup_expired()
        print("\n" + "=" * 50)
        print("执行完成")


if __name__ == "__main__":
    asyncio.run(main())
