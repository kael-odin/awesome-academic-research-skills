import unittest
from datetime import datetime, timedelta, timezone

from scripts.update_rankings import (
    classify_repo,
    compute_trend_score,
    find_window_snapshot,
    is_academic_skill_repo,
    rank_repositories,
    render_readme,
)


class RankingRulesTest(unittest.TestCase):
    def test_accepts_academic_skill_repository(self):
        repo = {
            "nameWithOwner": "example/academic-paper-skills",
            "description": "Claude Code skill for literature review, paper writing, and peer review",
            "repositoryTopics": {
                "nodes": [
                    {"topic": {"name": "academic-writing"}},
                    {"topic": {"name": "paper-review"}},
                ]
            },
            "stargazerCount": 240,
        }

        accepted, reasons = is_academic_skill_repo(repo, min_stars=100)

        self.assertTrue(accepted)
        self.assertIn("skill", reasons)
        self.assertIn("paper", reasons)

    def test_rejects_low_star_and_non_academic_repository(self):
        repo = {
            "nameWithOwner": "example/todo-agent-skill",
            "description": "Agent skill for todo lists and daily notes",
            "repositoryTopics": {"nodes": [{"topic": {"name": "productivity"}}]},
            "stargazerCount": 12,
        }

        accepted, reasons = is_academic_skill_repo(repo, min_stars=100)

        self.assertFalse(accepted)
        self.assertIn("below_min_stars", reasons)

    def test_rejects_generic_research_first_developer_tool(self):
        repo = {
            "nameWithOwner": "example/agent-harness",
            "description": "Skills, memory, security, and research-first development for Claude Code and Codex",
            "repositoryTopics": {"nodes": [{"topic": {"name": "developer-tools"}}]},
            "stargazerCount": 200000,
        }

        accepted, reasons = is_academic_skill_repo(repo, min_stars=100)

        self.assertFalse(accepted)
        self.assertIn("missing_strong_academic_signal", reasons)

    def test_rejects_prompt_paper_resource_list_without_skill_signal(self):
        repo = {
            "nameWithOwner": "example/prompt-engineering-guide",
            "description": "Guides, papers, lessons, notebooks and resources for prompt engineering and AI agents",
            "repositoryTopics": {"nodes": [{"topic": {"name": "papers"}}]},
            "stargazerCount": 70000,
        }

        accepted, reasons = is_academic_skill_repo(repo, min_stars=100)

        self.assertFalse(accepted)
        self.assertIn("missing_skill_signal", reasons)

    def test_rejects_research_library_without_skill_signal(self):
        repo = {
            "nameWithOwner": "example/py-research-library",
            "description": "A Python library for experiments, benchmarks, and research datasets",
            "repositoryTopics": {"nodes": [{"topic": {"name": "research"}}]},
            "stargazerCount": 9000,
        }

        accepted, reasons = is_academic_skill_repo(repo, min_stars=100)

        self.assertFalse(accepted)
        self.assertIn("missing_skill_signal", reasons)

    def test_rejects_coding_knowledge_graph_that_only_mentions_papers(self):
        repo = {
            "nameWithOwner": "example/graphify",
            "description": "AI coding assistant skill for Claude Code. Turn code, docs, papers, images, or videos into a knowledge graph.",
            "repositoryTopics": {"nodes": [{"topic": {"name": "skills"}}]},
            "stargazerCount": 70000,
        }

        accepted, reasons = is_academic_skill_repo(repo, min_stars=100)

        self.assertFalse(accepted)
        self.assertIn("missing_high_confidence_academic_signal", reasons)

    def test_accepts_chinese_academic_skill_repository(self):
        repo = {
            "nameWithOwner": "example/supervisor-skills",
            "description": "将博导十年科研经验炼化为可直接调用的 AI 技能。从 Idea 构思到论文投稿。",
            "repositoryTopics": {"nodes": [{"topic": {"name": "skills"}}]},
            "stargazerCount": 3000,
        }

        accepted, reasons = is_academic_skill_repo(repo, min_stars=100)

        self.assertTrue(accepted)
        self.assertIn("科研", reasons)

    def test_accepts_trusted_seed_with_general_science_scope(self):
        repo = {
            "nameWithOwner": "example/scientific-agent-skills",
            "description": "Ready-to-use Agent Skills for research, science, engineering, analysis, finance and writing",
            "repositoryTopics": {"nodes": []},
            "stargazerCount": 240,
        }

        accepted, reasons = is_academic_skill_repo(
            repo,
            min_stars=100,
            trusted_repositories={"example/scientific-agent-skills"},
        )

        self.assertTrue(accepted)
        self.assertIn("trusted_seed", reasons)

    def test_classifies_by_dominant_research_signal(self):
        repo = {
            "nameWithOwner": "example/deep-research-skill",
            "description": "Deep research skill for source validation and literature survey",
            "repositoryTopics": {"nodes": []},
        }

        category = classify_repo(repo)

        self.assertEqual(category["id"], "deep-research")

    def test_trend_score_rewards_recent_growth_and_recency(self):
        repo = {
            "stargazerCount": 500,
            "pushedAt": "2026-06-29T00:00:00Z",
            "createdAt": "2026-06-01T00:00:00Z",
        }
        previous = {"stars": 450}
        now = datetime(2026, 6, 30, tzinfo=timezone.utc)

        score = compute_trend_score(repo, previous, now=now)

        self.assertGreater(score, 50)

    def test_ranking_filters_and_orders_repositories(self):
        repos = [
            {
                "nameWithOwner": "example/a-paper-skill",
                "description": "Academic paper writing skill",
                "repositoryTopics": {"nodes": []},
                "stargazerCount": 110,
                "pushedAt": "2026-06-29T00:00:00Z",
                "createdAt": "2026-01-01T00:00:00Z",
                "url": "https://github.com/example/a-paper-skill",
            },
            {
                "nameWithOwner": "example/b-paper-skill",
                "description": "Academic paper writing skill",
                "repositoryTopics": {"nodes": []},
                "stargazerCount": 220,
                "pushedAt": "2026-06-29T00:00:00Z",
                "createdAt": "2026-01-01T00:00:00Z",
                "url": "https://github.com/example/b-paper-skill",
            },
            {
                "nameWithOwner": "example/random-agent",
                "description": "General coding helper",
                "repositoryTopics": {"nodes": []},
                "stargazerCount": 900,
                "pushedAt": "2026-06-29T00:00:00Z",
                "createdAt": "2026-01-01T00:00:00Z",
                "url": "https://github.com/example/random-agent",
            },
        ]

        ranked = rank_repositories(repos, min_stars=100, previous_snapshot={})

        self.assertEqual([item["repo"] for item in ranked], ["example/b-paper-skill", "example/a-paper-skill"])
        self.assertEqual([item["rank"] for item in ranked], [1, 2])

    def test_seven_day_delta_uses_window_snapshot(self):
        """star_delta_7d should reflect growth since the 7-day-ago snapshot."""
        repos = [
            {
                "nameWithOwner": "example/growing-skill",
                "description": "Academic research skill",
                "repositoryTopics": {"nodes": []},
                "stargazerCount": 500,
                "pushedAt": "2026-06-29T00:00:00Z",
                "createdAt": "2026-01-01T00:00:00Z",
                "url": "https://github.com/example/growing-skill",
            },
        ]
        # 7 days ago the repo had 420 stars; previous run saw 498.
        window_snapshot = {"example/growing-skill": {"stars": 420}}
        previous_snapshot = {"example/growing-skill": {"stars": 498}}

        ranked = rank_repositories(
            repos,
            min_stars=100,
            previous_snapshot=previous_snapshot,
            window_snapshot=window_snapshot,
        )

        self.assertEqual(ranked[0]["star_delta_7d"], 80)
        self.assertEqual(ranked[0]["star_delta_1d"], 2)
        # 80 stars in a week should mark it as rising at minimum.
        self.assertIn(ranked[0]["trend"]["id"], ("rising", "hot"))

    def test_seven_day_delta_falls_back_to_one_day_when_no_history(self):
        repos = [
            {
                "nameWithOwner": "example/skill",
                "description": "Academic research skill",
                "repositoryTopics": {"nodes": []},
                "stargazerCount": 150,
                "pushedAt": "2026-06-29T00:00:00Z",
                "createdAt": "2026-01-01T00:00:00Z",
                "url": "https://github.com/example/skill",
            },
        ]
        previous_snapshot = {"example/skill": {"stars": 140}}

        ranked = rank_repositories(
            repos,
            min_stars=100,
            previous_snapshot=previous_snapshot,
            window_snapshot=None,
        )

        # No window snapshot → fall back to the 1-day delta.
        self.assertEqual(ranked[0]["star_delta_7d"], 10)

    def test_find_window_snapshot_tolerates_missing_days(self):
        today = datetime(2026, 6, 30, tzinfo=timezone.utc)
        # History has a snapshot from 9 days ago but nothing at exactly 7.
        history = {
            (today - timedelta(days=9)).date().isoformat(): {"example/skill": {"stars": 100}},
        }

        snapshot = find_window_snapshot(history, today, window_days=7)

        self.assertIsNotNone(snapshot)
        self.assertIn("example/skill", snapshot)

    def test_render_readme_shows_all_categories_in_fixed_order(self):
        """The category overview must list every category, even zero-count ones,
        in the fixed CATEGORIES order — not a sorted/partial list."""
        repos = [
            {
                "nameWithOwner": "example/deep-research-skill",
                "description": "Deep research skill for source validation",
                "repositoryTopics": {"nodes": []},
                "stargazerCount": 200,
                "pushedAt": "2026-06-29T00:00:00Z",
                "createdAt": "2026-01-01T00:00:00Z",
                "url": "https://github.com/example/deep-research-skill",
            },
        ]
        ranked = rank_repositories(repos, min_stars=100, previous_snapshot={})
        data = {
            "metadata": {"generated_at": "2026-06-30T00:00:00Z", "min_stars": 100, "total": 1},
            "items": ranked,
        }

        readme = render_readme(data)

        # Every category label must appear, so counts always add up.
        for label in ["深度研究", "论文写作", "文献综述", "评审反馈", "实验复现", "学科专项", "综合研究"]:
            self.assertIn(label, readme)
        # The overview line itself must be in fixed order: extract just that line
        # and check the labels appear there in the CATEGORIES sequence.
        overview_line = next(line for line in readme.splitlines() if "分类概览" in line)
        positions = [overview_line.index(label) for label in ["深度研究", "论文写作", "文献综述", "评审反馈", "实验复现", "学科专项", "综合研究"]]
        self.assertEqual(positions, sorted(positions))

    def test_render_readme_newcomers_only_when_history_exists(self):
        """Newcomers block should appear only when a 7-day-ago snapshot exists
        and the repo was not in it. No history → no block (avoid a first-run flood)."""
        repos = [
            {
                "nameWithOwner": "example/new-skill",
                "description": "Academic research skill",
                "repositoryTopics": {"nodes": []},
                "stargazerCount": 150,
                "pushedAt": "2026-06-29T00:00:00Z",
                "createdAt": "2026-01-01T00:00:00Z",
                "url": "https://github.com/example/new-skill",
            },
        ]
        ranked = rank_repositories(repos, min_stars=100, previous_snapshot={})
        data = {
            "metadata": {"generated_at": "2026-06-30T00:00:00Z", "min_stars": 100, "total": 1},
            "items": ranked,
        }

        # No history at all → no newcomers section.
        self.assertNotIn("## 本周新收录", render_readme(data, window_snapshot=None))

        # A non-empty 7-day-ago snapshot that lacks this repo → newcomer.
        window_snapshot = {"example/other-skill": {"stars": 100}}
        readme = render_readme(data, window_snapshot=window_snapshot)
        self.assertIn("## 本周新收录", readme)
        self.assertIn("example/new-skill", readme)


if __name__ == "__main__":
    unittest.main()
