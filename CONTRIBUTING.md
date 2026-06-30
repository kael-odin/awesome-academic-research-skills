# Contributing

欢迎推荐新的学术研究 Skill 仓库，或改进排名规则。

## 收录标准

- 仓库必须明确服务学术、科研、论文、文献、评审或实验复现场景。
- 仓库必须具备 Skill、Agent、Workflow、Prompt、Claude Code、Codex、OpenCode 或类似可复用工作流信号。
- 默认最低门槛为 100 Stars（可在 [`config/ranking.json`](config/ranking.json) 调整）。
- fork、归档仓库、明显非学术用途仓库不会收录。

## 推荐方式

### 方式一：提 Issue（最简单）

使用 [推荐新仓库模板](https://github.com/kael-odin/awesome-academic-research-skills/issues/new?labels=recommendation&template=recommend-repo.yml) 提交，附上仓库链接和一句推荐理由。维护者会评估并加入种子列表。

### 方式二：提 PR

1. Fork 仓库。
2. 在 [`config/ranking.json`](config/ranking.json) 的 `seed_repositories` 中加入仓库全名（`owner/repo`）。
3. 本地验证：

```bash
python scripts/update_rankings.py
python -m unittest discover -s tests -v
```

4. 提交 PR，说明推荐理由。

## 改进规则

排名规则全部在 [`scripts/update_rankings.py`](scripts/update_rankings.py) 中，可审计。如果你想：

- 调整过滤信号 / 排除词 → 修改 `SKILL_TERMS`、`ACADEMIC_TERMS`、`NEGATIVE_TERMS`。
- 调整分类关键词 → 修改 `CATEGORIES`。
- 调整趋势窗口 / 历史保留天数 → 修改文件顶部的 `DELTA_WINDOW_DAYS`、`HISTORY_RETENTION_DAYS`。

任何规则改动请补充对应测试（[`tests/test_ranking.py`](tests/test_ranking.py)）。

## 历史快照说明

每日运行会在 `data/history/` 下生成日期命名的快照（保留近 60 天），用于计算 7 天 Stars 增量和"本周新收录"。PR 不需要手动维护这些文件，由 GitHub Actions 自动生成。详见 [`docs/methodology.md`](docs/methodology.md)。

---

English contributions are welcome. Please include why the repository is useful for academic or research workflows. The simplest path is to open an issue with the repository URL and a one-line reason; a maintainer will add it to the seed list.
