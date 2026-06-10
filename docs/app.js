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

const ALL_FIXTURES = Object.entries(GROUPS).flatMap(([group, teams]) =>
  groupFixtures(teams).map((f) => ({ group, ...f }))
);

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

function fmtOdds(p) {
  if (p < 1e-4) return "—";
  const o = 1 / p;
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

const TEAMS = Object.keys(TEAM_RATINGS).sort();
const state = {
  home: TEAMS.includes("Argentina") ? "Argentina" : TEAMS[0],
  away: TEAMS.includes("Algeria") ? "Algeria" : TEAMS.find((t) => t !== TEAMS[0]),
  slip: [],
  stake: 10,
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
  const cls = ["odds-btn", selected ? "selected" : "", extra.best ? "best" : "", extra.cls || ""].join(" ");
  const title = extra.title || pick;
  return `<button class="${cls}" data-id="${selId}" data-market="${market}" data-pick="${pick}"
            data-odds="${(1 / p).toFixed(4)}" data-prob="${p.toFixed(6)}" title="${title}">
            ${extra.top || ""}<span class="ob-odds">${fmtOdds(p)}</span>
            <span class="ob-prob">${extra.pct !== undefined ? `${extra.pct.toFixed(1)}%` : fmtPct(p)}</span></button>`;
}

function renderMatch() {
  const m = computeMatch(state.home, state.away);
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
  const row = (labelHtml, btns) =>
    `<div class="market-row"><span class="row-label">${labelHtml}</span>${btns}</div>`;
  const card = (name, inner) =>
    `<div class="market-card"><div class="market-name">${name}</div><div class="market-rows">${inner}</div></div>`;

  const m1x2 = card("Match Result (1X2)",
    row(label(m.home), oddsBtn(m, "1X2", `${dname(m.home)} Win`, m.pHome, { best: pick.key === "home", pct: hPct })) +
    row("🤝 Draw", oddsBtn(m, "1X2", "Draw", m.pDraw, { best: pick.key === "draw", pct: dPct })) +
    row(label(m.away), oddsBtn(m, "1X2", `${dname(m.away)} Win`, m.pAway, { best: pick.key === "away", pct: aPct })));

  const mdc = card("Double Chance",
    row(`${dname(m.home)} or Draw`, oddsBtn(m, "DC", `${dname(m.home)} or Draw`, m.pHome + m.pDraw)) +
    row(`${dname(m.home)} or ${dname(m.away)}`, oddsBtn(m, "DC", `${dname(m.home)} or ${dname(m.away)}`, m.pHome + m.pAway)) +
    row(`Draw or ${dname(m.away)}`, oddsBtn(m, "DC", `Draw or ${dname(m.away)}`, m.pDraw + m.pAway)));

  const mtot = card("Total Goals (Over / Under)",
    [1.5, 2.5, 3.5].map((line) =>
      row(`${line} goals`,
        oddsBtn(m, `OU${line}`, `Over ${line}`, m.totals[line], { title: `Over ${line} goals` }) +
        oddsBtn(m, `OU${line}`, `Under ${line}`, 1 - m.totals[line], { title: `Under ${line} goals` }))
    ).join(""));

  const mbtts = card("Both Teams To Score",
    row("Yes — both score", oddsBtn(m, "BTTS", "BTTS: Yes", m.pBtts)) +
    row("No — at least one blanks", oddsBtn(m, "BTTS", "BTTS: No", 1 - m.pBtts)));

  const top6 = m.scorelines.slice(0, 6);
  const ranks = ["①", "②", "③", "④", "⑤", "⑥"];
  const mcs = `<div class="market-card"><div class="market-name">Correct Score — top 6 most likely</div>
    <div class="score-grid">${top6.map((s, i) => {
      const pickLab = `Score ${s.h}–${s.g}`;
      const selId = `${m.home}|${m.away}|CS`;
      const selected = state.slip.some((x) => x.id === selId && x.pick === pickLab);
      return `<button class="odds-btn score-btn ${selected ? "selected" : ""} ${i === 0 ? "best" : ""}"
        data-id="${selId}" data-market="CS" data-pick="${pickLab}"
        data-odds="${(m.total / s.p).toFixed(4)}" data-prob="${(s.p / m.total).toFixed(6)}"
        title="${dname(m.home)} ${s.h} – ${s.g} ${dname(m.away)}">
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

function renderFixtures() {
  const g = $("groupFilter").value;
  const md = document.querySelector("#mdFilter .seg-btn.active").dataset.md;
  const list = ALL_FIXTURES.filter(
    (f) => (g === "all" || f.group === g) && (md === "all" || String(f.md) === md)
  );
  $("fixturesList").innerHTML = list.map((f) => `
    <div class="fixture-row">
      <span class="fx-meta">${f.group} · MD ${f.md}</span>
      <span class="fx-teams"><b>${label(f.home)}</b> <span class="fx-vs">vs</span> <b>${label(f.away)}</b></span>
      <button class="fx-btn" data-home="${f.home}" data-away="${f.away}">View odds →</button>
    </div>`).join("");
}

/* ---------------- bet slip ---------------- */

function renderSlip() {
  $("slipCount").textContent = state.slip.length;
  if (!state.slip.length) {
    $("slipBody").innerHTML = `<div class="slip-empty">Your slip is empty.<br><br>
      Tap any odds button in the Markets section to add a selection.
      Mix matches to build an accumulator.</div>`;
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
    <div class="slip-note">Fair odds from the model — play-money tokens only. Not real betting advice.</div>`;

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
  try {
    await WC26Auth.placeBet(state.stake, state.slip, totalOdds);
    state.slip = [];
    saveSlip();
    renderSlip();
    renderMatch();
    updateUserUI();
    toast("Bet placed! Good luck 🍀");
  } catch (e) {
    toast(e.message || "Could not place bet");
  }
}

async function renderLeague() {
  const user = WC26Auth.getUser();
  const board = await WC26Auth.getLeaderboard();
  const rank = board.findIndex((u) => u.id === user?.id) + 1;

  $("leagueYou").innerHTML = user
    ? `<div class="ly-row"><span>Your rank</span><b>#${rank || "—"} of ${board.length}</b></div>
       <div class="ly-row"><span>Your balance</span><b class="big">🪙 ${user.tokens.toLocaleString()}</b></div>`
    : "";

  $("leagueBody").innerHTML = board.map((u, i) => {
    const isYou = user && u.id === user.id;
    const medal = i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : i + 1;
    return `<tr class="${isYou ? "you" : ""}"><td>${medal}</td><td>${u.username}${isYou ? " (you)" : ""}</td><td>🪙 ${u.tokens.toLocaleString()}</td></tr>`;
  }).join("");

  const bets = user?.bets || [];
  $("betHistory").innerHTML = bets.length
    ? bets.slice(0, 10).map((b) => `
      <div class="bet-card">
        <div class="bet-top"><span>${b.legs} leg${b.legs > 1 ? "s" : ""} · stake ${b.stake}</span><span class="bet-odds">@${b.totalOdds.toFixed(2)}</span></div>
        <div class="bet-meta">Potential ${b.potential.toLocaleString()} tokens · ${new Date(b.placedAt).toLocaleDateString()}</div>
        ${b.picks.map((p) => `<div class="bet-pick">${p.pick} — ${p.match}</div>`).join("")}
      </div>`).join("")
    : `<p class="note">No bets placed yet. Build a slip and hit <strong>Place bet</strong>.</p>`;
}

function updateUserUI() {
  const user = WC26Auth.getUser();
  $("tokenBalance").textContent = user ? user.tokens.toLocaleString() : "—";
  $("userPill").textContent = user ? user.username : "";
}

function toggleSelection(btn) {
  const { id, market, pick } = btn.dataset;
  const odds = parseFloat(btn.dataset.odds);
  const [home, away] = id.split("|");
  const existing = state.slip.findIndex((s) => s.id === id);
  const marketNames = { "1X2": "Match Result", DC: "Double Chance", BTTS: "Both Teams To Score", CS: "Correct Score" };
  const marketName = marketNames[market] || (market.startsWith("OU") ? `Total Goals ${market.slice(2)}` : market);

  if (existing >= 0 && state.slip[existing].pick === pick) {
    state.slip.splice(existing, 1); // tap again to remove
  } else {
    const sel = { id, pick, odds, marketName, match: `${dname(home)} vs ${dname(away)}` };
    if (existing >= 0) state.slip[existing] = sel; // replace pick within same market
    else state.slip.push(sel);
    toast(`Added: ${pick} @${odds.toFixed(2)}`);
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
  $("view-match").classList.toggle("hidden", view !== "match");
  $("view-groups").classList.toggle("hidden", view !== "groups");
  $("view-league").classList.toggle("hidden", view !== "league");
  $("view-explain").classList.toggle("hidden", view !== "explain");
  if (view === "league") renderLeague();
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

/* ---------------- auth UI ---------------- */

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

/* ---------------- boot ---------------- */

(async () => {
  $("authModeNote").textContent = WC26Auth.isCloud()
    ? "Connected to cloud league — leaderboard syncs across all users."
    : "League is stored in this browser. Enable Firebase in firebase-config.js for a global leaderboard shared with friends.";

  await WC26Auth.init();
  WC26Auth.onChange((user) => {
    if (user && $("authGate").classList.contains("hidden") === false) enterApp();
    else updateUserUI();
  });

  if (WC26Auth.getUser()) enterApp();
  else showAuthGate();
})();
