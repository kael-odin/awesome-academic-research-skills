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
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "ranking.json"
DATA_PATH = ROOT / "data" / "rankings.json"
DATA_JS_PATH = ROOT / "data" / "rankings.js"
HISTORY_JS_PATH = ROOT / "data" / "history.js"
CSV_PATH = ROOT / "data" / "rankings.csv"
README_PATH = ROOT / "README.md"
HISTORY_DIR = ROOT / "data" / "history"
REPORTS_DIR = ROOT / "reports"
SITEMAP_PATH = ROOT / "sitemap.xml"
FEED_PATH = ROOT / "feed.xml"
OG_COVER_PATH = ROOT / "assets" / "og-cover.svg"
OG_COVER_PNG_PATH = ROOT / "assets" / "og-cover.png"

# Canonical public URL (GitHub Pages). Used for sitemap / RSS / Open Graph.
SITE_URL = "https://kael-odin.github.io/awesome-academic-research-skills"

# How many days of history to retain on disk. Older snapshots are pruned so the
# repo does not grow unboundedly over time.
HISTORY_RETENTION_DAYS = 60
# Window used for the mid-term star delta. A 7-day window smooths out the
# single-day noise that made the previous `star_delta_1d` almost always zero.
DELTA_WINDOW_DAYS = 7
# Longer-horizon window used for the auxiliary `star_delta_30d` and the
# sparkline series. Kept inside the retention window so the data exists.
LONG_WINDOW_DAYS = 30


DEFAULT_MIN_STARS = 100

# Repositories never listed in the ranking itself. The meta-repository must
# stay out of its own leaderboard (its description matches every signal by
# construction), while still being fetched normally when listed as a seed.
DEFAULT_EXCLUDED_REPOSITORIES = [
    "kael-odin/awesome-academic-research-skills",
]

SKILL_TERMS = [
    "skill",
    "skills",
    "agent skill",
    "agent skills",
    "claude code",
    "claude-skill",
    "claude-skills",
    "claude skill",
    "claude skills",
    "codex",
    "open code",
    "opencode",
    "mcp",
    "workflow",
    "pipeline",
    "plugin",
    "assistant",
    # Mainstream AI coding agent / editor names that signal "this is a
    # reusable agent capability" rather than a generic library.
    "cursor",
    "gemini",
    "copilot",
    "antigravity",
    "auggie",
    "roo",
    "cline",
    "continue.dev",
    "agent skill standard",
    "agent skills standard",
]

STRONG_SKILL_TERMS = [
    "skill",
    "skills",
    "agent skill",
    "agent skills",
    "claude code",
    "claude-skill",
    "claude-skills",
    "claude skill",
    "claude skills",
    "codex",
    "open code",
    "opencode",
    "mcp",
    "workflow",
    "plugin",
    "cursor rules",
    "gemini",
    "antigravity",
    "agent skill standard",
    "agent skills standard",
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
    # Retrieval / reasoning / publishing-flow signals that still indicate an
    # academic context when combined with a skill signal.
    "retrieval",
    "grounding",
    "reasoning",
    "systematic review",
    "meta-analysis",
    "preprint",
    "doi",
    "bibtex",
    "referee",
    "学者",
    "科研",
    "论文",
    "学术",
    "文献",
    "投稿",
    "实验",
    "综述",
    "复现",
    "审稿",
    "引用",
    "课题",
    "基金",
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
    "systematic review",
    "meta-analysis",
    "preprint",
    "doi",
    "bibtex",
    "referee",
    "科研",
    "论文",
    "学术",
    "文献",
    "投稿",
    "实验",
    "综述",
    "复现",
    "审稿",
    "引用",
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
    "screensaver",
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
    "collection of ai agent research papers",
    "curated list of papers",
    "awesome-ai-agent-papers",
    "z-library",
    "影子图书馆",
    "teach-yourself-research",
    "develop basic research skills",
    "developer-tools",
    "game mod",
    "minecraft",
    "game",
    "cheatsheet",
    "flashcard",
    "recipe",
    "fitness",
    "meal",
    "travel",
]

# Signals that a repository verifies the citations/references it produces —
# the single most differentiating quality feature for literature/deep-research
# skills, where hallucinated references are the dominant failure mode.
CITATION_VERIFICATION_TERMS = [
    "citation verif",
    "verified citation",
    "citations verified",
    "citation valid",
    "reference verif",
    "references verified",
    "reference check",
    "reference-checker",
    "check references",
    "checking scholarly ref",
    "source credibility",
    "evidence-grounded",
    "evidence-backed",
    "evidence-first",
    "引用核验",
    "引用验证",
    "文献核验",
    "参考文献是否真实",
    "检查参考文献",
    "核验参考文献",
    "可追溯文献",
    "证据审计",
    "可信证据",
    "零幻觉",
    "zero hallucinat",
    "no hallucinated",
    "hallucination-free",
    "fact-check",
    "source validation",
]

# A repository counts as stale (likely unmaintained) when it has not been
# pushed for this many days AND gained no stars in the 7-day window.
STALE_PUSH_DAYS = 30

CATEGORIES = [
    {
        "id": "deep-research",
        "zh": "深度研究",
        "en": "Deep Research",
        "keywords": [
            "deep research",
            "deep-research",
            "research agent",
            "autonomous research",
            "source validation",
            "autonomous discovery",
            "discovery",
            "kosmos",
            "idea generation",
            "research idea",
            "clarify-research-idea",
            "topic-feasibility",
            "深度研究",
            "深研",
            "自主科研",
            "自主研究",
            "选题",
            "可行性",
        ],
    },
    {
        "id": "paper-writing",
        "zh": "论文写作",
        "en": "Paper Writing",
        "keywords": [
            "paper writing",
            "paper-writing",
            "academic writing",
            "academic-writing",
            "manuscript",
            "latex",
            "beamer",
            "overleaf",
            "bibtex",
            "proofreading",
            "revise",
            "abstract",
            "introduction",
            "writing",
            "humanizer",
            "anti-defensive",
            "defensive writing",
            "aigc",
            "pptx",
            "presentation",
            "figure",
            "figures",
            "figures4papers",
            "illustration",
            "illustrator",
            "diagram",
            "diagrams",
            "visio",
            "tikz",
            "patent",
            "paper2patent",
            "论文写作",
            "学术写作",
            "写作",
            "润色",
            "改写",
            "降重",
            "防御性写作",
            "配图",
            "科研绘图",
            "论文绘图",
            "图表",
            "插画",
            "示意图",
            "答辩",
            "开题",
            "毕业论文",
            "学位论文",
            "专利",
        ],
    },
    {
        "id": "literature-review",
        "zh": "文献综述",
        "en": "Literature Review",
        "keywords": [
            "literature review",
            "literature-review",
            "literature survey",
            "systematic review",
            "citation",
            "citations",
            "bibliography",
            "zotero",
            "paper search",
            "paper-search",
            "paper retrieval",
            "reference check",
            "reference-checker",
            "reference verification",
            "cnki",
            "arxiv",
            "read-arxiv",
            "easyread",
            "literature-route",
            "agentero",
            "文献综述",
            "文献检索",
            "文献阅读",
            "文献管理",
            "文献回顾",
            "知网",
            "读论文",
            "论文精读",
            "论文翻译",
            "参考文献",
            "引用核验",
        ],
    },
    {
        "id": "peer-review",
        "zh": "评审反馈",
        "en": "Peer Review",
        "keywords": [
            "peer review",
            "peer-review",
            "paper review",
            "paper-review",
            "research-feedback",
            "research feedback",
            "paperjury",
            "paperdebugger",
            "reviewer",
            "feedback",
            "critique",
            "referee",
            "rebuttal",
            "stress-test",
            "审稿",
            "评审",
            "同行评审",
            "审稿意见",
            "回复审稿",
            "返修",
            "审查",
        ],
    },
    {
        "id": "experiment-reproducibility",
        "zh": "实验复现",
        "en": "Experiments",
        "keywords": [
            "experiment",
            "experiments",
            "experiment design",
            "experiment automation",
            "benchmark",
            "reproduce",
            "reproducibility",
            "paper reproduction",
            "replicate",
            "replication",
            "paper-replicate",
            "evaluation",
            "ablation",
            "paper-plot",
            "labrat",
            "实验",
            "复现",
        ],
    },
    {
        "id": "discipline-specific",
        "zh": "学科专项",
        "en": "Discipline Specific",
        "keywords": [
            "economics",
            "econ",
            "econometrics",
            "stata",
            "finance",
            "financial",
            "finai",
            "biology",
            "biotech",
            "biomedical",
            "chemistry",
            "medicine",
            "medical",
            "med-paper",
            "clinical",
            "phd",
            "physics",
            "math",
            "mathematics",
            "mathematical",
            "mathmodel",
            "math-modeling",
            "modelviz",
            "cumcm",
            "mcm",
            "icm",
            "statistics",
            "law",
            "education",
            "psychology",
            "sociology",
            "social-science",
            "social science",
            "empirical",
            "humanities",
            "management",
            "mgmt",
            "stem",
            "cv",
            "nlp",
            "ml",
            "drug discovery",
            "nature-skills",
            "数学建模",
            "医学",
            "临床",
            "经济学",
            "金融",
            "社科",
            "社会科学",
            "人文",
            "生物",
            "化学",
            "物理",
            "心理学",
            "教育学",
            "管理学",
        ],
    },
    {
        "id": "general-research",
        "zh": "综合研究",
        "en": "General Research",
        "keywords": ["academic", "research", "scientific", "science", "scholar", "科研", "学术"],
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


def _split_camel_case(value: str) -> str:
    return re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value or "")


def text_corpus(repo: dict[str, Any]) -> str:
    topics = repo.get("repositoryTopics", {}).get("nodes", [])
    topic_names = []
    for node in topics:
        topic = node.get("topic", {}) if isinstance(node, dict) else {}
        name = topic.get("name")
        if name:
            topic_names.append(name)

    parts = [
        _split_camel_case(repo.get("nameWithOwner", "")),
        _split_camel_case(repo.get("name", "")),
        repo.get("description") or "",
        " ".join(topic_names),
    ]
    return " ".join(parts).lower()


def _term_in_corpus(term: str, corpus: str) -> bool:
    """Match a keyword against a lowercased text corpus.

    Pure-ASCII keywords use ASCII-letter boundaries (allowing an optional
    trailing plural ``s``) so short tokens like ``roo``, ``law``, ``ml``, or
    ``cv`` never match inside unrelated English words (e.g. ``p[roo]freading``,
    ``dr-c[law]``, ``ht[ml]``), while still matching plurals (``journals``,
    ``workflows``, ``academics``) and across hyphens, slashes, or CJK text.
    """
    t = term.lower()
    if t.isascii():
        return re.search(rf"(?<![a-z]){re.escape(t)}s?(?![a-z])", corpus) is not None
    return t in corpus


def term_hits(corpus: str, terms: list[str]) -> list[str]:
    return [term for term in terms if _term_in_corpus(term, corpus)]


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
    full_corpus = text_corpus(repo)
    name_corpus = _split_camel_case(
        f"{repo.get('nameWithOwner', '')} {repo.get('name', '')}"
    ).lower()

    scores: list[tuple[int, int, dict[str, Any]]] = []
    name_hits: dict[str, int] = {}
    for category in CATEGORIES[:-1]:
        nh = sum(1 for kw in category["keywords"] if _term_in_corpus(kw, name_corpus))
        fh = sum(1 for kw in category["keywords"] if _term_in_corpus(kw, full_corpus))
        name_hits[category["id"]] = nh
        scores.append((fh + nh * 2, fh, category))

    scores.sort(key=lambda item: -item[0])
    best_total, _best_fh, best_cat = scores[0]
    fallback = CATEGORIES[-1]
    if best_total <= 0:
        return {"id": fallback["id"], "zh": fallback["zh"], "en": fallback["en"]}

    # If the repository name explicitly signals the top specific category,
    # keep that specific category.
    if name_hits.get(best_cat["id"], 0) > 0:
        return {"id": best_cat["id"], "zh": best_cat["zh"], "en": best_cat["en"]}

    # Repositories that span 3+ distinct research stages without a single
    # dominant stage belong in the multi-stage General Research category.
    matched_stages = sum(1 for _total, fh, _cat in scores if fh > 0)
    if matched_stages >= 3 and best_total <= scores[1][0] + 1:
        return {"id": fallback["id"], "zh": fallback["zh"], "en": fallback["en"]}

    return {"id": best_cat["id"], "zh": best_cat["zh"], "en": best_cat["en"]}


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
    long_window_snapshot: dict[str, Any] | None = None,
    excluded_repositories: set[str] | None = None,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    previous_snapshot = previous_snapshot or {}
    trusted_repositories = trusted_repositories or set()
    window_snapshot = window_snapshot or {}
    long_window_snapshot = long_window_snapshot or {}
    excluded_repositories = excluded_repositories or set()
    now = now or utc_now()
    ranked: list[dict[str, Any]] = []

    for repo in repos:
        name = repo["nameWithOwner"]
        if name in excluded_repositories:
            continue
        accepted, reasons = is_academic_skill_repo(
            repo,
            min_stars=min_stars,
            trusted_repositories=trusted_repositories,
        )
        if not accepted:
            continue

        previous = previous_snapshot.get(name, {}) if isinstance(previous_snapshot, dict) else {}
        stars = int(repo.get("stargazerCount") or 0)
        old_stars = previous_stars(previous)
        star_delta_1d = max(0, stars - old_stars) if old_stars is not None else 0

        # 7-day window delta — the primary growth signal shown to users.
        window_prev = window_snapshot.get(name, {}) if isinstance(window_snapshot, dict) else {}
        window_stars = previous_stars(window_prev)
        star_delta_7d = max(0, stars - window_stars) if window_stars is not None else star_delta_1d

        # 30-day window delta — an auxiliary, longer-horizon signal for the
        # sparkline / drawer. Falls back to the 7-day value when no older
        # snapshot exists (e.g. first weeks of operation).
        long_prev = long_window_snapshot.get(name, {}) if isinstance(long_window_snapshot, dict) else {}
        long_stars = previous_stars(long_prev)
        star_delta_30d = max(0, stars - long_stars) if long_stars is not None else star_delta_7d

        score = compute_trend_score(
            repo,
            previous,
            now=now,
            star_delta_window=star_delta_7d,
        )
        # Trend label is driven by the (less noisy) 7-day delta.
        trend = trend_label(star_delta_7d, score)
        category = classify_repo(repo)
        agents = detect_agents(repo)
        topics = [
            node.get("topic", {}).get("name")
            for node in repo.get("repositoryTopics", {}).get("nodes", [])
            if node.get("topic", {}).get("name")
        ]

        ranked_item: dict[str, Any] = {
            "rank": 0,
            "repo": name,
            "stars": stars,
            "star_delta_1d": star_delta_1d,
            "star_delta_7d": star_delta_7d,
            "star_delta_30d": star_delta_30d,
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
            "agents": agents,
            "precision_signals": sorted(set(reasons)),
            # Enrichment (only added, never removed from the legacy set).
            "stale": is_stale(repo, star_delta_7d, now),
            "verifies_citations": verifies_citations(repo),
            "forks": int(repo.get("forksCount") or 0),
            "open_issues": int(repo.get("openIssuesCount") or 0),
            "watchers": int(repo.get("watchersCount") or 0),
            "size_kb": int(repo.get("sizeKb") or 0),
            "default_branch": repo.get("defaultBranch") or "",
            "has_issues": bool(repo.get("hasIssues", False)),
            "has_wiki": bool(repo.get("hasWiki", False)),
            "has_discussions": bool(repo.get("hasDiscussions", False)),
            "license": repo.get("license") or {"key": "", "name": "", "spdx_id": ""},
        }
        if "skillsCount" in repo:
            ranked_item["skills_count"] = repo["skillsCount"]
        ranked.append(ranked_item)

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


def item_to_repo_input(item: dict[str, Any]) -> dict[str, Any]:
    """Convert an already-ranked item (from ``rankings.json`` or ``history/*.json``)
    back into the canonical repository input dict consumed by ``rank_repositories``.
    """
    full_name = item.get("repo") or item.get("nameWithOwner") or ""
    topics = item.get("topics") or []
    result: dict[str, Any] = {
        "nameWithOwner": full_name,
        "name": full_name.split("/")[-1] if full_name else "",
        "description": item.get("description") or "",
        "stargazerCount": int(item.get("stars") or item.get("stargazerCount") or 0),
        "createdAt": item.get("created_date") or item.get("createdAt") or "",
        "updatedAt": item.get("last_push_date") or item.get("updatedAt") or "",
        "pushedAt": item.get("last_push_date") or item.get("pushedAt") or "",
        "url": item.get("url") or f"https://github.com/{full_name}",
        "homepageUrl": item.get("homepage") or item.get("homepageUrl") or "",
        "isArchived": bool(item.get("isArchived", False)),
        "isFork": bool(item.get("isFork", False)),
        "primaryLanguage": {"name": item.get("language") or ""},
        "repositoryTopics": {
            "nodes": [{"topic": {"name": t}} for t in topics if isinstance(t, str)]
        },
        "forksCount": int(item.get("forks") or 0),
        "openIssuesCount": int(item.get("open_issues") or 0),
        "sizeKb": int(item.get("size_kb") or 0),
        "defaultBranch": item.get("default_branch") or "",
        "hasIssues": bool(item.get("has_issues", False)),
        "hasWiki": bool(item.get("has_wiki", False)),
        "hasDiscussions": bool(item.get("has_discussions", False)),
        "watchersCount": int(item.get("watchers") or 0),
        "license": item.get("license") or {"key": "", "name": "", "spdx_id": ""},
    }
    if "skills_count" in item:
        result["skillsCount"] = item["skills_count"]
    return result


def find_previous_day_snapshot(
    history: dict[str, dict[str, Any]],
    today: datetime,
) -> dict[str, Any] | None:
    """Return the most recent history snapshot strictly before ``today``."""
    today_key = today.date().isoformat()
    prior_keys = sorted(key for key in history if key < today_key)
    if not prior_keys:
        return None
    return history[prior_keys[-1]]


def save_history_snapshot(
    data: dict[str, Any],
    today: datetime,
    overwrite: bool = False,
) -> None:
    """Persist today's ranking as a dated snapshot and prune old entries."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_path = _history_path(today)
    # Only write once per day by default to keep history idempotent under re-runs,
    # unless overwrite=True (e.g. --recompute refreshing derived categories/signals).
    if overwrite or not snapshot_path.exists():
        snapshot_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    cutoff = today - timedelta(days=HISTORY_RETENTION_DAYS)
    for entry in HISTORY_DIR.glob("*.json"):
        try:
            entry_date = datetime.fromisoformat(entry.stem).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if entry_date < cutoff:
            entry.unlink(missing_ok=True)


RETRYABLE_STATUS_CODES = {403, 429, 500, 502, 503, 504}


def github_request(
    path: str,
    token: str | None,
    params: dict[str, Any] | None = None,
    retries: int = 3,
) -> dict[str, Any]:
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

    last_error: Exception | None = None
    for attempt in range(retries):
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            last_error = error
            # 403 covers both hard rate limits and secondary abuse limits.
            transient = error.code in RETRYABLE_STATUS_CODES
            if not transient or attempt >= retries - 1:
                raise
            retry_after = (error.headers or {}).get("Retry-After") if error.headers else None
            delay = int(retry_after) if retry_after and retry_after.isdigit() else 2**attempt * 2
            print(f"warning: HTTP {error.code} on {url.split('?')[0]}, retrying in {delay}s", file=sys.stderr)
            time.sleep(delay)
        except urllib.error.URLError as error:
            last_error = error
            if attempt >= retries - 1:
                raise
            delay = 2**attempt * 2
            print(f"warning: network error on {url.split('?')[0]}: {error.reason}, retrying in {delay}s", file=sys.stderr)
            time.sleep(delay)
    raise last_error  # pragma: no cover - retries exhausted above


def rest_to_repo(item: dict[str, Any]) -> dict[str, Any]:
    topics = item.get("topics") or []
    license_node = item.get("license") or {}
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
        # Enrichment fields (only added, never removed from the legacy set).
        "forksCount": item.get("forks_count") or 0,
        "openIssuesCount": item.get("open_issues_count") or 0,
        "sizeKb": item.get("size") or 0,
        "defaultBranch": item.get("default_branch") or "",
        "hasIssues": bool(item.get("has_issues", False)),
        "hasWiki": bool(item.get("has_wiki", False)),
        "hasDiscussions": bool(item.get("has_discussions", False)),
        "watchersCount": item.get("watchers_count") or 0,
        "license": {
            "key": license_node.get("key") or "",
            "name": license_node.get("name") or "",
            "spdx_id": license_node.get("spdx_id") or "",
        } if isinstance(license_node, dict) else {"key": "", "name": "", "spdx_id": ""},
    }


def search_repositories(
    query: str,
    min_stars: int,
    token: str | None,
    max_pages: int = 2,
) -> list[dict[str, Any]]:
    q = f"{query} stars:>={min_stars} fork:false archived:false"
    items: list[dict[str, Any]] = []
    try:
        for page in range(1, max_pages + 1):
            data = github_request(
                "/search/repositories",
                token,
                {
                    "q": q,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 100,
                    "page": page,
                },
            )
            page_items = data.get("items", [])
            items.extend(page_items)
            # Stop early when the last page is short or search hits the
            # GitHub-wide 1000-result ceiling.
            if len(page_items) < 100 or page * 100 >= data.get("total_count", 0):
                break
            time.sleep(1.5)
    except urllib.error.HTTPError as error:
        message = error.read().decode("utf-8", errors="replace")
        print(f"warning: search failed for {query!r}: {error.code} {message}", file=sys.stderr)
        return items
    return [rest_to_repo(item) for item in items]


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
        # Search API allows 30 requests/minute; with up to 2 pages per query
        # this keeps even the worst case (2 pages every query) under the cap.
        time.sleep(2.5)

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
    if "opencode" in corpus or "open code" in corpus or "open-code" in corpus:
        badges.append("OpenCode")
    if "mcp" in corpus:
        badges.append("MCP")
    return "/".join(badges) if badges else "通用"


# Canonical platform catalog — mirrors the frontend AGENT_PLATFORMS list.
# Each entry: (backend_id, match_terms). The backend_id is written to the
# JSON `agents` field and CSV `agents` column; the frontend maps it to a
# human label. Keeping the ids stable lets old snapshots filter correctly.
AGENT_PLATFORMS = [
    (
        "claude-code",
        [
            "claude code",
            "claude-code",
            "claude code skill",
            "claude-skill",
            "claude-skills",
            "claude skill",
            "claude skills",
            "for claude",
            "and claude",
            "claude/codex",
            "codex/claude",
            "codex / claude",
            "claude / codex",
        ],
    ),
    ("codex", ["codex"]),
    ("opencode", ["opencode", "open code", "open-code"]),
    ("cursor", ["cursor"]),
    ("gemini", ["gemini"]),
    ("cline", ["cline"]),
    ("mcp", ["mcp"]),
]


def detect_agents(repo: dict[str, Any]) -> list[str]:
    """Return the list of target-agent platform ids inferred from the repo corpus."""
    corpus = text_corpus(repo)
    found: list[str] = []
    for platform_id, terms in AGENT_PLATFORMS:
        if any(_term_in_corpus(term, corpus) for term in terms):
            found.append(platform_id)
    return found


def verifies_citations(repo: dict[str, Any]) -> bool:
    """Whether the repo advertises citation/reference verification."""
    corpus = text_corpus(repo)
    return any(term in corpus for term in CITATION_VERIFICATION_TERMS)


def is_stale(repo: dict[str, Any], star_delta_7d: int, now: datetime) -> bool:
    """Likely-unmaintained heuristic: no push in STALE_PUSH_DAYS and zero
    7-day star growth. Deliberately conservative — both conditions together."""
    pushed_at = parse_datetime(repo.get("pushedAt"))
    if not pushed_at:
        return False
    days_since_push = (now - pushed_at).total_seconds() / 86400
    return days_since_push >= STALE_PUSH_DAYS and star_delta_7d <= 0


def count_skill_files_in_tree(tree: list[Any]) -> int:
    """Count SKILL.md entries in a git-tree payload (pure, testable)."""
    return sum(
        1
        for node in tree
        if isinstance(node, dict)
        and str(node.get("path", "")).rsplit("/", 1)[-1].lower() == "skill.md"
    )


def count_skill_files(full_name: str, branch: str, token: str | None) -> int | None:
    """Count SKILL.md files in a repository via the git trees API.

    Returns ``None`` when the tree cannot be fetched (missing repo, network,
    rate limit after retries). For very large trees GitHub may return
    ``truncated: true`` — the count is then a lower bound, which is fine for
    display purposes.
    """
    try:
        data = github_request(
            f"/repos/{full_name}/git/trees/{branch or 'HEAD'}",
            token,
            {"recursive": "1"},
        )
    except (urllib.error.HTTPError, urllib.error.URLError) as error:
        print(f"warning: skill tree fetch failed for {full_name}: {error}", file=sys.stderr)
        return None
    return count_skill_files_in_tree(data.get("tree") or [])


def enrich_skill_counts(items: list[dict[str, Any]], token: str | None) -> None:
    """Attach `skills_count` to each ranked item (only-add enrichment)."""
    for item in items:
        branch = item.get("default_branch") or ""
        item["skills_count"] = count_skill_files(item["repo"], branch, token)
        time.sleep(0.15)


# Map a backend platform id to a short human label for README / display.
_AGENT_LABELS = {
    "claude-code": "Claude",
    "codex": "Codex",
    "opencode": "OpenCode",
    "cursor": "Cursor",
    "gemini": "Gemini",
    "cline": "Cline",
    "mcp": "MCP",
}


def agents_to_label(agent_ids: list[str]) -> str:
    """Render the structured agents list as a /-joined label (通用 when empty)."""
    labels = [_AGENT_LABELS.get(aid, aid) for aid in agent_ids if aid]
    return "/".join(labels) if labels else "通用"


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
        agent = agents_to_label(item.get("agents", []))
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

[![Last update](https://img.shields.io/badge/updated-{metadata['generated_at'][:10].replace('-', '--')}-0f766e)](#今日榜单)
[![Repositories](https://img.shields.io/badge/repositories-{metadata['total']}-2563eb)](#今日榜单)
[![Min stars](https://img.shields.io/badge/min%20stars-{metadata['min_stars']}-334155)](#收录标准)
[![Online dashboard](https://img.shields.io/badge/online-dashboard-b3552a)](https://kael-odin.github.io/awesome-academic-research-skills/)
[![License: MIT](https://img.shields.io/badge/license-MIT-22c55e)](LICENSE)
[![Auto update](https://img.shields.io/badge/auto%20update-daily-6366f1)](.github/workflows/update-rankings.yml)

[English](#english) · [可视化页面](https://kael-odin.github.io/awesome-academic-research-skills/) · [English Dashboard](https://kael-odin.github.io/awesome-academic-research-skills/en/) · [月报](reports/) · [JSON](data/rankings.json) · [CSV](data/rankings.csv) · [RSS](feed.xml) · [Sitemap](sitemap.xml) · [排名方法](docs/methodology.md) · [更新日志](docs/changelog.md) · [贡献指南](CONTRIBUTING.md)

## 项目特色

- 🔄 **每日自动更新** — GitHub Actions 每天 02:20 UTC 运行，自动搜索、过滤、排名并提交。
- 🎯 **精准双重信号过滤** — 必须同时命中"Skill/Agent/Workflow"与"Academic/Research/Paper"信号，挡住泛 AI 项目。
- 📈 **7 天 / 30 天趋势窗口** — 基于历史快照计算一周 Stars 增量，并展示 30 天 sparkline 趋势曲线，告别单日抖动假象。
- 🆕 **本周新收录** — 自动识别近 7 天新进入榜单的仓库。
- 🏷️ **适用 Agent 标签** — 推断每个仓库面向 Claude Code / Codex / OpenCode / Cursor / Gemini / MCP。
- 🌐 **双语可视化** — 中文优先，支持英文切换、搜索、分类筛选与多维度排序。
- 🎨 **深色模式 & 卡片视图** — 一键切换明暗主题，表格 / 卡片双视图，仓库详情抽屉，收藏夹与 URL 状态分享。
- ⌨️ **键盘快捷键** — `/` 搜索 · `t` 主题 · `l` 语言 · `v` 视图 · `f` 收藏 · `Esc` 关闭。
- 🔍 **SEO & 订阅** — 提供 sitemap、Open Graph、JSON-LD 结构化数据与 RSS 订阅源，方便被搜索引擎和 RSS 阅读器发现。
- 📦 **机器可读** — 提供 JSON / CSV 数据文件（含 license、forks、open issues 等字段），方便二次开发与订阅。

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

**Awesome Academic Research Skills** is a daily-updated ranking of GitHub repositories that provide academic, paper-writing, literature-review, deep-research, peer-review, and experiment-reproducibility skills for AI coding agents (Claude Code, Codex, OpenCode, Cursor, Gemini, …).

The ranking requires **both** a skill/agent/workflow signal **and** an academic/research/paper signal. Low-star, archived, forked, and clearly unrelated repositories are excluded. The trend column shows 7-day star growth, with a 30-day sparkline in the dashboard.

### Dashboard features

- Bilingual (Chinese-first, English switch), **dark mode**, and a responsive **table / card** dual view.
- Per-repo **trend sparkline**, **detail drawer**, **favorites** (with JSON export), and **shareable URL state** (filters/sort/view/lang/theme persisted in `#hash`).
- **Keyboard shortcuts**: `/` search · `t` theme · `l` language · `v` view · `f` favorites · `Esc` close.
- **SEO & subscription**: sitemap, Open Graph cover, JSON-LD `ItemList`, and an **RSS feed** of daily newcomers + trending repos.
- Machine-readable **JSON** / **CSV** (incl. license, forks, open issues, 30-day delta).

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
                "star_delta_30d",
                "trend_score",
                "trend",
                "category",
                "description",
                "language",
                "license",
                "forks",
                "open_issues",
                "agents",
                "skills_count",
                "stale",
                "verifies_citations",
                "last_push_date",
                "url",
            ],
        )
        writer.writeheader()
        for item in items:
            license_name = (item.get("license") or {}).get("name", "") if isinstance(item.get("license"), dict) else ""
            writer.writerow(
                {
                    "rank": item["rank"],
                    "repo": item["repo"],
                    "stars": item["stars"],
                    "star_delta_1d": item["star_delta_1d"],
                    "star_delta_7d": item["star_delta_7d"],
                    "star_delta_30d": item["star_delta_30d"],
                    "trend_score": item["trend_score"],
                    "trend": item["trend"]["en"],
                    "category": item["category"]["en"],
                    "description": item["description"],
                    "language": item.get("language", ""),
                    "license": license_name,
                    "forks": item.get("forks", 0),
                    "open_issues": item.get("open_issues", 0),
                    "agents": "|".join(item.get("agents", [])),
                    "skills_count": "" if item.get("skills_count") is None else item["skills_count"],
                    "stale": bool(item.get("stale", False)),
                    "verifies_citations": bool(item.get("verifies_citations", False)),
                    "last_push_date": item["last_push_date"],
                    "url": item["url"],
                }
            )


def render_data_js(data: dict[str, Any]) -> str:
    # Compact separators: these files are machine-consumed by the dashboard;
    # indenting them tripled the transfer size of history.js for no benefit.
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"window.ACADEMIC_SKILLS_RANKINGS={payload};\n"


def render_history_js(history_payload: dict[str, Any]) -> str:
    payload = json.dumps(history_payload, ensure_ascii=False, separators=(",", ":"))
    return f"window.ACADEMIC_SKILLS_HISTORY={payload};\n"


def write_outputs(data: dict[str, Any], window_snapshot: dict[str, Any] | None = None) -> None:
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    DATA_JS_PATH.write_text(render_data_js(data), encoding="utf-8")
    history = load_history_snapshots()
    HISTORY_JS_PATH.write_text(render_history_js(render_history_series(history)), encoding="utf-8")
    build_monthly_reports(history)
    render_csv(data["items"])
    README_PATH.write_text(render_readme(data, window_snapshot=window_snapshot), encoding="utf-8")
    write_seo_assets(data, window_snapshot=window_snapshot)


def build_dataset(
    config: dict[str, Any],
    repos: list[dict[str, Any]],
    token: str | None = None,
    enrich_skills: bool = True,
    now: datetime | None = None,
    overwrite_today_snapshot: bool = False,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    min_stars = int(config.get("min_stars", DEFAULT_MIN_STARS))
    now = now or utc_now()
    history = load_history_snapshots()
    previous = find_previous_day_snapshot(history, now) or load_previous_snapshot()
    window_snapshot = find_window_snapshot(history, now, DELTA_WINDOW_DAYS)
    long_window_snapshot = find_window_snapshot(history, now, LONG_WINDOW_DAYS)
    trusted_repositories = set(config.get("seed_repositories", []))
    excluded_repositories = set(
        config.get("exclude_repositories", DEFAULT_EXCLUDED_REPOSITORIES)
    )
    items = rank_repositories(
        repos,
        min_stars=min_stars,
        previous_snapshot=previous,
        trusted_repositories=trusted_repositories,
        window_snapshot=window_snapshot,
        long_window_snapshot=long_window_snapshot,
        excluded_repositories=excluded_repositories,
        now=now,
    )
    max_results = int(config.get("max_results", 100))
    items = items[:max_results]
    for index, item in enumerate(items, start=1):
        item["rank"] = index

    if enrich_skills:
        enrich_skill_counts(items, token)

    generated_at = now.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    data = {
        "metadata": {
            "generated_at": generated_at,
            "min_stars": min_stars,
            "total": len(items),
            "source": "GitHub REST Search API",
            "ranking": "stars_desc_then_trend_score",
            "trend_window_days": DELTA_WINDOW_DAYS,
            "long_window_days": LONG_WINDOW_DAYS,
            "history_retention_days": HISTORY_RETENTION_DAYS,
        },
        "items": items,
    }

    # Persist today's snapshot so future runs can compute the 7-day delta.
    save_history_snapshot(data, now, overwrite=overwrite_today_snapshot)
    return data, window_snapshot


def render_history_series(history: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Build a compact per-repo star history series for the frontend sparkline.

    Returns ``{metadata: {...}, series: {repo: [{date, stars}, ...]}}``. Each
    point is a daily snapshot we have on disk; missing days are simply absent
    (the sparkline renderer connects the available points). Only ``stars`` is
    kept per point to keep payload size well under 100 KB for ~100 repos × 30 d.
    """
    series: dict[str, list[dict[str, Any]]] = {}
    for date_key in sorted(history.keys()):
        snapshot = history[date_key]
        if not isinstance(snapshot, dict):
            continue
        for repo, item in snapshot.items():
            if not isinstance(item, dict):
                continue
            stars = item.get("stars") or item.get("stargazerCount")
            if stars is None:
                # Need a stars figure to plot.
                continue
            series.setdefault(repo, []).append({"date": date_key, "stars": int(stars)})
    return {
        "metadata": {
            "series_points": sum(len(points) for points in series.values()),
            "repos": len(series),
            "window_days": HISTORY_RETENTION_DAYS,
        },
        "series": series,
    }


REPORT_THEME_BOOTSTRAP = (
    '<script>try{var t=localStorage.getItem("ars-theme")||(matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light");'
    'document.documentElement.dataset.theme=t;document.documentElement.style.colorScheme=t;}catch(e){}</script>'
)
REPORT_FONTS_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com" />\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />\n'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;0,6..72,700;1,6..72,400;1,6..72,500&family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" />'
)
REPORT_THEME_SCRIPT = (
    "<script>(function(){var b=document.getElementById('reportTheme');if(!b)return;"
    "b.addEventListener('click',function(){var d=document.documentElement;"
    "var n=d.dataset.theme==='dark'?'light':'dark';d.dataset.theme=n;d.style.colorScheme=n;"
    "try{localStorage.setItem('ars-theme',n);}catch(e){}});})();</script>"
)
REPORT_HEADER = """<header class="report-header">
  <a class="brand" href="../"><span class="brand-mark" aria-hidden="true">ARS</span><span class="brand-text">Academic Research Skills</span></a>
  <div class="report-actions">
    <a href="../">榜单</a>
    <a href="index.html">全部月报</a>
    <button type="button" id="reportTheme" aria-label="切换主题">◐ 主题</button>
  </div>
</header>"""
REPORT_FOOTER = """<footer class="report-footer">
  <span>MIT · kael-odin/awesome-academic-research-skills</span>
  <a href="../feed.xml">RSS 订阅</a>
  <a href="../">可视化榜单</a>
  <span>数据基于每日快照自动生成</span>
</footer>"""


def _upgrade_report_page(html: str) -> str:
    """Bring already-frozen month pages onto the current journal chrome."""
    if REPORT_FONTS_LINK not in html:
        html = html.replace(
            '<link rel="stylesheet" href="../assets/styles.css" />',
            REPORT_FONTS_LINK + '\n<link rel="stylesheet" href="../assets/styles.css" />',
            1,
        )
    if 'class="report-header"' not in html:
        html = html.replace("<body>", "<body>\n" + REPORT_HEADER, 1)
    html = html.replace(
        '<main style="max-width:960px;margin:0 auto;padding:32px 20px">',
        '<main class="report-main">',
    )
    if 'class="report-footer"' not in html:
        html = html.replace("</body>", REPORT_FOOTER + "\n" + REPORT_THEME_SCRIPT + "\n</body>", 1)
    html = re.sub(r"<h2>🆕\s*", "<h2>", html)
    html = re.sub(r"<h2>📈\s*", "<h2>", html)
    html = re.sub(r"<h2>⏸️\s*", "<h2>", html)
    html = re.sub(r"<h2>🚪\s*", "<h2>", html)
    return html


def render_month_report(
    month: str,
    history: dict[str, dict[str, dict[str, Any]]],
    first_seen: dict[str, str],
    prev_repos: set[str],
    all_months: list[str],
) -> str | None:
    """Render one monthly report page (新星 / 上升 / 停滞 / 跌出) as static HTML."""
    dates = sorted(key for key in history if key.startswith(month))
    if not dates:
        return None
    last_snap = history[dates[-1]]

    rows: list[dict[str, Any]] = []
    for repo, item in last_snap.items():
        stars_last = previous_stars(item)
        if stars_last is None:
            continue
        stars_first: int | None = None
        for d in dates:
            if repo in history[d]:
                stars_first = previous_stars(history[d][repo])
                if stars_first is not None:
                    break
        base = stars_first if stars_first is not None else stars_last
        rows.append(
            {
                "repo": repo,
                "stars": stars_last,
                "delta": stars_last - base,
                "item": item,
            }
        )

    is_newcomer_month = lambda repo: first_seen.get(repo, "")[:7] == month  # noqa: E731
    newcomers = sorted(
        (r for r in rows if is_newcomer_month(r["repo"])),
        key=lambda r: (-r["stars"], r["repo"].lower()),
    )
    risers = sorted((r for r in rows if r["delta"] > 0), key=lambda r: (-r["delta"], -r["stars"]))[:10]
    stalled = sorted(
        (r for r in rows if r["delta"] <= 0 and not is_newcomer_month(r["repo"])),
        key=lambda r: (-r["stars"], r["repo"].lower()),
    )
    dropped = sorted(prev_repos - set(last_snap))

    def table(entries: list[dict[str, Any]]) -> str:
        if not entries:
            return "<p class='muted'>本月无条目。</p>"
        body = "".join(
            f"<tr><td>{i}</td><td><a href='{r['item'].get('url', '#')}'>{xml_escape(r['repo'])}</a></td>"
            f"<td>{r['stars']:,}</td><td>{r['delta']:+d}</td><td>{xml_escape(r['item'].get('category', {}).get('zh', ''))}</td></tr>"
            for i, r in enumerate(entries, 1)
        )
        return (
            "<div class='report-table-wrap'><table class='report-table'><thead><tr><th>#</th><th>仓库</th><th>月末 Stars</th>"
            "<th>月增量</th><th>分类</th></tr></thead>"
            f"<tbody>{body}</tbody></table></div>"
        )

    dropped_html = (
        "<ul>"
        + "".join(f"<li>{xml_escape(repo)}</li>" for repo in dropped)
        + "</ul>"
        if dropped
        else "<p class='muted'>本月无跌出仓库。</p>"
    )
    nav = " · ".join(
        f"<a href='{m}.html'>{m}</a>" if m != month else f"<b>{m}</b>" for m in all_months
    )
    total_stars = sum(r["stars"] for r in rows)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{month} 月度报告 · Awesome Academic Research Skills</title>
{REPORT_THEME_BOOTSTRAP}
<link rel="canonical" href="{SITE_URL}/reports/{month}.html" />
{REPORT_FONTS_LINK}
<link rel="stylesheet" href="../assets/styles.css" />
</head>
<body>
{REPORT_HEADER}
<main class="report-main">
<h1>{month} 月度报告</h1>
<p class="muted">收录 {len(rows)} 个仓库 · 合计 {total_stars:,}★ · 报告期 {dates[0]} → {dates[-1]}</p>
<nav>{nav}</nav>

<h2>本月新收录（{len(newcomers)}）</h2>
{table(newcomers)}
<h2>月度上升前 10</h2>
{table(risers)}
<h2>增长停滞（{len(stalled)}）</h2>
{table(stalled)}
<h2>本月跌出（{len(dropped)}）</h2>
{dropped_html}
</main>
{REPORT_FOOTER}
{REPORT_THEME_SCRIPT}
</body>
</html>
"""


def build_monthly_reports(history: dict[str, dict[str, dict[str, Any]]]) -> None:
    """Render per-month report pages under ``reports/``.

    Past months are frozen (written once) so the 60-day snapshot retention
    never degrades an already-published report; only the current month
    regenerates on every run. Frozen report filenames on disk are merged into
    the month navigation and index so pruned snapshot months never disappear.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    existing_months = {
        entry.stem
        for entry in REPORTS_DIR.glob("*.html")
        if re.fullmatch(r"\d{4}-\d{2}", entry.stem)
    }
    history_months = sorted({key[:7] for key in history})
    all_months = sorted(set(history_months) | existing_months)
    if not all_months:
        return
    # Re-render the active month in `history` (typically the latest month on disk).
    latest_history_month = history_months[-1] if history_months else utc_now().strftime("%Y-%m")
    current_month = utc_now().strftime("%Y-%m")

    first_seen: dict[str, str] = {}
    for date_key in sorted(history):
        for repo in history[date_key]:
            first_seen.setdefault(repo, date_key)

    for index, month in enumerate(history_months):
        month_page = REPORTS_DIR / f"{month}.html"
        if month_page.exists() and month not in {current_month, latest_history_month}:
            # Keep frozen report content, but ensure its <nav> includes all known months.
            existing_html = month_page.read_text(encoding="utf-8")
            nav = " · ".join(
                f"<a href='{m}.html'>{m}</a>" if m != month else f"<b>{m}</b>"
                for m in all_months
            )
            updated_html = re.sub(r"<nav>.*?</nav>", f"<nav>{nav}</nav>", existing_html, count=1)
            if updated_html != existing_html:
                month_page.write_text(updated_html, encoding="utf-8")
            continue
        prev_repos: set[str] = set()
        if index > 0:
            prev_dates = sorted(key for key in history if key.startswith(history_months[index - 1]))
            if prev_dates:
                prev_repos = set(history[prev_dates[-1]])
        report = render_month_report(month, history, first_seen, prev_repos, all_months)
        if report:
            month_page.write_text(report, encoding="utf-8")

    # Also refresh <nav> on any older frozen month pages outside the active history window.
    for month in existing_months - set(history_months):
        month_page = REPORTS_DIR / f"{month}.html"
        if not month_page.exists():
            continue
        existing_html = month_page.read_text(encoding="utf-8")
        nav = " · ".join(
            f"<a href='{m}.html'>{m}</a>" if m != month else f"<b>{m}</b>"
            for m in all_months
        )
        updated_html = re.sub(r"<nav>.*?</nav>", f"<nav>{nav}</nav>", existing_html, count=1)
        if updated_html != existing_html:
            month_page.write_text(updated_html, encoding="utf-8")

    # Bring every month page — frozen or fresh — onto the journal chrome.
    for month in all_months:
        month_page = REPORTS_DIR / f"{month}.html"
        if not month_page.exists():
            continue
        html = month_page.read_text(encoding="utf-8")
        upgraded = _upgrade_report_page(html)
        if upgraded != html:
            month_page.write_text(upgraded, encoding="utf-8")

    links = "".join(f"<li><a href='{m}.html'>{m} 月度报告</a></li>" for m in reversed(all_months))
    (REPORTS_DIR / "index.html").write_text(
        f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>月度报告 · Awesome Academic Research Skills</title>
{REPORT_THEME_BOOTSTRAP}
<link rel="canonical" href="{SITE_URL}/reports/" />
{REPORT_FONTS_LINK}
<link rel="stylesheet" href="../assets/styles.css" />
</head>
<body>
{REPORT_HEADER}
<main class="report-main">
<h1>月度报告</h1>
<p class="muted">每月自动总结：新收录、上升、停滞与跌出的仓库。</p>
<ul>
{links}
</ul>
</main>
{REPORT_FOOTER}
{REPORT_THEME_SCRIPT}
</body>
</html>
""",
        encoding="utf-8",
    )


def xml_escape(value: str) -> str:
    return (
        (value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def render_sitemap(data: dict[str, Any]) -> str:
    """Generate sitemap.xml covering the dashboard, README, monthly reports, and data endpoints."""
    lastmod = (data.get("metadata", {}).get("generated_at") or "")[:10]
    urls = [
        ("", lastmod, "1.0", "daily"),
        ("en/", lastmod, "0.9", "daily"),
        ("reports/", lastmod, "0.6", "weekly"),
        ("data/rankings.json", lastmod, "0.5", "daily"),
        ("data/rankings.csv", lastmod, "0.4", "daily"),
        ("docs/methodology.md", lastmod, "0.4", "monthly"),
        ("docs/discoverability.md", lastmod, "0.3", "monthly"),
        ("CONTRIBUTING.md", lastmod, "0.3", "monthly"),
    ]
    if REPORTS_DIR.exists():
        report_months = sorted(
            entry.stem
            for entry in REPORTS_DIR.glob("*.html")
            if re.fullmatch(r"\d{4}-\d{2}", entry.stem)
        )
        for month in reversed(report_months):
            urls.append((f"reports/{month}.html", lastmod, "0.5", "monthly"))
    entries = []
    for path, lm, prio, freq in urls:
        loc = f"{SITE_URL}/{path}".rstrip("/") if path else SITE_URL + "/"
        entries.append(
            "  <url>\n"
            f"    <loc>{xml_escape(loc)}</loc>\n"
            f"    <lastmod>{lm}</lastmod>\n"
            f"    <changefreq>{freq}</changefreq>\n"
            f"    <priority>{prio}</priority>\n"
            "  </url>"
        )
    return '<?xml version="1.0" encoding="UTF-8"?>\n' \
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' \
        + "\n".join(entries) + "\n</urlset>\n"


def rfc822_timestamp(value: str) -> str:
    """Render an ISO timestamp as RFC-822 (RSS 2.0 requires it, e.g.
    ``Sat, 26 Sep 2026 07:43:42 GMT``); ISO 8601 fails strict validators."""
    parsed = parse_datetime(value)
    return format_datetime(parsed) if parsed else ""


def render_feed(data: dict[str, Any], window_snapshot: dict[str, Any] | None = None) -> str:
    """Generate an RSS 2.0 feed of newcomers + top trending repos for daily订阅."""
    items = data.get("items", [])
    metadata = data.get("metadata", {})
    generated = rfc822_timestamp(metadata.get("generated_at", ""))
    newcomers = [it for it in items if is_newcomer(it, window_snapshot)]
    trending = sorted(items, key=lambda i: -(i.get("star_delta_7d") or 0))[:10]
    featured = newcomers[:8] + [it for it in trending if it not in newcomers][: (10 - len(newcomers))]
    featured = featured[:12]

    entries = []
    for it in featured:
        title = f"{it['repo']} ({it['stars']:,}★, +{it.get('star_delta_7d') or 0}/7d)"
        link = it.get("url") or ""
        desc = truncate(it.get("description") or "", 200)
        cat = it.get("category", {}).get("en", "")
        guid = f"{SITE_URL}/#{it['repo']}"
        entries.append(
            "    <item>\n"
            f"      <title>{xml_escape(title)}</title>\n"
            f"      <link>{xml_escape(link)}</link>\n"
            f"      <guid isPermaLink=\"false\">{xml_escape(guid)}</guid>\n"
            f"      <description>{xml_escape(desc)}</description>\n"
            f"      <category>{xml_escape(cat)}</category>\n"
            f"      <pubDate>{xml_escape(generated)}</pubDate>\n"
            "    </item>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "  <channel>\n"
        f"    <title>Awesome Academic Research Skills</title>\n"
        f"    <link>{SITE_URL}/</link>\n"
        "    <description>每日自动更新的学术论文与科研 Agent Skill 排行榜 · Daily ranking of academic research agent skills on GitHub</description>\n"
        f"    <language>{'zh-CN'}</language>\n"
        f"    <lastBuildDate>{xml_escape(generated)}</lastBuildDate>\n"
        f"    <atom:link href=\"{SITE_URL}/feed.xml\" rel=\"self\" type=\"application/rss+xml\"/>\n"
        + "\n".join(entries) + "\n"
        "  </channel>\n</rss>\n"
    )


def render_og_cover(data: dict[str, Any]) -> str:
    """Generate a simple SVG Open Graph cover showing the day's headline stats."""
    metadata = data.get("metadata", {})
    items = data.get("items", [])
    total = metadata.get("total", len(items))
    generated = (metadata.get("generated_at") or "")[:10]
    total_stars = sum(it.get("stars", 0) for it in items)
    top = items[0] if items else None
    # Short enough that a 36px name never collides with the star count below.
    top_name = truncate(top["repo"], 30) if top else "—"
    top_stars = f"{top['stars']:,}★" if top else ""

    # Single CJK-capable family for every text run: cairo's toy font API does
    # not do per-glyph fallback, so a Latin-first stack renders Chinese as
    # tofu. "Noto Sans CJK SC" is installed by fonts-noto-cjk in CI; the
    # later entries keep local (Windows/macOS) previews readable.
    font = "Noto Sans CJK SC, Microsoft YaHei, PingFang SC, sans-serif"

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0e1521"/>
      <stop offset="55%" stop-color="#13233a"/>
      <stop offset="100%" stop-color="#0f3a36"/>
    </linearGradient>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#2dd4bf"/>
      <stop offset="100%" stop-color="#60a5fa"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="630" fill="url(#bg)"/>
  <rect x="0" y="0" width="1200" height="8" fill="url(#accent)"/>
  <text x="80" y="150" font-family="{font}" font-size="34" fill="#8a94a6" font-weight="600">Awesome Academic Research Skills</text>
  <text x="78" y="260" font-family="{font}" font-size="84" fill="#e6ebf2" font-weight="800">学术论文 Skill 排行</text>
  <text x="80" y="330" font-family="{font}" font-size="30" fill="#9ee7d8" font-weight="600">{total} repos · {total_stars:,} stars · updated {generated}</text>
  <rect x="80" y="390" width="1040" height="160" rx="20" fill="#161f30" stroke="#25304a" stroke-width="1"/>
  <text x="112" y="445" font-family="{font}" font-size="24" fill="#8a94a6" font-weight="600">#1 TOP</text>
  <text x="112" y="498" font-family="{font}" font-size="38" fill="#e6ebf2" font-weight="700">{xml_escape(top_name)}</text>
  <text x="112" y="532" font-family="{font}" font-size="26" fill="#fbbf24" font-weight="800">{xml_escape(top_stars)}</text>
</svg>
"""


def render_og_cover_png(svg_text: str) -> bytes | None:
    """Rasterize the OG cover to PNG when the optional ``cairosvg`` extra is
    installed. Open Graph / Twitter crawlers do not render SVG, so the PNG is
    the image social platforms actually show; locally (no cairosvg) the SVG
    remains the only artifact and nothing fails."""
    try:
        import cairosvg  # type: ignore[import-not-found]
    except ImportError:
        print("info: cairosvg not installed, skipping og-cover.png (pip install cairosvg)", file=sys.stderr)
        return None
    return cairosvg.svg2png(
        bytestring=svg_text.encode("utf-8"),
        output_width=1200,
        output_height=630,
    )


def write_seo_assets(data: dict[str, Any], window_snapshot: dict[str, Any] | None = None) -> None:
    SITEMAP_PATH.write_text(render_sitemap(data), encoding="utf-8")
    FEED_PATH.write_text(render_feed(data, window_snapshot=window_snapshot), encoding="utf-8")
    OG_COVER_PATH.parent.mkdir(parents=True, exist_ok=True)
    svg_text = render_og_cover(data)
    OG_COVER_PATH.write_text(svg_text, encoding="utf-8")
    png_bytes = render_og_cover_png(svg_text)
    if png_bytes:
        OG_COVER_PNG_PATH.write_bytes(png_bytes)


def main() -> int:
    parser = argparse.ArgumentParser(description="Update academic research skill rankings")
    parser.add_argument("--config", default=str(CONFIG_PATH), help="Path to ranking config JSON")
    parser.add_argument("--offline-fixture", help="Use a local JSON list of repository objects instead of GitHub API")
    parser.add_argument(
        "--recompute",
        action="store_true",
        help="Re-apply filtering, classification, and rendering to existing data/rankings.json without calling GitHub API",
    )
    args = parser.parse_args()

    config = load_config(Path(args.config))
    if args.recompute:
        existing = load_json(DATA_PATH, {})
        existing_items = existing.get("items", []) if isinstance(existing, dict) else []
        repos = [item_to_repo_input(item) for item in existing_items]
        gen_ts = parse_datetime((existing.get("metadata") or {}).get("generated_at"))
        data, window_snapshot = build_dataset(
            config,
            repos,
            enrich_skills=False,
            now=gen_ts,
            overwrite_today_snapshot=True,
        )
    elif args.offline_fixture:
        repos = load_json(Path(args.offline_fixture), [])
        data, window_snapshot = build_dataset(config, repos, enrich_skills=False)
    else:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        repos = collect_repositories(config, token)
        data, window_snapshot = build_dataset(config, repos, token=token)
    write_outputs(data, window_snapshot=window_snapshot)
    print(f"updated {len(data['items'])} repositories at {data['metadata']['generated_at']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
