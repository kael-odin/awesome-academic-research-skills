# 排名方法

本仓库使用可解释规则筛选学术研究 Skill 仓库，避免泛 AI 项目、普通论文列表或通用 Agent 框架混入榜单。所有规则都在 [`scripts/update_rankings.py`](../scripts/update_rankings.py) 中实现，可审计、可复现。

## 候选发现

- `config/ranking.json` 中的 `seed_repositories` 会被直接拉取元数据。
- `search_queries` 通过 GitHub Search API 搜索候选仓库（限定 `stars:>=100 fork:false archived:false`）。
- 每次更新都会按 `nameWithOwner` 去重。

## 精准过滤

仓库需要**同时**满足：

- Stars 达到 `min_stars`（默认 100）。
- 不是 fork。
- 未归档。
- 命中至少一个 Skill/Agent/Workflow 信号（`skill`、`claude code`、`codex`、`opencode`、`mcp`、`workflow` 等）。
- 命中至少一个 Academic/Research/Paper 信号（`academic`、`paper`、`literature`、`peer review`、`科研`、`论文` 等）。
- 进一步要求**强信号**与**高置信度学术信号**命中（或属于可信种子仓库）。
- 未命中明显非学术排除词（`leetcode`、`trading`、`minecraft` 等）。

> 这套"双重信号 + 强信号"机制是榜单质量的核心：它把单纯"AI 论文列表"或"通用 Agent 框架"挡在门外，只保留真正把科研流程封装成可复用 Skill 的仓库。

## 趋势分

趋势分由以下信号加权组成：

- **近 7 天新增 Stars**（`star_delta_7d`）—— 主信号，权重 1.2。
- 最近 push 的时间新鲜度（90 天内衰减）。
- 新仓库加权（180 天内衰减）。
- 当前 Stars 规模（`log10` 平滑）。

### 为什么用 7 天而不是 1 天？

早期版本对比单日 Stars 增量（`star_delta_1d`），但 GitHub API 返回的计数在 24 小时内经常不变，导致趋势几乎恒为 0、所有仓库都显示"稳定"。改用 7 天滚动窗口后，趋势能真实反映一周内的增长势头。

### 历史快照

每日运行会把当天榜单保存到 `data/history/YYYY-MM-DD.json`（保留近 60 天）。趋势分和"本周新收录"都基于这些快照计算：

- `star_delta_7d` = 今日 Stars − 7 天前快照中的 Stars（容忍缺失天数，向前查找最近可用快照）。
- `star_delta_30d` = 今日 Stars − 30 天前快照中的 Stars（同样容忍缺失；无更长历史时退化为 7 天值）。
- `data/history.js` = 近 60 天每仓库的 `[{date, stars}]` 序列，供前端 sparkline 渲染（缺失天数自动跳过，曲线连接可用点）。
- "本周新收录" = 当前榜单中、但 7 天前快照中没有的仓库。

首次运行（无历史快照）时，`star_delta_7d` 退化为 `star_delta_1d`，`star_delta_30d` 退化为 `star_delta_7d`，且不显示新收录区块——避免首日刷屏。

## 主排序

主榜单按 **Stars 降序** 排列，趋势分作为辅助识别近期上升仓库。可视化页面支持按趋势、Stars、最近更新重新排序。

## 分类

每个仓库按关键词命中数归入 7 个分类之一（见 README）。分类按固定优先级匹配，确保结果稳定。

## 数据字段

`data/rankings.json` 中每个仓库包含：

- 基础：`repo`、`stars`、`star_delta_1d` / `star_delta_7d` / `star_delta_30d`、`trend_score`、`trend`、`category`、`description`、`language`、`topics`、`url`、`homepage`。
- 丰富：`forks`、`open_issues`、`watchers`、`size_kb`、`default_branch`、`has_issues`、`has_wiki`、`has_discussions`、`license`（含 `key` / `name` / `spdx_id`）。
- 审计：`precision_signals`（命中的精准过滤信号，便于复现与调试）。

所有字段均为**只新增不删除**，旧消费者向前兼容。CSV（`data/rankings.csv`）包含上述基础 + 丰富字段的扁平子集。

## SEO 与订阅资产

每次更新同步生成（见 `scripts/update_rankings.py` 的 `write_seo_assets`）：

- `sitemap.xml` — 首页 + README + 数据端点 + 文档，带 `lastmod` / `changefreq` / `priority`。
- `feed.xml` — RSS 2.0，每日条目 = 本周新收录 + 7 天趋势前 10，含 `atom:self` 自引用。
- `assets/og-cover.svg` — 1200×630 Open Graph 封面，展示当日总量、总 Stars、更新日期与榜首仓库。
- `robots.txt` — 允许全部抓取并指向 sitemap。
- `index.html` 内嵌 JSON-LD `ItemList`（前端动态填充前 20 名）。

这些资产让搜索引擎、社交平台与 RSS 阅读器都能稳定发现并展示榜单。
