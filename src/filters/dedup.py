"""去重引擎 — 基于 SQLite 本地缓存，防止同一新闻重复推送"""

import sqlite3
import hashlib
import os
import time
from datetime import datetime


DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "sent.db",
)


def _ensure_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sent_news (
            hash TEXT PRIMARY KEY,
            title TEXT,
            source TEXT,
            sent_time INTEGER
        )
    """)
    conn.commit()
    return conn


def _hash_news(title: str, source: str) -> str:
    raw = f"{title.strip()}|{source.strip()}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def is_duplicate(title: str, source: str) -> bool:
    """判断这条新闻是否已经推送过"""
    conn = _ensure_db()
    h = _hash_news(title, source)
    row = conn.execute(
        "SELECT 1 FROM sent_news WHERE hash = ?", (h,)
    ).fetchone()
    conn.close()
    return row is not None


def mark_sent(title: str, source: str):
    """标记新闻为已推送"""
    conn = _ensure_db()
    h = _hash_news(title, source)
    conn.execute(
        "INSERT OR REPLACE INTO sent_news (hash, title, source, sent_time) VALUES (?, ?, ?, ?)",
        (h, title, source, int(time.time())),
    )
    conn.commit()
    conn.close()


def cleanup_expired(days: int = 90):
    """清理超过指定天数的旧记录"""
    conn = _ensure_db()
    cutoff = int(time.time()) - days * 86400
    conn.execute("DELETE FROM sent_news WHERE sent_time < ?", (cutoff,))
    conn.commit()
    conn.close()
