# 📈 GitHub Trending

> WorkBuddy Skill — GitHub 热门仓库获取技能，支持官方增星榜、全品类搜索、AI 专榜及增速指标，纯 Python 标准库实现。

## ✨ 功能特性

| 模式 | 命令标志 | 说明 |
|------|---------|------|
| **官方增星榜** | `--official` | 直接抓取 `github.com/trending` 页面，按周期内**真实新增 star** 排序，显示精确增量（`X stars today/this week/this month`） |
| **全品类模式** | `--category all`（默认） | 覆盖所有语言，支持 `--language` 按语言过滤，自动跨主流语言补采保证多样性 |
| **AI 专榜模式** | `--category ai` | 仅返回 AI / ML / LLM / Agent 方向仓库，按关键词与话题双路检索 |

### 排序维度（API 模式）

| 排序 | 标志 | 说明 |
|------|------|------|
| **累计 star** | `--sort stars`（默认） | 按累计 star 排序，近似官方 trending |
| **日均增速** | `--sort growth` | 按 `stars / 仓库年龄天数` 排序，揪出"年轻但涨得猛"的新爆款 |
| **真实跨天增量** | `--sort velocity` | 基于本地快照库计算真实日增量，首次运行记录基线，后续显示真实 delta |

## 🚀 快速开始

```bash
# 📈 官方真实增星榜（github.com/trending，最权威）
python3 scripts/github_trending.py --official --period weekly
python3 scripts/github_trending.py --official --period daily --language python

# 本周全品类热门 Top 20（默认，按累计 star）
python3 scripts/github_trending.py --period weekly

# 本周 Python 热门
python3 scripts/github_trending.py --period weekly --language python

# 本月 AI/ML/LLM 热门 Top 15
python3 scripts/github_trending.py --period monthly --category ai --limit 15

# 🚀 找出 AI 赛道里"涨得最快"的新仓库（按日均增速）
python3 scripts/github_trending.py --period weekly --category ai --sort growth --limit 15

# 📈 真实跨天 star 增量榜（首次 seed 基线，之后显示真实增量）
python3 scripts/github_trending.py --category ai --sort velocity --limit 15

# 今日全品类，输出 JSON
python3 scripts/github_trending.py --period daily --json
```

## 📋 参数说明

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--period` | `-p` | `weekly` | 时间范围：`daily` / `weekly` / `monthly` |
| `--limit` | `-n` | `20` | 返回项目数量 |
| `--language` | `-l` | 全部 | 编程语言过滤，如 `python`、`go`、`rust` |
| `--category` | `-c` | `all` | `all`=全品类；`ai`=仅 AI/ML/LLM（仅 API 模式） |
| `--sort` | `-s` | `stars` | 排序指标（仅 API 模式）：`stars` / `growth` / `velocity` |
| `--official` | — | 否 | 抓取官方 github.com/trending 页面（真实增星榜） |
| `--token` | `-t` | 环境变量 | GitHub PAT，也可设置 `GITHUB_TOKEN` 环境变量 |
| `--json` | — | 否 | 输出原始 JSON |

## 🔑 提高 API 限额

不带 token 时 GitHub API 限制 10 次/分钟；带 token 可提升到 30 次/分钟。

```bash
export GITHUB_TOKEN=your_personal_access_token
python3 scripts/github_trending.py --category ai
```

## 📁 项目结构

```
github-trending/
├── SKILL.md                    # WorkBuddy 技能定义文件
├── scripts/
│   └── github_trending.py      # 主脚本（纯 Python 标准库）
└── .gitignore
```

## 🛠 技术实现

- **纯 Python 标准库**，无 pip 依赖，仅访问 `api.github.com` 或 `github.com`
- **官方模式**：`urllib` 抓取 `github.com/trending` 页面，正则解析仓库卡片
- **API 模式**：调用 `api.github.com/search/repositories` 搜索 API
- **增速模式**：本地快照库 `trending_snapshot.json` 记录历史 star，计算真实跨天增量

## ❓ 常见问题

<details>
<summary><b>哪种模式最能反映"star 增长快"？</b></summary>

`--official` 模式最权威——它直接呈现 github.com/trending 官方按周期内新增 star 排序的榜单，含精确增量数字。API 模式的 `--sort growth`（年龄折算）/ `--sort velocity`（快照对比）是其补充，优势是可叠加 AI 过滤与任意周期。
</details>

<details>
<summary><b>官方模式提示抓取失败？</b></summary>

多为网络/GitHub 限流。可去掉 `--official` 改用 API 模式（需 `GITHUB_TOKEN` 提额）；或稍后重试。
</details>

<details>
<summary><b>API 模式提示 HTTP 403 / rate limit exceeded？</b></summary>

设置 `GITHUB_TOKEN` 或稍后重试。
</details>

## 📄 License

MIT
