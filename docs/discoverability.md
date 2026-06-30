# 可发现性清单（一次性设置）

这份清单上的项目需要在 **GitHub 网页 UI** 上手动设置，脚本无法代劳。它们是别人能不能找到你仓库的前提，请逐项完成。

## 1. 仓库 About 描述与 Topics（最重要）

进入仓库主页 → 右侧 About 一栏的齿轮图标：

**Description**（建议文案，中英双语任选其一）：

```
面向中文用户的学术论文与科研 Agent Skill 每日排行榜 · 自动搜索、过滤并排名 GitHub 上的 Claude Code / Codex / OpenCode 科研 Skill 仓库
```

或英文：

```
A daily-updated ranking of GitHub repositories providing academic, paper-writing, deep-research, and peer-review skills for AI coding agents.
```

**Topics**（最多 20 个，建议至少加这些）：

```
awesome-list  academic-research  research-skills  agent-skills  claude-code
codex  opencode  paper-writing  literature-review  deep-research
peer-review  scientific-research  ai-agents  mcp  phd
academic-writing  daily-update  ranking  curated-list
```

> Topics 是 GitHub 搜索和话题页（github.com/topics）抓取的主要依据，直接影响曝光。

## 2. 仓库网址（Homepage）

在同一个 About 面板里，把 Homepage 设为 GitHub Pages 地址：

```
https://kael-odin.github.io/awesome-academic-research-skills/
```

这样仓库卡片右侧会显示一个可点击的可视化页面入口。

## 3. Releases

虽然是数据型仓库，但建议打一个 `v1.0` tag 并发布 Release，描述"首个稳定版：21 个仓库、7 天趋势、双语可视化"。Release 会出现在 GitHub 的 explore / email digest 里。

## 4. 默认分支保护（可选但推荐）

Settings → Branches → 给 `main` 加规则：要求 PR 通过测试再合并。这能防止误提交破坏自动化。

## 5. Issue 模板已就绪

`.github/ISSUE_TEMPLATE/recommend-repo.yml` 已创建。用户点 New Issue 时会看到"推荐新仓库"模板，降低贡献门槛。

## 6. SEO 元数据

`index.html` 已包含 `<meta name="description">`。如需进一步 SEO，可在 Pages 页面根目录加 `robots.txt` 和 `sitemap.xml`（可选）。

## 7. 推广（设置完成后）

- 在相关仓库的 Issue / Discussions 里**适度**介绍（避免垃圾营销）。
- 在知乎、小红书、V2EX、即刻、X 等平台发一条"我做了个每日自动更新的科研 Agent Skill 排行榜"。
- 提交到 [awesome](https://github.com/sindresorhus/awesome) 列表的 `awesome-ai` / `awesome-claude-code` 等子列表（需符合它们的格式要求）。
- 在被收录的高星仓库的 README/Discussion 里提一句"已收录到 awesome-academic-research-skills 榜单"（征得作者同意）。
