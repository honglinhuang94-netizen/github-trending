// GitHub Trending 静态前端
// 数据由 GitHub Actions 定期生成,提交到 static/data/ 目录,
// 这里直接 fetch JSON 文件渲染 (使用相对路径,适配 username.github.io/repo/ 这种子路径)
(() => {
  const PERIOD_LABELS = {
    daily: "今日热门",
    weekly: "本周热门",
    monthly: "本月热门",
  };
  const PERIOD_DESCRIPTIONS = {
    daily: "过去 24 小时内获得最多 star 的项目",
    weekly: "过去 7 天内获得最多 star 的项目",
    monthly: "过去 30 天内获得最多 star 的项目",
  };

  // 缓存所有周期数据,避免切换 tab 重复拉取
  const cache = {};
  const state = {
    period: "daily",
    loading: false,
  };

  // DOM
  const $tabs = document.querySelectorAll(".tab");
  const $refresh = document.getElementById("refresh-btn");
  const $list = document.getElementById("repo-list");
  const $status = document.getElementById("status");
  const $meta = document.getElementById("meta");

  // ---- 工具函数 ----
  function formatNumber(n) {
    if (typeof n !== "number" || !isFinite(n)) return "0";
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(1).replace(/\.0$/, "") + "M";
    if (n >= 1_000) return (n / 1_000).toFixed(1).replace(/\.0$/, "") + "k";
    return n.toLocaleString();
  }

  function langColor(lang) {
    if (!lang) return "#8b949e";
    const key = lang.toLowerCase().replace(/\s+/g, "-");
    const map = {
      python: "#3572A5", javascript: "#f1e05a", typescript: "#3178c6",
      go: "#00ADD8", rust: "#dea584", java: "#b07219", shell: "#89e051",
      "c++": "#f34b7d", "c#": "#178600", c: "#555555", html: "#e34c26",
      css: "#563d7c", ruby: "#701516", php: "#4F5D95", swift: "#F05138",
      kotlin: "#A97BFF", scala: "#c22d40", dart: "#00B4AB", lua: "#000080",
      elixir: "#6e4a7e", haskell: "#5e5086", vue: "#41b883",
    };
    return map[key] || "#8b949e";
  }

  function escapeHtml(s) {
    return (s || "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  function showLoading() {
    $status.hidden = false;
    $status.className = "status";
    $status.innerHTML = '<span class="spinner"></span>正在加载榜单...';
    $list.innerHTML = "";
  }

  function showError(msg) {
    $status.hidden = false;
    $status.className = "status error";
    $status.textContent = "加载失败: " + msg;
  }

  function showEmpty() {
    $status.hidden = false;
    $status.className = "status";
    $status.innerHTML = '暂无该周期的数据。<br>如果你刚刚部署,请到 GitHub 仓库的 <strong>Actions</strong> 页面手动触发一次 <code>Update Trending Data</code> workflow。';
  }

  function clearStatus() {
    $status.hidden = true;
    $status.innerHTML = "";
  }

  // ---- 渲染 ----
  function renderCards(payload) {
    const items = payload.items || [];
    if (!items.length) {
      $list.innerHTML = '<div class="status">该周期没有返回任何项目。</div>';
      return;
    }
    $list.innerHTML = items.map((it) => {
      const langDot = it.language
        ? `<span class="lang-dot" style="background:${langColor(it.language)}"></span>`
        : "";
      const langHtml = it.language
        ? `<span class="lang-badge">${langDot}${escapeHtml(it.language)}</span>`
        : "";
      const periodLabel = {
        daily: "今日新增", weekly: "本周新增", monthly: "本月新增",
      }[state.period];

      const contribsHtml = (it.contributors || []).slice(0, 5).map((src) =>
        `<img src="${escapeHtml(src)}" alt="" loading="lazy" />`
      ).join("");

      const zhDesc = it.description_zh || "";
      const enDesc = it.description || "";
      const showOriginal = zhDesc && zhDesc !== enDesc;

      return `
        <article class="card">
          <div class="rank">${it.rank}</div>
          <div class="card-body">
            <div class="card-title">
              <a href="${escapeHtml(it.url)}" target="_blank" rel="noopener">${escapeHtml(it.name)}</a>
              ${langHtml}
            </div>
            ${zhDesc ? `<p class="card-desc zh">${escapeHtml(zhDesc)}</p>` : ""}
            ${showOriginal ? `<p class="card-desc-original">原文: ${escapeHtml(enDesc)}</p>` : ""}
            <div class="card-stats">
              <a href="${escapeHtml(it.url)}" target="_blank" rel="noopener" title="总 star 数">
                <svg class="icon" viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.75.75 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z"/></svg>
                <span class="star-total">${formatNumber(it.stars_total)}</span>
              </a>
              <span title="${escapeHtml(periodLabel)}新增 star" class="star-period">
                <svg class="icon" viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M1.5 1.75V13.5h13.75a.75.75 0 0 1 0 1.5H.75a.75.75 0 0 1-.75-.75V1.75a.75.75 0 0 1 1.5 0Zm14.28 2.53-1.06-1.06L9.22 8.72a.75.75 0 0 1-1.06 0L5.97 6.53l-1.06 1.06 2.75 2.75a1.5 1.5 0 0 0 2.12 0l5.0-5.0Z"/></svg>
                +${formatNumber(it.stars_period)} ${periodLabel}
              </span>
              <a href="${escapeHtml(it.url)}/forks" target="_blank" rel="noopener" class="forks" title="fork 数">
                <svg class="icon" viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z"/></svg>
                ${formatNumber(it.forks)}
              </a>
              ${contribsHtml ? `<span class="contributors" title="本期热门贡献者">${contribsHtml}</span>` : ""}
            </div>
          </div>
        </article>
      `;
    }).join("");
  }

  function timeAgo(ts) {
    if (!ts) return "";
    const diff = Math.floor(Date.now() / 1000 - ts);
    if (diff < 60) return `${diff} 秒前`;
    if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`;
    return `${Math.floor(diff / 86400)} 天前`;
  }

  function renderMeta(payload) {
    const generated = payload.generated_at;
    const ago = timeAgo(generated);
    const exact = generated
      ? new Date(generated * 1000).toLocaleString("zh-CN")
      : "";
    $meta.innerHTML = `
      <strong>${PERIOD_LABELS[state.period]}</strong> ·
      ${PERIOD_DESCRIPTIONS[state.period]} ·
      共 <strong>${payload.count}</strong> 个项目 ·
      数据更新于 <strong>${ago}</strong>${exact ? ` (${exact})` : ""}
    `;
  }

  // ---- 数据加载 ----
  async function load(period) {
    if (state.loading) return;
    state.loading = true;
    state.period = period;
    $refresh.classList.add("spinning");
    $refresh.disabled = true;
    showLoading();

    try {
      const cached = cache[period];
      if (cached) {
        clearStatus();
        renderMeta(cached);
        renderCards(cached);
        return;
      }
      // 使用相对路径,适配 username.github.io/repo-name/ 这种子路径部署
      const resp = await fetch(`./data/trending-${period}.json`, { cache: "no-store" });
      if (resp.status === 404) {
        showEmpty();
        return;
      }
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`);
      }
      const data = await resp.json();
      cache[period] = data;
      clearStatus();
      renderMeta(data);
      renderCards(data);
    } catch (e) {
      showError(e.message || String(e));
    } finally {
      state.loading = false;
      $refresh.classList.remove("spinning");
      $refresh.disabled = false;
    }
  }

  // ---- 事件 ----
  $tabs.forEach((t) => {
    t.addEventListener("click", () => {
      if (state.loading) return;
      const period = t.dataset.period;
      if (period === state.period && cache[period]) return;
      $tabs.forEach((x) => x.classList.toggle("active", x === t));
      load(period);
    });
  });

  $refresh.addEventListener("click", () => {
    // 强制重新拉取 (绕过内存缓存)
    delete cache[state.period];
    load(state.period);
  });

  // 启动
  load("daily");
})();
