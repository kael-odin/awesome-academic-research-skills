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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "ranking.json"
DATA_PATH = ROOT / "data" / "rankings.json"
DATA_JS_PATH = ROOT / "data" / "rankings.js"
CSV_PATH = ROOT / "data" / "rankings.csv"
README_PATH = ROOT / "README.md"


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
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


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
) -> float:
    now = now or utc_now()
    stars = int(repo.get("stargazerCount") or 0)
    old_stars = previous_stars(previous)
    star_delta = max(0, stars - old_stars) if old_stars is not None else 0

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
) -> list[dict[str, Any]]:
    previous_snapshot = previous_snapshot or {}
    trusted_repositories = trusted_repositories or set()
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
        star_delta = max(0, stars - old_stars) if old_stars is not None else 0
        score = compute_trend_score(repo, previous)
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
                "star_delta_1d": star_delta,
                "trend_score": score,
                "trend": trend_label(star_delta, score),
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


def render_readme(data: dict[str, Any]) -> str:
    items = data["items"]
    metadata = data["metadata"]
    top_rows = items[:50]
    category_counts: dict[str, int] = {}
    for item in items:
        label = item["category"]["zh"]
        category_counts[label] = category_counts.get(label, 0) + 1

    rows = []
    for item in top_rows:
        repo_link = f"[{markdown_escape(item['repo'])}]({item['url']})"
        delta = f"+{item['star_delta_1d']}" if item["star_delta_1d"] else "0"
        trend = f"{item['trend']['zh']} ({delta})"
        rows.append(
            "| {rank} | {repo} | {stars:,} | {trend} | {category} | {desc} | {date} |".format(
                rank=item["rank"],
                repo=repo_link,
                stars=item["stars"],
                trend=markdown_escape(trend),
                category=markdown_escape(item["category"]["zh"]),
                desc=markdown_escape(truncate(item["description"], 110)),
                date=item["last_push_date"],
            )
        )

    category_summary = "、".join(f"{name} {count}" for name, count in sorted(category_counts.items()))

    return f"""# Awesome Academic Research Skills

面向中文用户的学术论文与科研 Agent Skill 排行仓库。每天自动搜索、过滤并更新 GitHub 上与论文写作、文献综述、深度研究、评审反馈、实验复现相关的 Skill/Agent/Workflow 仓库。

[English](#english) · [数据文件](data/rankings.json) · [CSV](data/rankings.csv) · [可视化页面](https://kael-odin.github.io/awesome-academic-research-skills/)

![Last update](https://img.shields.io/badge/updated-{metadata['generated_at'][:10]}-0f766e)
![Min stars](https://img.shields.io/badge/min%20stars-{metadata['min_stars']}-334155)
![Repositories](https://img.shields.io/badge/repositories-{metadata['total']}-2563eb)

## 今日榜单

- 更新时间：`{metadata['generated_at']}`
- 收录门槛：GitHub Stars >= `{metadata['min_stars']}`，排除 fork、归档仓库和明显非学术项目。
- 精准规则：必须同时命中 Skill/Agent/Workflow 信号和 Academic/Research/Paper 信号。
- 趋势指标：综合最近新增 stars、最近 push 时间、新仓库加权和总体 stars 规模。
- 分类概览：{category_summary or "暂无数据"}

| # | 仓库 | Stars | 趋势 | 分类 | 简介 | 最近更新 |
|---:|---|---:|---|---|---|---|
{chr(10).join(rows) if rows else "| - | - | - | - | - | 暂无符合条件的仓库 | - |"}

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

1. 浏览上方榜单，优先查看 Stars、趋势和分类。
2. 打开 [可视化页面](https://kael-odin.github.io/awesome-academic-research-skills/) 使用搜索、分类筛选、排序和中英文切换。
3. 机器读取请使用 [data/rankings.json](data/rankings.json) 或 [data/rankings.csv](data/rankings.csv)。
4. 如需推荐新仓库，提交 Issue 或 PR；仓库需要明确服务学术/科研/论文场景，并达到最低星标门槛。

## 自动更新

GitHub Actions 每天运行一次 `.github/workflows/update-rankings.yml`：

- 使用 GitHub Search API 搜索候选仓库。
- 拉取种子仓库和新候选仓库元数据。
- 应用精准过滤、分类和趋势计算。
- 更新 `README.md`、`data/rankings.json`、`data/rankings.csv`、`data/rankings.js`。
- 如数据发生变化，自动提交到 `main`。

手动本地更新：

```bash
python scripts/update_rankings.py
python -m unittest discover -s tests -v
```

## English

Awesome Academic Research Skills is a daily updated ranking of GitHub repositories that provide academic, paper-writing, literature-review, deep-research, peer-review, and experiment-reproducibility skills for AI coding agents and research agents.

The ranking requires both a skill/agent/workflow signal and an academic/research/paper signal. Low-star, archived, forked, and clearly unrelated repositories are excluded. The static dashboard supports Chinese and English language switching.

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


def write_outputs(data: dict[str, Any]) -> None:
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    DATA_JS_PATH.write_text(render_data_js(data), encoding="utf-8")
    render_csv(data["items"])
    README_PATH.write_text(render_readme(data), encoding="utf-8")


def build_dataset(config: dict[str, Any], repos: list[dict[str, Any]]) -> dict[str, Any]:
    min_stars = int(config.get("min_stars", DEFAULT_MIN_STARS))
    previous = load_previous_snapshot()
    trusted_repositories = set(config.get("seed_repositories", []))
    items = rank_repositories(
        repos,
        min_stars=min_stars,
        previous_snapshot=previous,
        trusted_repositories=trusted_repositories,
    )
    max_results = int(config.get("max_results", 100))
    items = items[:max_results]
    for index, item in enumerate(items, start=1):
        item["rank"] = index

    generated_at = utc_now().replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {
        "metadata": {
            "generated_at": generated_at,
            "min_stars": min_stars,
            "total": len(items),
            "source": "GitHub REST Search API",
            "ranking": "stars_desc_then_trend_score",
        },
        "items": items,
    }


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

    data = build_dataset(config, repos)
    write_outputs(data)
    print(f"updated {len(data['items'])} repositories at {data['metadata']['generated_at']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
