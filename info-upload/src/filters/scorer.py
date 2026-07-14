"""重要性评分 — 关键词匹配 + Gemini AI 辅助（可选）"""

import os
import json
from typing import Optional


_KEYWORDS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "config",
    "keywords.json",
)


def _load_keywords() -> list[str]:
    try:
        with open(_KEYWORDS_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
            return config.get("high_priority", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return [
            "降息", "加息", "降准", "涨停", "跌停", "退市", "重组", "并购",
            "减持", "暴雷", "违约", "处罚", "立案", "业绩预告", "黑天鹅",
        ]


def keyword_score(title: str) -> tuple[int, list[str]]:
    """
    基于关键词匹配打分。
    返回 (score, matched_keywords)
    """
    keywords = _load_keywords()
    score = 0
    matched = []

    for kw in keywords:
        if kw in title:
            score += 2
            matched.append(kw)

    if len(title) < 8 and matched:
        score += 1

    return min(score, 10), matched


def ai_score(news_items: list[dict]) -> Optional[list[dict]]:
    """
    使用 Gemini 进行语义评分（可选，需要 GEMINI_API_KEY 环境变量）。
    返回格式: [{"id": index, "score": 1-10, "direction": "positive"/"negative"/"neutral", "summary": "..."}, ...]
    如果 API Key 未配置或调用失败，返回 None，调用方降级为 keyword_score。
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("[AI评分] 未配置 GEMINI_API_KEY，使用关键词模式")
        return None

    try:
        import google.generativeai as genai
    except ImportError:
        print("[AI评分] google-generativeai 未安装，使用关键词模式")
        return None

    genai.configure(api_key=api_key)

    news_json = json.dumps(
        [
            {"id": i, "title": item["title"], "source": item.get("source", "")}
            for i, item in enumerate(news_items)
        ],
        ensure_ascii=False,
    )

    prompt = f"""你是专业金融新闻分析师。对每条新闻进行重要性评分(1-10)，判断市场影响方向。

评分标准：
- 8-10分：突发重大事件（央行加息降息降准/黑天鹅/公司暴雷破产/重大并购重组/退市/监管处罚/业绩暴雷或暴增）
- 5-7分：重要但可预期的信息（定期业绩报告/行业政策出台/评级调整/公司公告）
- 1-4分：常规信息、市场噪音、非重大公司动态

方向判断：
- "positive"：明显利好
- "negative"：明显利空
- "neutral"：中性或影响不明确

返回纯JSON数组，不要markdown代码块、不要额外文字：
[{{"id": 0, "score": 7, "direction": "negative", "summary": "15字内中文摘要"}}]

新闻列表：
{news_json}"""

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.1, "max_output_tokens": 1024},
        )

        text = response.text.strip()

        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if len(lines) > 2 and lines[-1].strip() == "```" else lines[1:])

        results = json.loads(text)
        print(f"[AI评分] Gemini 成功评分 {len(results)} 条新闻")
        return results

    except json.JSONDecodeError as e:
        print(f"[AI评分] JSON 解析失败: {e}")
        print(f"[AI评分] 原始返回: {text[:200]}")
    except Exception as e:
        print(f"[AI评分] Gemini 调用失败: {e}")

    return None
