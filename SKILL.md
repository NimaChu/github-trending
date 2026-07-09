---
name: github-trending
description: "Combined GitHub trending fetcher with a star-growth focus. Modes: (1) --official scrapes the REAL github.com/trending page — the authoritative leaderboard ranked by stars gained in the window, showing exact 'X stars today/this week/this month' increments; (2) Search-API full-spectrum mode (all languages, --language filter); (3) AI-focused mode (--category ai, AI/LLM/Agent keywords+topics). Supports --sort growth/velocity for star-growth metrics. Use when the user asks for GitHub trending, 热门项目, AI 趋势, 开源动态, star 增长, popular repos, or leaderboards. Pure stdlib, no pip deps. Triggers: GitHub、trending、开源、热门、AI趋势、排行榜、star增长、增星."
version: 1.0.0
agent_created: true
allowed-tools: Bash,Read
display_name: "github-trending"
visibility: "public"
---

# GitHub Trending (Combined)

合并两种能力于一体的 GitHub 热门仓库获取技能：

- **全品类模式**（`--category all`，默认）：覆盖所有语言，支持 `--language` 按语言过滤，并自动跨主流语言补采以保证多样性。
- **AI 专榜模式**（`--category ai`）：仅返回 AI / ML / LLM / Agent 方向仓库，按关键词（ai / llm / gpt / agent / transformer / diffusion / rag / ml）与话题（artificial-intelligence / llm / generative-ai / ai-agent）检索。

API 模式均按 `daily / weekly / monthly` 周期返回，输出 Markdown 排行榜（含 star、forks、语言、topics、描述）或原始 JSON。仅依赖 Python 标准库，仅访问 `api.github.com`。

**官方增星榜（`--official`，最权威的"star 增长快"来源）**：直接抓取 `github.com/trending` 页面——它本身就是按"周期内真实新增 star"排序的官方榜单，每个仓库卡片标注 `X stars today / this week / this month` 精确增量。支持 `--period`（daily/weekly/monthly）与 `--language` 过滤，但**不支持 AI 过滤**（传 `--category ai` 会被忽略并提示）。无需 token（公开页）。

**增速维度（`--sort`，仅 API 模式）**：
- `stars`（默认）：按累计 star 排序，近似官方 trending。
- `growth`：**按日均增速排序**（`stars / 仓库年龄天数`），立刻可用，专门揪出"年轻但涨得猛"的新爆款。
- `velocity`：**按真实跨天 star 增量排序**，依赖本地快照库 `trending_snapshot.json`（每次运行自动记录基线）。首次运行仅记录基线，之后运行（或明天的定时推送）即显示真实日增量。

## 快速开始

```bash
# 📈 官方真实增星榜（github.com/trending，按周期内新增 star 排序）— 最权威
python3 scripts/github_trending.py --official --period weekly
python3 scripts/github_trending.py --official --period daily --language python

# 本周全品类热门 Top 20（默认，按累计 star）
python3 scripts/github_trending.py --period weekly

# 本周 Python 热门
python3 scripts/github_trending.py --period weekly --language python

# 本月 AI/ML/LLM 热门 Top 15
python3 scripts/github_trending.py --period monthly --category ai --limit 15

# 🚀 找出 AI 赛道里"涨得最快"的新仓库（按日均增速，API 模式）
python3 scripts/github_trending.py --period weekly --category ai --sort growth --limit 15

# 📈 真实跨天 star 增量榜（首次 seed 基线，之后显示真实增量，API 模式）
python3 scripts/github_trending.py --category ai --sort velocity --limit 15

# 今日全品类，输出 JSON
python3 scripts/github_trending.py --period daily --json
```

## 参数说明

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--period` | `-p` | `weekly` | 时间范围：`daily` / `weekly` / `monthly` |
| `--limit` | `-n` | `20` | 返回项目数量 |
| `--language` | `-l` | 全部 | 编程语言过滤，如 `python`、`go`、`rust`（官方与 API 模式均生效） |
| `--category` | `-c` | `all` | `all`=全品类；`ai`=仅 AI/ML/LLM（仅 API 模式；官方模式忽略并提示） |
| `--sort` | `-s` | `stars` | 排序指标（仅 API 模式）：`stars`=累计star；`growth`=日均增速(按年龄)；`velocity`=真实跨天增量 |
| `--official` | — | 否 | 抓取官方 github.com/trending 页面（真实增星榜；支持 --language/--period，忽略 --category） |
| `--token` | `-t` | 环境变量 | GitHub PAT，也可设置 `GITHUB_TOKEN`（仅 API 模式需要） |
| `--json` | — | 否 | 输出原始 JSON |

## 提高 API 限额

不带 token 时 GitHub API 限制 10 次/分钟；带 token 可提升到 30 次/分钟。

```bash
export GITHUB_TOKEN=your_personal_access_token
python3 scripts/github_trending.py --category ai
```

## 实现说明

- 纯 Python 标准库，无 pip 依赖。
- **官方模式（`--official`）**：`urllib` 抓取 `https://github.com/trending?since=PERIOD[&spoken_language_code]`，正则解析每个 `<article class="Box-row">`：仓库名（`<h2><a href>`）、描述（`<p class="col-9">`）、总 star / forks（stargazers / forks 链接）、语言、以及 `* stars today/this week/this month` 真实增量标签。
- **API 模式**：调用 `https://api.github.com/search/repositories` 真实 API。
- 全品类：`pushed:>=DATE stars:>=10` + `sort=stars`，无语言过滤时跨主流语言补采。
- AI 模式：AI 关键词（name/description）+ AI 话题双路检索，去重后按 star 排序。
- `--sort growth`：本地按 `stargazers_count / 仓库年龄天数` 重排候选池（多拉候选以覆盖不同年龄段），立刻发现新晋爆款。
- `--sort velocity`：基于本地快照库 `trending_snapshot.json`（每次运行 upsert 当前 star）。首次无历史 → 记录基线；之后读历史算真实 delta/天。

## 常见问题

**Q: 哪种模式最能反映"star 增长快"？** `--official` 模式最权威——它直接呈现 github.com/trending 官方按周期内新增 star 排序的榜单，含精确增量数字。API 模式的 `--sort growth`（年龄折算）/`--sort velocity`（快照对比）是其补充，优势是可叠加 AI 过滤与任意周期。

**Q: 官方模式提示抓取失败？** 多为网络/GitHub 限流。可去掉 `--official` 改用 API 模式（需 `GITHUB_TOKEN` 提额）；或稍后重试。

**Q: API 模式提示 HTTP 403 / rate limit exceeded？** 设置 `GITHUB_TOKEN` 或稍后重试。

**Q: 支持哪些编程语言？** 所有 GitHub 支持的语言标识符，如 `python`、`javascript`、`typescript`、`go`、`rust`、`java`、`cpp`、`swift`、`kotlin` 等。
