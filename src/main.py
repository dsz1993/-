"""金融重大信息推送系统 — 主入口
编排：抓取 → 去重 → 评分 → 推送
"""

import sys
import os
import asyncio
import aiohttp

# 添加 src 到 path
sys.path.insert(0, os.path.dirname(__file__))

from fetchers.cls_news import fetch_cls_telegraph
from fetchers.eastmoney_news import fetch_eastmoney_news
from filters.dedup import is_duplicate, mark_sent, cleanup_expired
from filters.scorer import keyword_score, ai_score
from pushers.wecom_bot import push_to_wecom
from pushers.telegram_bot import push_to_telegram


async def main():
    print("=" * 50)
    print("金融重大信息推送系统 v1.0")
    print("=" * 50)

    async with aiohttp.ClientSession() as session:
        # ── 第一步：多源并发抓取 ──
        print("\n📡 [1/4] 抓取新闻...")
        tasks = [
            fetch_cls_telegraph(session, limit=30),
            fetch_eastmoney_news(session, pagesize=30),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_news = []
        for i, result in enumerate(results):
            source_name = ["财联社", "东方财富"][i]
            if isinstance(result, Exception):
                print(f"  ⚠ {source_name} 抓取异常: {result}")
            else:
                print(f"  ✅ {source_name}: {len(result)} 条")
                all_news.extend(result)

        if not all_news:
            print("\n❌ 无新闻数据，退出")
            return

        # ── 第二步：去重 ──
        print(f"\n🔍 [2/4] 去重（原始 {len(all_news)} 条）...")
        unique_news = []
        for item in all_news:
            if not is_duplicate(item["title"], item["source"]):
                unique_news.append(item)
            else:
                pass  # 已推送过 → 丢弃
        print(f"  → 去重后 {len(unique_news)} 条")

        if not unique_news:
            print("\n✅ 无新新闻，退出")
            cleanup_expired()  # 顺便清理过期缓存
            return

        # ── 第三步：重要性评分 ──
        print(f"\n🧠 [3/4] 重要性评分...")

        # 优先尝试 AI 评分
        ai_results = ai_score(unique_news)

        scored_news = []
        if ai_results:
            score_map = {r["id"]: r for r in ai_results}
            for i, item in enumerate(unique_news):
                r = score_map.get(i)
                if r is None:
                    continue  # AI 未对这条评分，跳过
                item["score"] = r["score"]
                item["direction"] = r["direction"]
                item["summary"] = r.get("summary", "")
                item["ai_note"] = "Gemini"
                scored_news.append(item)

            important = [n for n in scored_news if n.get("score", 0) >= 5]
        else:
            # AI 不可用，降级为关键词评分
            for item in unique_news:
                score, matched = keyword_score(item["title"])
                item["score"] = score
                item["direction"] = "neutral"
                item["summary"] = item["title"]
                item["ai_note"] = "关键词"
                scored_news.append(item)

            # 关键词模式：至少命中 1 个关键词才推送
            important = [n for n in scored_news if n.get("score", 0) >= 2]

        print(f"  → 重要新闻 {len(important)} 条 / 总计 {len(scored_news)} 条")

        if not important:
            print("\n✅ 无重大新闻，退出")
            cleanup_expired()
            return

        # ── 第四步：推送（多通道并发） ──
        print(f"\n📤 [4/4] 推送 {len(important)} 条...")
        push_tasks = [
            push_to_wecom(important, session),
            push_to_telegram(important, session),
        ]
        results = await asyncio.gather(*push_tasks, return_exceptions=True)

        wecom_ok = results[0] if not isinstance(results[0], Exception) else False
        telegram_ok = results[1] if not isinstance(results[1], Exception) else False

        if wecom_ok:
            print("  ✅ 企业微信推送成功")
        else:
            print("  ⚠ 企业微信推送失败")

        if telegram_ok:
            print("  ✅ Telegram 推送成功")
        else:
            print("  ⚠ Telegram 推送失败（未配置则静默跳过）")

        # 任一通道推送成功即标记已发送
        if wecom_ok or telegram_ok:
            for item in important:
                mark_sent(item["title"], item["source"])
            print("✅ 推送完成")
        else:
            print("⚠️ 所有通道推送失败（未标记已发送，下次会重试）")

        # 清理过期记录
        cleanup_expired()
        print("\n" + "=" * 50)
        print("执行完成")


if __name__ == "__main__":
    asyncio.run(main())
