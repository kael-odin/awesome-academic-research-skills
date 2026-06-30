# Contributing

欢迎推荐新的学术研究 Skill 仓库。

## 收录标准

- 仓库必须明确服务学术、科研、论文、文献、评审或实验复现场景。
- 仓库必须具备 Skill、Agent、Workflow、Prompt、Claude Code、Codex、OpenCode 或类似可复用工作流信号。
- 默认最低门槛为 100 Stars。
- fork、归档仓库、明显非学术用途仓库不会收录。

## 推荐方式

1. 提交 Issue，附上仓库链接和一句推荐理由。
2. 或修改 `config/ranking.json` 的 `seed_repositories` 并提交 PR。
3. 运行：

```bash
python scripts/update_rankings.py
python -m unittest discover -s tests -v
```

English recommendations are welcome. Please include why the repository is useful for academic or research workflows.
