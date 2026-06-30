# Methodology

本仓库使用可解释规则筛选学术研究 Skill 仓库，避免泛 AI 项目、普通论文列表或通用 Agent 框架混入榜单。

## Candidate discovery

- `config/ranking.json` 中的种子仓库会被直接拉取。
- `search_queries` 会通过 GitHub Search API 搜索候选仓库。
- 每次更新都会去重。

## Precision filter

仓库需要同时满足：

- Stars 达到 `min_stars`。
- 不是 fork。
- 未归档。
- 命中至少一个 Skill/Agent/Workflow 信号。
- 命中至少一个 Academic/Research/Paper 信号。
- 未命中明显非学术排除词。

## Trend score

趋势分由以下信号组成：

- 相比上次快照的新增 Stars。
- 最近 push 的时间。
- 新仓库加权。
- 当前 Stars 规模。

主榜仍按 Stars 排序，趋势分用于辅助识别近期上升仓库。可视化页面支持按趋势重新排序。
