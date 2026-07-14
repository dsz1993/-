# 金融重大信息推送系统

这是一个托管在 GitHub Actions 上自动运行的金融信息推送项目。你不需要在本地运行，只需要把本项目上传到 GitHub，配置好 Secrets，GitHub 会按计划自动执行。

## 功能

- 定时抓取市场新闻并推送
- 定时监控自选股行情/公告并推送
- 支持企业微信机器人推送
- 支持 Telegram 推送
- 可选接入 Gemini API 做重要性辅助评分

## 一、上传到 GitHub 的正确结构

上传后，仓库根目录必须长这样：

```text
README.md
requirements.txt
.gitignore
.github/
  workflows/
    market-news.yml
    watchlist-alert.yml
config/
  keywords.json
  watchlist.json
src/
  main.py
  watchlist_alert.py
  fetchers/
  filters/
  pushers/
```

注意：`.github` 文件夹必须在仓库根目录，否则 GitHub Actions 不会识别。

## 二、配置 GitHub Secrets

进入你的仓库：

```text
Settings → Secrets and variables → Actions → New repository secret
```

至少配置一个推送渠道。

### 方案 A：企业微信机器人，推荐

新增：

```text
Name: WECOM_WEBHOOK
Value: 你的企业微信机器人 Webhook 地址
```

企业微信机器人 Webhook 通常长这样：

```text
https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxx
```

### 方案 B：Telegram

如果使用 Telegram，新增：

```text
Name: TELEGRAM_BOT_TOKEN
Value: 你的 Telegram Bot Token
```

```text
Name: TELEGRAM_CHAT_ID
Value: 你的 Telegram Chat ID
```

### 可选：Gemini

如果你有 Gemini API Key，可以新增：

```text
Name: GEMINI_API_KEY
Value: 你的 Gemini API Key
```

不配置 Gemini 也可以运行，系统会使用关键词规则评分。
