/* ============ WC26 Match Centre ============
 * Client-side port of src/models/poisson_engine.py:
 *   λ_A = GLOBAL_BASE_XG × att_A × def_B × (squad_A / squad_B)
 * Goal counts are independent Poisson; the 10×10 joint grid gives
 * every market shown. Odds are fair odds (1 / probability).
 */

"use strict";

const MAX_GOALS = 10;        // scan grid size (matches the Python engine)
const HEAT_CAP = 6;          // heatmap shows 0..5 and aggregates 6+
const DIST_CAP = 7;          // goal distribution shows 0..6 and aggregates 7+
const BOOK_MARGIN = 0.0;      // 5% bookmaker margin on displayed odds (tune in one place)

/* ---------------- static tournament data ---------------- */

const FLAGS = {
  "Mexico": "🇲🇽", "South Africa": "🇿🇦", "South Korea": "🇰🇷", "Czechia": "🇨🇿",
  "Canada": "🇨🇦", "Bosnia and Herzegovina": "🇧🇦", "Qatar": "🇶🇦", "Switzerland": "🇨🇭",
  "Brazil": "🇧🇷", "Morocco": "🇲🇦", "Haiti": "🇭🇹", "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
  "United States": "🇺🇸", "Paraguay": "🇵🇾", "Australia": "🇦🇺", "Turkey": "🇹🇷",
  "Germany": "🇩🇪", "Curacao": "🇨🇼", "Ivory Coast": "🇨🇮", "Ecuador": "🇪🇨",
  "Netherlands": "🇳🇱", "Japan": "🇯🇵", "Sweden": "🇸🇪", "Tunisia": "🇹🇳",
  "Belgium": "🇧🇪", "Egypt": "🇪🇬", "Iran": "🇮🇷", "New Zealand": "🇳🇿",
  "Spain": "🇪🇸", "Cape Verde": "🇨🇻", "Saudi Arabia": "🇸🇦", "Uruguay": "🇺🇾",
  "France": "🇫🇷", "Senegal": "🇸🇳", "Iraq": "🇮🇶", "Norway": "🇳🇴",
  "Argentina": "🇦🇷", "Algeria": "🇩🇿", "Austria": "🇦🇹", "Jordan": "🇯🇴",
  "Portugal": "🇵🇹", "DR Congo": "🇨🇩", "Uzbekistan": "🇺🇿", "Colombia": "🇨🇴",
  "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Croatia": "🇭🇷", "Ghana": "🇬🇭", "Panama": "🇵🇦",
};

const DISPLAY_NAMES = { "Turkey": "Türkiye", "Curacao": "Curaçao" };

const GROUPS = {
  "Group A": ["Mexico", "South Africa", "South Korea", "Czechia"],
  "Group B": ["Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland"],
  "Group C": ["Brazil", "Morocco", "Haiti", "Scotland"],
  "Group D": ["United States", "Paraguay", "Australia", "Turkey"],
  "Group E": ["Germany", "Curacao", "Ivory Coast", "Ecuador"],
  "Group F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
  "Group G": ["Belgium", "Egypt", "Iran", "New Zealand"],
  "Group H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
  "Group I": ["France", "Senegal", "Iraq", "Norway"],
  "Group J": ["Argentina", "Algeria", "Austria", "Jordan"],
  "Group K": ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
  "Group L": ["England", "Croatia", "Ghana", "Panama"],
};

// Round-robin pairings by tournament matchday convention (same as the CLI app).
function groupFixtures(teams) {
  return [
    { md: 1, home: teams[0], away: teams[1] },
    { md: 1, home: teams[2], away: teams[3] },
    { md: 2, home: teams[0], away: teams[2] },
    { md: 2, home: teams[3], away: teams[1] },
    { md: 3, home: teams[3], away: teams[0] },
    { md: 3, home: teams[1], away: teams[2] },
  ];
}

let liveFixtures = WC26_FIXTURES;
let liveFixturesMeta = typeof FIXTURES_META !== "undefined" ? FIXTURES_META : {};

function getFixtures() {
  return liveFixtures;
}

function getFixture(home, away) {
  return liveFixtures.find(
    (f) => (f.home === home && f.away === away) || (f.home === away && f.away === home)
  );
}

function isBettable(home, away) {
  const fx = getFixture(home, away);
  if (!fx) return false;
  if (typeof WC26FixtureHelpers !== "undefined") {
    return WC26FixtureHelpers.isBettableFixture(fx);
  }
  return !!(fx.bettable && fx.status === "pending");
}

function fmtKickoff(iso) {
  if (!iso) return "Date TBD";
  return new Date(iso).toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function fixtureStatusLabel(f) {
  if (f.status === "settled" && f.homeScore != null) {
    return `${f.homeScore}–${f.awayScore} FT`;
  }
  if (f.status === "live") return "LIVE";
  if (!f.bettable && f.kickoff) return "Betting closed";
  if (!f.kickoff) return "Awaiting schedule";
  return fmtKickoff(f.kickoff);
}

/* ---------------- Poisson engine ---------------- */

const FACT = [1];
for (let i = 1; i < MAX_GOALS + 2; i++) FACT[i] = FACT[i - 1] * i;
const pmf = (k, lam) => (Math.exp(-lam) * Math.pow(lam, k)) / FACT[k];

function computeMatch(home, away) {
  const a = TEAM_RATINGS[home];
  const b = TEAM_RATINGS[away];
  const lambdaH = GLOBAL_BASE_XG * a.att * b.def * (a.squad / b.squad);
  const lambdaA = GLOBAL_BASE_XG * b.att * a.def * (b.squad / a.squad);

  const grid = [];
  let total = 0;
  for (let h = 0; h < MAX_GOALS; h++) {
    grid[h] = [];
    for (let g = 0; g < MAX_GOALS; g++) {
      grid[h][g] = pmf(h, lambdaH) * pmf(g, lambdaA);
      total += grid[h][g];
    }
  }

  let pHome = 0, pDraw = 0, pAway = 0, pBtts = 0;
  const totals = {};
  for (const line of [1.5, 2.5, 3.5]) totals[line] = 0;
  const scorelines = [];
  for (let h = 0; h < MAX_GOALS; h++) {
    for (let g = 0; g < MAX_GOALS; g++) {
      const p = grid[h][g] / total; // renormalise the truncated tail, like the Python engine
      if (h > g) pHome += p;
      else if (h === g) pDraw += p;
      else pAway += p;
      if (h >= 1 && g >= 1) pBtts += p;
      for (const line of [1.5, 2.5, 3.5]) if (h + g > line) totals[line] += p;
      scorelines.push({ h, g, p });
    }
  }
  scorelines.sort((x, y) => y.p - x.p);

  return { home, away, lambdaH, lambdaA, grid, total, pHome, pDraw, pAway, pBtts, totals, scorelines };
}

/* ---------------- formatting helpers ---------------- */

const flag = (t) => FLAGS[t] || "⚽";
const dname = (t) => DISPLAY_NAMES[t] || t;
const label = (t) => `${flag(t)} ${dname(t)}`;

function bookOdds(p) {
  if (p < 1e-4) return Infinity;
  return 1 / Math.min(0.999, p * (1 + BOOK_MARGIN));
}

function fmtOdds(p) {
  const o = bookOdds(p);
  if (!isFinite(o)) return "—";
  if (o >= 100) return o.toFixed(0);
  return o.toFixed(2);
}
const fmtPct = (p, dp = 1) => `${(p * 100).toFixed(dp)}%`;

// Round W/D/L to one decimal so the displayed trio always sums to 100.0%.
function outcomeTriple(pH, pD, pA) {
  const raw = [pH * 100, pD * 100, pA * 100];
  const r = raw.map((v) => Math.round(v * 10) / 10);
  const drift = Math.round((100 - (r[0] + r[1] + r[2])) * 10) / 10;
  if (drift) {
    const i = raw.indexOf(Math.max(...raw));
    r[i] = Math.round((r[i] + drift) * 10) / 10;
  }
  return r;
}

/* ---------------- app state ---------------- */

const SCHEDULED_TEAMS = [...new Set(WC26_FIXTURES.flatMap((f) => [f.home, f.away]))]
  .filter((t) => TEAM_RATINGS[t])
  .sort();
const TEAMS = SCHEDULED_TEAMS.length ? SCHEDULED_TEAMS : Object.keys(TEAM_RATINGS).sort();
const firstFx = WC26_FIXTURES.find((f) => f.bettable) || WC26_FIXTURES[0];
const state = {
  home: firstFx?.home || (TEAMS.includes("Argentina") ? "Argentina" : TEAMS[0]),
  away: firstFx?.away || (TEAMS.includes("Algeria") ? "Algeria" : TEAMS.find((t) => t !== TEAMS[0])),
  slip: [],
  stake: 10,
  selectedPrivateLeague: localStorage.getItem("wc26-selected-private-league") || null,
};

try {
  const saved = JSON.parse(localStorage.getItem("wc26-slip") || "null");
  if (saved && Array.isArray(saved.slip)) {
    state.slip = saved.slip;
    if (typeof saved.stake === "number") state.stake = saved.stake;
  }
} catch (e) { /* fresh start */ }

const $ = (id) => document.getElementById(id);
const saveSlip = () =>
  localStorage.setItem("wc26-slip", JSON.stringify({ slip: state.slip, stake: state.stake }));

/* ---------------- match view rendering ---------------- */

function fillSelects() {
  const mk = (sel, value, exclude) => {
    sel.innerHTML = TEAMS.filter((t) => t !== exclude)
      .map((t) => `<option value="${t}" ${t === value ? "selected" : ""}>${label(t)}</option>`)
      .join("");
  };
  mk($("homeSelect"), state.home, state.away);
  mk($("awaySelect"), state.away, state.home);
}

function oddsBtn(m, market, pick, p, extra = {}) {
  const selId = `${m.home}|${m.away}|${market}`;
  const selected = state.slip.some((s) => s.id === selId && s.pick === pick);
  const locked = extra.locked;
  const cls = ["odds-btn", selected ? "selected" : "", extra.best ? "best" : "", extra.cls || "", locked ? "locked" : ""]
    .filter(Boolean)
    .join(" ");
  const title = extra.title || pick;
  const dis = locked ? "disabled" : "";
  return `<button class="${cls}" data-id="${selId}" data-market="${market}" data-pick="${pick}"
            data-odds="${bookOdds(p).toFixed(4)}" data-prob="${p.toFixed(6)}" title="${title}" ${dis}>
            ${extra.top || ""}<span class="ob-odds">${fmtOdds(p)}</span>
            <span class="ob-prob">${extra.pct !== undefined ? `${extra.pct.toFixed(1)}%` : fmtPct(p)}</span></button>`;
}

function renderMatch() {
  const m = computeMatch(state.home, state.away);
  const fx = getFixture(state.home, state.away);
  const locked = !isBettable(state.home, state.away);
  const lockEl = $("matchLockBanner");
  if (fx && locked) {
    lockEl.classList.remove("hidden");
    lockEl.textContent =
      fx.status === "settled"
        ? `Final: ${dname(fx.home)} ${fx.homeScore}–${fx.awayScore} ${dname(fx.away)} — betting closed.`
        : fx.status === "live"
          ? "Match in progress — betting closed."
          : fx.kickoff
            ? `Kickoff ${fmtKickoff(fx.kickoff)} — betting closed for this match.`
            : "This match is not open for betting yet. Load the live schedule with scripts/fetch_fixtures.py.";
  } else if (fx && fx.kickoff) {
    lockEl.classList.remove("hidden");
    lockEl.classList.add("open");
    lockEl.textContent = `${fx.group} · ${fmtKickoff(fx.kickoff)} · betting open until kickoff`;
  } else {
    lockEl.classList.add("hidden");
    lockEl.classList.remove("open");
  }

  const [hPct, dPct, aPct] = outcomeTriple(m.pHome, m.pDraw, m.pAway);
  const outcomes = [
    { lab: `${dname(m.home)} Win`, pct: hPct, p: m.pHome, key: "home" },
    { lab: "Draw", pct: dPct, p: m.pDraw, key: "draw" },
    { lab: `${dname(m.away)} Win`, pct: aPct, p: m.pAway, key: "away" },
  ];
  const pick = outcomes.reduce((x, y) => (y.pct > x.pct ? y : x));

  // --- hero ---
  $("heroCard").innerHTML = `
    <div class="hero-grid">
      <div class="hero-team">
        <div class="hero-flag">${flag(m.home)}</div>
        <div class="hero-name">${dname(m.home)}</div>
        <div class="hero-xg" title="Expected goals: the average number of goals this team is predicted to score in this matchup — an average, not a guarantee.">xG <b>${m.lambdaH.toFixed(2)}</b></div>
      </div>
      <div class="hero-mid">
        <div class="hero-vs">VS</div>
        <div class="pick-badge"><small>MODEL PICK</small>${pick.lab} · ${pick.pct.toFixed(1)}%</div>
      </div>
      <div class="hero-team">
        <div class="hero-flag">${flag(m.away)}</div>
        <div class="hero-name">${dname(m.away)}</div>
        <div class="hero-xg" title="Expected goals: the average number of goals this team is predicted to score in this matchup — an average, not a guarantee.">xG <b>${m.lambdaA.toFixed(2)}</b></div>
      </div>
    </div>`;

  // --- outcome bar ---
  $("outcomeBar").innerHTML = `
    <div class="outcome-legend">
      <span class="ol-home">${dname(m.home)} ${hPct.toFixed(1)}%</span>
      <span class="ol-draw">Draw ${dPct.toFixed(1)}%</span>
      <span class="ol-away">${dname(m.away)} ${aPct.toFixed(1)}%</span>
    </div>
    <div class="outcome-bar">
      <div class="seg-home" style="width:${hPct}%"></div>
      <div class="seg-draw" style="width:${dPct}%"></div>
      <div class="seg-away" style="width:${aPct}%"></div>
    </div>`;

  // --- markets ---
  const lockOpt = { locked };
  const row = (labelHtml, btns) =>
    `<div class="market-row"><span class="row-label">${labelHtml}</span>${btns}</div>`;
  const card = (name, inner) =>
    `<div class="market-card"><div class="market-name">${name}</div><div class="market-rows">${inner}</div></div>`;

  const m1x2 = card("Match Result (1X2)",
    row(label(m.home), oddsBtn(m, "1X2", `${dname(m.home)} Win`, m.pHome, { ...lockOpt, best: pick.key === "home", pct: hPct })) +
    row("🤝 Draw", oddsBtn(m, "1X2", "Draw", m.pDraw, { ...lockOpt, best: pick.key === "draw", pct: dPct })) +
    row(label(m.away), oddsBtn(m, "1X2", `${dname(m.away)} Win`, m.pAway, { ...lockOpt, best: pick.key === "away", pct: aPct })));

  const mdc = card("Double Chance",
    row(`${dname(m.home)} or Draw`, oddsBtn(m, "DC", `${dname(m.home)} or Draw`, m.pHome + m.pDraw, lockOpt)) +
    row(`${dname(m.home)} or ${dname(m.away)}`, oddsBtn(m, "DC", `${dname(m.home)} or ${dname(m.away)}`, m.pHome + m.pAway, lockOpt)) +
    row(`Draw or ${dname(m.away)}`, oddsBtn(m, "DC", `Draw or ${dname(m.away)}`, m.pDraw + m.pAway, lockOpt)));

  const mtot = card("Total Goals (Over / Under)",
    [1.5, 2.5, 3.5].map((line) =>
      row(`${line} goals`,
        oddsBtn(m, `OU${line}`, `Over ${line}`, m.totals[line], { ...lockOpt, title: `Over ${line} goals` }) +
        oddsBtn(m, `OU${line}`, `Under ${line}`, 1 - m.totals[line], { ...lockOpt, title: `Under ${line} goals` }))
    ).join(""));

  const mbtts = card("Both Teams To Score",
    row("Yes — both score", oddsBtn(m, "BTTS", "BTTS: Yes", m.pBtts, lockOpt)) +
    row("No — at least one blanks", oddsBtn(m, "BTTS", "BTTS: No", 1 - m.pBtts, lockOpt)));

  const top6 = m.scorelines.slice(0, 6);
  const ranks = ["①", "②", "③", "④", "⑤", "⑥"];
  const mcs = `<div class="market-card"><div class="market-name">Correct Score — top 6 most likely</div>
    <div class="score-grid">${top6.map((s, i) => {
      const pickLab = `Score ${s.h}–${s.g}`;
      const selId = `${m.home}|${m.away}|CS`;
      const selected = state.slip.some((x) => x.id === selId && x.pick === pickLab);
      return `<button class="odds-btn score-btn ${selected ? "selected" : ""} ${i === 0 ? "best" : ""} ${locked ? "locked" : ""}"
        data-id="${selId}" data-market="CS" data-pick="${pickLab}"
        data-odds="${bookOdds(s.p / m.total).toFixed(4)}" data-prob="${(s.p / m.total).toFixed(6)}"
        title="${dname(m.home)} ${s.h} – ${s.g} ${dname(m.away)}" ${locked ? "disabled" : ""}>
        <span class="rank-dot">${ranks[i]}${i === 0 ? " most likely" : ""}</span>
        <span class="ob-odds ob-score">${s.h} – ${s.g}</span>
        <span class="ob-prob">${fmtPct(s.p / m.total, 2)} · @${fmtOdds(s.p / m.total)}</span></button>`;
    }).join("")}</div></div>`;

  $("marketsGrid").innerHTML = m1x2 + mdc + mtot + mbtts + mcs;

  // --- goal distributions ---
  renderDist($("distHome"), m.home, m.lambdaH, false);
  renderDist($("distAway"), m.away, m.lambdaA, true);

  // --- score heatmap ---
  renderHeatmap(m);
}

function renderDist(el, team, lam, isAway) {
  const probs = [];
  for (let k = 0; k < DIST_CAP; k++) probs.push({ k: String(k), p: pmf(k, lam) });
  probs.push({ k: `${DIST_CAP}+`, p: Math.max(0, 1 - probs.reduce((s, r) => s + r.p, 0)) });
  const maxP = Math.max(...probs.map((r) => r.p));
  el.innerHTML = `
    <div class="ic-title">${label(team)} — goal distribution</div>
    <div class="ic-sub">Chance of scoring exactly N goals · xG ${lam.toFixed(2)}</div>
    ${probs.map((r) => `
      <div class="dist-row ${isAway ? "away" : ""}">
        <span class="dr-label">${r.k}</span>
        <span class="dr-track"><span class="dr-fill" style="width:${(r.p / maxP) * 100}%; display:block"></span></span>
        <span class="dr-val">${fmtPct(r.p)}</span>
      </div>`).join("")}`;
}

function renderHeatmap(m) {
  // aggregate the 10×10 grid into 0..5 and 6+ buckets, renormalised
  const n = HEAT_CAP + 1;
  const agg = Array.from({ length: n }, () => Array(n).fill(0));
  for (let h = 0; h < MAX_GOALS; h++)
    for (let g = 0; g < MAX_GOALS; g++)
      agg[Math.min(h, HEAT_CAP)][Math.min(g, HEAT_CAP)] += m.grid[h][g] / m.total;
  const maxP = Math.max(...agg.flat());
  const lab = (i) => (i === HEAT_CAP ? `${HEAT_CAP}+` : String(i));

  let rows = `<tr><th></th><th class="axis" colspan="${n}">${label(m.away)} goals →</th></tr>`;
  rows += `<tr><th class="axis">${flag(m.home)} ↓</th>${Array.from({ length: n }, (_, g) => `<th>${lab(g)}</th>`).join("")}</tr>`;
  for (let h = 0; h < n; h++) {
    rows += `<tr><th>${lab(h)}</th>`;
    for (let g = 0; g < n; g++) {
      const p = agg[h][g];
      const alpha = maxP > 0 ? Math.pow(p / maxP, 0.85) : 0;
      const hot = alpha > 0.55;
      rows += `<td class="${hot ? "hot" : ""}" style="background:rgba(31,212,127,${(alpha * 0.92).toFixed(3)})"
        title="${dname(m.home)} ${lab(h)} – ${lab(g)} ${dname(m.away)} · ${fmtPct(p, 2)} (fair odds ${fmtOdds(p)})">
        ${p >= 0.005 ? fmtPct(p, 1) : "·"}</td>`;
    }
    rows += "</tr>";
  }
  $("heatmapCard").innerHTML = `
    <div class="heatmap-title">Exact scoreline probabilities</div>
    <div class="heatmap-sub">Rows: ${dname(m.home)} goals · Columns: ${dname(m.away)} goals.
      Greener = more likely. Hover any cell for fair odds.</div>
    <table class="heatmap">${rows}</table>`;
}

/* ---------------- groups view ---------------- */

function renderGroups() {
  $("groupsGrid").innerHTML = Object.entries(GROUPS).map(([gname, teams]) => {
    const xpts = Object.fromEntries(teams.map((t) => [t, 0]));
    for (const f of groupFixtures(teams)) {
      const r = computeMatch(f.home, f.away);
      xpts[f.home] += 3 * r.pHome + r.pDraw;
      xpts[f.away] += 3 * r.pAway + r.pDraw;
    }
    const sorted = [...teams].sort((a, b) => xpts[b] - xpts[a]);
    return `<div class="group-card"><h3>${gname} <small>xPts</small></h3>
      ${sorted.map((t, i) => `
        <div class="gc-row ${i < 2 ? "qualify" : ""}">
          <span class="gc-pos">${i + 1}</span>
          <span class="gc-team">${label(t)}</span>
          <span class="gc-pts">${xpts[t].toFixed(1)}</span>
        </div>`).join("")}
    </div>`;
  }).join("");
}

function fixtureRowHtml(f, { showActions = true } = {}) {
  const H = WC26FixtureHelpers;
  const status = H.effectiveStatus(f);
  const statusCls =
    status === "settled" ? "done" : status === "live" ? "live" : isBettable(f.home, f.away) ? "open" : "locked";
  const canBet = isBettable(f.home, f.away);
  const actionBtn = !showActions
    ? ""
    : canBet
      ? `<button class="fx-btn" data-home="${f.home}" data-away="${f.away}">View odds →</button>`
      : status === "live"
        ? `<button class="fx-btn fx-btn-muted" data-home="${f.home}" data-away="${f.away}">View match →</button>`
        : `<span class="fx-locked-label">Betting closed</span>`;
  return `
    <div class="fixture-row ${canBet ? "" : "fixture-closed"}">
      <span class="fx-meta">${f.group} · MD ${f.md}</span>
      <span class="fx-teams"><b>${label(f.home)}</b> <span class="fx-vs">vs</span> <b>${label(f.away)}</b></span>
      <span class="fx-status ${statusCls}">${H.statusLabel(f)}</span>
      ${actionBtn}
    </div>`;
}

function formatFixtureMeta(meta) {
  if (meta?.source !== "api" || !meta.updatedAt) return "awaiting schedule";
  const updated = new Date(meta.updatedAt);
  const mins = Math.round((Date.now() - updated) / 60000);
  if (mins > 15) return `updated ${updated.toLocaleString()} · may be stale (${mins} min old)`;
  if (mins < 2) return "updated just now";
  return `updated ${mins} min ago`;
}

function renderFixtures() {
  const g = $("groupFilter").value;
  const md = document.querySelector("#mdFilter .seg-btn.active").dataset.md;
  const H = WC26FixtureHelpers;

  const list = getFixtures()
    .filter((f) => (g === "all" || f.group === g) && (md === "all" || String(f.md) === md))
    .sort((a, b) => {
      const rank = (f) => (f.status === "live" ? 0 : f.status === "pending" ? 1 : 2);
      const dr = rank(a) - rank(b);
      if (dr !== 0) return dr;
      if (a.status === "settled" && b.status === "settled") {
        return (b.kickoff || "").localeCompare(a.kickoff || "");
      }
      return (a.kickoff || "").localeCompare(b.kickoff || "");
    });

  const finished = list.filter((f) => H.isFinished(f)).length;
  const meta = liveFixturesMeta || FIXTURES_META || {};
  const sync = formatFixtureMeta(meta);
  $("fixturesTitle").innerHTML = `Tournament Schedule <span class="fair-tag" id="fixturesMeta"></span>`;
  $("fixturesMeta").textContent =
    meta.source === "api"
      ? `${list.length} matches · ${finished} finished · ${sync}`
      : `${list.length} matches · awaiting schedule`;

  $("fixturesList").innerHTML = list.length
    ? list.map((f) => fixtureRowHtml(f, { showActions: f.status !== "settled" })).join("")
    : `<p class="note">No matches in this filter.</p>`;
}

/* ---------------- bet slip ---------------- */

function matchKey(home, away) {
  return `${home}|${away}`;
}

function marketFamily(market) {
  if (market === "CS") return "cs";
  if (market === "1X2" || market === "DC") return "outcome";
  if (market.startsWith("OU")) return "ou";
  if (market === "BTTS") return "btts";
  return "other";
}

function sameMatchSelections(home, away) {
  const key = matchKey(home, away);
  return state.slip.filter((s) => matchKey(s.home, s.away) === key);
}

/** Block correlated same-match legs: CS stands alone; 1X2 and DC don't stack. */
function canAddToSlip(sel, excludeId = null) {
  const others = sameMatchSelections(sel.home, sel.away).filter((s) => s.id !== excludeId);
  const family = marketFamily(sel.market);

  if (family === "cs") {
    if (others.length) {
      return { ok: false, msg: "Correct score must be the only pick for this match" };
    }
    return { ok: true };
  }
  if (others.some((s) => marketFamily(s.market) === "cs")) {
    return { ok: false, msg: "Remove the correct score pick to add other markets for this match" };
  }
  if (family === "outcome") {
    const otherOutcome = others.find((s) => marketFamily(s.market) === "outcome");
    if (otherOutcome) return { ok: true, replaceOutcome: otherOutcome };
  }
  return { ok: true };
}

function renderSlip() {
  $("slipCount").textContent = state.slip.length;
  if (!state.slip.length) {
    $("slipBody").innerHTML = `<div class="slip-empty">Your slip is empty.<br><br>
      Tap any odds button in the Markets section to add a selection.
      Mix matches to build an accumulator.<br><br>
      Same match: combine result (1X2 or double chance) with goals markets — not with correct score.</div>`;
    $("slipFoot").innerHTML = "";
    return;
  }
  $("slipBody").innerHTML = state.slip.map((s, i) => `
    <div class="sel-card">
      <div class="sel-top"><span class="sel-pick">${s.pick}</span><span class="sel-odds">@${s.odds.toFixed(2)}</span></div>
      <div class="sel-meta">${s.match} · ${s.marketName}</div>
      <button class="sel-remove" data-i="${i}">Remove</button>
    </div>`).join("");

  const totalOdds = state.slip.reduce((x, s) => x * s.odds, 1);
  const ret = state.stake * totalOdds;
  const user = WC26Auth.getUser();
  const balance = user ? user.tokens : 0;

  $("slipFoot").innerHTML = `
    <div class="slip-line"><span>Selections</span><b>${state.slip.length}</b></div>
    <div class="slip-line"><span>Combined fair odds</span><b class="big">@${totalOdds >= 100 ? totalOdds.toFixed(0) : totalOdds.toFixed(2)}</b></div>
    <div class="slip-line"><span>Model chance all land</span><b>${fmtPct(1 / totalOdds, totalOdds > 50 ? 2 : 1)}</b></div>
    <div class="stake-row"><label>Stake</label><input type="number" id="stakeInput" min="1" step="1" max="${balance}" value="${state.stake}"><label>tokens</label></div>
    <div class="slip-line"><span>Potential return</span><b class="big">${ret >= 1000 ? ret.toFixed(0) : ret.toFixed(2)}</b></div>
    ${user ? `<div class="slip-line"><span>Your balance</span><b>🪙 ${balance.toLocaleString()}</b></div>` : ""}
    <div class="slip-actions">
      <button class="slip-send" id="slipSend">📤 Send bet slip</button>
      <button class="slip-place" id="slipPlace">✅ Place bet</button>
    </div>
    <button class="slip-clear" id="slipClear">Clear slip</button>
    <div class="slip-note">${(BOOK_MARGIN * 100).toFixed(0)}% bookmaker margin applied to displayed odds.</div>`;

  $("stakeInput").addEventListener("input", (e) => {
    state.stake = Math.max(1, parseFloat(e.target.value) || 1);
    saveSlip();
    renderSlip();
    $("stakeInput").focus();
  });
  $("slipSend").addEventListener("click", () => sendBetSlip(totalOdds));
  $("slipPlace").addEventListener("click", () => placeBet(totalOdds));
  $("slipClear").addEventListener("click", () => {
    state.slip = [];
    saveSlip();
    renderSlip();
    renderMatch();
  });
}

async function sendBetSlip(totalOdds) {
  if (!state.slip.length) { toast("Slip is empty"); return; }
  const text = WC26Auth.formatSlipForShare(state.slip, state.stake, totalOdds);
  try {
    if (navigator.share) {
      await navigator.share({ title: "WC26 Bet Slip", text });
      toast("Bet slip shared!");
      return;
    }
  } catch (e) { /* fall through to clipboard */ }
  try {
    await navigator.clipboard.writeText(text);
    toast("Bet slip copied to clipboard!");
  } catch {
    prompt("Copy your bet slip:", text);
  }
}

async function placeBet(totalOdds) {
  const closed = state.slip.find((s) => !isBettable(s.home, s.away));
  if (closed) {
    toast("Betting closed for one or more selections on your slip");
    return;
  }
  try {
    await WC26Auth.placeBet(state.stake, state.slip, totalOdds);
    state.slip = [];
    saveSlip();
    renderSlip();
    renderMatch();
    updateUserUI();
    toast("Bet placed! Good luck 🍀");
    if (!$("view-mybets").classList.contains("hidden")) renderMyBets();
  } catch (e) {
    toast(e.message || "Could not place bet");
  }
}

async function renderLeague() {
  const user = WC26Auth.getUser();
  const board = await WC26Auth.getLeaderboard();
  const rank = board.findIndex((u) => u.id === user?.id) + 1;

  $("leagueYou").innerHTML = user
    ? `<div class="ly-row"><span>Global rank</span><b>#${rank || "—"} of ${board.length}</b></div>
       <div class="ly-row"><span>Your balance</span><b class="big">🪙 ${user.tokens.toLocaleString()}</b></div>
       <div class="ly-row"><span>Playing as</span><b>${user.username}</b></div>`
    : "";

  $("leagueBody").innerHTML = board.map((u, i) => {
    const isYou = user && u.id === user.id;
    const medal = i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : i + 1;
    return `<tr class="${isYou ? "you" : ""}"><td>${medal}</td><td>${u.username}${isYou ? " (you)" : ""}</td><td>🪙 ${u.tokens.toLocaleString()}</td></tr>`;
  }).join("");

  $("privateLeagueNote").textContent = WC26Auth.isCloud()
    ? "Create a league, share the 6-digit ID with friends, or join theirs."
    : "Private leagues work in this browser only. Enable Firebase for leagues shared with friends online.";

  if (!user) {
    $("privateLeagueTabs").classList.add("hidden");
    $("privateLeaguePanel").classList.add("hidden");
    return;
  }

  const privateLeagues = await WC26Auth.getPrivateLeagues();
  if (!privateLeagues.length) {
    $("privateLeagueTabs").classList.add("hidden");
    $("privateLeaguePanel").classList.add("hidden");
    return;
  }

  if (!state.selectedPrivateLeague || !privateLeagues.some((l) => (l.code || l.id) === state.selectedPrivateLeague)) {
    state.selectedPrivateLeague = privateLeagues[0].code || privateLeagues[0].id;
    localStorage.setItem("wc26-selected-private-league", state.selectedPrivateLeague);
  }

  $("privateLeagueTabs").classList.remove("hidden");
  $("privateLeagueTabs").innerHTML = privateLeagues
    .map((l) => {
      const code = l.code || l.id;
      const active = code === state.selectedPrivateLeague ? "active" : "";
      return `<button class="pl-tab ${active}" data-league="${code}">${l.name}</button>`;
    })
    .join("");

  const active = privateLeagues.find((l) => (l.code || l.id) === state.selectedPrivateLeague) || privateLeagues[0];
  const code = active.code || active.id;
  const pBoard = await WC26Auth.getPrivateLeagueLeaderboard(code);
  const pRank = pBoard.findIndex((u) => u.id === user.id) + 1;

  $("privateLeaguePanel").classList.remove("hidden");
  $("privateLeagueYou").innerHTML = `
    <div class="ly-row"><span>Rank in this group</span><b>#${pRank || "—"} of ${pBoard.length}</b></div>
    <div class="ly-row"><span>Your balance</span><b class="big">🪙 ${user.tokens.toLocaleString()}</b></div>`;
  $("privateLeagueMeta").innerHTML = `
    <span class="pl-id">League ID: <b id="activeLeagueCode">${code}</b></span>
    <button class="pl-copy" type="button" id="copyLeagueCodeBtn">Copy ID</button>`;
  $("privateLeagueBody").innerHTML = pBoard.map((u, i) => {
    const isYou = u.id === user.id;
    const medal = i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : i + 1;
    return `<tr class="${isYou ? "you" : ""}"><td>${medal}</td><td>${u.username}${isYou ? " (you)" : ""}</td><td>🪙 ${u.tokens.toLocaleString()}</td></tr>`;
  }).join("");
}

function showLeagueModal(mode) {
  $("leagueModalBackdrop").classList.remove("hidden");
  $("leagueModal").classList.remove("hidden");
  $("leagueModalError").classList.add("hidden");
  $("createLeagueForm").classList.toggle("hidden", mode !== "create");
  $("joinLeagueForm").classList.toggle("hidden", mode !== "join");
  $("leagueModalTitle").textContent = mode === "create" ? "Create private league" : "Join private league";
}

function hideLeagueModal() {
  $("leagueModalBackdrop").classList.add("hidden");
  $("leagueModal").classList.add("hidden");
  $("createLeagueName").value = "";
  $("joinLeagueCode").value = "";
  $("leagueModalError").classList.add("hidden");
}

function showLeagueModalError(msg) {
  const el = $("leagueModalError");
  el.textContent = msg;
  el.classList.toggle("hidden", !msg);
}

function betEditable(bet) {
  if (bet.status !== "open") return false;
  return bet.picks.every((p) => p.home && p.away && isBettable(p.home, p.away));
}

function betStatusLabel(status) {
  return { open: "Open", won: "Won", lost: "Lost", cancelled: "Cancelled" }[status] || status;
}

async function renderMyBets() {
  const user = WC26Auth.getUser();
  if (!user) {
    $("myBetsList").innerHTML = `<p class="note">Log in to view your bets.</p>`;
    return;
  }
  const bets = WC26Auth.getBets();
  if (!bets.length) {
    $("myBetsList").innerHTML = `<p class="note">No bets yet. Pick a match, build a slip, and hit <strong>Place bet</strong>.</p>`;
    return;
  }

  $("myBetsList").innerHTML = bets
    .map((b) => {
      const editable = betEditable(b);
      const statusCls = b.status === "open" ? "open" : b.status === "won" ? "won" : b.status === "lost" ? "lost" : "cancelled";
      return `
    <div class="panel my-bet-card" data-bet-id="${b.id}">
      <div class="bet-top">
        <span class="bet-status ${statusCls}">${betStatusLabel(b.status)}</span>
        <span>${b.legs} leg${b.legs > 1 ? "s" : ""} · @${b.totalOdds.toFixed(2)}</span>
      </div>
      <div class="bet-meta">Placed ${new Date(b.placedAt).toLocaleString()} · Potential <b>${b.potential.toLocaleString()}</b> tokens</div>
      ${b.picks
        .map(
          (p, i) => `
        <div class="bet-pick-row">
          <span>${p.pick} — ${p.match}</span>
          ${editable ? `<button class="bet-leg-remove" data-action="remove-leg" data-bet="${b.id}" data-leg="${i}">Remove</button>` : ""}
        </div>`
        )
        .join("")}
      <div class="my-bet-foot">
        ${
          editable
            ? `<label class="stake-edit">Stake <input type="number" min="1" max="${user.tokens + b.stake}" value="${b.stake}" data-stake-input="${b.id}"></label>
               <button class="bet-save-stake" data-action="save-stake" data-bet="${b.id}">Update stake</button>
               <button class="bet-cancel" data-action="cancel" data-bet="${b.id}">Cancel bet · refund ${b.stake}</button>`
            : `<span class="bet-locked-stake">Stake: ${b.stake} tokens</span>`
        }
      </div>
    </div>`;
    })
    .join("");
}

function updateUserUI() {
  const user = WC26Auth.getUser();
  $("tokenBalance").textContent = user ? user.tokens.toLocaleString() : "—";
  $("userPill").textContent = user ? user.username : "";
}

function outcomeKey(market, pick, home, away) {
  if (market === "1X2") {
    if (pick === "Draw") return "draw";
    if (pick === `${dname(home)} Win`) return "home";
    if (pick === `${dname(away)} Win`) return "away";
  }
  if (market === "DC") {
    if (pick === `${dname(home)} or Draw`) return "1X";
    if (pick === `${dname(home)} or ${dname(away)}`) return "12";
    if (pick === `Draw or ${dname(away)}`) return "X2";
  }
  if (market.startsWith("OU")) {
    const line = market.slice(2);
    if (pick === `Over ${line}`) return `over_${line}`;
    if (pick === `Under ${line}`) return `under_${line}`;
  }
  if (market === "BTTS") return pick === "BTTS: Yes" ? "btts_yes" : "btts_no";
  if (market === "CS") {
    const m = pick.match(/(\d+)[–-](\d+)/);
    if (m) return `cs_${m[1]}_${m[2]}`;
  }
  return null;
}

function toggleSelection(btn) {
  if (btn.disabled || btn.classList.contains("locked")) return;
  const { id, market, pick } = btn.dataset;
  const odds = parseFloat(btn.dataset.odds);
  const [home, away] = id.split("|");
  if (!isBettable(home, away)) {
    toast("Betting closed for this match");
    return;
  }
  const fx = getFixture(home, away);
  const existing = state.slip.findIndex((s) => s.id === id);
  const marketNames = { "1X2": "Match Result", DC: "Double Chance", BTTS: "Both Teams To Score", CS: "Correct Score" };
  const marketName = marketNames[market] || (market.startsWith("OU") ? `Total Goals ${market.slice(2)}` : market);

  if (existing >= 0 && state.slip[existing].pick === pick) {
    state.slip.splice(existing, 1); // tap again to remove
  } else {
    const sel = {
      id,
      pick,
      odds,
      market,
      marketName,
      home,
      away,
      fixtureId: fx?.id ?? null,
      outcome: outcomeKey(market, pick, home, away),
      match: `${dname(home)} vs ${dname(away)}`,
    };
    if (existing >= 0) {
      state.slip[existing] = sel; // replace pick within same market
      toast(`Added: ${pick} @${odds.toFixed(2)}`);
    } else {
      const check = canAddToSlip(sel);
      if (!check.ok) {
        toast(check.msg);
        return;
      }
      if (check.replaceOutcome) {
        const idx = state.slip.indexOf(check.replaceOutcome);
        if (idx >= 0) state.slip.splice(idx, 1);
        toast(`Swapped ${check.replaceOutcome.pick} for ${pick}`);
      } else {
        toast(`Added: ${pick} @${odds.toFixed(2)}`);
      }
      state.slip.push(sel);
    }
  }
  saveSlip();
  renderSlip();
  renderMatch();
}

/* ---------------- misc UI ---------------- */

let toastTimer = null;
function toast(msg) {
  const el = $("toast");
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 1800);
}

function showView(view) {
  document.querySelectorAll(".nav-pill").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
  $("view-matches").classList.toggle("hidden", view !== "matches");
  $("view-match").classList.toggle("hidden", view !== "match");
  $("view-groups").classList.toggle("hidden", view !== "groups");
  $("view-mybets").classList.toggle("hidden", view !== "mybets");
  $("view-league").classList.toggle("hidden", view !== "league");
  $("view-explain").classList.toggle("hidden", view !== "explain");
  if (view === "matches") renderFixtures();
  if (view === "league") renderLeague();
  if (view === "mybets") renderMyBets();
  window.scrollTo({ top: 0 });
}

function openSlip(open) {
  $("slipPanel").classList.toggle("open", open);
  $("slipBackdrop").classList.toggle("open", open);
}

/* ---------------- wiring ---------------- */

$("homeSelect").addEventListener("change", (e) => { state.home = e.target.value; fillSelects(); renderMatch(); });
$("awaySelect").addEventListener("change", (e) => { state.away = e.target.value; fillSelects(); renderMatch(); });
$("swapBtn").addEventListener("click", () => {
  [state.home, state.away] = [state.away, state.home];
  fillSelects(); renderMatch();
});

document.querySelectorAll(".nav-pill").forEach((b) => b.addEventListener("click", () => showView(b.dataset.view)));
$("brand").addEventListener("click", () => showView("matches"));
$("backToMatches").addEventListener("click", () => showView("matches"));
$("slipToggle").addEventListener("click", () => openSlip(true));
$("slipClose").addEventListener("click", () => openSlip(false));
$("slipBackdrop").addEventListener("click", () => openSlip(false));

$("marketsGrid").addEventListener("click", (e) => {
  const btn = e.target.closest(".odds-btn");
  if (btn) toggleSelection(btn);
});

$("groupFilter").innerHTML =
  `<option value="all">All groups</option>` +
  Object.keys(GROUPS).map((g) => `<option value="${g}">${g}</option>`).join("");
$("groupFilter").addEventListener("change", renderFixtures);
document.querySelectorAll("#mdFilter .seg-btn").forEach((b) =>
  b.addEventListener("click", () => {
    document.querySelectorAll("#mdFilter .seg-btn").forEach((x) => x.classList.remove("active"));
    b.classList.add("active");
    renderFixtures();
  })
);

$("fixturesList").addEventListener("click", (e) => {
  const btn = e.target.closest(".fx-btn");
  if (!btn) return;
  state.home = btn.dataset.home;
  state.away = btn.dataset.away;
  fillSelects();
  renderMatch();
  showView("match");
  toast(`Loaded ${dname(state.home)} vs ${dname(state.away)}`);
});

$("myBetsList").addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-action]");
  if (!btn) return;
  const betId = btn.dataset.bet;
  try {
    if (btn.dataset.action === "cancel") {
      await WC26Auth.cancelBet(betId);
      toast("Bet cancelled — stake refunded");
    } else if (btn.dataset.action === "remove-leg") {
      await WC26Auth.removeBetLeg(betId, parseInt(btn.dataset.leg, 10));
      toast("Leg removed");
    } else if (btn.dataset.action === "save-stake") {
      const input = document.querySelector(`[data-stake-input="${betId}"]`);
      await WC26Auth.updateBetStake(betId, input.value);
      toast("Stake updated");
    }
    updateUserUI();
    renderMyBets();
  } catch (err) {
    toast(err.message || "Could not update bet");
  }
});

$("createLeagueBtn").addEventListener("click", () => showLeagueModal("create"));
$("joinLeagueBtn").addEventListener("click", () => showLeagueModal("join"));
$("leagueModalClose").addEventListener("click", hideLeagueModal);
$("leagueModalBackdrop").addEventListener("click", hideLeagueModal);

$("createLeagueForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  showLeagueModalError("");
  try {
    const league = await WC26Auth.createPrivateLeague($("createLeagueName").value);
    state.selectedPrivateLeague = league.code;
    localStorage.setItem("wc26-selected-private-league", league.code);
    hideLeagueModal();
    renderLeague();
    toast(`League created! Share ID ${league.code} with friends`);
  } catch (err) {
    showLeagueModalError(err.message);
  }
});

$("joinLeagueForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  showLeagueModalError("");
  try {
    const league = await WC26Auth.joinPrivateLeague($("joinLeagueCode").value);
    state.selectedPrivateLeague = league.code || league.id;
    localStorage.setItem("wc26-selected-private-league", state.selectedPrivateLeague);
    hideLeagueModal();
    renderLeague();
    toast(`Joined ${league.name}!`);
  } catch (err) {
    showLeagueModalError(err.message);
  }
});

$("privateLeagueTabs").addEventListener("click", (e) => {
  const tab = e.target.closest(".pl-tab");
  if (!tab) return;
  state.selectedPrivateLeague = tab.dataset.league;
  localStorage.setItem("wc26-selected-private-league", state.selectedPrivateLeague);
  renderLeague();
});

$("privateLeaguePanel").addEventListener("click", async (e) => {
  if (!e.target.closest("#copyLeagueCodeBtn")) return;
  const code = $("activeLeagueCode")?.textContent;
  if (!code) return;
  try {
    await navigator.clipboard.writeText(code);
    toast("League ID copied!");
  } catch {
    prompt("Copy league ID:", code);
  }
});

/* ---------------- auth UI ---------------- */

function fixturesFingerprint(fixtures) {
  return fixtures
    .map((f) => `${f.id}:${f.status}:${f.homeScore ?? ""}:${f.awayScore ?? ""}`)
    .join("|");
}

function applyFixtureData(data) {
  if (!data?.fixtures?.length) return false;
  const fp = fixturesFingerprint(data.fixtures);
  const metaChanged = data.meta?.updatedAt && data.meta.updatedAt !== liveFixturesMeta?.updatedAt;
  if (fp === fixturesFingerprint(liveFixtures)) {
    if (metaChanged) {
      liveFixturesMeta = data.meta;
      if (!$("view-matches").classList.contains("hidden")) renderFixtures();
    }
    return false;
  }
  liveFixtures = data.fixtures;
  liveFixturesMeta = data.meta;
  return true;
}

function refreshFixtureViews() {
  if (!$("view-matches").classList.contains("hidden")) renderFixtures();
  if (!$("view-match").classList.contains("hidden")) renderMatch();
  if (!$("view-groups").classList.contains("hidden")) renderGroups();
  if (!$("view-mybets").classList.contains("hidden")) renderMyBets();
}

async function fetchFixtureJson() {
  const urls = [];
  if (typeof SITE_CONFIG !== "undefined" && SITE_CONFIG.fixturesRawUrl) {
    urls.push(`${SITE_CONFIG.fixturesRawUrl}?t=${Date.now()}`);
  }
  urls.push(`fixtures.json?t=${Date.now()}`);
  for (const url of urls) {
    try {
      const res = await fetch(url, { cache: "no-store" });
      if (res.ok) return res.json();
    } catch {
      /* try next source */
    }
  }
  return null;
}

async function pollFixtures() {
  const data = await fetchFixtureJson();
  if (!data) return;
  if (applyFixtureData(data)) refreshFixtureViews();
}

function startFixturePolling() {
  pollFixtures();
  setInterval(pollFixtures, 60 * 1000);
  setInterval(() => {
    if (!$("mainPage").classList.contains("hidden")) refreshFixtureViews();
  }, 60 * 1000);
}

function showAuthError(msg) {
  const el = $("authError");
  el.textContent = msg;
  el.classList.toggle("hidden", !msg);
}

function enterApp() {
  $("authGate").classList.add("hidden");
  $("mainHeader").classList.remove("hidden");
  $("mainPage").classList.remove("hidden");
  updateUserUI();
  fillSelects();
  renderMatch();
  renderGroups();
  renderFixtures();
  renderSlip();
  startFixturePolling();
  showView("matches");
}

function showAuthGate() {
  $("authGate").classList.remove("hidden");
  $("mainHeader").classList.add("hidden");
  $("mainPage").classList.add("hidden");
}

document.querySelectorAll(".auth-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".auth-tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    const isLogin = tab.dataset.tab === "login";
    $("loginForm").classList.toggle("hidden", !isLogin);
    $("signupForm").classList.toggle("hidden", isLogin);
    showAuthError("");
  });
});

$("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  showAuthError("");
  try {
    await WC26Auth.login($("loginEmail").value, $("loginPassword").value);
    enterApp();
  } catch (err) {
    showAuthError(err.message);
  }
});

$("signupForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  showAuthError("");
  try {
    await WC26Auth.signup($("signupUsername").value, $("signupEmail").value, $("signupPassword").value);
    enterApp();
    toast(`Welcome! You received ${WC26Auth.STARTING_TOKENS.toLocaleString()} tokens 🪙`);
  } catch (err) {
    showAuthError(err.message);
  }
});

$("logoutBtn").addEventListener("click", () => {
  WC26Auth.logout();
  showAuthGate();
});

if (typeof SITE_CONFIG !== "undefined") {
  const foot = $("footerLink");
  foot.href = SITE_CONFIG.githubUrl;
  foot.textContent = SITE_CONFIG.footerLabel;
}

/* ---------------- boot ---------------- */

(async () => {
  $("authModeNote").textContent = WC26Auth.isCloud()
    ? "Connected to cloud league — leaderboard syncs across all users."
    : "League is stored in this browser. Enable Firebase in firebase-config.js for a global leaderboard shared with friends.";

  await WC26Auth.init();
  WC26Auth.onChange((user) => {
    if (user && $("authGate").classList.contains("hidden") === false) enterApp();
    else updateUserUI();
    if (!$("view-mybets").classList.contains("hidden")) renderMyBets();
    if (!$("view-league").classList.contains("hidden")) renderLeague();
  });

  if (WC26Auth.getUser()) enterApp();
  else showAuthGate();
})();
