(function () {
  "use strict";
  const data = (window.ACADEMIC_SKILLS_RANKINGS || { metadata: {}, items: [] });
  const hist = (window.ACADEMIC_SKILLS_HISTORY || { series: {} });

  const SAFE = (v, d) => (v === undefined || v === null ? d : v);

  const state = {
    lang: localStorage.getItem("ars-lang") || "zh",
    theme: localStorage.getItem("ars-theme") || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"),
    view: localStorage.getItem("ars-view") || (matchMedia("(max-width: 760px)").matches ? "card" : "table"),
    query: "",
    category: "all",
    agent: "all",
    sort: "rank",
    favorites: JSON.parse(localStorage.getItem("ars-favorites") || "[]"),
    favOnly: false,
  };

  /* Agent platform catalog — the order here is the display/sort order. */
  const AGENT_PLATFORMS = [
    { id: "claude-code", label: "Claude Code", match: ["claude code", "claude-code", "claude code skill"] },
    { id: "codex", label: "Codex", match: ["codex"] },
    { id: "opencode", label: "OpenCode", match: ["opencode", "open code", "open-code"] },
    { id: "cursor", label: "Cursor", match: ["cursor"] },
    { id: "gemini", label: "Gemini", match: ["gemini"] },
    { id: "cline", label: "Cline", match: ["cline"] },
    { id: "mcp", label: "MCP", match: ["mcp"] },
  ];

  const translations = {
    zh: {
      skipToContent: "跳到主内容",
      mastheadVol: "Vol.1",
      heroTitle: '学术论文 Skill <em>排行</em>',
      heroSubtitle: "每天自动发现、过滤并排名 GitHub 上服务论文写作、文献综述、深度研究、评审反馈和实验复现的 Agent Skill 仓库。",
      heroHint: "提示：按 <b>/</b> 聚焦搜索 · <b>t</b> 主题 · <b>l</b> 语言 · <b>v</b> 视图",
      tocTitle: "本期目录",
      repos: "收录仓库", minStars: "最低 Stars", updated: "最近更新",
      searchLabel: "搜索仓库、简介、分类", categoryLabel: "分类", allCategories: "全部分类",
      agentLabel: "平台", allAgents: "全部平台", agentGeneral: "通用",
      sortLabel: "排序", sortRank: "综合排名", sortTrend: "趋势优先", sortStars: "Stars 优先",
      sortUpdated: "最近更新", sortDelta30: "30 天增量",
      viewTable: "表格", viewCard: "卡片",
      favoritesOnly: "仅看收藏", exportFav: "导出收藏",
      tableTitle: "完整榜单", tableHint: "精准过滤：必须同时命中学术研究信号与 Skill/Agent/Workflow 信号。点击任意行查看详情。",
      downloadJson: "下载 JSON", downloadCsv: "下载 CSV",
      repo: "仓库", trend: "趋势", spark: "7d 趋势", category: "分类",
      description: "简介", updatedCol: "更新", empty: "没有匹配当前筛选条件的仓库。",
      methodTitle: "排名方法",
      methodCopy: "榜单按 Stars 主排序，并展示趋势分。趋势分综合近期新增 Stars、最近 push、新仓库加权和总体规模；低星、fork、归档及明显非学术仓库会被排除。",
      methodA: "精准信号", methodADetail: "academic/research/paper + skill/agent/workflow",
      methodB: "每日更新", methodBDetail: "GitHub Actions UTC 定时运行",
      methodC: "双语视图", methodCDetail: "中文优先，支持英文切换",
      shortcuts: "快捷键：/ 搜索 · t 主题 · l 语言 · v 视图 · f 收藏 · Esc 关闭",
      // stat strip
      statTotalStars: "总 Stars", statAvgStars: "平均 Stars", statNet7d: "近 7d 净增",
      statHotRepo: "最热仓库", statCats: "分类分布",
      // drawer
      drEyebrow: "收录条目",
      drDescription: "简介", drTopics: "Topics", drLanguage: "主要语言", drCreated: "创建时间",
      drPushed: "最近更新", drTrend: "趋势分", drSignals: "精准信号",
      drDelta1d: "日增量", drDelta7d: "7d 增量", drDelta30d: "30d 增量",
      drLicense: "许可证", drForks: "Forks", drIssues: "Open Issues",
      drAgent: "适用 Agent", drOpenRepo: "在 GitHub 打开", drHomepage: "访问主页",
      drCopyMd: "复制为 Markdown", drSuggest: "推荐本仓库收录",
      stars: "Stars", noHistory: "暂无历史数据",
      toastCopied: "已复制 Markdown 到剪贴板",
    },
    en: {
      skipToContent: "Skip to content",
      mastheadVol: "Vol.1",
      heroTitle: 'Academic Research <em>Skills</em>',
      heroSubtitle: "A daily updated ranking of GitHub repositories for paper writing, literature review, deep research, peer review, and experiment reproducibility agent skills.",
      heroHint: "Tip: press <b>/</b> to search · <b>t</b> theme · <b>l</b> language · <b>v</b> view",
      tocTitle: "In this issue",
      repos: "Repositories", minStars: "Min Stars", updated: "Updated",
      searchLabel: "Search repositories, descriptions, categories", categoryLabel: "Category", allCategories: "All categories",
      agentLabel: "Platform", allAgents: "All platforms", agentGeneral: "General",
      sortLabel: "Sort", sortRank: "Ranking", sortTrend: "Trend first", sortStars: "Stars first",
      sortUpdated: "Recently updated", sortDelta30: "30-day growth",
      viewTable: "Table", viewCard: "Cards",
      favoritesOnly: "Favorites only", exportFav: "Export favorites",
      tableTitle: "Full Ranking", tableHint: "Precision filter: must match both academic research and skill/agent/workflow signals. Click any row for details.",
      downloadJson: "Download JSON", downloadCsv: "Download CSV",
      repo: "Repository", trend: "Trend", spark: "7d trend", category: "Category",
      description: "Description", updatedCol: "Updated", empty: "No repositories match the current filters.",
      methodTitle: "Ranking Method",
      methodCopy: "Repositories are ranked mainly by Stars and enriched with a trend score. The trend score combines recent star growth, recent pushes, new-repository weighting, and overall scale.",
      methodA: "Precision signals", methodADetail: "academic/research/paper + skill/agent/workflow",
      methodB: "Daily update", methodBDetail: "Scheduled by GitHub Actions in UTC",
      methodC: "Bilingual view", methodCDetail: "Chinese first with English switching",
      shortcuts: "Shortcuts: / search · t theme · l language · v view · f favorites · Esc close",
      statTotalStars: "Total Stars", statAvgStars: "Avg Stars", statNet7d: "Net 7d growth",
      statHotRepo: "Hottest repo", statCats: "Category mix",
      drEyebrow: "Entry",
      drDescription: "Description", drTopics: "Topics", drLanguage: "Language", drCreated: "Created",
      drPushed: "Last push", drTrend: "Trend score", drSignals: "Precision signals",
      drDelta1d: "1d delta", drDelta7d: "7d delta", drDelta30d: "30d delta",
      drLicense: "License", drForks: "Forks", drIssues: "Open issues",
      drAgent: "Target agent", drOpenRepo: "Open on GitHub", drHomepage: "Visit homepage",
      drCopyMd: "Copy as Markdown", drSuggest: "Suggest this repo",
      stars: "Stars", noHistory: "No history yet",
      toastCopied: "Markdown copied to clipboard",
    },
  };

  const fmt = (v) => new Intl.NumberFormat(state.lang === "zh" ? "zh-CN" : "en-US").format(v || 0);
  const t = (k) => translations[state.lang][k] || k;
  const catName = (item) => (state.lang === "zh" ? item.category.zh : item.category.en);
  const trendName = (item) => (state.lang === "zh" ? item.trend.zh : item.trend.en);
  const esc = (s) => String(s || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  /* ---------- theme ---------- */
  function applyTheme() {
    document.documentElement.dataset.theme = state.theme;
    const btn = document.getElementById("themeToggle");
    if (btn) btn.setAttribute("aria-label", state.theme === "dark" ? "Switch to light" : "Switch to dark");
  }
  function toggleTheme() {
    state.theme = state.theme === "dark" ? "light" : "dark";
    localStorage.setItem("ars-theme", state.theme);
    applyTheme();
  }

  /* ---------- i18n ---------- */
  function setLanguage(lang) {
    state.lang = lang;
    localStorage.setItem("ars-lang", lang);
    document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
    document.querySelectorAll("[data-i18n]").forEach((n) => { n.textContent = t(n.dataset.i18n); });
    // HTML-bearing i18n (e.g. hero title with an <em> accent) is applied as
    // innerHTML so the markup survives; values are hardcoded in translations.
    document.querySelectorAll("[data-i18n-html]").forEach((n) => { n.innerHTML = t(n.dataset.i18nHtml); });
    document.querySelectorAll(".lang-button").forEach((b) => {
      const on = b.dataset.lang === lang;
      b.classList.toggle("active", on);
      b.setAttribute("aria-pressed", String(on));
    });
    document.title = (lang === "zh" ? "学术论文 Skill 排行" : "Academic Research Skills Ranking") + " · Awesome Academic Research Skills";
    populateAgentFilter();
    render();
  }

  /* ---------- agent detection ---------- */
  function detectAgents(item) {
    // Prefer the structured backend field when present; otherwise infer from
    // the text corpus so the filter works on older snapshots too.
    if (Array.isArray(item.agents) && item.agents.length) return item.agents;
    const c = [item.repo, item.description, ...(item.topics || [])].join(" ").toLowerCase();
    const found = [];
    for (const p of AGENT_PLATFORMS) {
      if (p.match.some((m) => c.includes(m))) found.push(p.id);
    }
    return found;
  }
  function agentBadge(item) {
    const ids = detectAgents(item);
    if (!ids.length) return state.lang === "zh" ? "通用" : "General";
    return ids.map((id) => (AGENT_PLATFORMS.find((p) => p.id === id) || {}).label || id).join(" · ");
  }
  function agentChips(item) {
    const ids = detectAgents(item);
    if (!ids.length) {
      return `<span class="agent-chip">${state.lang === "zh" ? "通用" : "General"}</span>`;
    }
    return ids.map((id) => {
      const p = AGENT_PLATFORMS.find((x) => x.id === id);
      return `<span class="agent-chip">${esc((p || {}).label || id)}</span>`;
    }).join("");
  }

  /* ---------- favorites ---------- */
  const isFav = (repo) => state.favorites.includes(repo);
  function toggleFav(repo) {
    const i = state.favorites.indexOf(repo);
    if (i >= 0) state.favorites.splice(i, 1); else state.favorites.push(repo);
    localStorage.setItem("ars-favorites", JSON.stringify(state.favorites));
    updateFavUI();
    render();
  }
  function updateFavUI() {
    document.getElementById("favCount").textContent = state.favorites.length;
    document.getElementById("favToggle").setAttribute("aria-pressed", String(state.favOnly));
  }

  /* ---------- sparkline ---------- */
  function sparkline(repo, w, h) {
    w = w || 100; h = h || 28;
    const points = (hist.series && hist.series[repo]) || [];
    if (!points.length) {
      return `<svg width="${w}" height="${h}" role="img" aria-label="${t("noHistory")}"><line x1="0" y1="${h / 2}" x2="${w}" y2="${h / 2}" stroke="var(--ars-line)" stroke-dasharray="3 3"/></svg>`;
    }
    const stars = points.map((p) => p.stars);
    const min = Math.min(...stars), max = Math.max(...stars);
    const range = max - min || 1;
    const step = points.length > 1 ? w / (points.length - 1) : 0;
    const coords = stars.map((s, i) => [i * step, h - 3 - ((s - min) / range) * (h - 6)]);
    const poly = coords.map((c) => `${c[0].toFixed(1)},${c[1].toFixed(1)}`).join(" ");
    const last = coords[coords.length - 1];
    const item = (data.items.find((it) => it.repo === repo) || {});
    const trendId = (item.trend || {}).id || "steady";
    const color = trendId === "hot" ? "var(--ars-trend-hot-fg)" : trendId === "rising" ? "var(--ars-accent)" : "var(--ars-muted)";
    const label = `${repo}: ${min}→${max} ⭐ (${points.length}d)`;
    return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(label)}">
      <title>${esc(label)}</title>
      <polyline points="${poly}" fill="none" stroke="${color}" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/>
      <circle cx="${last[0].toFixed(1)}" cy="${last[1].toFixed(1)}" r="2.4" fill="${color}"/>
    </svg>`;
  }

  /* ---------- filtering / sorting ---------- */
  function filteredItems() {
    const q = state.query.trim().toLowerCase();
    let items = data.items.filter((item) => {
      if (state.category !== "all" && item.category.id !== state.category) return false;
      if (state.agent !== "all" && !detectAgents(item).includes(state.agent)) return false;
      if (state.favOnly && !isFav(item.repo)) return false;
      if (!q) return true;
      return [item.repo, item.description, item.category.zh, item.category.en,
        item.trend.zh, item.trend.en, (item.topics || []).join(" "),
        SAFE(item.language, ""), agentBadge(item)]
        .join(" ").toLowerCase().includes(q);
    });
    items = items.slice();
    if (state.sort === "trend") items.sort((a, b) => b.trend_score - a.trend_score || b.stars - a.stars);
    else if (state.sort === "stars") items.sort((a, b) => b.stars - a.stars || a.rank - b.rank);
    else if (state.sort === "updated") items.sort((a, b) => (b.last_push_date || "").localeCompare(a.last_push_date || "") || a.rank - b.rank);
    else if (state.sort === "delta30") items.sort((a, b) => (SAFE(b.star_delta_30d, b.star_delta_7d) || 0) - (SAFE(a.star_delta_30d, a.star_delta_7d) || 0) || b.stars - a.stars);
    else items.sort((a, b) => a.rank - b.rank);
    return items;
  }

  /* ---------- category strip ---------- */
  function renderCategoryStrip() {
    const c = document.getElementById("categoryStrip");
    const counts = new Map();
    data.items.forEach((it) => {
      const cur = counts.get(it.category.id) || { category: it.category, count: 0 };
      cur.count += 1; counts.set(it.category.id, cur);
    });
    c.innerHTML = "";
    const all = document.createElement("button");
    all.className = "category-card" + (state.category === "all" ? " active" : "");
    all.innerHTML = `<strong>${fmt(data.items.length)}</strong><span>${t("allCategories")}</span>`;
    all.onclick = () => { state.category = "all"; document.getElementById("categoryFilter").value = "all"; syncHash(); render(); };
    c.appendChild(all);
    Array.from(counts.values()).sort((a, b) => b.count - a.count).forEach(({ category, count }) => {
      const card = document.createElement("button");
      card.className = "category-card" + (state.category === category.id ? " active" : "");
      card.innerHTML = `<strong>${fmt(count)}</strong><span>${state.lang === "zh" ? category.zh : category.en}</span>`;
      card.onclick = () => { state.category = category.id; document.getElementById("categoryFilter").value = category.id; syncHash(); render(); };
      c.appendChild(card);
    });
  }

  /* ---------- stat strip ---------- */
  function renderStatStrip() {
    const c = document.getElementById("statStrip");
    const items = data.items;
    if (!items.length) { c.innerHTML = ""; return; }
    const totalStars = items.reduce((s, i) => s + i.stars, 0);
    const avg = Math.round(totalStars / items.length);
    const net7 = items.reduce((s, i) => s + (SAFE(i.star_delta_7d, 0) || 0), 0);
    const hot = items.slice().sort((a, b) => (SAFE(b.star_delta_7d, 0) || 0) - (SAFE(a.star_delta_7d, 0) || 0))[0];
    const counts = new Map();
    items.forEach((i) => counts.set(i.category.id, (counts.get(i.category.id) || 0) + 1));
    const maxC = Math.max(...counts.values());
    const catRows = Array.from(counts.entries()).map(([id, n]) => {
      const cat = (data.items.find((i) => i.category.id === id) || {}).category || { zh: id, en: id };
      const lbl = state.lang === "zh" ? cat.zh : cat.en;
      return `<div class="cat-bar-row"><span>${esc(lbl)}</span><span class="cat-bar-track"><span class="cat-bar-fill" style="width:${(n / maxC * 100).toFixed(0)}%"></span></span><b>${n}</b></div>`;
    }).join("");
    c.innerHTML = `
      <div class="stat-card"><div class="sv">${fmt(totalStars)}</div><div class="sl">${t("statTotalStars")}</div></div>
      <div class="stat-card"><div class="sv">${fmt(avg)}</div><div class="sl">${t("statAvgStars")}</div></div>
      <div class="stat-card"><div class="sv">+${fmt(net7)}</div><div class="sl">${t("statNet7d")}</div></div>
      <div class="stat-card"><div class="sv" style="font-size:14px;line-height:1.3">${esc(hot ? hot.repo.split("/").pop() : "-")}</div><div class="sl">${t("statHotRepo")}</div></div>
      <div class="stat-card"><div class="cat-bar">${catRows}</div><div class="sl" style="margin-top:8px">${t("statCats")}</div></div>`;
  }

  /* ---------- table view ---------- */
  function renderTable() {
    const body = document.getElementById("rankingBody");
    const empty = document.getElementById("emptyState");
    const items = filteredItems();
    empty.hidden = items.length > 0;
    body.innerHTML = "";
    items.forEach((item) => {
      const tr = document.createElement("tr");
      tr.tabIndex = 0;
      tr.dataset.repo = item.repo;
      const trendId = item.trend.id === "hot" ? "hot" : item.trend.id === "steady" ? "steady" : "rising";
      const glyph = trendId === "hot" ? "∧" : trendId === "rising" ? "↗" : "—";
      const d7 = SAFE(item.star_delta_7d, SAFE(item.star_delta_1d, 0)) || 0;
      const d30 = SAFE(item.star_delta_30d, d7);
      const topics = (item.topics || []).slice(0, 3).join(", ");
      const fav = isFav(item.repo) ? "on" : "";
      tr.innerHTML = `
        <td class="rank-cell">${item.rank}</td>
        <td class="repo-cell">
          <a href="${esc(item.url)}" target="_blank" rel="noreferrer">${esc(item.repo)}</a>
          <span class="repo-meta">${esc(item.language || "GitHub")}${topics ? " · " + esc(topics) : ""}</span>
        </td>
        <td class="stars">${fmt(item.stars)}${d7 ? `<span class="delta-chip">+${fmt(d7)}</span>` : ""}</td>
        <td><span class="trend-mark ${trendId}"><span class="glyph">${glyph}</span><span class="label">${trendName(item)}</span></span></td>
        <td class="spark-cell">${sparkline(item.repo)}</td>
        <td><span class="category-pill">${catName(item)}</span></td>
        <td class="description-cell">${esc(item.description || "")}</td>
        <td>${esc(item.last_push_date || "")}</td>
        <td><button class="fav-star ${fav}" data-fav="${esc(item.repo)}" aria-label="favorite" aria-pressed="${fav === "on"}">★</button></td>`;
      tr.addEventListener("click", (e) => {
        if (e.target.closest(".fav-star") || e.target.closest("a")) return;
        openDrawer(item.repo);
      });
      tr.addEventListener("keydown", (e) => { if (e.key === "Enter") openDrawer(item.repo); });
      body.appendChild(tr);
    });
    // attach favorite handlers
    body.querySelectorAll(".fav-star").forEach((b) => {
      b.addEventListener("click", (e) => { e.stopPropagation(); toggleFav(b.dataset.fav); });
    });
  }

  /* ---------- card view ---------- */
  function renderCards() {
    const grid = document.getElementById("cardGrid");
    const empty = document.getElementById("emptyState");
    const items = filteredItems();
    empty.hidden = items.length > 0;
    grid.innerHTML = "";
    items.forEach((item, idx) => {
      const d7 = SAFE(item.star_delta_7d, SAFE(item.star_delta_1d, 0)) || 0;
      const trendId = item.trend.id === "hot" ? "hot" : item.trend.id === "steady" ? "steady" : "rising";
      const glyph = trendId === "hot" ? "∧" : trendId === "rising" ? "↗" : "—";
      const rankCls = item.rank <= 3 ? "gold" : "";
      const fav = isFav(item.repo) ? "on" : "";
      const card = document.createElement("article");
      card.className = "repo-card";
      card.style.animationDelay = (idx % 20) * 0.02 + "s";
      card.tabIndex = 0;
      card.dataset.repo = item.repo;
      card.innerHTML = `
        <div class="card-top">
          <div>
            <span class="card-rank ${rankCls}">${item.rank}</span>
          </div>
          <button class="fav-star ${fav}" data-fav="${esc(item.repo)}" aria-label="favorite" aria-pressed="${fav === "on"}">★</button>
        </div>
        <a class="card-name" href="${esc(item.url)}" target="_blank" rel="noreferrer">${esc(item.repo)}</a>
        <div class="card-pills">
          <span class="trend-mark ${trendId}"><span class="glyph">${glyph}</span><span class="label">${trendName(item)}${d7 ? " +"+fmt(d7) : ""}</span></span>
          <span class="category-pill">${catName(item)}</span>
        </div>
        <div class="card-stars">${fmt(item.stars)} <small>${t("stars")}</small></div>
        <div class="card-desc">${esc(item.description || "")}</div>
        <div class="card-spark">${sparkline(item.repo, 240, 32)}</div>
        <div class="card-meta">
          <span>${esc(item.language || "GitHub")}</span>
          <span>${esc(item.last_push_date || "")}</span>
        </div>`;
      card.addEventListener("click", (e) => {
        if (e.target.closest(".fav-star") || e.target.closest("a")) return;
        openDrawer(item.repo);
      });
      card.addEventListener("keydown", (e) => { if (e.key === "Enter") openDrawer(item.repo); });
      grid.appendChild(card);
    });
    grid.querySelectorAll(".fav-star").forEach((b) => {
      b.addEventListener("click", (e) => { e.stopPropagation(); toggleFav(b.dataset.fav); });
    });
  }

  /* ---------- drawer ---------- */
  function toast(msg) {
    const el = document.getElementById("toast");
    if (!el) return;
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.classList.remove("show"), 2200);
  }
  function copyAsMarkdown(item) {
    const d7 = SAFE(item.star_delta_7d, SAFE(item.star_delta_1d, 0)) || 0;
    const cat = state.lang === "zh" ? item.category.zh : item.category.en;
    const agents = agentBadge(item);
    const md = `| ${item.rank} | [${item.repo}](${item.url}) | ${item.stars.toLocaleString()}${d7 ? ` (+${d7})` : ""} | ${cat} | ${agents} | ${item.last_push_date || ""} |`;
    const fallback = () => { const ta = document.createElement("textarea"); ta.value = md; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); ta.remove(); toast(t("toastCopied")); };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(md).then(() => toast(t("toastCopied")), fallback);
    } else { fallback(); }
  }
  function openDrawer(repo) {
    const item = data.items.find((i) => i.repo === repo);
    if (!item) return;
    const d7 = SAFE(item.star_delta_7d, 0) || 0;
    const d1 = SAFE(item.star_delta_1d, 0) || 0;
    const d30 = SAFE(item.star_delta_30d, d7);
    const lic = (item.license && (item.license.name || item.license.spdx_id)) || "-";
    const topics = (item.topics || []).map((tp) => `<span class="topic-chip">${esc(tp)}</span>`).join("");
    const sigs = (item.precision_signals || []).map((s) => `<span class="sig-tag">${esc(s)}</span>`).join("");
    const suggestUrl = `https://github.com/kael-odin/awesome-academic-research-skills/issues/new?title=${encodeURIComponent("Recommend: " + item.repo)}&body=${encodeURIComponent("I'd like to recommend **" + item.repo + "** (" + item.url + ") for inclusion.\n\nReason: \n")}`;
    const foot = [
      `<a class="data-link" href="${esc(item.url)}" target="_blank" rel="noreferrer">${t("drOpenRepo")} ↗</a>`,
      item.homepage ? `<a class="data-link" href="${esc(item.homepage)}" target="_blank" rel="noreferrer">${t("drHomepage")} ↗</a>` : "",
      `<button class="data-link" type="button" id="copyMdBtn">${t("drCopyMd")}</button>`,
      `<a class="data-link" href="${esc(suggestUrl)}" target="_blank" rel="noreferrer">${t("drSuggest")} ↗</a>`,
    ].join("");
    document.getElementById("drawerEyebrow").textContent = `${t("drEyebrow")} #${item.rank} · ${catName(item)}`;
    document.getElementById("drawerTitle").textContent = item.repo;
    document.getElementById("drawerBody").innerHTML = `
      <div class="drawer-field"><div class="lbl">${t("drDescription")}</div><div class="val serif">${esc(item.description || "")}</div></div>
      <div class="stat-row">
        <div class="sb"><div class="n">${fmt(item.stars)}</div><div class="k">${t("stars")}</div></div>
        <div class="sb"><div class="n">+${fmt(d7)}</div><div class="k">${t("drDelta7d")}</div></div>
        <div class="sb"><div class="n">+${fmt(d30)}</div><div class="k">${t("drDelta30d")}</div></div>
      </div>
      <div class="drawer-field"><div class="lbl">${t("drAgent")}</div><div class="agent-chips">${agentChips(item)}</div></div>
      <div class="drawer-field"><div class="lbl">${t("drTopics")}</div><div class="drawer-topics">${topics || "-"}</div></div>
      <div class="drawer-field"><div class="lbl">${t("drSignals")}</div><div class="sig-list">${sigs || "-"}</div></div>
      <hr class="drawer-divider" />
      <div class="stat-row">
        <div class="sb"><div class="n">${fmt(SAFE(item.forks,0))}</div><div class="k">${t("drForks")}</div></div>
        <div class="sb"><div class="n">${fmt(SAFE(item.open_issues,0))}</div><div class="k">${t("drIssues")}</div></div>
        <div class="sb"><div class="n" style="font-size:12px">${esc(lic)}</div><div class="k">${t("drLicense")}</div></div>
      </div>
      <div class="drawer-field"><div class="lbl">${t("drLanguage")}</div><div class="val">${esc(item.language || "-")}</div></div>
      <div class="drawer-field"><div class="lbl">${t("drCreated")}</div><div class="val">${esc(item.created_date || "-")}</div></div>
      <div class="drawer-field"><div class="lbl">${t("drPushed")}</div><div class="val">${esc(item.last_push_date || "-")}</div></div>
      <div class="drawer-field"><div class="lbl">${t("drTrend")}</div><div class="val">${fmt(item.trend_score)} · +${fmt(d1)}/day</div></div>`;
    document.getElementById("drawerFoot").innerHTML = foot;
    const copyBtn = document.getElementById("copyMdBtn");
    if (copyBtn) copyBtn.addEventListener("click", () => copyAsMarkdown(item));
    const drawer = document.getElementById("drawer");
    drawer.hidden = false;
    requestAnimationFrame(() => drawer.classList.add("open"));
    document.getElementById("drawerClose").focus();
  }
  function closeDrawer() {
    const drawer = document.getElementById("drawer");
    drawer.classList.remove("open");
    setTimeout(() => { drawer.hidden = true; }, 280);
  }

  /* ---------- view switching ---------- */
  function setView(v) {
    state.view = v;
    localStorage.setItem("ars-view", v);
    document.querySelectorAll(".view-button").forEach((b) => {
      const on = b.dataset.view === v;
      b.classList.toggle("active", on);
      b.setAttribute("aria-pressed", String(on));
    });
    const table = document.getElementById("rankingTable");
    const cards = document.getElementById("cardGrid");
    table.hidden = v !== "table";
    cards.hidden = v !== "card";
    syncHash();
    render();
  }

  /* ---------- URL hash state ---------- */
  function syncHash() {
    const p = new URLSearchParams();
    if (state.query) p.set("q", state.query);
    if (state.category !== "all") p.set("cat", state.category);
    if (state.agent !== "all") p.set("agent", state.agent);
    if (state.sort !== "rank") p.set("sort", state.sort);
    if (state.view !== "table") p.set("view", state.view);
    if (state.lang !== "zh") p.set("lang", state.lang);
    if (state.theme !== "light") p.set("theme", state.theme);
    if (state.favOnly) p.set("fav", "1");
    const h = p.toString();
    history.replaceState(null, "", h ? "#" + h : location.pathname);
  }
  function readHash() {
    const m = new URLSearchParams(location.hash.slice(1));
    if (m.has("q")) state.query = m.get("q");
    if (m.has("cat")) state.category = m.get("cat");
    if (m.has("agent")) state.agent = m.get("agent");
    if (m.has("sort")) state.sort = m.get("sort");
    if (m.has("view")) state.view = m.get("view");
    if (m.has("lang")) state.lang = m.get("lang");
    if (m.has("theme")) state.theme = m.get("theme");
    if (m.has("fav")) state.favOnly = m.get("fav") === "1";
    // reflect into controls
    const si = document.getElementById("searchInput"); if (si) si.value = state.query;
    const cf = document.getElementById("categoryFilter"); if (cf) cf.value = state.category;
    const af = document.getElementById("agentFilter"); if (af) af.value = state.agent;
    const ss = document.getElementById("sortSelect"); if (ss) ss.value = state.sort;
  }

  /* ---------- category filter ---------- */
  function populateCategoryFilter() {
    const select = document.getElementById("categoryFilter");
    const cats = new Map();
    data.items.forEach((it) => cats.set(it.category.id, it.category));
    Array.from(cats.values()).sort((a, b) => a.en.localeCompare(b.en)).forEach((c) => {
      const o = document.createElement("option");
      o.value = c.id; o.dataset.zh = c.zh; o.dataset.en = c.en;
      o.textContent = state.lang === "zh" ? c.zh : c.en;
      select.appendChild(o);
    });
  }
  function syncCategoryLabels() {
    document.querySelectorAll("#categoryFilter option").forEach((o) => {
      o.textContent = o.value === "all" ? t("allCategories") : (state.lang === "zh" ? o.dataset.zh : o.dataset.en);
    });
  }

  /* ---------- agent platform filter ---------- */
  function populateAgentFilter() {
    const select = document.getElementById("agentFilter");
    if (!select) return;
    const current = state.agent;
    // Count per platform so the dropdown reflects what's actually available.
    const counts = new Map();
    data.items.forEach((it) => detectAgents(it).forEach((id) => counts.set(id, (counts.get(id) || 0) + 1)));
    select.innerHTML = `<option value="all">${t("allAgents")}</option>`;
    AGENT_PLATFORMS.filter((p) => counts.has(p.id)).forEach((p) => {
      const o = document.createElement("option");
      o.value = p.id;
      o.textContent = `${p.label} (${counts.get(p.id)})`;
      select.appendChild(o);
    });
    if (current !== "all" && !Array.from(select.options).some((o) => o.value === current)) {
      state.agent = "all";
    }
    select.value = state.agent;
  }

  /* ---------- hero table-of-contents ---------- */
  function renderToc() {
    const list = document.getElementById("tocList");
    if (!list) return;
    const counts = new Map();
    let totalStars = 0;
    data.items.forEach((it) => {
      counts.set(it.category.id, (counts.get(it.category.id) || 0) + 1);
      totalStars += it.stars || 0;
    });
    // Render in the backend's canonical category order, omitting zero counts.
    const seen = Array.from(counts.entries()).sort((a, b) => b[1] - a[1]);
    list.innerHTML = seen.map(([id, n], i) => {
      const cat = (data.items.find((it) => it.category.id === id) || {}).category || { zh: id, en: id };
      const label = state.lang === "zh" ? cat.zh : cat.en;
      return `<div class="toc-row">
        <span class="num">${String(i + 1).padStart(2, "0")}</span>
        <span class="name">${esc(label)}</span>
        <span class="leader"></span>
        <span class="count">${fmt(n)}</span>
      </div>`;
    }).join("");
    document.getElementById("tocRepos").textContent = fmt(data.items.length);
    document.getElementById("tocStars").textContent = fmt(totalStars);
  }

  /* ---------- masthead (issue number + date) ---------- */
  function renderMasthead() {
    const gen = (data.metadata.generated_at || "").slice(0, 10);
    document.getElementById("mastheadDate").textContent = gen || "—";
    // Issue number = days since a fixed epoch, so it increments daily and
    // reads like a journal issue (No.207). Epoch chosen from repo start.
    const epoch = Date.UTC(2026, 5, 30); // 2026-06-30
    const now = gen ? Date.parse(gen) : Date.now();
    const issue = Math.max(1, Math.floor((now - epoch) / 86400000) + 1);
    document.getElementById("mastheadIssue").textContent = "No." + issue;
    document.getElementById("tocUpdated").textContent = gen || "—";
  }

  /* ---------- summary ---------- */
  function renderSummary() {
    renderMasthead();
  }

  /* ---------- JSON-LD ---------- */
  function renderLdJson() {
    const el = document.getElementById("ld-json");
    if (!el) return;
    const top = data.items.slice(0, 20);
    const payload = {
      "@context": "https://schema.org",
      "@type": "ItemList",
      "name": "Awesome Academic Research Skills",
      "description": "Daily ranking of academic & research agent skills on GitHub.",
      "url": "https://kael-odin.github.io/awesome-academic-research-skills/",
      "itemListElement": top.map((it, i) => ({
        "@type": "ListItem",
        "position": i + 1,
        "name": it.repo,
        "url": it.url,
      })),
    };
    el.textContent = JSON.stringify(payload);
  }

  /* ---------- master render ---------- */
  function render() {
    syncCategoryLabels();
    renderSummary();
    renderToc();
    renderStatStrip();
    renderCategoryStrip();
    if (state.view === "card") { renderCards(); } else { renderTable(); }
    renderLdJson();
    updateFavUI();
    syncHash();
  }

  /* ---------- events ---------- */
  function wire() {
    document.querySelectorAll(".lang-button").forEach((b) => b.addEventListener("click", () => setLanguage(b.dataset.lang)));
    document.getElementById("themeToggle").addEventListener("click", toggleTheme);
    document.querySelectorAll(".view-button").forEach((b) => b.addEventListener("click", () => setView(b.dataset.view)));
    document.getElementById("favToggle").addEventListener("click", () => { state.favOnly = !state.favOnly; updateFavUI(); syncHash(); render(); });
    document.getElementById("searchInput").addEventListener("input", (e) => { state.query = e.target.value; if (state.view === "card") renderCards(); else renderTable(); syncHash(); });
    document.getElementById("categoryFilter").addEventListener("change", (e) => { state.category = e.target.value; render(); });
    document.getElementById("agentFilter").addEventListener("change", (e) => { state.agent = e.target.value; syncHash(); render(); });
    document.getElementById("sortSelect").addEventListener("change", (e) => { state.sort = e.target.value; render(); });
    document.getElementById("drawerClose").addEventListener("click", closeDrawer);
    document.getElementById("drawerScrim").addEventListener("click", closeDrawer);
    document.getElementById("exportFav").addEventListener("click", () => {
      const favs = data.items.filter((i) => isFav(i.repo)).map((i) => ({ repo: i.repo, stars: i.stars, url: i.url, category: i.category.en }));
      const blob = new Blob([JSON.stringify({ exported_at: new Date().toISOString(), favorites: favs }, null, 2)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "ars-favorites.json";
      a.click();
      URL.revokeObjectURL(a.href);
    });
    window.addEventListener("hashchange", () => {
      const prevLang = state.lang, prevTheme = state.theme;
      readHash();
      if (state.theme !== prevTheme) { applyTheme(); localStorage.setItem("ars-theme", state.theme); }
      if (state.lang !== prevLang) { setLanguage(state.lang); return; }
      render();
      setView(state.view);
    });

    document.addEventListener("keydown", (e) => {
      const tag = (e.target.tagName || "").toLowerCase();
      const typing = tag === "input" || tag === "select" || tag === "textarea";
      if (e.key === "Escape") { closeDrawer(); return; }
      if (typing) return;
      if (e.key === "/") { e.preventDefault(); document.getElementById("searchInput").focus(); }
      else if (e.key === "t") toggleTheme();
      else if (e.key === "l") setLanguage(state.lang === "zh" ? "en" : "zh");
      else if (e.key === "v") setView(state.view === "table" ? "card" : "table");
      else if (e.key === "f") { state.favOnly = !state.favOnly; updateFavUI(); syncHash(); render(); }
    });
  }

  /* ---------- init ---------- */
  applyTheme();
  readHash();
  populateCategoryFilter();
  populateAgentFilter();
  wire();
  setView(state.view);
  setLanguage(state.lang);
})();
