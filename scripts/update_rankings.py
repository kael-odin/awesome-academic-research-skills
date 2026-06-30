#!/usr/bin/env python3
"""Update the academic research skills ranking.

The script intentionally uses only the Python standard library so GitHub
Actions can run it without dependency installation.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import math
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "ranking.json"
DATA_PATH = ROOT / "data" / "rankings.json"
DATA_JS_PATH = ROOT / "data" / "rankings.js"
CSV_PATH = ROOT / "data" / "rankings.csv"
README_PATH = ROOT / "README.md"
HISTORY_DIR = ROOT / "data" / "history"

# How many days of history to retain on disk. Older snapshots are pruned so the
# repo does not grow unboundedly over time.
HISTORY_RETENTION_DAYS = 60
# Window used for the mid-term star delta. A 7-day window smooths out the
# single-day noise that made the previous `star_delta_1d` almost always zero.
DELTA_WINDOW_DAYS = 7


DEFAULT_MIN_STARS = 100

SKILL_TERMS = [
    "skill",
    "skills",
    "agent skill",
    "agent skills",
    "claude code",
    "codex",
    "open code",
    "opencode",
    "mcp",
    "workflow",
    "pipeline",
    "plugin",
    "assistant",
]

STRONG_SKILL_TERMS = [
    "skill",
    "skills",
    "agent skill",
    "agent skills",
    "claude code",
    "codex",
    "open code",
    "opencode",
    "workflow",
    "pipeline",
    "plugin",
]

ACADEMIC_TERMS = [
    "academic",
    "research",
    "paper",
    "papers",
    "literature",
    "survey",
    "review",
    "peer review",
    "scientific",
    "science",
    "arxiv",
    "latex",
    "phd",
    "thesis",
    "dissertation",
    "experiment",
    "experiments",
    "reproducibility",
    "citation",
    "bibliography",
    "manuscript",
    "journal",
    "conference",
    "proofreading",
    "scholar",
    "source validation",
    "科研",
    "论文",
    "学术",
    "文献",
    "投稿",
    "实验",
]

STRONG_ACADEMIC_TERMS = [
    "academic",
    "paper",
    "papers",
    "literature",
    "survey",
    "peer review",
    "scientific",
    "science",
    "arxiv",
    "latex",
    "phd",
    "thesis",
    "dissertation",
    "experiment",
    "experiments",
    "reproducibility",
    "citation",
    "bibliography",
    "manuscript",
    "journal",
    "conference",
    "proofreading",
    "scholar",
    "source validation",
    "autonomous discovery",
    "科研",
    "论文",
    "学术",
    "文献",
    "投稿",
    "实验",
]

HIGH_CONFIDENCE_ACADEMIC_TERMS = [
    "academic",
    "academic research",
    "academic writing",
    "research skill",
    "research skills",
    "scientific agent",
    "ai scientist",
    "paper writing",
    "research paper",
    "academic paper",
    "paper review",
    "paper reproduction",
    "proofreading",
    "literature review",
    "literature survey",
    "peer review",
    "source validation",
    "phd",
    "latex",
    "manuscript",
    "journal",
    "conference",
    "autonomous discovery",
    "科研",
    "论文",
    "学术",
    "文献",
    "投稿",
]

NEGATIVE_TERMS = [
    "leetcode",
    "interview",
    "wallpaper",
    "theme",
    "portfolio",
    "resume",
    "cryptocurrency",
    "crypto",
    "trading bot",
    "trading",
    "quant investment",
    "investment",
    "market analytics",
    "finance application",
    "design alternative",
    "desktop app",
    "prompt engineering guide",
    "curated list of chatgpt prompts",
    "developer-tools",
    "game mod",
    "minecraft",
]

CATEGORIES = [
    {
        "id": "deep-research",
        "zh": "深度研究",
        "en": "Deep Research",
        "keywords": ["deep research", "research agent", "autonomous research", "source validation", "discovery"],
    },
    {
        "id": "paper-writing",
        "zh": "论文写作",
        "en": "Paper Writing",
        "keywords": ["paper writing", "manuscript", "latex", "proofreading", "revise", "abstract", "writing"],
    },
    {
        "id": "literature-review",
        "zh": "文献综述",
        "en": "Literature Review",
        "keywords": ["literature review", "literature survey", "citation", "bibliography", "zotero"],
    },
    {
        "id": "peer-review",
        "zh": "评审反馈",
        "en": "Peer Review",
        "keywords": ["peer review", "reviewer", "feedback", "critique", "referee"],
    },
    {
        "id": "experiment-reproducibility",
        "zh": "实验复现",
        "en": "Experiments",
        "keywords": ["experiment", "experiments", "benchmark", "reproduce", "reproducibility", "evaluation"],
    },
    {
        "id": "discipline-specific",
        "zh": "学科专项",
        "en": "Discipline Specific",
        "keywords": ["economics", "biology", "biotech", "chemistry", "medicine", "phd", "cv", "nlp", "ml"],
    },
    {
        "id": "general-research",
        "zh": "综合研究",
        "en": "General Research",
        "keywords": ["academic", "research", "scientific", "science", "scholar"],
    },
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    # Treat naive timestamps (e.g. bare dates "2026-06-24") as UTC so arithmetic
    # against the aware `now` never fails.
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def date_only(value: str | None) -> str:
    parsed = parse_datetime(value)
    if parsed is None:
        return ""
    return parsed.date().isoformat()


def text_corpus(repo: dict[str, Any]) -> str:
    topics = repo.get("repositoryTopics", {}).get("nodes", [])
    topic_names = []
    for node in topics:
        topic = node.get("topic", {}) if isinstance(node, dict) else {}
        name = topic.get("name")
        if name:
            topic_names.append(name)

    parts = [
        repo.get("nameWithOwner", ""),
        repo.get("name", ""),
        repo.get("description") or "",
        " ".join(topic_names),
    ]
    return " ".join(parts).lower()


def term_hits(corpus: str, terms: list[str]) -> list[str]:
    return [term for term in terms if term.lower() in corpus]


def is_academic_skill_repo(
    repo: dict[str, Any],
    min_stars: int = DEFAULT_MIN_STARS,
    trusted_repositories: set[str] | None = None,
) -> tuple[bool, list[str]]:
    """Return whether a repository is likely an academic/research skill repo.

    The filter is deliberately explicit: a repo needs both a skill/agent signal
    and an academic/research/paper signal. This avoids broad "AI paper" or
    generic "agent" projects dominating the ranking.
    """

    reasons: list[str] = []
    stars = int(repo.get("stargazerCount") or 0)
    if stars < min_stars:
        reasons.append("below_min_stars")

    if repo.get("isArchived"):
        reasons.append("archived")
    if repo.get("isFork"):
        reasons.append("fork")

    corpus = text_corpus(repo)
    skill_hits = term_hits(corpus, SKILL_TERMS)
    strong_skill_hits = term_hits(corpus, STRONG_SKILL_TERMS)
    academic_hits = term_hits(corpus, ACADEMIC_TERMS)
    strong_academic_hits = term_hits(corpus, STRONG_ACADEMIC_TERMS)
    high_confidence_academic_hits = term_hits(corpus, HIGH_CONFIDENCE_ACADEMIC_TERMS)
    negative_hits = term_hits(corpus, NEGATIVE_TERMS)
    trusted_repositories = trusted_repositories or set()
    trusted = repo.get("nameWithOwner") in trusted_repositories

    reasons.extend(skill_hits[:3])
    reasons.extend(academic_hits[:4])
    if trusted:
        reasons.append("trusted_seed")
    if not skill_hits:
        reasons.append("missing_skill_signal")
    if skill_hits and not strong_skill_hits and not trusted:
        reasons.append("missing_strong_skill_signal")
    if academic_hits and not strong_academic_hits and not trusted:
        reasons.append("missing_strong_academic_signal")
    if strong_academic_hits and not high_confidence_academic_hits and not trusted:
        reasons.append("missing_high_confidence_academic_signal")
    if negative_hits:
        reasons.extend([f"negative:{hit}" for hit in negative_hits[:2]])

    accepted = (
        stars >= min_stars
        and not repo.get("isArchived")
        and not repo.get("isFork")
        and bool(skill_hits)
        and (bool(strong_skill_hits) or trusted)
        and bool(academic_hits)
        and (bool(strong_academic_hits) or trusted)
        and (bool(high_confidence_academic_hits) or trusted)
        and not negative_hits
    )
    return accepted, reasons


def classify_repo(repo: dict[str, Any]) -> dict[str, str]:
    corpus = text_corpus(repo)
    best = CATEGORIES[-1]
    best_score = -1
    for category in CATEGORIES:
        score = sum(1 for keyword in category["keywords"] if keyword.lower() in corpus)
        if score > best_score:
            best = category
            best_score = score
    return {"id": best["id"], "zh": best["zh"], "en": best["en"]}


def previous_stars(previous: dict[str, Any] | None) -> int | None:
    if not previous:
        return None
    if "stars" in previous:
        return int(previous["stars"])
    if "stargazerCount" in previous:
        return int(previous["stargazerCount"])
    return None


def compute_trend_score(
    repo: dict[str, Any],
    previous: dict[str, Any] | None,
    now: datetime | None = None,
    star_delta_window: int = 0,
) -> float:
    now = now or utc_now()
    stars = int(repo.get("stargazerCount") or 0)
    old_stars = previous_stars(previous)
    # Prefer the multi-day window delta when available: it is far less noisy
    # than the single-day delta. Fall back to the previous-run delta otherwise.
    star_delta = max(0, star_delta_window) if star_delta_window else (
        max(0, stars - old_stars) if old_stars is not None else 0
    )

    pushed_at = parse_datetime(repo.get("pushedAt"))
    created_at = parse_datetime(repo.get("createdAt"))

    recency_score = 0.0
    if pushed_at:
        days_since_push = max(0.0, (now - pushed_at).total_seconds() / 86400)
        recency_score = max(0.0, 20.0 - min(days_since_push, 90.0) / 4.5)

    new_repo_score = 0.0
    if created_at:
        age_days = max(0.0, (now - created_at).total_seconds() / 86400)
        new_repo_score = max(0.0, 12.0 - min(age_days, 180.0) / 15.0)

    scale_score = math.log10(stars + 1) * 8 if stars > 0 else 0.0
    score = star_delta * 1.2 + recency_score + new_repo_score + scale_score
    return round(score, 2)


def trend_label(star_delta: int, score: float) -> dict[str, str]:
    if star_delta >= 20 or score >= 70:
        return {"id": "hot", "zh": "热门上升", "en": "Hot"}
    if star_delta > 0 or score >= 35:
        return {"id": "rising", "zh": "持续增长", "en": "Rising"}
    return {"id": "steady", "zh": "稳定", "en": "Steady"}


def rank_repositories(
    repos: list[dict[str, Any]],
    min_stars: int = DEFAULT_MIN_STARS,
    previous_snapshot: dict[str, Any] | None = None,
    trusted_repositories: set[str] | None = None,
    window_snapshot: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    previous_snapshot = previous_snapshot or {}
    trusted_repositories = trusted_repositories or set()
    window_snapshot = window_snapshot or {}
    now = now or utc_now()
    ranked: list[dict[str, Any]] = []

    for repo in repos:
        accepted, reasons = is_academic_skill_repo(
            repo,
            min_stars=min_stars,
            trusted_repositories=trusted_repositories,
        )
        if not accepted:
            continue

        name = repo["nameWithOwner"]
        previous = previous_snapshot.get(name, {}) if isinstance(previous_snapshot, dict) else {}
        stars = int(repo.get("stargazerCount") or 0)
        old_stars = previous_stars(previous)
        star_delta_1d = max(0, stars - old_stars) if old_stars is not None else 0

        # 7-day window delta — the primary growth signal shown to users.
        window_prev = window_snapshot.get(name, {}) if isinstance(window_snapshot, dict) else {}
        window_stars = previous_stars(window_prev)
        star_delta_7d = max(0, stars - window_stars) if window_stars is not None else star_delta_1d

        score = compute_trend_score(
            repo,
            previous,
            now=now,
            star_delta_window=star_delta_7d,
        )
        # Trend label is driven by the (less noisy) 7-day delta.
        trend = trend_label(star_delta_7d, score)
        category = classify_repo(repo)
        topics = [
            node.get("topic", {}).get("name")
            for node in repo.get("repositoryTopics", {}).get("nodes", [])
            if node.get("topic", {}).get("name")
        ]

        ranked.append(
            {
                "rank": 0,
                "repo": name,
                "stars": stars,
                "star_delta_1d": star_delta_1d,
                "star_delta_7d": star_delta_7d,
                "trend_score": score,
                "trend": trend,
                "category": category,
                "description": repo.get("description") or "",
                "language": (repo.get("primaryLanguage") or {}).get("name") or repo.get("language") or "",
                "topics": topics,
                "created_date": date_only(repo.get("createdAt")),
                "last_push_date": date_only(repo.get("pushedAt") or repo.get("updatedAt")),
                "url": repo.get("url") or repo.get("html_url") or "",
                "homepage": repo.get("homepageUrl") or repo.get("homepage") or "",
                "precision_signals": sorted(set(reasons)),
            }
        )

    ranked.sort(key=lambda item: (-item["stars"], -item["trend_score"], item["repo"].lower()))
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    return ranked


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    return load_json(path, {})


def load_previous_snapshot(path: Path = DATA_PATH) -> dict[str, Any]:
    data = load_json(path, {})
    items = data.get("items", []) if isinstance(data, dict) else []
    return {item["repo"]: item for item in items if item.get("repo")}


def _history_path(date: datetime) -> Path:
    return HISTORY_DIR / f"{date.date().isoformat()}.json"


def load_history_snapshots() -> dict[str, dict[str, Any]]:
    """Return a mapping of ``YYYY-MM-DD`` -> {repo: item} for every snapshot on disk.

    History snapshots let us compute a multi-day star delta instead of relying
    on a single previous-run value that is almost always identical to the
    current value (which made ``star_delta_1d`` stuck at zero).
    """
    snapshots: dict[str, dict[str, Any]] = {}
    if not HISTORY_DIR.exists():
        return snapshots
    for entry in HISTORY_DIR.glob("*.json"):
        data = load_json(entry, {})
        items = data.get("items", []) if isinstance(data, dict) else []
        snapshots[entry.stem] = {item["repo"]: item for item in items if item.get("repo")}
    return snapshots


def find_window_snapshot(
    history: dict[str, dict[str, Any]],
    today: datetime,
    window_days: int,
) -> dict[str, Any] | None:
    """Find the historical snapshot closest to ``window_days`` ago.

    Tolerates missing days (workflow skipped, run failed) by scanning a few
    days around the target. Returns the repo->item mapping for that day, or
    ``None`` if no snapshot exists within the tolerance band.
    """
    for offset in range(window_days, window_days + 5):
        target = today - timedelta(days=offset)
        key = target.date().isoformat()
        if key in history:
            return history[key]
    return None


def save_history_snapshot(data: dict[str, Any], today: datetime) -> None:
    """Persist today's ranking as a dated snapshot and prune old entries."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_path = _history_path(today)
    # Only write once per day to keep history idempotent under re-runs.
    if not snapshot_path.exists():
        snapshot_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    cutoff = today - timedelta(days=HISTORY_RETENTION_DAYS)
    for entry in HISTORY_DIR.glob("*.json"):
        try:
            entry_date = datetime.fromisoformat(entry.stem).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if entry_date < cutoff:
            entry.unlink(missing_ok=True)


def github_request(path: str, token: str | None, params: dict[str, Any] | None = None) -> dict[str, Any]:
    if path.startswith("https://"):
        url = path
    else:
        url = "https://api.github.com" + path
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "awesome-academic-research-skills-updater",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def rest_to_repo(item: dict[str, Any]) -> dict[str, Any]:
    topics = item.get("topics") or []
    return {
        "nameWithOwner": item["full_name"],
        "name": item.get("name") or item["full_name"].split("/")[-1],
        "description": item.get("description") or "",
        "stargazerCount": item.get("stargazers_count") or 0,
        "createdAt": item.get("created_at"),
        "updatedAt": item.get("updated_at"),
        "pushedAt": item.get("pushed_at"),
        "url": item.get("html_url"),
        "homepageUrl": item.get("homepage"),
        "isArchived": item.get("archived", False),
        "isFork": item.get("fork", False),
        "primaryLanguage": {"name": item.get("language") or ""},
        "repositoryTopics": {"nodes": [{"topic": {"name": topic}} for topic in topics]},
    }


def search_repositories(query: str, min_stars: int, token: str | None) -> list[dict[str, Any]]:
    q = f"{query} stars:>={min_stars} fork:false archived:false"
    try:
        data = github_request(
            "/search/repositories",
            token,
            {
                "q": q,
                "sort": "stars",
                "order": "desc",
                "per_page": 50,
            },
        )
    except urllib.error.HTTPError as error:
        message = error.read().decode("utf-8", errors="replace")
        print(f"warning: search failed for {query!r}: {error.code} {message}", file=sys.stderr)
        return []
    return [rest_to_repo(item) for item in data.get("items", [])]


def fetch_repository(full_name: str, token: str | None) -> dict[str, Any] | None:
    try:
        data = github_request(f"/repos/{full_name}", token)
    except urllib.error.HTTPError as error:
        if error.code != 404:
            message = error.read().decode("utf-8", errors="replace")
            print(f"warning: repository fetch failed for {full_name}: {error.code} {message}", file=sys.stderr)
        return None
    return rest_to_repo(data)


def collect_repositories(config: dict[str, Any], token: str | None) -> list[dict[str, Any]]:
    min_stars = int(config.get("min_stars", DEFAULT_MIN_STARS))
    repos: dict[str, dict[str, Any]] = {}

    for full_name in config.get("seed_repositories", []):
        repo = fetch_repository(full_name, token)
        if repo:
            repos[repo["nameWithOwner"]] = repo
        time.sleep(0.15)

    for query in config.get("search_queries", []):
        for repo in search_repositories(query, min_stars, token):
            repos[repo["nameWithOwner"]] = repo
        time.sleep(1.8)

    return list(repos.values())


def markdown_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def truncate(value: str, limit: int) -> str:
    clean = " ".join((value or "").split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"


def agent_badge(corpus: str) -> str:
    """Infer which coding agent a repository targets from its text corpus."""
    badges = []
    if "claude code" in corpus or "claude-code" in corpus or "claude code skill" in corpus:
        badges.append("Claude")
    if "codex" in corpus:
        badges.append("Codex")
    if "opencode" in corpus or "open code" in corpus:
        badges.append("OpenCode")
    if "mcp" in corpus:
        badges.append("MCP")
    return "/".join(badges) if badges else "通用"


def is_newcomer(item: dict[str, Any], window_snapshot: dict[str, Any] | None) -> bool:
    """A repo is a newcomer if it was not in the 7-day-ago snapshot."""
    if not window_snapshot:
        return False
    return item["repo"] not in window_snapshot


def render_readme(data: dict[str, Any], window_snapshot: dict[str, Any] | None = None) -> str:
    items = data["items"]
    metadata = data["metadata"]
    top_rows = items[:50]
    category_counts: dict[str, int] = {cat["id"]: 0 for cat in CATEGORIES}
    category_labels = {cat["id"]: cat["zh"] for cat in CATEGORIES}
    for item in items:
        category_counts[item["category"]["id"]] = category_counts.get(item["category"]["id"], 0) + 1

    rows = []
    for item in top_rows:
        repo_link = f"[{markdown_escape(item['repo'])}]({item['url']})"
        delta_7d = item.get("star_delta_7d", 0)
        delta_str = f"+{delta_7d}" if delta_7d else "0"
        trend = f"{item['trend']['zh']} (7d:{delta_str})"
        agent = agent_badge(f"{item['repo']} {item['description']} {' '.join(item.get('topics') or [])}".lower())
        rows.append(
            "| {rank} | {repo} | {stars:,} | {trend} | {category} | {agent} | {desc} | {date} |".format(
                rank=item["rank"],
                repo=repo_link,
                stars=item["stars"],
                trend=markdown_escape(trend),
                category=markdown_escape(item["category"]["zh"]),
                agent=markdown_escape(agent),
                desc=markdown_escape(truncate(item["description"], 90)),
                date=item["last_push_date"],
            )
        )

    # Category summary in the fixed order defined by CATEGORIES, including
    # zero-count categories so the overview always adds up to the total.
    category_summary = " · ".join(
        f"{category_labels[cat_id]} {category_counts.get(cat_id, 0)}"
        for cat_id in category_counts
    )

    # Newcomers: repos that appeared since the 7-day-ago snapshot.
    newcomers = [item for item in items if is_newcomer(item, window_snapshot)]
    newcomers_block = ""
    if newcomers:
        newcomer_lines = []
        for item in newcomers[:10]:
            newcomer_lines.append(
                f"- **[{markdown_escape(item['repo'])}]({item['url']})** — {markdown_escape(truncate(item['description'], 80))} ({item['stars']:,} ⭐, {item['category']['zh']})"
            )
        newcomers_block = (
            "\n## 本周新收录\n\n"
            "近 7 天新进入榜单的仓库：\n\n"
            + "\n".join(newcomer_lines)
            + "\n"
        )

    return f"""# Awesome Academic Research Skills

> 面向中文用户的学术论文与科研 Agent Skill 每日排行榜。自动搜索、过滤并排名 GitHub 上与论文写作、文献综述、深度研究、评审反馈、实验复现相关的 Skill / Agent / Workflow 仓库。

[![Last update](https://img.shields.io/badge/updated-{metadata['generated_at'][:10]}-0f766e)](#今日榜单)
[![Repositories](https://img.shields.io/badge/repositories-{metadata['total']}-2563eb)](#今日榜单)
[![Min stars](https://img.shields.io/badge/min%20stars-{metadata['min_stars']}-334155)](#收录标准)
[![License: MIT](https://img.shields.io/badge/license-MIT-22c55e)](LICENSE)
[![Auto update](https://img.shields.io/badge/auto%20update-daily-6366f1)](.github/workflows/update-rankings.yml)

[English](#english) · [可视化页面](https://kael-odin.github.io/awesome-academic-research-skills/) · [JSON](data/rankings.json) · [CSV](data/rankings.csv) · [排名方法](docs/methodology.md) · [贡献指南](CONTRIBUTING.md)

## 项目特色

- 🔄 **每日自动更新** — GitHub Actions 每天 02:20 UTC 运行，自动搜索、过滤、排名并提交。
- 🎯 **精准双重信号过滤** — 必须同时命中"Skill/Agent/Workflow"与"Academic/Research/Paper"信号，挡住泛 AI 项目。
- 📈 **7 天趋势窗口** — 基于历史快照计算一周 Stars 增长，告别单日抖动导致的"全稳定"假象。
- 🆕 **本周新收录** — 自动识别近 7 天新进入榜单的仓库。
- 🏷️ **适用 Agent 标签** — 推断每个仓库面向 Claude Code / Codex / OpenCode / MCP。
- 🌐 **双语可视化** — 中文优先，支持英文切换、搜索、分类筛选与多维度排序。
- 📦 **机器可读** — 提供 JSON / CSV 数据文件，方便二次开发与订阅。

## 今日榜单

- 更新时间：`{metadata['generated_at']}`
- 收录门槛：GitHub Stars ≥ `{metadata['min_stars']}`，排除 fork、归档仓库和明显非学术项目。
- 精准规则：必须同时命中 Skill/Agent/Workflow 信号 **和** Academic/Research/Paper 信号。
- 趋势指标：基于近 7 天新增 Stars、最近 push 时间、新仓库加权和总体 Stars 规模综合计算。
- 分类概览：{category_summary or "暂无数据"}

| # | 仓库 | Stars | 趋势 | 分类 | 适用 Agent | 简介 | 最近更新 |
|---:|---|---:|---|---|---|---|---|
{chr(10).join(rows) if rows else "| - | - | - | - | - | - | 暂无符合条件的仓库 | - |"}
{newcomers_block}
## 分类标准

| 分类 | 说明 |
|---|---|
| 深度研究 | 多阶段 research agent、source validation、autonomous discovery、deep research workflow |
| 论文写作 | 论文构思、写作、润色、LaTeX、proofreading、revision |
| 文献综述 | literature survey、citation、bibliography、source collection |
| 评审反馈 | peer review、reviewer feedback、critique、referee report |
| 实验复现 | experiment design、benchmark、evaluation、reproducibility |
| 学科专项 | 面向经济学、生物、医学、ML/CV/NLP 等具体领域 |
| 综合研究 | 覆盖多个科研流程的通用 research skill |

## 使用方式

1. 浏览上方榜单，优先查看 Stars、趋势（7 天增量）和分类。
2. 打开 [可视化页面](https://kael-odin.github.io/awesome-academic-research-skills/) 使用搜索、分类筛选、排序和中英文切换。
3. 机器读取请使用 [data/rankings.json](data/rankings.json) 或 [data/rankings.csv](data/rankings.csv)。
4. 如需推荐新仓库，提交 Issue（附仓库链接和一句推荐理由）或直接 PR 修改 `config/ranking.json`。

## 收录标准

- 仓库必须明确服务学术、科研、论文、文献、评审或实验复现场景。
- 仓库必须具备 Skill、Agent、Workflow、Claude Code、Codex、OpenCode 或类似可复用工作流信号。
- 默认最低门槛为 100 Stars（可在 `config/ranking.json` 调整）。
- fork、归档仓库、明显非学术用途仓库不会收录。

## 自动更新

GitHub Actions 每天运行一次 [.github/workflows/update-rankings.yml](.github/workflows/update-rankings.yml)：

- 使用 GitHub Search API 搜索候选仓库 + 拉取种子仓库元数据。
- 应用精准过滤、分类和趋势计算（基于 `data/history/` 下的每日历史快照）。
- 更新 `README.md`、`data/rankings.json`、`data/rankings.csv`、`data/rankings.js`。
- 保存当日快照到 `data/history/YYYY-MM-DD.json`（保留近 60 天）。
- 如数据发生变化，自动提交到 `main`。

手动本地更新：

```bash
python scripts/update_rankings.py
python -m unittest discover -s tests -v
```

## English

**Awesome Academic Research Skills** is a daily-updated ranking of GitHub repositories that provide academic, paper-writing, literature-review, deep-research, peer-review, and experiment-reproducibility skills for AI coding agents (Claude Code, Codex, OpenCode, …).

The ranking requires **both** a skill/agent/workflow signal **and** an academic/research/paper signal. Low-star, archived, forked, and clearly unrelated repositories are excluded. The trend column shows 7-day star growth. A bilingual static dashboard is available at the link above.

## License

MIT
"""


def render_csv(items: list[dict[str, Any]]) -> None:
    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "rank",
                "repo",
                "stars",
                "star_delta_1d",
                "star_delta_7d",
                "trend_score",
                "trend",
                "category",
                "description",
                "last_push_date",
                "url",
            ],
        )
        writer.writeheader()
        for item in items:
            writer.writerow(
                {
                    "rank": item["rank"],
                    "repo": item["repo"],
                    "stars": item["stars"],
                    "star_delta_1d": item["star_delta_1d"],
                    "star_delta_7d": item["star_delta_7d"],
                    "trend_score": item["trend_score"],
                    "trend": item["trend"]["en"],
                    "category": item["category"]["en"],
                    "description": item["description"],
                    "last_push_date": item["last_push_date"],
                    "url": item["url"],
                }
            )


def render_data_js(data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    return f"window.ACADEMIC_SKILLS_RANKINGS = {payload};\n"


def write_outputs(data: dict[str, Any], window_snapshot: dict[str, Any] | None = None) -> None:
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    DATA_JS_PATH.write_text(render_data_js(data), encoding="utf-8")
    render_csv(data["items"])
    README_PATH.write_text(render_readme(data, window_snapshot=window_snapshot), encoding="utf-8")


def build_dataset(config: dict[str, Any], repos: list[dict[str, Any]]) -> dict[str, Any]:
    min_stars = int(config.get("min_stars", DEFAULT_MIN_STARS))
    now = utc_now()
    previous = load_previous_snapshot()
    history = load_history_snapshots()
    window_snapshot = find_window_snapshot(history, now, DELTA_WINDOW_DAYS)
    trusted_repositories = set(config.get("seed_repositories", []))
    items = rank_repositories(
        repos,
        min_stars=min_stars,
        previous_snapshot=previous,
        trusted_repositories=trusted_repositories,
        window_snapshot=window_snapshot,
        now=now,
    )
    max_results = int(config.get("max_results", 100))
    items = items[:max_results]
    for index, item in enumerate(items, start=1):
        item["rank"] = index

    generated_at = now.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    data = {
        "metadata": {
            "generated_at": generated_at,
            "min_stars": min_stars,
            "total": len(items),
            "source": "GitHub REST Search API",
            "ranking": "stars_desc_then_trend_score",
            "trend_window_days": DELTA_WINDOW_DAYS,
            "history_retention_days": HISTORY_RETENTION_DAYS,
        },
        "items": items,
    }

    # Persist today's snapshot so future runs can compute the 7-day delta.
    save_history_snapshot(data, now)
    return data, window_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="Update academic research skill rankings")
    parser.add_argument("--config", default=str(CONFIG_PATH), help="Path to ranking config JSON")
    parser.add_argument("--offline-fixture", help="Use a local JSON list of repository objects instead of GitHub API")
    args = parser.parse_args()

    config = load_config(Path(args.config))
    if args.offline_fixture:
        repos = load_json(Path(args.offline_fixture), [])
    else:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        repos = collect_repositories(config, token)

    data, window_snapshot = build_dataset(config, repos)
    write_outputs(data, window_snapshot=window_snapshot)
    print(f"updated {len(data['items'])} repositories at {data['metadata']['generated_at']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
