/* World Order Monitor — static site. Data: window.WORLD_DATA (site/data/data.js). */
(function () {
  "use strict";
  const DATA = window.WORLD_DATA;
  const E = DATA.entities;
  const META = DATA.meta;
  const GAUGES = DATA.gauges;
  const GBY = Object.fromEntries(GAUGES.map(g => [g.id, g]));
  const $ = (s, el = document) => el.querySelector(s);
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // Countries shown before anything is clicked: the big powers (Dalio's top tier + largest economies)
  const BIG = ["USA", "CHN", "EUZ", "IND", "JPN", "DEU", "RUS", "GBR", "FRA", "KOR", "BRA", "CAN"];

  // ------------------------------------------------------------------ colour scales (validated, see SPEC)
  const dark = () => document.documentElement.dataset.theme === "dark" ||
    (document.documentElement.dataset.theme !== "light" && matchMedia("(prefers-color-scheme: dark)").matches);
  const PAL = {
    light: {
      blue: ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281", "#0b2a55"],
      orange: ["#ef9a66", "#e5773f", "#c95a22", "#8f3a12"],
      red: ["#ee8a80", "#e06055", "#c4403a", "#962d29", "#64201d"],
      neutral: "#d6d4cc", aqua: "#1baf7a", catBlue: "#2a78d6", catOrange: "#eb6834", flat: "#b5b3ab",
    },
    dark: {
      blue: ["#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4", "#cde2fb"],
      orange: ["#9a4219", "#b85020", "#d26a35", "#f0a678"],
      red: ["#a0342d", "#bd453e", "#d4574f", "#e87b72", "#f4aca5"],
      neutral: "#4a4a46", aqua: "#199e70", catBlue: "#3987e5", catOrange: "#d95926", flat: "#5f5e59",
    },
  };
  const P = () => PAL[dark() ? "dark" : "light"];

  const DEBT_L = META.debt_labels, INT_L = META.internal_labels, WAR_L = META.war_levels;

  const LAYERS = {
    power: {
      label: "Power score",
      desc: "Overall power score (0–1), Dalio's 'Empire score' rebuilt from the eight key measures of power and the additional determinants, then calibrated to his published 2024 index.",
      bins: [0.05, 0.1, 0.15, 0.22, 0.35, 0.55],
      value: e => e.power,
      color(e) { const v = e.power; if (v == null) return null; const b = this.bins; let i = 0; while (i < b.length - 1 && v >= b[i + 1]) i++; return v < b[0] ? P().blue[0] : P().blue[i]; },
      legend() { const b = this.bins, c = P().blue; return { title: "Power", items: c.map((col, i) => [col, i === 0 ? `< ${b[1]}` : i === c.length - 1 ? `≥ ${b[i]}` : `${b[i]}–${b[i + 1]}`]) }; },
      fmt: e => e.power == null ? "n/a" : e.power.toFixed(2),
    },
    trend: {
      label: "20-year trend",
      desc: `Change in power score since about ${META.then_year} (Dalio shows a 20-year change for every gauge). Blue means rising, red means declining.`,
      value: e => e.delta20,
      color(e) {
        const v = e.delta20; if (v == null) return null; const p = P();
        if (v <= -0.05) return p.red[3]; if (v <= -0.02) return p.red[2]; if (v <= -0.008) return p.red[0];
        if (v < 0.008) return p.neutral; if (v < 0.025) return p.blue[1]; if (v < 0.06) return p.blue[3]; return p.blue[5];
      },
      legend() { const p = P(); return { title: "Δ power", items: [[p.red[3], "≤ −0.05"], [p.red[2], "−0.05 to −0.02"], [p.red[0], "−0.02 to −0.008"], [p.neutral, "flat"], [p.blue[1], "+0.008 to +0.025"], [p.blue[3], "+0.025 to +0.06"], [p.blue[5], "≥ +0.06"]] }; },
      fmt: e => e.delta20 == null ? "n/a" : (e.delta20 >= 0 ? "+" : "") + e.delta20.toFixed(3),
    },
    debt: {
      label: "Debt cycle",
      desc: "Stage in the big (long-term) debt cycle, from How Countries Go Broke: sound money → debt build-up → top/squeeze → deleveraging or crisis → crisis receding.",
      value: e => e.cycles.debt.stage,
      color(e) { const s = e.cycles.debt.stage; if (!s) return null; const p = P(); return s === 5 ? p.aqua : p.orange[s - 1]; },
      legend() { const p = P(); return { title: "Debt stage", items: [1, 2, 3, 4].map(s => [p.orange[s - 1], `${s} ${DEBT_L[s]}`]).concat([[p.aqua, `5 ${DEBT_L[5]}`]]) }; },
      fmt: e => e.cycles.debt.stage ? `${e.cycles.debt.stage} · ${DEBT_L[e.cycles.debt.stage]}` : "n/a",
    },
    internal: {
      label: "Internal order",
      desc: "Stage in the internal order/disorder cycle (Changing World Order, ch. 5). Stages 1–2 are a new order being built (blue), 3 is peace and prosperity (neutral), and 4–6 are decay into conflict (red).",
      value: e => e.cycles.internal.stage,
      color(e) { const s = e.cycles.internal.stage; if (!s) return null; const p = P(); return s === 1 ? p.blue[3] : s === 2 ? p.blue[1] : s === 3 ? p.neutral : p.red[[0, 0, 0, 0, 1, 3, 4][s]]; },
      legend() { const p = P(); return { title: "Internal stage", items: [[p.blue[3], "1 New order"], [p.blue[1], "2 Building systems"], [p.neutral, "3 Peace & prosperity"], [p.red[1], "4 Excesses, gaps"], [p.red[3], "5 Bad finances + conflict"], [p.red[4], "6 Civil war"]] }; },
      fmt: e => e.cycles.internal.stage ? `${e.cycles.internal.stage} · ${INT_L[e.cycles.internal.stage]}` : "n/a",
    },
    external: {
      label: "External conflict",
      desc: "The most severe of Dalio's types of war the country is in, as of the research date: trade → technology → geopolitical → capital (sanctions) → military.",
      value: e => e.cycles.external.level,
      color(e) { const l = e.cycles.external.level; const p = P(); return l === 0 ? p.neutral : p.red[l - 1]; },
      legend() { const p = P(); return { title: "War ladder", items: WAR_L.map((w, i) => [i === 0 ? p.neutral : p.red[i - 1], `${i} ${w}`]) }; },
      fmt: e => `${e.cycles.external.level} · ${WAR_L[e.cycles.external.level]}`,
    },
    arc: {
      label: "Empire arc",
      desc: "Phase on Dalio's archetypal rise-and-decline arc, from the 20-year power trend and the lagging-versus-leading strengths gap.",
      value: e => e.cycles.arc.phase,
      color(e) { const p = P(); const ph = e.cycles.arc.phase; if (e.power == null) return null; return ph === "Rising" ? p.aqua : ph === "Declining" ? p.catOrange : ph === "Flat" ? p.flat : p.catBlue; },
      legend() { const p = P(); return { title: "Phase", items: [[p.aqua, "Rising"], [p.catBlue, "Near peak / plateau"], [p.catOrange, "Declining"], [p.flat, "Flat (minor power)"]] }; },
      fmt: e => e.cycles.arc.phase,
    },
  };
  let layer = "power";
  let selected = null;

  // ------------------------------------------------------------------ formatting
  const STAT = {
    gdp_ppp: ["GDP (PPP, intl $)", "money"], gdp_usd: ["GDP (current US$)", "money"], gdp_pc_ppp: ["GDP per capita (PPP)", "money0"],
    pop: ["Population", "count"], ppp_share: ["Share of world GDP (PPP, IMF)", "pct"], growth_fcst: ["Expected real growth, next 5 yrs (IMF)", "pct1"],
    exports: ["Exports of goods & services", "money"], exports_gdp: ["Exports, % GDP", "pct"],
    mil_usd: ["Military spending (SIPRI)", "money"], mil_gdp: ["Military spending, % GDP", "pct1"], armed_forces: ["Armed forces personnel", "count"], nukes: ["Nuclear warheads", "count"],
    rd_usd: ["R&D spending", "money"], rd_gdp: ["R&D, % GDP", "pct2"], patents: ["Resident patent applications", "count"], researchers: ["Researchers per million people", "count"], hitech: ["High-tech exports, % manuf. exports", "pct"],
    tert_enr: ["Tertiary enrolment (gross %)", "pct"], tert_students: ["Tertiary students", "count"], hci: ["Human Capital Index (0–1)", "dec2"], test_scores: ["Harmonised test scores (300–625)", "dec0"],
    price_level: ["Price level (US = 1)", "dec2"], output_per_worker: ["GDP per person employed (PPP $)", "money0"],
    gcf_gdp: ["Investment (gross capital formation), % GDP", "pct"], gcf_usd: ["Investment, US$", "money"], savings: ["Gross savings, % GDP", "pct"], lpi: ["Logistics Performance Index (1–5)", "dec2"],
    mcap: ["Stock market capitalisation", "money"], traded: ["Value of stocks traded", "money"], gfci_rank: ["Best financial centre, GFCI rank", "rank"],
    cofer: ["Share of world FX reserves", "pct1"], swift: ["Share of global payments (SWIFT)", "pct1"],
    gov_debt: ["Government gross debt, % GDP", "pct"], fiscal_bal: ["Budget balance, % GDP", "pctS"], primary_bal: ["Primary balance, % GDP", "pctS"], revenue: ["Government revenue, % GDP", "pct"],
    interest_gdp: ["Net interest, % GDP", "pct1"], interest_rev: ["Interest payments, % revenue", "pct1"], private_debt: ["Private debt, % GDP (IMF)", "pct"], hh_debt: ["Household debt, % GDP", "pct"], nfc_debt: ["Corporate debt, % GDP", "pct"],
    private_credit: ["Bank credit to private sector, % GDP", "pct"], ext_debt: ["External debt, % GNI", "pct"], inflation: ["Inflation, %", "pct1"], ca: ["Current account, % GDP", "pctS"], reserves: ["FX reserves incl. gold", "money"],
    gini: ["Gini index (0–100)", "dec1"], top10: ["Income share of top 10%", "pct"], unemp: ["Unemployment, %", "pct1"], lfp: ["Labour-force participation, %", "pct"], age65: ["Population aged 65+, %", "pct"],
    land: ["Land area, km²", "count"], rents: ["Natural-resource rents, % GDP", "pct1"], rents_usd: ["Natural-resource rents, US$", "money"], energy_imp: ["Net energy imports, % of use (negative = exporter)", "pct"],
    wgi_rl: ["Rule of Law (WGI, −2.5…2.5)", "dec2"], wgi_cc: ["Control of Corruption (WGI)", "dec2"], wgi_ge: ["Government Effectiveness (WGI)", "dec2"], wgi_pv: ["Political Stability (WGI)", "dec2"], wgi_va: ["Voice & Accountability (WGI)", "dec2"],
  };
  function money(v) {
    const a = Math.abs(v);
    if (a >= 1e12) return "$" + (v / 1e12).toFixed(a >= 1e13 ? 1 : 2) + "T";
    if (a >= 1e9) return "$" + (v / 1e9).toFixed(a >= 1e11 ? 0 : 1) + "B";
    if (a >= 1e6) return "$" + (v / 1e6).toFixed(0) + "M";
    return "$" + Math.round(v).toLocaleString("en-US");
  }
  function count(v) {
    if (v >= 1e9) return (v / 1e9).toFixed(2) + " bn";
    if (v >= 1e6) return (v / 1e6).toFixed(1) + " m";
    return Math.round(v).toLocaleString("en-US");
  }
  function fmtStat(k, v) {
    if (v == null || Number.isNaN(v)) return "n/a";
    const t = (STAT[k] || [k, "dec2"])[1];
    switch (t) {
      case "money": return money(v);
      case "money0": return "$" + Math.round(v).toLocaleString("en-US");
      case "count": return count(v);
      case "pct": return v.toFixed(0) + "%";
      case "pct1": return v.toFixed(1) + "%";
      case "pct2": return v.toFixed(2) + "%";
      case "pctS": return (v > 0 ? "+" : "") + v.toFixed(1) + "%";
      case "dec0": return v.toFixed(0);
      case "dec1": return v.toFixed(1);
      case "rank": return "#" + v;
      default: return v.toFixed(2);
    }
  }
  const stat = (e, k) => e.stats[k] ? e.stats[k].v : null;
  function deltaHtml(d) {
    if (d == null) return `<span class="delta flat">no 20-yr data</span>`;
    const cls = d > 0.008 ? "up" : d < -0.008 ? "down" : "flat";
    const arrow = cls === "up" ? "▲" : cls === "down" ? "▼" : "▶";
    return `<span class="delta ${cls}" title="Change in power score since ~${META.then_year}">${arrow} ${(d >= 0 ? "+" : "") + d.toFixed(3)} / 20y</span>`;
  }
  const chipDot = c => `<span class="dot" style="background:${c}"></span>`;
  function cycleChips(e) {
    const c = e.cycles;
    return `<div class="chips">
      ${c.debt.stage ? `<span class="chip" title="Big debt cycle">${chipDot(LAYERS.debt.color(e))}Debt ${c.debt.stage}/5 · ${esc(DEBT_L[c.debt.stage])}</span>` : ""}
      ${c.internal.stage ? `<span class="chip" title="Internal order cycle">${chipDot(LAYERS.internal.color(e))}Internal ${c.internal.stage}/6 · ${esc(INT_L[c.internal.stage])}</span>` : ""}
      <span class="chip" title="External order — Dalio's war ladder">${chipDot(LAYERS.external.color(e))}${esc(WAR_L[c.external.level])}</span>
      ${e.power != null ? `<span class="chip" title="Position on the empire arc">${chipDot(LAYERS.arc.color(e))}${esc(c.arc.phase)}</span>` : ""}
    </div>`;
  }

  // ------------------------------------------------------------------ tooltip
  const tip = $("#tooltip");
  function showTip(html, ev) {
    tip.innerHTML = html; tip.hidden = false;
    const pad = 14, r = tip.getBoundingClientRect();
    let x = ev.clientX + pad, y = ev.clientY + pad;
    if (x + r.width > innerWidth - 8) x = ev.clientX - r.width - pad;
    if (y + r.height > innerHeight - 8) y = ev.clientY - r.height - pad;
    tip.style.left = Math.max(8, x) + "px"; tip.style.top = Math.max(8, y) + "px";
  }
  const hideTip = () => { tip.hidden = true; };

  // ------------------------------------------------------------------ map
  let mapPaths, mapSvg, mapG;
  function buildMap() {
    const topo = window.WORLD_TOPO;
    const feats = topojson.feature(topo, topo.objects.countries).features.filter(f => f.properties.name !== "Antarctica");
    const fixes = { "Kosovo": "XKX", "N. Cyprus": "CYP", "Somaliland": "SOM" };
    feats.forEach(f => { f.iso = DATA.num2iso[String(f.id).padStart(3, "0")] || fixes[f.properties.name] || null; });
    const W = 960, H = 480;
    const proj = d3.geoNaturalEarth1().fitExtent([[4, 4], [W - 4, H - 4]], { type: "Sphere" });
    const path = d3.geoPath(proj);
    mapSvg = d3.select("#map").append("svg").attr("viewBox", `0 0 ${W} ${H}`).attr("role", "img").attr("aria-label", "World map coloured by the selected layer");
    mapG = mapSvg.append("g");
    mapG.append("path").attr("class", "sphere").attr("d", path({ type: "Sphere" }));
    mapPaths = mapG.selectAll("path.country").data(feats).join("path")
      .attr("class", "country").attr("d", path)
      .attr("tabindex", d => E[d.iso] ? 0 : null)
      .attr("aria-label", d => E[d.iso] ? E[d.iso].name : d.properties.name)
      .on("mousemove", (ev, d) => {
        const e = E[d.iso];
        if (!e) { showTip(`<b>${esc(d.properties.name)}</b><br><span class="muted">no data</span>`, ev); return; }
        showTip(`<b>${esc(e.name)}</b>
          <div class="tt-row"><span>${esc(LAYERS[layer].label)}</span><span>${esc(LAYERS[layer].fmt(e))}</span></div>
          ${layer !== "power" ? `<div class="tt-row"><span>Power score</span><span>${LAYERS.power.fmt(e)}</span></div>` : ""}
          ${e.rank ? `<div class="tt-row"><span>Rank</span><span>#${e.rank} of ${e.nRanked}</span></div>` : ""}`, ev);
      })
      .on("mouseleave", hideTip)
      .on("click", (ev, d) => { if (E[d.iso]) select(d.iso); })
      .on("keydown", (ev, d) => { if ((ev.key === "Enter" || ev.key === " ") && E[d.iso]) { ev.preventDefault(); select(d.iso); } });
    const zoom = d3.zoom().scaleExtent([1, 8]).translateExtent([[0, 0], [W, H]])
      .on("zoom", ev => mapG.attr("transform", ev.transform));
    mapSvg.call(zoom).on("dblclick.zoom", null);
    paintMap();
  }
  function paintMap() {
    const L = LAYERS[layer];
    mapPaths.attr("fill", d => { const e = E[d.iso]; return (e && L.color(e)) || getComputedStyle(document.documentElement).getPropertyValue("--nodata"); })
      .classed("selected", d => d.iso === selected);
    const lg = L.legend();
    $("#legend").innerHTML = `<span class="ttl">${esc(lg.title)}</span>` +
      lg.items.map(([c, t]) => `<span><span class="sw" style="background:${c}"></span>${esc(t)}</span>`).join("") +
      `<span><span class="sw" style="background:var(--nodata)"></span>no data</span>`;
    $("#layer-desc").textContent = L.desc;
  }
  function buildLayerBar() {
    const bar = $("#layer-bar");
    bar.innerHTML = Object.entries(LAYERS).map(([k, L]) => `<button role="tab" data-layer="${k}" aria-selected="${k === layer}">${esc(L.label)}</button>`).join("");
    bar.addEventListener("click", ev => {
      const b = ev.target.closest("button"); if (!b) return;
      layer = b.dataset.layer;
      bar.querySelectorAll("button").forEach(x => x.setAttribute("aria-selected", x.dataset.layer === layer));
      paintMap(); renderTable();
    });
  }

  // ------------------------------------------------------------------ overview (nothing selected)
  let showAll24 = false;
  function renderOverview() {
    const list = (showAll24 ? Object.values(E).filter(e => e.inDalio24 || e.iso === "EUZ") : BIG.map(i => E[i]).filter(Boolean))
      .sort((a, b) => (b.power || 0) - (a.power || 0));
    $("#panel").innerHTML = `
      <div class="panel-head">
        <div><h2>The big powers right now</h2>
        <p class="section-sub">Each card shows the power score with its 20-year trend, and where the country sits on the three big cycles plus the empire arc. Click a card or the map for the full evidence.</p></div>
        <button class="btn" id="toggle24">${showAll24 ? "Show the 12 big powers" : "Show all of Dalio's 24"}</button>
      </div>
      <div class="cards">${list.map(card).join("")}</div>`;
    $("#toggle24").onclick = () => { showAll24 = !showAll24; renderOverview(); };
    $("#panel").querySelectorAll(".card").forEach(c => c.addEventListener("click", () => select(c.dataset.iso)));
  }
  function card(e) {
    const debt = stat(e, "gov_debt"), top10 = stat(e, "top10"), gini = stat(e, "gini");
    return `<button class="card panel-card" data-iso="${e.iso}" aria-label="Open ${esc(e.name)}">
      <div class="card-top">
        <div><div class="card-name">${esc(e.name)}</div>
          <div class="card-rank">${e.rank ? `#${e.rank} of ${e.nRanked}` : e.iso === "EUZ" ? "bloc (not ranked)" : ""}${e.dalio2024 != null ? ` · Dalio 2024: ${e.dalio2024.toFixed(2)}` : ""}</div>
          ${deltaHtml(e.delta20)}</div>
        <div class="score"><div class="num">${e.power != null ? e.power.toFixed(2) : "–"}</div><div class="lbl">power score</div></div>
      </div>
      ${cycleChips(e)}
      <div class="kv">
        <div><span class="k">Share of world GDP (PPP)</span><span class="v">${e.shares.gdp_ppp != null ? e.shares.gdp_ppp.toFixed(1) + "%" : "n/a"}</span></div>
        <div><span class="k">Gov. debt, % GDP</span><span class="v">${debt != null ? debt.toFixed(0) + "%" : "n/a"}</span></div>
        <div><span class="k">${top10 != null ? "Top-10% income share" : "Gini index"}</span><span class="v">${top10 != null ? top10.toFixed(0) + "%" : gini != null ? gini.toFixed(0) : "n/a"}</span></div>
        <div><span class="k">Share of world military spend</span><span class="v">${e.shares.mil_usd != null ? e.shares.mil_usd.toFixed(1) + "%" : "n/a"}</span></div>
      </div>
    </button>`;
  }

  // ------------------------------------------------------------------ detail
  function stepper(n, cur, colorFn) {
    let h = `<div class="stepper" aria-hidden="true">`;
    for (let i = 1; i <= n; i++) h += `<span class="${i === cur ? "on" : ""}" style="background:${colorFn(i)}"></span>`;
    return h + `</div>`;
  }
  function renderDetail(e) {
    const c = e.cycles, p = P();
    const debtC = s => s === 5 ? p.aqua : p.orange[s - 1];
    const intC = s => s === 1 ? p.blue[3] : s === 2 ? p.blue[1] : s === 3 ? p.neutral : p.red[[0, 0, 0, 0, 1, 3, 4][s]];
    const warC = l => l === 0 ? p.neutral : p.red[l - 1];
    const basis = b => `<span class="basis">${b === "computed" ? "computed by rule" : b === "curated" ? "curated assessment" : b === "curated list" ? "curated list" : "default"}</span>`;
    const verdict = e.verdict2022 ? `<blockquote>“${esc(e.name)} ${esc(e.verdict2022.charAt(0).toLowerCase() + e.verdict2022.slice(1))}”<cite>Dalio's computer-generated reading, Country Power Index 2022 (data as of Jan 2022) · <a href="${esc(META.dalio_sources.source_2022.url)}" target="_blank" rel="noopener">source</a></cite></blockquote>` : "";
    const quotes = (e.quotes || []).map(q => `<blockquote>“${esc(q.text)}”<cite>${esc(q.src)} · ${esc(q.date)} · <a href="${esc(q.url)}" target="_blank" rel="noopener">source</a></cite></blockquote>`).join("");
    const groups = [["cycle", "The big cycles"], ["key", "The eight key measures of power"], ["add", "Additional determinants"]];
    const d22map = { debt: "Debt Burden", growth: "Expected Growth", gaps: "Gaps in Wealth", conflict: "Internal Conflict", external: "External Order",
      education: "Education", innovation: "Innovation & Technology", cost: "Cost Competitiveness", military: "Military Strength", trade: "Trade",
      output: "Economic Output", markets: "Markets & Financial Center", reserve: "Reserve Currency Status", infra: "Infrastructure & Investment",
      governance: "Governance/Rule of Law", geology: "Geology", alloc: "Resource-Allocation Efficiency", character: "Character/Civility/Determination", nature: "Acts of Nature" };
    const gaugeRows = groups.map(([gid, title]) => `<div class="g-group"><h4>${title}</h4>` + GAUGES.filter(g => g.group === gid).map(g => {
      const v = e.gauges[g.id];
      const d22 = e.dalio2022gauges ? e.dalio2022gauges[d22map[g.id]] : null;
      if (!v) return `<div class="g-row" data-g="${g.id}"><div class="g-name">${esc(g.name)}<span class="rel">${esc(g.rel)}</span></div><div class="g-bar"></div><div class="g-val muted">not measured</div></div>`;
      const t = v.t == null ? "" : v.t > 0.01 ? `<span class="delta up">▲</span>` : v.t < -0.01 ? `<span class="delta down">▼</span>` : `<span class="delta flat">▶</span>`;
      return `<div class="g-row" data-g="${g.id}" data-d22="${d22 == null ? "" : d22}">
        <div class="g-name">${esc(g.name)}<span class="rel">${esc(g.rel)}</span></div>
        <div class="g-bar"><span class="mid"></span><span class="fill" style="width:${Math.max(1.5, v.s * 100).toFixed(1)}%"></span></div>
        <div class="g-val"><b>${Math.round(v.s * 100)}</b> ${v.r ? `<span class="muted">#${v.r}/${v.n}</span>` : ""} ${t}</div></div>`;
    }).join("") + `</div>`).join("");

    // evidence table, grouped by gauge
    const used = new Set();
    let proofRows = "";
    const statRow = k => {
      const s = e.stats[k]; if (!s || used.has(k)) return ""; used.add(k);
      const src = s.src || {};
      const share = e.shares[k] != null ? ` <span class="muted">(${e.shares[k].toFixed(1)}% of world)</span>` : "";
      return `<tr><td>${esc((STAT[k] || [k])[0])}${s.note && k !== "gfci_rank" ? ` <span class="muted">${esc(s.note)}</span>` : ""}</td><td class="v">${fmtStat(k, s.v)}${share}</td>
        <td class="tnum">${esc(s.y)}${s.stale ? `<span class="stale" title="Older than 5 years">stale</span>` : ""}</td>
        <td>${src.url ? `<a href="${esc(src.url)}" target="_blank" rel="noopener">${esc(src.org)}</a>` : esc(src.org || "")}<div class="muted" style="font-size:.72rem">${esc(src.label || "")}</div></td></tr>`;
    };
    for (const g of GAUGES) {
      const keys = [...g.size, ...g.quality].concat(g.id === "debt" ? ["primary_bal", "revenue", "hh_debt", "nfc_debt", "private_credit", "reserves"] : g.id === "output" ? ["gdp_usd", "pop", "ppp_share"] : []);
      const rows = keys.map(statRow).join("");
      if (rows) proofRows += `<tr class="grp"><td colspan="4">${esc(g.name)}</td></tr>` + rows;
    }
    const rest = Object.keys(e.stats).map(statRow).join("");
    if (rest) proofRows += `<tr class="grp"><td colspan="4">Other</td></tr>` + rest;

    const cmp = e.dalio2024 != null ? `Dalio's 2024 index: <b>${e.dalio2024.toFixed(2)}</b>${e.dalio2022 != null ? ` · 2022: ${e.dalio2022.toFixed(2)}` : ""}` : "Not in Dalio's 24-country index";
    $("#panel").innerHTML = `
      <div class="panel-head"><button class="btn" id="back">← Back to the big powers</button>
        <span class="muted" style="font-size:.8rem">Link to this page: <a href="#${e.iso}">#${e.iso}</a></span></div>
      <div class="detail">
        <div class="panel-card d-head">
          <div><h2>${esc(e.name)}</h2>
            <div class="meta">${esc(e.region || "")}${e.income ? " · " + esc(e.income) : ""}${e.rank ? ` · #${e.rank} of ${e.nRanked} countries` : ""}${e.rank24 ? ` · #${e.rank24} of Dalio's 24` : ""}</div>
            ${cycleChips(e)}</div>
          <div><div class="score"><div class="num">${e.power != null ? e.power.toFixed(2) : "–"}</div><div class="lbl">power score (0–1)</div></div>
            <div class="compare">${deltaHtml(e.delta20)}<br>${cmp}</div></div>
        </div>
        <div class="panel-card summary"><p>${esc(e.summary)}</p></div>
        ${verdict || quotes ? `<div class="panel-card dalio-voice"><h3>In Dalio's own words</h3>${verdict}${quotes}</div>` : ""}
        <div class="cycles">
          <div class="panel-card cycle"><h4>Big debt cycle</h4>
            <div class="stage">${c.debt.stage ? `Stage ${c.debt.stage} of 5 · ${esc(DEBT_L[c.debt.stage])}` : "Not enough data"}</div>
            ${stepper(5, c.debt.stage, debtC)}<div class="stepper-lbl"><span>sound money</span><span>recovery</span></div>
            <p class="why">${esc(c.debt.why)}</p>${basis(c.debt.basis)}</div>
          <div class="panel-card cycle"><h4>Internal order cycle</h4>
            <div class="stage">${c.internal.stage ? `Stage ${c.internal.stage} of 6 · ${esc(INT_L[c.internal.stage])}` : "Not enough data"}</div>
            ${stepper(6, c.internal.stage, intC)}<div class="stepper-lbl"><span>new order</span><span>civil war</span></div>
            <p class="why">${esc(c.internal.why)}</p>${basis(c.internal.basis)}</div>
          <div class="panel-card cycle"><h4>External order: war ladder</h4>
            <div class="stage">Level ${c.external.level} of 5 · ${esc(WAR_L[c.external.level])}</div>
            ${stepper(6, c.external.level + 1, i => warC(i - 1))}<div class="stepper-lbl"><span>peace</span><span>military war</span></div>
            <p class="why">${esc(c.external.why)}</p>${basis(c.external.basis)}</div>
          <div class="panel-card cycle"><h4>Empire arc</h4>
            <div class="stage">${esc(c.arc.phase)}</div>
            <div id="mini-arc"></div>
            <p class="why">20-year power change ${e.delta20 == null ? "n/a" : (e.delta20 >= 0 ? "+" : "") + e.delta20.toFixed(3)}; lagging minus leading strengths ${c.arc.lagMinusLead >= 0 ? "+" : ""}${c.arc.lagMinusLead.toFixed(2)} (positive means late-cycle: finance and currency outlast education and innovation).</p>
            <span class="basis">computed by rule</span></div>
        </div>
        <div class="panel-card gauges"><h3>Dalio's 18 determinants</h3>
          <p class="section-sub" style="margin-top:4px">Score from 0 to 100 (higher is stronger, so for debt and conflict a low score means a heavy burden or strong conflict). The rank is among all countries with data, and the arrow shows the change since ~${META.then_year}. Hover a row to see how it is built and, for Dalio's 24, his 2022 z-score.</p>
          ${gaugeRows}</div>
        <div class="panel-card proof"><h3>The evidence: every number behind the scores</h3>
          <p class="section-sub" style="margin-top:4px">Latest available value, its year and the source. Values older than 5 years are marked stale.</p>
          <div class="proof-scroll"><table><thead><tr><th>Statistic</th><th>Value</th><th>Year</th><th>Source</th></tr></thead><tbody>${proofRows}</tbody></table></div></div>
      </div>`;
    $("#back").onclick = () => select(null);
    $("#panel").querySelectorAll(".g-row").forEach(row => {
      row.addEventListener("mousemove", ev => {
        const g = GBY[row.dataset.g], v = e.gauges[g.id];
        const d22 = row.dataset.d22;
        showTip(`<b>${esc(g.name)}</b><div style="margin:4px 0">${esc(g.desc)}</div>
          ${v && v.sz != null ? `<div class="tt-row"><span>Size component</span><span>${Math.round(v.sz * 100)}</span></div>` : ""}
          ${v && v.q != null ? `<div class="tt-row"><span>Quality component</span><span>${Math.round(v.q * 100)}</span></div>` : ""}
          ${d22 !== "" ? `<div class="tt-row"><span>Dalio 2022 z-score</span><span>${(+d22 > 0 ? "+" : "") + d22}</span></div>` : ""}`, ev);
      });
      row.addEventListener("mouseleave", hideTip);
    });
    drawArc($("#mini-arc"), [e], { mini: true });
  }

  // ------------------------------------------------------------------ arc chart
  function drawArc(el, list, opts = {}) {
    el.innerHTML = "";
    const W = opts.mini ? 300 : 1000, H = opts.mini ? 120 : 380;
    const m = opts.mini ? { l: 10, r: 10, t: 14, b: 22 } : { l: 30, r: 30, t: 36, b: 46 };
    const x = u => m.l + ((u + 1) / 2) * (W - m.l - m.r);
    const curveY = u => H - m.b - (H - m.t - m.b) * Math.exp(-Math.pow(u / 0.55, 2));
    const svg = d3.select(el).append("svg").attr("viewBox", `0 0 ${W} ${H}`).attr("role", "img")
      .attr("aria-label", "Archetypal big cycle: rise, peak and decline, with countries placed on it");
    const pts = d3.range(-1, 1.001, 0.02).map(u => [x(u), curveY(u)]);
    svg.append("path").attr("d", d3.line()(pts)).attr("fill", "none").attr("stroke", "var(--axis)").attr("stroke-width", 2);
    svg.append("line").attr("x1", m.l).attr("x2", W - m.r).attr("y1", H - m.b).attr("y2", H - m.b).attr("stroke", "var(--grid)");
    const zones = [[-1, -0.2, "RISING"], [-0.2, 0.2, "PEAK"], [0.2, 1, "DECLINE"]];
    zones.forEach(([a, b, t]) => svg.append("text").attr("x", x((a + b) / 2)).attr("y", H - m.b + (opts.mini ? 15 : 20)).attr("text-anchor", "middle").attr("font-size", opts.mini ? 10 : 12).attr("letter-spacing", ".08em").text(t));
    if (!opts.mini) {
      const notes = [[-0.78, "education, innovation, competitiveness improve"], [0, "output, trade, military at their height"], [0.78, "debt, internal conflict; finance and currency fade last"]];
      notes.forEach(([u, t]) => svg.append("text").attr("x", x(u)).attr("y", H - m.b + 36).attr("text-anchor", "middle").attr("font-size", 11).attr("fill", "var(--muted)").text(t));
    }
    const rScale = d3.scaleSqrt().domain([0, 0.9]).range(opts.mini ? [5, 9] : [5, 22]);
    const items = list.filter(e => e.power != null).sort((a, b) => b.power - a.power);
    // simple vertical stacking to avoid overlap
    const placed = [];
    items.forEach(e => {
      const u = e.cycles.arc.u, cx = x(u); let cy = curveY(u); const r = rScale(e.power);
      let tries = 0;
      while (placed.some(p => Math.hypot(p.cx - cx, p.cy - cy) < p.r + r + 2) && tries < 40) { cy -= 4; tries++; }
      placed.push({ e, cx, cy, r });
    });
    const g = svg.append("g");
    placed.forEach(({ e, cx, cy, r }) => {
      const node = g.append("g").style("cursor", opts.mini ? "default" : "pointer");
      node.append("circle").attr("cx", cx).attr("cy", cy).attr("r", r).attr("fill", LAYERS.arc.color(e)).attr("stroke", "var(--surface)").attr("stroke-width", 2);
      if (!opts.mini) node.append("text").attr("x", cx).attr("y", cy - r - 5).attr("text-anchor", "middle").attr("class", "lbl-strong").attr("font-size", 12).text(e.iso === "EUZ" ? "Eurozone" : e.name.length > 12 ? e.iso : e.name);
      node.on("mousemove", ev => showTip(`<b>${esc(e.name)}</b><div class="tt-row"><span>Phase</span><span>${esc(e.cycles.arc.phase)}</span></div><div class="tt-row"><span>Power</span><span>${e.power.toFixed(2)}</span></div><div class="tt-row"><span>20-yr change</span><span>${e.delta20 == null ? "n/a" : (e.delta20 >= 0 ? "+" : "") + e.delta20.toFixed(3)}</span></div>`, ev))
        .on("mouseleave", hideTip);
      if (!opts.mini) node.on("click", () => select(e.iso));
    });
  }

  // ------------------------------------------------------------------ comparison chart (dot plot)
  function drawCompare() {
    const fit = META.fit;
    $("#cmp-sub").innerHTML = `Dalio does not publish his exact weights. Our scores combine the same determinants built from public data, with weights and scaling fitted to his 2024 scores. Fit across his 24 entities: Pearson <b>r = ${fit.pearson}</b>, rank correlation <b>${fit.spearman}</b>, mean absolute error <b>${fit.mae}</b>. Large gaps mark where public data and Dalio's proprietary inputs disagree.`;
    const list = Object.values(E).filter(e => e.dalio2024 != null).sort((a, b) => b.dalio2024 - a.dalio2024);
    const el = $("#cmp-chart"); el.innerHTML = `<div class="legend-row"><span><span class="sw" style="background:var(--s2)"></span>Dalio 2024 (published)</span><span><span class="sw" style="background:var(--s1)"></span>This site (computed ${esc(META.research_date)})</span></div>`;
    const rowH = 24, m = { l: 120, r: 40, t: 24, b: 10 }, W = 1000, H = m.t + m.b + rowH * list.length;
    const x = d3.scaleLinear().domain([0, 1]).range([m.l, W - m.r]);
    const svg = d3.select(el).append("svg").attr("viewBox", `0 0 ${W} ${H}`).attr("role", "img").attr("aria-label", "Dot plot comparing computed and Dalio power scores");
    const gx = svg.append("g").attr("class", "grid");
    x.ticks(10).forEach(t => {
      gx.append("line").attr("x1", x(t)).attr("x2", x(t)).attr("y1", m.t - 6).attr("y2", H - m.b);
      svg.append("text").attr("x", x(t)).attr("y", m.t - 10).attr("text-anchor", "middle").attr("font-size", 11).attr("class", "tnum").text(t.toFixed(1));
    });
    list.forEach((e, i) => {
      const y = m.t + i * rowH + rowH / 2;
      const row = svg.append("g").style("cursor", "pointer").on("click", () => select(e.iso));
      row.append("rect").attr("x", 0).attr("y", y - rowH / 2).attr("width", W).attr("height", rowH).attr("fill", "transparent");
      row.append("text").attr("x", m.l - 10).attr("y", y + 4).attr("text-anchor", "end").attr("class", "lbl-strong").text(e.name);
      if (e.power != null) row.append("line").attr("x1", x(e.dalio2024)).attr("x2", x(e.power)).attr("y1", y).attr("y2", y).attr("stroke", "var(--axis)").attr("stroke-width", 2);
      row.append("circle").attr("cx", x(e.dalio2024)).attr("cy", y).attr("r", 6).attr("fill", "var(--s2)").attr("stroke", "var(--surface)").attr("stroke-width", 2);
      if (e.power != null) row.append("circle").attr("cx", x(e.power)).attr("cy", y).attr("r", 6).attr("fill", "var(--s1)").attr("stroke", "var(--surface)").attr("stroke-width", 2);
      row.on("mousemove", ev => showTip(`<b>${esc(e.name)}</b><div class="tt-row"><span>Dalio 2024</span><span>${e.dalio2024.toFixed(2)}</span></div><div class="tt-row"><span>This site</span><span>${e.power == null ? "n/a" : e.power.toFixed(2)}</span></div><div class="tt-row"><span>Difference</span><span>${e.power == null ? "n/a" : (e.power - e.dalio2024 >= 0 ? "+" : "") + (e.power - e.dalio2024).toFixed(2)}</span></div>`, ev)).on("mouseleave", hideTip);
    });
  }

  // ------------------------------------------------------------------ table
  const COLS = [
    ["rank", "#", e => e.rank, "n"], ["name", "Country", e => e.name], ["power", "Power", e => e.power, "n", v => v == null ? "–" : v.toFixed(2)],
    ["delta", "20-yr Δ", e => e.delta20, "n", v => v == null ? "–" : (v >= 0 ? "+" : "") + v.toFixed(3)],
    ["debt", "Debt stage", e => e.cycles.debt.stage, "", (v, e) => v ? `<span class="swatch" style="background:${LAYERS.debt.color(e)}"></span>${v} ${esc(DEBT_L[v])}` : "–"],
    ["internal", "Internal stage", e => e.cycles.internal.stage, "", (v, e) => v ? `<span class="swatch" style="background:${LAYERS.internal.color(e)}"></span>${v} ${esc(INT_L[v])}` : "–"],
    ["war", "War ladder", e => e.cycles.external.level, "", (v, e) => `<span class="swatch" style="background:${LAYERS.external.color(e)}"></span>${v} ${esc(WAR_L[v])}`],
    ["arc", "Arc phase", e => e.power == null ? null : e.cycles.arc.phase, "", (v, e) => v ? `<span class="swatch" style="background:${LAYERS.arc.color(e)}"></span>${esc(v)}` : "–"],
    ["gdebt", "Gov. debt % GDP", e => stat(e, "gov_debt"), "n", v => v == null ? "–" : v.toFixed(0)],
    ["growth", "Exp. growth", e => stat(e, "growth_fcst"), "n", v => v == null ? "–" : v.toFixed(1) + "%"],
    ["d24", "Dalio 2024", e => e.dalio2024, "n", v => v == null ? "" : v.toFixed(2)],
  ];
  let sortKey = "power", sortDir = -1;
  function renderTable() {
    const f = ($("#table-filter").value || "").toLowerCase();
    const col = COLS.find(c => c[0] === sortKey);
    const rows = Object.values(E).filter(e => !f || e.name.toLowerCase().includes(f) || e.iso.toLowerCase() === f)
      .sort((a, b) => {
        const va = col[2](a), vb = col[2](b);
        if (va == null && vb == null) return 0; if (va == null) return 1; if (vb == null) return -1;
        return (typeof va === "string" ? va.localeCompare(vb) : va - vb) * sortDir;
      });
    $("#rank-table").innerHTML = `<thead><tr>${COLS.map(c => `<th data-k="${c[0]}" ${c[0] === sortKey ? `aria-sort="${sortDir > 0 ? "ascending" : "descending"}"` : ""} ${c[3] === "n" ? 'style="text-align:right"' : ""}>${c[1]}</th>`).join("")}</tr></thead>
      <tbody>${rows.map(e => `<tr data-iso="${e.iso}">${COLS.map(c => { const v = c[2](e); return `<td class="${c[3] || ""}">${c[4] ? c[4](v, e) : esc(v == null ? "–" : v)}</td>`; }).join("")}</tr>`).join("")}</tbody>`;
  }
  function wireTable() {
    $("#rank-table").addEventListener("click", ev => {
      const th = ev.target.closest("th");
      if (th) { const k = th.dataset.k; if (k === sortKey) sortDir *= -1; else { sortKey = k; sortDir = (k === "name" || k === "rank") ? 1 : -1; } renderTable(); return; }
      const tr = ev.target.closest("tr[data-iso]"); if (tr) select(tr.dataset.iso);
    });
    $("#table-filter").addEventListener("input", renderTable);
  }

  // ------------------------------------------------------------------ methodology + footer
  function renderMethod() {
    const fit = META.fit;
    const gRows = GAUGES.map(g => `<tr><td><b>${esc(g.name)}</b></td><td>${g.group === "cycle" ? "Big cycle" : g.group === "key" ? "Key 8" : "Additional"}</td><td>${esc(g.rel)}</td><td>${esc(g.desc)}</td></tr>`).join("");
    $("#method").innerHTML = `
      <h2 id="method-h">Method: how Dalio's model is rebuilt here</h2>
      <p>Dalio's <em>Changing World Order</em> argues that the rise and decline of countries is driven by <b>three big cycles</b>: the long-term debt and money cycle, the internal order/disorder cycle and the external order/disorder cycle. He measures their effects through <b>18 determinants</b>, including <b>eight key measures of power</b>: education, innovation & technology, cost competitiveness, military strength, trade, economic output, markets & financial centre, and reserve-currency status. In his annual index each determinant is a composite of several statistics, normalised across countries (z-scores, or percent ranks) and averaged into an overall 0–1 power score. He publishes the scores but not his exact weights or full data. This site is an <b>independent replication from public data</b>. It is not Dalio's or Bridgewater's model.</p>
      <h3>Scoring</h3>
      <ul>
        <li>Every gauge mixes a <b>size</b> part (share of the world total, compressed by exponent P = ${fit.P}) and a <b>quality</b> part (percent rank among all countries), following Dalio's note that he weighs both absolute and per-capita measures.</li>
        <li>Power = the mean of the eight key measures plus the additional determinants (weight ${fit.wa}) and the big-cycle gauges (weight ${fit.wc}). It is then linearly scaled (a = ${fit.a}, b = ${fit.b}) to Dalio's published 2024 scores. Fit over ${fit.n} entities: r = ${fit.pearson}, Spearman = ${fit.spearman}, MAE = ${fit.mae}.</li>
        <li>The 20-year trend recomputes each gauge with data nearest to ${META.then_year}. Gauges without history (external conflict, forecast growth) are left out of the trend.</li>
        <li>The <b>Eurozone</b> is shown as one bloc, as Dalio does: sizes are summed across the ${META.eurozone_members.length} members and ratios are GDP-weighted. Its trade figure counts only exports leaving the euro area (about 45% of members' total exports).</li>
      </ul>
      <h3>Cycle positions</h3>
      <ul>
        <li><b>Debt cycle (1–5):</b> the debt-risk score (1 − Debt Burden gauge) gives stage 1 below 0.35 and stage 2 from 0.35 to 0.6. Stage 3 applies at 0.6 or above, or when debt is at least 100% of GDP, or interest is at least 15% of revenue. Stage 4 applies when inflation is at least 40%, interest is at least 35% of revenue, or the country is in default. Stage 5 means a restructuring has been completed. The ~28 major countries carry a curated assessment written against Dalio's statements.</li>
        <li><b>Internal order (1–6):</b> internal stress = 0.4·gaps + 0.4·conflict + 0.2·debt-risk. Stress of 0.45 or more gives stage 4. Stress of 0.6 or more gives stage 5 when combined with debt stage ≥ 3 or political stability below −1. Stage 6 means civil war (curated list, or WGI political stability ≤ −2). Stage 1 means a new regime consolidating (curated).</li>
        <li><b>External order (0–5):</b> Dalio's ladder of war types, curated from events up to the research date.</li>
        <li><b>Empire arc:</b> position u = −(20-yr Δ / 0.05)·0.75 + (lagging − leading strengths)·0.5. Rising if u < −0.2, declining if u > 0.2.</li>
      </ul>
      <h3>The determinants and how each is measured</h3>
      <div class="scroll"><table><thead><tr><th>Determinant</th><th>Group</th><th>Dalio's reliability</th><th>Construction here</th></tr></thead><tbody>${gRows}</tbody></table></div>
      <h3>Limitations</h3>
      <ul>
        <li>Public data lags: many World Bank series end in 2022–2024, and stale values are flagged. Dalio's proprietary inputs (credit ratings, partisanship and protest counts, surveys of attitudes, venture funding) are not available, so proxies are used.</li>
        <li>Curated assessments are judgments. Each one states its reasoning and links to sources, and each is labelled curated rather than computed.</li>
        <li>Acts of Nature is not measured. Taiwan has IMF data only, because the World Bank does not cover it.</li>
      </ul>
      <h3>Sources</h3>
      <ul>${META.sources.map(s => `<li><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a></li>`).join("")}</ul>`;
  }
  function renderFooter() {
    $("#date-chip").textContent = `Research date: ${META.research_date}`;
    $("#footer").innerHTML = `
      <p class="research-date">Research date: ${esc(META.research_date)}</p>
      <p>Data pulled from the World Bank and IMF APIs on ${esc(META.data_fetched)}. Vintages: IMF WEO (latest, with forecasts to 2031), IMF COFER Q2 2026, SWIFT Global Currency Tracker Jun 2026, GFCI 40 (Sep 2026), FAS nuclear forces 2026, World Bank WGI (updated ${esc(META.vintages["GOV_WGI_RL.EST"] || "n/a")}), WDI (updated ${esc(META.vintages["NY.GDP.MKTP.PP.CD"] || "n/a")}).</p>
      <p>${esc(META.edition_note)} To make a new edition: update <code>research/curated.json</code>, run <code>python3 scripts/fetch_data.py --force</code> and <code>python3 scripts/build_data.py</code>; the date above updates automatically.</p>
      <p class="muted">An independent visualisation of the framework in Ray Dalio's <em>Principles for Dealing with the Changing World Order</em> (2021) and <em>How Countries Go Broke</em> (2025). It is not affiliated with Ray Dalio, Bridgewater or economicprinciples.org, and it is not investment advice.</p>`;
  }

  // ------------------------------------------------------------------ selection / routing
  function select(iso, fromHash) {
    selected = iso && E[iso] ? iso : null;
    if (!fromHash) history.replaceState(null, "", selected ? "#" + selected : location.pathname + location.search);
    if (selected) renderDetail(E[selected]); else renderOverview();
    paintMap();
    if (!fromHash || selected) $("#panel").scrollIntoView({ behavior: fromHash ? "auto" : "smooth", block: "start" });
  }
  function wireSearch() {
    const names = Object.values(E).sort((a, b) => a.name.localeCompare(b.name));
    $("#country-list").innerHTML = names.map(e => `<option value="${esc(e.name)}"></option>`).join("");
    const go = () => { const v = $("#search").value.trim().toLowerCase(); const hit = names.find(e => e.name.toLowerCase() === v) || names.find(e => e.name.toLowerCase().startsWith(v)); if (hit && v) { select(hit.iso); $("#search").value = ""; } };
    $("#search").addEventListener("change", go);
    $("#search").addEventListener("keydown", ev => { if (ev.key === "Enter") go(); });
  }

  function init() {
    buildLayerBar(); buildMap(); wireSearch(); wireTable(); renderTable();
    drawArc($("#arc-chart"), BIG.map(i => E[i]).filter(Boolean).concat(["IDN", "TUR", "SAU", "AUS", "MEX", "SGP"].map(i => E[i]).filter(Boolean)));
    drawCompare(); renderMethod(); renderFooter();
    const h = location.hash.slice(1).toUpperCase();
    if (h && E[h]) select(h, true); else renderOverview();
    addEventListener("hashchange", () => { const k = location.hash.slice(1).toUpperCase(); select(E[k] ? k : null, true); });
    matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { paintMap(); renderTable(); selected ? renderDetail(E[selected]) : renderOverview(); drawArc($("#arc-chart"), BIG.map(i => E[i]).filter(Boolean)); });
  }
  init();
})();
