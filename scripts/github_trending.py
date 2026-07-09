#!/usr/bin/env python3
"""github-trending — combined GitHub trending fetcher with star growth/velocity.

Two data sources:
- --official : scrape the REAL github.com/trending page (ranks by stars gained in the
               window; each card shows exact "X stars today/this week/this month").
- default    : GitHub Search API — full-spectrum (all languages, --language filter) and
               AI-focused (--category ai) modes, plus --sort growth/velocity metrics.

Pure stdlib. Only calls https://api.github.com or https://github.com.
"""

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
SNAPSHOT_PATH = os.path.join(SKILL_DIR, "trending_snapshot.json")

PERIOD_DAYS = {"daily": 1, "weekly": 7, "monthly": 30}
PERIOD_LABELS = {"daily": "今日热门", "weekly": "本周热门", "monthly": "本月热门"}
PERIOD_EMOJI = {"daily": "🔥", "weekly": "📊", "monthly": "📈"}

# Languages used to diversify results when no language filter is given (from trending-cn)
LANGUAGES = [
    "", "python", "javascript", "typescript", "go", "rust",
    "java", "cpp", "c", "swift", "kotlin", "ruby", "php",
]

# AI keyword + topic filters (from github-ai-trends)
AI_KEYWORDS = ["ai", "llm", "gpt", "agent", "transformer", "diffusion", "rag", "ml"]
AI_TOPICS = ["artificial-intelligence", "llm", "generative-ai", "ai-agent"]


def gh_search(query, per_page=30, token=None):
    params = urllib.parse.urlencode({
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": per_page,
    })
    url = f"https://api.github.com/search/repositories?{params}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "github-trending/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read()).get("items", [])
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[WARN] GitHub API HTTP {e.code}: {body[:200]}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"[WARN] GitHub API error: {e}", file=sys.stderr)
        return []


def fetch_official(period="weekly", limit=25, language="", token=None):
    """Scrape the official github.com/trending page — the REAL star-increment leaderboard.

    The page ranks repos by stars gained in the selected window (daily/weekly/monthly) and
    shows the exact increment on each card ("X stars today/this week/this month").
    """
    base = "https://github.com/trending"
    if language:
        base += f"/{urllib.parse.quote(language)}"
    base += f"?since={period}"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; github-trending/1.0)",
        "Accept": "text/html",
    }
    req = urllib.request.Request(base, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[WARN] 官方 trending 页抓取失败: {e}", file=sys.stderr)
        return []

    delta_label = {"daily": "today", "weekly": "this week", "monthly": "this month"}.get(period, period)
    parts = re.split(r'<article class="Box-row">', html)
    repos = []
    for art in parts[1:]:
        m = re.search(r'<h2[^>]*>\s*<a[^>]*href="/([^"]+)"', art)
        if not m:
            continue
        full = m.group(1).strip("/")
        if full.count("/") != 1:
            continue
        repo = {
            "full_name": full,
            "html_url": "https://github.com/" + full,
            "description": "",
            "stargazers_count": 0,
            "forks_count": 0,
            "language": None,
            "topics": [],
            "created_at": None,
            "delta_stars": None,
            "delta_label": delta_label,
        }
        dm = re.search(r'<p class="col-9[^"]*">(.*?)</p>', art, re.S)
        if dm:
            repo["description"] = re.sub(r'<[^>]+>', "", dm.group(1)).strip()
        sm = re.search(r'/stargazers"[^>]*>.*?([\d,]+)\s*</a>', art, re.S)
        if sm:
            repo["stargazers_count"] = int(sm.group(1).replace(",", ""))
        fm = re.search(r'/forks"[^>]*>.*?([\d,]+)\s*</a>', art, re.S)
        if fm:
            repo["forks_count"] = int(fm.group(1).replace(",", ""))
        lm = re.search(r'<span itemprop="programmingLanguage">([^<]+)</span>', art)
        if lm:
            repo["language"] = lm.group(1).strip()
        dm2 = re.search(r'([\d,]+)\s+stars\s+' + re.escape(delta_label), art)
        if dm2:
            repo["delta_stars"] = int(dm2.group(1).replace(",", ""))
        repos.append(repo)
    return repos[:limit]


def fetch_trending(period="weekly", limit=20, language="", category="all", token=None, sort="stars"):
    days = PERIOD_DAYS.get(period, 7)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    seen = set()
    results = []

    # When sorting by growth/velocity we need a larger candidate pool (more ages)
    mult = 4 if sort in ("growth", "velocity") else 2
    lang_filter = f" language:{language}" if language else ""

    if category == "ai":
        for kw in AI_KEYWORDS:
            if len(results) >= limit * mult:
                break
            q = f"{kw} in:name,description pushed:>={since} stars:>=10{lang_filter}"
            for item in gh_search(q, per_page=30, token=token):
                if item["full_name"] not in seen:
                    seen.add(item["full_name"])
                    results.append(item)
        for topic in AI_TOPICS:
            if len(results) >= limit * mult * 2:
                break
            q = f"topic:{topic} pushed:>={since} stars:>=10{lang_filter}"
            for item in gh_search(q, per_page=30, token=token):
                if item["full_name"] not in seen:
                    seen.add(item["full_name"])
                    results.append(item)
    else:
        q = f"pushed:>={since} stars:>=10{lang_filter}"
        for item in gh_search(q, per_page=min(limit * mult, 100), token=token):
            if item["full_name"] not in seen:
                seen.add(item["full_name"])
                results.append(item)
        if not language and len(results) < limit * mult:
            for lang in LANGUAGES[1:6]:
                if len(results) >= limit * mult * 2:
                    break
                q = f"pushed:>={since} stars:>=50 language:{lang}"
                for item in gh_search(q, per_page=20, token=token):
                    if item["full_name"] not in seen:
                        seen.add(item["full_name"])
                        results.append(item)

    return results  # caller sorts by metric


def repo_age_days(repo):
    try:
        ca = datetime.fromisoformat(repo["created_at"].replace("Z", "+00:00"))
        return max(1, (datetime.now(timezone.utc) - ca).days)
    except Exception:
        return 1


def stars_per_day(repo):
    return repo.get("stargazers_count", 0) / repo_age_days(repo)


def load_snapshot():
    try:
        with open(SNAPSHOT_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_snapshot(snap):
    try:
        with open(SNAPSHOT_PATH, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] 快照保存失败: {e}", file=sys.stderr)


def update_snapshot(snap, repos):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for r in repos:
        snap[r["full_name"]] = {"stars": r.get("stargazers_count", 0), "ts": now}
    save_snapshot(snap)


def velocity_info(repo, snap):
    prev = snap.get(repo["full_name"])
    if not prev:
        return None
    try:
        pts = datetime.fromisoformat(prev["ts"].replace("Z", "+00:00"))
    except Exception:
        return None
    days = (datetime.now(timezone.utc) - pts).total_seconds() / 86400.0
    if days <= 0:
        return None
    delta = repo.get("stargazers_count", 0) - prev.get("stars", 0)
    per_day = delta / days
    return {"delta": delta, "days": days, "per_day": per_day, "prev": prev.get("stars", 0)}


def fmt_num(n):
    return f"{n/1000:.1f}k" if n >= 1000 else str(n)


def format_output(repos, period, category, metric, snap):
    label = PERIOD_LABELS.get(period, period)
    emoji = PERIOD_EMOJI.get(period, "📊")
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M CST")
    cat_tag = " · AI" if category == "ai" else ""
    metric_tag = {"stars": "", "growth": " · 按日均增速", "velocity": " · 按真实star增量",
                  "official": " · 官方增星榜"}[metric]
    lines = [
        f"{emoji} **GitHub Trending — {label}{cat_tag}{metric_tag}**",
        f"数据时间：{now}  |  共 {len(repos)} 个项目",
        "",
    ]
    if metric == "velocity":
        has_hist = any(velocity_info(r, snap) for r in repos)
        if not has_hist:
            lines.append("> ⚠️ 首次运行：已记录 star 基线，下次运行（或明天的定时推送）将显示真实跨天 star 增量。")
            lines.append("")
    if metric == "official":
        lines.append("> 来源：github.com/trending（按周期内**真实新增 star** 排序，官方权威；不支持 AI 过滤，可用 --language）")
        lines.append("")
    for i, r in enumerate(repos, 1):
        stars = fmt_num(r.get("stargazers_count", 0))
        forks = fmt_num(r.get("forks_count", 0))
        lang = r.get("language") or "N/A"
        desc = r.get("description") or ""
        if len(desc) > 96:
            desc = desc[:93] + "..."
        name = r["full_name"]
        url = r["html_url"]
        topics = r.get("topics", [])[:3]
        topic_str = "  `" + "` `".join(topics) + "`" if topics else ""
        meta = f"⭐ {stars}  🍴 {forks}  🔤 {lang}{topic_str}"
        if metric == "growth":
            spd = stars_per_day(r)
            age = repo_age_days(r)
            meta += f"  🚀 ≈{fmt_num(int(spd))}/天（年龄 {age}天）"
        elif metric == "velocity":
            vi = velocity_info(r, snap)
            if vi:
                sign = "+" if vi["delta"] >= 0 else ""
                meta += f"  📈 {sign}{vi['delta']}⭐ / {vi['days']:.1f}天 (≈{fmt_num(int(vi['per_day']))}/天)"
            else:
                meta += "  📌 基线已记录"
        elif metric == "official":
            d = r.get("delta_stars")
            if d is not None:
                meta += f"  📈 +{d:,} stars {r.get('delta_label', '')}"
        lines.append(f"**#{i}** [{name}]({url})")
        lines.append(meta)
        if desc:
            lines.append(f"> {desc}")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="GitHub Trending — 官方增星榜 / 全品类 / AI 专榜 + 增速指标")
    parser.add_argument("--period", "-p", choices=["daily", "weekly", "monthly"],
                        default="weekly", help="时间范围（默认 weekly）")
    parser.add_argument("--limit", "-n", type=int, default=20, help="返回数量（默认 20）")
    parser.add_argument("--language", "-l", default="",
                        help="编程语言过滤，如 python/javascript/go（默认不过滤）")
    parser.add_argument("--category", "-c", choices=["all", "ai"], default="all",
                        help="all=全品类；ai=仅 AI/ML/LLM（默认 all，官方模式忽略此项）")
    parser.add_argument("--sort", "-s", choices=["stars", "growth", "velocity"],
                        default="stars",
                        help="排序指标(非官方模式)：stars=累计star(默认)；growth=日均增速；velocity=真实跨天增量")
    parser.add_argument("--official", action="store_true",
                        help="直接抓取官方 github.com/trending 页面（真实增星榜；支持 --language/--period，忽略 --category）")
    parser.add_argument("--token", "-t", default=os.environ.get("GITHUB_TOKEN", ""),
                        help="GitHub PAT 或设置 GITHUB_TOKEN 环境变量")
    parser.add_argument("--json", action="store_true", help="输出原始 JSON")
    args = parser.parse_args()

    # ---- Official github.com/trending mode (real star-increment leaderboard) ----
    if args.official:
        if args.category == "ai":
            print("[WARN] 官方 trending 页不支持 AI 过滤，已忽略 --category ai；用 --language 按语言过滤",
                  file=sys.stderr)
        print(f"[INFO] 抓取官方 github.com/trending (period={args.period}, language={args.language or '全部'})...",
              file=sys.stderr)
        repos = fetch_official(args.period, args.limit, args.language)
        if not repos:
            print("[ERROR] 官方页抓取失败（网络/GitHub 限流）；可去掉 --official 改用 Search API 模式",
                  file=sys.stderr)
            sys.exit(1)
        if args.sort == "stars":
            repos.sort(key=lambda r: r.get("stargazers_count", 0), reverse=True)
        repos = repos[:args.limit]
        if args.json:
            output = [{
                "rank": i,
                "name": r["full_name"],
                "url": r["html_url"],
                "description": r.get("description"),
                "stars": r.get("stargazers_count", 0),
                "forks": r.get("forks_count", 0),
                "language": r.get("language"),
                "delta_stars": r.get("delta_stars"),
                "delta_label": r.get("delta_label"),
            } for i, r in enumerate(repos, 1)]
            json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
        else:
            print(format_output(repos, args.period, "all", "official", {}))
        return

    # ---- Search API mode (full-spectrum / AI, with growth & velocity) ----
    print(f"[INFO] 正在获取 GitHub trending (period={args.period}, category={args.category}, sort={args.sort})...",
          file=sys.stderr)
    repos = fetch_trending(args.period, args.limit, args.language, args.category, args.token, args.sort)
    if not repos:
        print("[ERROR] 未获取到数据，请检查网络或 GitHub API 限额", file=sys.stderr)
        sys.exit(1)
    print(f"[INFO] 获取到 {len(repos)} 个候选", file=sys.stderr)

    # Load snapshot (OLD values, used for velocity delta vs previous run)
    snap = load_snapshot()

    # Sort by metric (velocity uses OLD snapshot)
    if args.sort == "growth":
        repos.sort(key=stars_per_day, reverse=True)
    elif args.sort == "velocity":
        def vkey(r):
            vi = velocity_info(r, snap)
            return vi["per_day"] if vi else -1
        repos.sort(key=vkey, reverse=True)
    else:
        repos.sort(key=lambda r: r.get("stargazers_count", 0), reverse=True)

    repos = repos[:args.limit]

    if args.json:
        output = [{
            "rank": i,
            "name": r["full_name"],
            "url": r["html_url"],
            "description": r.get("description"),
            "stars": r.get("stargazers_count", 0),
            "forks": r.get("forks_count", 0),
            "language": r.get("language"),
            "topics": r.get("topics", []),
            "created_at": r.get("created_at"),
            "stars_per_day": round(stars_per_day(r), 1),
            "velocity": velocity_info(r, snap),
        } for i, r in enumerate(repos, 1)]
        json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
    else:
        print(format_output(repos, args.period, args.category, args.sort, snap))

    # Persist NEW snapshot AFTER output (so next run computes real delta)
    if args.sort == "velocity":
        update_snapshot(snap, repos)


if __name__ == "__main__":
    main()
