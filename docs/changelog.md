# 更新日志 · Changelog

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。数据型仓库的"功能"指榜单 / 脚本 / 可视化能力，而非仓库数据本身（数据每日自动更新）。

## v2.1 — 2026-09-27

工程质量与发布管道修复，全部改动有测试覆盖（29/29 通过）。

### 排名脚本与数据

- **榜单不再收录自身**：新增 `exclude_repositories` 配置（默认排除本仓库），排行榜不再把自己排进榜。
- **搜索翻页 + 限流退避**：每个查询最多抓 2 页（per_page 50 → 100），长尾仓库可被发现；`github_request` 对 403/429/5xx 按 `Retry-After` / 指数退避重试，查询间隔放宽以守住 Search API 30 次/分钟上限。
- **RSS 规范化**：`pubDate` / `lastBuildDate` 从 ISO 8601 改为 RSS 2.0 要求的 RFC-822 格式。
- **Sitemap 规范化**：移除 `#english` 锚点 URL（sitemap 协议不允许 fragment）。
- **数据脚本瘦身**：`rankings.js` / `history.js` 改用紧凑 JSON 分隔符（history.js 约 204KB → 约 70KB），并在 `index.html` 中以 `defer` 加载。

### 发布管道（CI/CD）

- **新增 PR CI**：`.github/workflows/ci.yml` 在 pull_request / push 时校验 JSON 并跑全部测试——此前 PR 没有任何机器验证。
- **update workflow 并发保护**：加 `concurrency` 组，避免手动触发与定时跑的 auto-commit 互相冲突。
- **失败通知去重**：连续失败时改为在已有 `auto-update-failure` issue 下追加评论，不再每天开新 issue。
- **Open Graph 封面 PNG 化**：CI 安装 `cairosvg` + Noto CJK 字体，每日把 `og-cover.svg` 栅格化为 `og-cover.png` 并提交（OG / Twitter 抓取器不渲染 SVG）；`index.html` 的 `og:image` / `twitter:image` 改指向 PNG。

### 杂项

- 移除 `renderTable` 中未使用的 `d30` 死代码；修复 `hashchange` 双重渲染；简化 `render_history_series` 中易误读的 `or/and` 复合条件；修正 TOC 渲染注释与实际排序不一致。
- 新增「反馈 / Bug 报告」issue 模板，并允许空白 issue。

## v2.0 — 2026-07-10

可视化重做 + 数据增强 + SEO 订阅。一次大版本升级，覆盖四个方向。

### 可视化与交互（前端）

- **设计系统**：完整 design token，明 / 暗双主题（手动切换 + `prefers-color-scheme`），渐变标题，表格数字等宽对齐。
- **双视图**：表格 + 响应式卡片网格（`auto-fill 300px`），视图状态持久化到 `localStorage`。
- **趋势 sparkline**：基于 `data/history.js` 在前端渲染内联 SVG 7d/30d 趋势曲线（无库）；无历史时降级为虚线。
- **详情抽屉**：点击任意行 / 卡片滑出右侧抽屉，展示完整元数据、topics、精准信号、适用 Agent、统计与外链。
- **收藏夹**：每行星标切换、"仅看收藏"过滤、计数徽章、导出为 JSON。
- **URL 状态分享**：`query/category/sort/view/lang/theme/favorites` 序列化进 `location.hash`，分享链接可复现视图。
- **键盘快捷键**：`/` 搜索 · `t` 主题 · `l` 语言 · `v` 视图 · `f` 收藏 · `Esc` 关闭。
- **统计概览条**：总 Stars、平均 Stars、近 7d 净增、最热仓库、分类分布 mini-bar。
- **无障碍**：跳转链接、`aria-pressed` / `aria-label`、`role=dialog`、sparkline `<title>`、`prefers-reduced-motion` 降级。

### 排名脚本与数据增强（后端）

- **丰富字段**：`rest_to_repo` 抽取 `forks_count` / `open_issues_count` / `size_kb` / `default_branch` / `has_issues` / `has_wiki` / `has_discussions` / `watchers_count` / `license`（key/name/spdx_id），并 surfacing 到每个 item。
- **30 天增量**：新增 `star_delta_30d`（30 天窗口，无更长历史时退化为 7d）。
- **历史聚合**：生成 `data/history.js`（紧凑的每仓库 `{date, stars}` 序列）供前端 sparkline。
- **信号扩充**：`SKILL_TERMS` 加 cursor / gemini / copilot / antigravity / cline / continue 等；`ACADEMIC_TERMS` 加 retrieval / grounding / systematic review / preprint / doi 及中文（综述 / 复现 / 审稿 / 引用 等）；`NEGATIVE_TERMS` 加 cheatsheet / game / fitness 等；分类关键词扩充（beamer / overleaf / physics / math / statistics / law / education 等）。
- **搜索查询**：新增 8 条查询（含中文 `科研 skill` / `论文 skill` / `文献综述 skill`）。
- **CSV**：新增 `language` / `license` / `forks` / `open_issues` / `star_delta_30d` 列。
- **测试**：新增 7 个测试（丰富字段、30d 增量、cursor 接受、cheatsheet 拒绝、历史序列），共 21/21 通过。

### SEO 与可发现性

- `robots.txt`、`sitemap.xml`（首页 + 数据端点 + 文档）、`feed.xml`（RSS 2.0，每日新收录 + 趋势上升）、`assets/og-cover.svg`（1200×630 每日封面）。
- `index.html`：Open Graph、Twitter Card、canonical、RSS 发现链接、sitemap 链接、内联 SVG favicon、JSON-LD `ItemList`。
- workflow `file_pattern` 覆盖所有新资产。

### 双语与文档

- i18n 补齐所有新增 UI 文案（视图 / 主题 / 收藏 / 快捷键 / 抽屉 / 统计 / 空状态）。
- README 特色列表与 English 段全面更新；新增 [更新日志](docs/changelog.md) 链接。
- `docs/methodology.md` 补 30 天窗口、`history.js`、数据字段、SEO 资产说明。
- `docs/discoverability.md` 更新 SEO 资产清单与 v2.0 Release 提示。
- `CONTRIBUTING.md` 新增"贡献前端样式 / 新视图"小节。
- Issue 模板新增"适用 Agent"多选。

## v1.0.0 — 2026-06-30

首个稳定版：21 个仓库、7 天趋势窗口、历史快照（60 天保留）、双语可视化、自动每日更新、GitHub Pages 部署、测试与贡献指南。
