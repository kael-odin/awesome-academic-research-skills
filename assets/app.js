(function () {
  const data = window.ACADEMIC_SKILLS_RANKINGS || { metadata: {}, items: [] };
  const state = {
    lang: localStorage.getItem("ars-lang") || "zh",
    query: "",
    category: "all",
    sort: "rank",
  };

  const translations = {
    zh: {
      heroTitle: "学术论文 Skill 排行",
      heroSubtitle:
        "每天自动发现、过滤并排名 GitHub 上服务论文写作、文献综述、深度研究、评审反馈和实验复现的 Agent Skill 仓库。",
      repos: "收录仓库",
      minStars: "最低 Stars",
      updated: "最近更新",
      searchLabel: "搜索仓库、简介、分类",
      categoryLabel: "分类",
      allCategories: "全部分类",
      sortLabel: "排序",
      sortRank: "综合排名",
      sortTrend: "趋势优先",
      sortStars: "Stars 优先",
      sortUpdated: "最近更新",
      tableTitle: "完整榜单",
      tableHint: "精准过滤：必须同时命中学术研究信号与 Skill/Agent/Workflow 信号。",
      downloadJson: "下载 JSON",
      repo: "仓库",
      trend: "趋势",
      category: "分类",
      description: "简介",
      updatedCol: "更新",
      empty: "没有匹配当前筛选条件的仓库。",
      methodTitle: "排名方法",
      methodCopy:
        "榜单按 Stars 主排序，并展示趋势分。趋势分综合近期新增 Stars、最近 push、新仓库加权和总体规模；低星、fork、归档及明显非学术仓库会被排除。",
      methodA: "精准信号",
      methodADetail: "academic/research/paper + skill/agent/workflow",
      methodB: "每日更新",
      methodBDetail: "GitHub Actions UTC 定时运行",
      methodC: "双语视图",
      methodCDetail: "中文优先，支持英文切换",
    },
    en: {
      heroTitle: "Academic Research Skills Ranking",
      heroSubtitle:
        "A daily updated ranking of GitHub repositories for paper writing, literature review, deep research, peer review, and experiment reproducibility agent skills.",
      repos: "Repositories",
      minStars: "Min Stars",
      updated: "Updated",
      searchLabel: "Search repositories, descriptions, categories",
      categoryLabel: "Category",
      allCategories: "All categories",
      sortLabel: "Sort",
      sortRank: "Ranking",
      sortTrend: "Trend first",
      sortStars: "Stars first",
      sortUpdated: "Recently updated",
      tableTitle: "Full Ranking",
      tableHint: "Precision filter: repositories must match both academic research and skill/agent/workflow signals.",
      downloadJson: "Download JSON",
      repo: "Repository",
      trend: "Trend",
      category: "Category",
      description: "Description",
      updatedCol: "Updated",
      empty: "No repositories match the current filters.",
      methodTitle: "Ranking Method",
      methodCopy:
        "Repositories are ranked mainly by Stars and enriched with a trend score. The trend score combines recent star growth, recent pushes, new-repository weighting, and overall scale.",
      methodA: "Precision signals",
      methodADetail: "academic/research/paper + skill/agent/workflow",
      methodB: "Daily update",
      methodBDetail: "Scheduled by GitHub Actions in UTC",
      methodC: "Bilingual view",
      methodCDetail: "Chinese first with English switching",
    },
  };

  function formatNumber(value) {
    return new Intl.NumberFormat(state.lang === "zh" ? "zh-CN" : "en-US").format(value || 0);
  }

  function text(key) {
    return translations[state.lang][key] || key;
  }

  function categoryName(item) {
    return state.lang === "zh" ? item.category.zh : item.category.en;
  }

  function trendName(item) {
    return state.lang === "zh" ? item.trend.zh : item.trend.en;
  }

  function setLanguage(lang) {
    state.lang = lang;
    localStorage.setItem("ars-lang", lang);
    document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
    document.querySelectorAll("[data-i18n]").forEach((node) => {
      node.textContent = text(node.dataset.i18n);
    });
    document.querySelectorAll(".lang-button").forEach((button) => {
      button.classList.toggle("active", button.dataset.lang === lang);
    });
    render();
  }

  function populateCategoryFilter() {
    const select = document.getElementById("categoryFilter");
    const categories = new Map();
    data.items.forEach((item) => {
      categories.set(item.category.id, item.category);
    });
    Array.from(categories.values())
      .sort((a, b) => a.en.localeCompare(b.en))
      .forEach((category) => {
        const option = document.createElement("option");
        option.value = category.id;
        option.dataset.zh = category.zh;
        option.dataset.en = category.en;
        option.textContent = state.lang === "zh" ? category.zh : category.en;
        select.appendChild(option);
      });
  }

  function syncCategoryLabels() {
    document.querySelectorAll("#categoryFilter option").forEach((option) => {
      if (option.value === "all") {
        option.textContent = text("allCategories");
      } else {
        option.textContent = state.lang === "zh" ? option.dataset.zh : option.dataset.en;
      }
    });
  }

  function filteredItems() {
    const query = state.query.trim().toLowerCase();
    let items = data.items.filter((item) => {
      const matchesCategory = state.category === "all" || item.category.id === state.category;
      if (!matchesCategory) {
        return false;
      }
      if (!query) {
        return true;
      }
      return [
        item.repo,
        item.description,
        item.category.zh,
        item.category.en,
        item.trend.zh,
        item.trend.en,
        (item.topics || []).join(" "),
      ]
        .join(" ")
        .toLowerCase()
        .includes(query);
    });

    items = items.slice();
    if (state.sort === "trend") {
      items.sort((a, b) => b.trend_score - a.trend_score || b.stars - a.stars);
    } else if (state.sort === "stars") {
      items.sort((a, b) => b.stars - a.stars || a.rank - b.rank);
    } else if (state.sort === "updated") {
      items.sort((a, b) => (b.last_push_date || "").localeCompare(a.last_push_date || "") || a.rank - b.rank);
    } else {
      items.sort((a, b) => a.rank - b.rank);
    }
    return items;
  }

  function renderCategoryStrip() {
    const container = document.getElementById("categoryStrip");
    const counts = new Map();
    data.items.forEach((item) => {
      const current = counts.get(item.category.id) || { category: item.category, count: 0 };
      current.count += 1;
      counts.set(item.category.id, current);
    });
    container.innerHTML = "";
    Array.from(counts.values())
      .sort((a, b) => b.count - a.count)
      .forEach(({ category, count }) => {
        const card = document.createElement("button");
        card.type = "button";
        card.className = "category-card";
        card.innerHTML = `<strong>${formatNumber(count)}</strong><span>${state.lang === "zh" ? category.zh : category.en}</span>`;
        card.addEventListener("click", () => {
          state.category = category.id;
          document.getElementById("categoryFilter").value = category.id;
          render();
        });
        container.appendChild(card);
      });
  }

  function renderTable() {
    const body = document.getElementById("rankingBody");
    const empty = document.getElementById("emptyState");
    const items = filteredItems();
    body.innerHTML = "";
    empty.hidden = items.length > 0;

    items.forEach((item) => {
      const row = document.createElement("tr");
      const trendClass = item.trend.id === "hot" ? "trend-pill hot" : "trend-pill";
      const delta7 = item.star_delta_7d || item.star_delta_1d || 0;
      const delta = delta7 ? `+${formatNumber(delta7)}` : "0";
      const topics = (item.topics || []).slice(0, 3).join(", ");
      row.innerHTML = `
        <td class="rank-cell">${item.rank}</td>
        <td class="repo-cell">
          <a href="${item.url}" target="_blank" rel="noreferrer">${item.repo}</a>
          <span class="repo-meta">${item.language || "GitHub"}${topics ? " · " + topics : ""}</span>
        </td>
        <td class="stars">${formatNumber(item.stars)}</td>
        <td><span class="${trendClass}">${trendName(item)} · 7d:${delta}</span></td>
        <td><span class="category-pill">${categoryName(item)}</span></td>
        <td class="description-cell">${item.description || ""}</td>
        <td>${item.last_push_date || ""}</td>
      `;
      body.appendChild(row);
    });
  }

  function renderSummary() {
    document.getElementById("totalRepos").textContent = formatNumber(data.metadata.total || data.items.length);
    document.getElementById("minStars").textContent = formatNumber(data.metadata.min_stars || 100);
    document.getElementById("updatedAt").textContent = (data.metadata.generated_at || "").slice(0, 10) || "-";
  }

  function render() {
    syncCategoryLabels();
    renderSummary();
    renderCategoryStrip();
    renderTable();
  }

  document.querySelectorAll(".lang-button").forEach((button) => {
    button.addEventListener("click", () => setLanguage(button.dataset.lang));
  });
  document.getElementById("searchInput").addEventListener("input", (event) => {
    state.query = event.target.value;
    renderTable();
  });
  document.getElementById("categoryFilter").addEventListener("change", (event) => {
    state.category = event.target.value;
    render();
  });
  document.getElementById("sortSelect").addEventListener("change", (event) => {
    state.sort = event.target.value;
    renderTable();
  });

  populateCategoryFilter();
  setLanguage(state.lang);
})();
