# 金融重大信息推送系统

基于 GitHub Actions 的零成本金融新闻推送，定时抓取免费数据源 → AI 语义过滤 → 企业微信 / Telegram 实时推送。

## 架构

```
GitHub Actions Cron → 多源抓取(财联社+东方财富) → 去重(SQLite) → Gemini AI 评分 → 多通道推送(企微/Telegram)
```

## 快速部署（5 分钟）

### 1. 创建 GitHub 仓库

将本项目代码推送到 GitHub 仓库（公开仓库即可，无限免费）。

### 2. 配置推送渠道（至少选一个）

**推荐：企业微信群机器人**

1. 注册 [企业微信](https://work.weixin.qq.com/)（个人免费）
2. 创建一个群聊 → 群设置 → 添加群机器人
3. 复制 Webhook URL（形如 `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx`）
4. 企业微信绑定个人微信：设置 → 账号 → 微信插件 → 扫码绑定，之后微信里直接收消息

**备选：Telegram Bot**

1. 在 Telegram 搜 `@BotFather` → `/newbot` → 创建机器人 → 拿到 Token
2. 搜你的机器人 → `/start` 激活
3. 获取 Chat ID：浏览器访问 `https://api.telegram.org/bot<你的Token>/getUpdates`，找到 `chat.id`

### 3. 配置 GitHub Secrets

仓库 → Settings → Secrets and variables → Actions → New repository secret：

| Secret 名称 | 值 | 必须 |
|---|---|---|
| `WECOM_WEBHOOK` | 企业微信机器人 Webhook URL | 推荐 |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | 备选 |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID | 备选 |
| `GEMINI_API_KEY` | Google Gemini API Key | 可选 |

> 不配 `GEMINI_API_KEY` 时系统自动降级为关键词匹配模式，仍可正常运行。
> 企微和 Telegram 可同时配置，双通道并发推送。

### 4. 获取 Gemini API Key（可选但推荐）

1. 访问 [Google AI Studio](https://aistudio.google.com/apikey)
2. 点击 "Create API Key"
3. 复制 Key 存入 GitHub Secret `GEMINI_API_KEY`

Gemini 免费层：1,500 次请求/天，本项目远在免费额度内。免费层不会自动扣费。

### 5. 验证

Actions 页面 → 选择 workflow → Run workflow → 手动触发一次。检查手机是否收到推送。

## 运行频率

| 时段 | 频率 |
|---|---|
| 交易时段（周一至五 9:00-15:00） | 每 15 分钟 |
| 盘前盘后（周一至五） | 每 2 小时 |
| 周末 | 每 6 小时 |

## 两种运行模式

| | Gemini AI 模式 | 关键词模式 |
|---|---|---|
| 触发条件 | 配置了 `GEMINI_API_KEY` | 未配置 Key（自动降级） |
| 评分方式 | Gemini 语义理解，1-10 分精确打分 | keywords.json 关键词匹配，命中 +2 分 |
| 推送阈值 | ≥ 5 分 | ≥ 1 个关键词 |
| 摘要 | AI 自动生成 15 字摘要 | 使用原标题 |
| 方向判断 | 自动判定利好/利空/中性 | 默认中性 |

## 数据源

| 数据源 | 类型 | 需要 API Key | 接入方式 |
|---|---|---|---|
| 财联社电报 | A 股实时快讯 | 否 | 公开 JSON API |
| 东方财富 | 要闻 + 公告 | 否 | 公开 JSON API |

## 项目结构

```
financial-push/
├── .github/workflows/market-news.yml   # GitHub Actions 定时任务
├── src/
│   ├── main.py                          # 主入口，编排全流程
│   ├── fetchers/                        # 数据抓取
│   │   ├── cls_news.py                  #   财联社电报
│   │   └── eastmoney_news.py            #   东方财富要闻 + 公告
│   ├── filters/                         # 过滤评分
│   │   ├── dedup.py                     #   SQLite 去重
│   │   └── scorer.py                    #   关键词 + Gemini AI 双模式评分
│   └── pushers/                         # 推送渠道
│       ├── wecom_bot.py                 #   企业微信（支持超长分片）
│       └── telegram_bot.py              #   Telegram（备选）
├── config/
│   └── keywords.json                    # 重大信息关键词
├── data/sent.db                         # 已推送记录（自动生成）
├── requirements.txt
└── README.md
```

## 成本

完全免费。公开仓库 GitHub Actions 无限免费；所有数据源为公开接口；Gemini 免费层足够；企业微信 / Telegram 均免费。

## 后续计划

- [ ] Phase 2：自选股异动监控
- [ ] Phase 3：飞书 / Discord 渠道
