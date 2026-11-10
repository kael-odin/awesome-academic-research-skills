# 更新日志 · Changelog

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。数据型仓库的"功能"指榜单 / 脚本 / 可视化能力，而非仓库数据本身（数据每日自动更新）。

## v2.4 — 2026-11-10

视觉与可用性整修：消除暗色首屏闪烁，修复隐藏元素失效，补齐分页与粘性表头，收紧焦点与对比度，月报并入期刊体系（44/44 测试通过）。

### 首屏与主题

- **暗色首屏不再闪白**：两个主站 `<head>` 在样式表之前加入阻塞式主题引导脚本；有存储偏好时首帧即深色，未选择时跟随系统。`html.preload` 在加载完成前禁用 `body` 的 0.25s 颜色过渡，消除浅→深淡入。新增 `color-scheme`，原生下拉与滚动条随主题切换。
- **主题状态单一来源**：初始化先读 URL 再应用主题；修复旧 `#theme=dark` 书签与 localStorage 不同步、按 `t` 看似无效的问题。`/en/` 上手动切换的语言在刷新后保持。

### 布局与扫读

- **修复 `[hidden]` 被作者样式覆盖**：全局 `[hidden]{display:none!important}`；空对比条不再常驻页面，切换视图后隐藏的卡片网格不再撑高文档（此前 375px 下可达 65,597px）。
- **表格重做**：固定布局与列宽，1440px 下不再横向溢出；摘要两行截断；日期不换行；表格容器限高并成为滚动容器，表头真正粘性。
- **分页**：每页 25 条，带页码、上一页/下一页、`aria-current` 与跳转后回滚到榜单顶部；筛选、搜索、排序后自动回到第 1 页；结果计数改为「显示 1–25 / 116」。
- **移动端**：手机默认卡片视图（忽略桌面保存的表格偏好）；隐藏重复的 Hero 目录；统计卡两列；视图切换不再撑成空胶囊。

### 无障碍与细节

- **弹层焦点**：抽屉与对比弹层打开后把焦点移入、Tab 循环、背景 `inert`、锁定滚动；关闭后焦点回到触发元素。弹层打开时全局快捷键不再作用于背景。
- **对比度**：焦点环改为实色（浅色 5.9:1 / 深色 9:1）；次要文字 `--ars-faint` 提升到 4.5:1 以上；收藏星未选中时可见，hover 变为金色。
- **10px 界面标签统一提升到 11px**（表头、筛选标签、抽屉字段名、信号标签）；表格行与目录行支持空格键。
- **文案**：中文页 TOC 页脚与 Skills 徽章中文化；`.muted` 补上样式规则；`.hero-hint` 不再被 `.hero p` 覆盖成 17px 正文。

### 月报

- 月报页并入期刊体系：共享报头（品牌、返回榜单、全部月报、主题切换）与页脚，衬线大标题、去 emoji 章节标题、表格链接与暗色模式对齐主站。已冻结的历史月报（2026-07 至 2026-10）同步升级模板，并保留原有数据。

## v2.3 — 2026-11-09

精准分类重塑、假阳性剔除、月报与英文站 Bug 修复，以及看板快速筛选与轨迹可视化升级（42/42 测试通过）。

### 排名脚本与数据质量

- **词边界与驼峰切分匹配（`_term_in_corpus`）**：纯 ASCII 关键词改为词边界 + 可选复数匹配（`(?<![a-z])term s?(?![a-z])`），并对仓库名做驼峰切分（`TopJournal` → `Top Journal`），彻底消除 `"roo"` 误匹配 `"p[roo]freading"`、`"law"` 误匹配 `"dr-claw"`、`"ml"` 误匹配 `"html"` 等子串碰撞，同时保留 `journals` / `workflows` / `academics` 等复数命中。
- **剔除 4 个假阳性仓库**：将 `"pipeline"` 从强技能信号移除（避免 `alephpi/Texo` 等仅含训练 pipeline 的 OCR 模型入榜），并扩充排除规则拦截论文阅读清单（`VoltAgent/awesome-ai-agent-papers`）、影子图书馆资源站（`hoochanlon/hamuleite`）与非 AI 自学指南（`zheng95z/teach-yourself-research`）。
- **分类算法修复与中英双语词表**：
  - 修复 `classify_repo` 初始 `best_score = -1` 导致零命中中文仓库全部落入 `deep-research`（`CATEGORIES[0]`）而非 `general-research`（`CATEGORIES[-1]`）的 Bug。
  - 为全部 7 个分类补齐中英双语关键词，引入仓库名权重加成与多阶段（≥3 个科研阶段）归入「综合研究」机制，解决了此前 `general-research` 吞噬专类仓库（54 → 17）及「评审反馈」长期为 0 的问题。
- **Agent 识别与引用核验扩充**：识别 `claude-skill` / `Claude Skill` / `Codex / Claude` 等写法（找回 4 个漏标仓库）；扩充 `CITATION_VERIFICATION_TERMS`（覆盖 `reference-checker`、`source credibility`、`evidence-grounded`、`可追溯文献`、`证据审计` 等，核验仓库从 2 个增至 9 个）。
- **新增 `--recompute` 离线重算模式与同日快照幂等**：支持不消耗 GitHub API 配额直接基于本地 `data/rankings.json` 与 `data/history/` 秒级重算并刷新全套产物；`build_dataset` 优先读取前一自然日快照计算 `star_delta_1d`，避免同日重跑将日增量清零。
- **月报与 Sitemap 修复**：修复月中新收录仓库因 `dates[0]` 缺失而月增量恒为 `+0` 的 Bug；合并磁盘已冻结历史月报（`2026-07`、`2026-08`）到 `reports/index.html`、月报导航栏与 `sitemap.xml`，防止 60 天快照回收后旧月报入口丢失；月报页同步支持深色模式与响应式表格。

### 可视化与交互（前端）

- **快速质量筛选栏 + 实时结果计数**：表格上方新增 `🔥 热门上升`、`✓ 引用核验`、`📦 含 SKILL.md`、`✨ 排除停更` 一键筛选胶囊、一键 `↺ 重置筛选` 与 `显示 X / Y 个仓库` 实时计数，全部状态同步至 URL `#hash`。
- **新增排序维度**：支持按 `7 天增量`（`delta7`）与 `Skills 数量`（`skills`）直接排序。
- **可交互目录（Hero TOC）与统计条**：点击「本期目录」任意分类或统计条分类分布可直接筛选并平滑滚动至主榜；点击「最热仓库」卡片直接打开该仓库详情抽屉并显示 7d 增量。
- **详情抽屉 60 天星标轨迹图**：抽屉内新增带起止日期与区间增量的完整星标历史曲线卡片。
- **增长对比图按真实日历对齐**：修复新旧仓库按数组下标强行拉伸至同一宽度的失真问题，改为按真实日期轴对齐并标注起止日期、Y 轴百分比刻度及图例总增幅。
- **修复 `/en/` 英文站默认语言覆盖与 JSON-LD URL**：访问中文主站不再污染 `/en/` 的默认英文语言设置，`/en/` 的 JSON-LD `url` 保持独立规范地址。

## v2.2 — 2026-09-27

从"发现"走向"信任与使用"：新增质量信号、月度报告、独立英文页与一批让榜单可以直接用的交互。

### 排名脚本与数据

- **`max_results` 100 → 150**：搜索翻页后收录量触及旧上限，放宽到 150。
- **`skills_count` 字段**：每日用 git trees API 统计每个仓库的 `SKILL.md` 数量（API 失败为 `null`，大仓库在 GitHub 截断树时为下界）——比 Stars 更贴近"实用性"的硬信号。
- **`stale` 字段**：超过 30 天无 push 且 7 天零 Star 增长的仓库标记为"疑似停更"（两条件同时满足才标记，保守策略）。
- **`verifies_citations` 字段**：按描述/主题关键词识别是否宣传"引用核验 / 零幻觉文献 / source validation"——文献与深研类仓库最关键的差异点。
- **月度报告**：`reports/YYYY-MM.html` 每月自动总结新收录、上升前 10、停滞与跌出仓库；历史月份页面一旦生成就冻结，不受 60 天快照回收影响。入口在 `reports/index.html`。
- 以上新字段均同步进 CSV；README / sitemap 新增 English Dashboard、月报入口。

### 可视化与交互（前端）

- **科研阶段导航**：分类条改为固定科研阶段顺序（① 深度研究 → ② 文献综述 → ③ 实验复现 → ④ 论文写作 → ⑤ 评审反馈 → ⑥ 学科专项 → ⑦ 综合），与真实科研流程对齐。
- **质量徽章**：表格 / 卡片 / 抽屉展示 `N skills`、`引用核验 ✓`、`疑似停更` 徽章；抽屉统计行新增 Skills 数。
- **一键复制安装命令**：抽屉内复制 `npx skills add owner/repo`（skills.sh 标准 CLI），把"看榜"变成"装上"。
- **详情深链**：抽屉状态写入 URL hash（`#repo=owner/name`），任意条目可分享直达。
- **增长对比**：勾选最多 3 个仓库（表格 / 卡片的 ⇄ 按钮），底部托盘 + 弹层叠加显示相对各自窗口起点的 Star 增长百分比曲线。
- **订阅入口前移**：头部新增 RSS 与月报按钮。
- **独立英文页 `/en/`**：英文为默认语言的完整镜像页（`hreflang` 双向标注、独立 canonical / OG / JSON-LD），主站保留中文优先 + 手动切换。
- **修复**：sparkline 与趋势色引用了不存在的 CSS 变量（`--ars-line` / `--ars-accent` / `--ars-trend-hot-fg`），颜色一直走无效回退，已改为真实 token（`--ars-rule` / `--ars-ember` / `--ars-teal` / `--ars-faint`）。

### 发布管道（CI/CD）

- **PR 推荐自动核验**：`verify-pr.yml` 在改动了 `config/ranking.json` 的 PR 上自动提取新增种子仓库，逐个调 GitHub API 核对收录标准（≥100★、非 fork、未归档），以表格评论贴到 PR（同 PR 更新而非新增评论）。

### 测试

- 新增 9 个测试（SKILL.md 计数、stale 判定、引用核验、月报渲染、字段输出），共 34/34 通过。

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
