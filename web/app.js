// Keyhole dashboard: latest ranked buys, company lookup, holdings check, biggest sales.
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const money = (n) => (n >= 1e9 ? "$" + (n / 1e9).toFixed(2) + "B" : n >= 1e6 ? "$" + (n / 1e6).toFixed(1) + "M" : n >= 1e3 ? "$" + (n / 1e3).toFixed(0) + "K" : "$" + Math.round(n || 0));
const api = (p) => fetch(p).then((r) => r.json());
const ring = (s) => { const c = 2 * Math.PI * 24; return `<svg viewBox="0 0 56 56"><circle cx="28" cy="28" r="24" fill="none" stroke="rgba(27,26,60,.08)" stroke-width="4"/><circle cx="28" cy="28" r="24" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round" stroke-dasharray="${c}" stroke-dashoffset="${c * (1 - s / 100)}"/></svg>`; };

async function loadBuys() {
  const r = await api("/api/buys?min=25000&limit=25");
  if (r.error) { $("#buys").innerHTML = `<p class="err">${esc(r.error)}</p>`; return; }
  $("#buysWin").textContent = `${r.window} · ${r.scannedFilings} filings read`;
  $("#buys").innerHTML = r.buys.length ? r.buys.map((t) => `<div class="item" data-t="${esc(t.ticker || "")}" title="${esc(t.signal.why.join(" · "))}">
    <div class="score ${t.signal.level}">${ring(t.signal.score)}${t.signal.score}</div>
    <div class="who">${t.ticker ? `<span class="tk">${esc(t.ticker)}</span>` : ""}<b>${esc(t.insider)}</b> <span class="dim">· ${esc(t.role)}</span>
      <small>${esc(t.company)} · ${esc(t.signal.why.slice(1).join(" · "))}</small></div>
    <div class="amt buy">${money(t.value)}<small>${t.stakeChangePct ? `+${t.stakeChangePct}% stake · ` : ""}${esc(t.date)}</small></div></div>`).join("") : `<p class="hint">No open-market buys above $25K in the newest filings.</p>`;
}

async function loadSales() {
  const r = await api("/api/sales?min=1000000&limit=12");
  if (r.error) { $("#sales").innerHTML = `<p class="err">${esc(r.error)}</p>`; return; }
  $("#salesWin").textContent = r.window;
  $("#sales").innerHTML = r.sales.length ? r.sales.map((t) => `<div class="item" data-t="${esc(t.ticker || "")}" style="grid-template-columns:1fr auto">
    <div class="who">${t.ticker ? `<span class="tk">${esc(t.ticker)}</span>` : ""}<b>${esc(t.insider)}</b> <span class="dim">· ${esc(t.role)}</span>
      <small>${esc(t.company)} · ${t.planned10b5_1 ? '<span class="pill plan">10b5-1 plan</span>' : '<span class="pill disc">not pre-scheduled</span>'}</small></div>
    <div class="amt sell">${money(t.value)}<small>${t.stakeChangePct ? `−${t.stakeChangePct}% stake · ` : ""}${esc(t.date)}</small></div></div>`).join("") : `<p class="hint">No sales above $1M in the newest filings.</p>`;
}

const FLAG = { "insiders buying": "f-buying", "unplanned selling": "f-unplanned", "routine selling": "f-routine", quiet: "f-quiet", "not covered": "f-nc" };
async function loadHoldings() {
  $("#holdings").innerHTML = `<div class="skel"></div>`;
  const r = await api("/api/holdings?t=" + encodeURIComponent($("#ht").value));
  if (r.error) { $("#holdings").innerHTML = `<p class="err">${esc(r.error)}</p>`; return; }
  $("#holdings").innerHTML = r.holdings.map((h) => `<div class="hrow" data-t="${esc(h.ticker)}"><b>${esc(h.ticker)}</b><div><span class="pill ${FLAG[h.flag]}">${esc(h.flag)}</span><p>${esc(h.read)}</p></div></div>`).join("");
}

let cur = null, days = 180;
async function lookup(t) {
  if (!t) return;
  cur = t.toUpperCase(); $("#co").hidden = false; $("#coName").textContent = cur; $("#coMeta").textContent = "reading filings…"; $("#coRead").textContent = ""; $("#coKpis").innerHTML = ""; $("#coTrades").innerHTML = "";
  $("#status").textContent = `reading ${cur} filings from the SEC…`;
  scrollTo({ top: 0, behavior: "smooth" });
  const r = await api(`/api/ticker?t=${encodeURIComponent(cur)}&days=${days}`);
  $("#status").textContent = "SEC Form 4 filings · read-only";
  if (r.error) { $("#coMeta").textContent = ""; $("#coRead").innerHTML = `<span class="err">${esc(r.error)}</span>`; return; }
  const s = r.summary;
  $("#coName").textContent = `${r.company.name} (${r.company.ticker})`;
  $("#coMeta").textContent = `last ${r.days} days · ${r.filings} Form 4 filings`;
  $("#coRead").textContent = s.read;
  $("#coKpis").innerHTML = [
    ["Open-market buys", `<span class="buy">${money(s.openMarketBuys.value)}</span>`, `${s.openMarketBuys.count} trades · ${s.openMarketBuys.people} people`],
    ["Open-market sales", `<span class="sell">${money(s.openMarketSales.value)}</span>`, `${s.openMarketSales.count} trades · ${s.openMarketSales.people} people`],
    ["Sales on a 10b5-1 plan", `${s.openMarketSales.plannedPct}%`, "pre-scheduled = routine"],
    ["Strongest buy", s.strongestBuy ? `${s.strongestBuy.score}/100` : "–", s.strongestBuy ? `${esc(s.strongestBuy.insider)} · ${money(s.strongestBuy.value)}` : "no open-market buys"],
  ].map(([a, b, c]) => `<div class="kpi"><span>${a}</span><b>${b}</b><small>${c}</small></div>`).join("");
  $("#coTrades").innerHTML = `<tr><th>Date</th><th>Insider</th><th>Role</th><th>What</th><th class="num">Shares</th><th class="num">Price</th><th class="num">Value</th><th>Plan</th><th></th></tr>` +
    r.trades.map((t) => `<tr><td>${esc(t.date)}</td><td>${esc(t.insider)}</td><td>${esc(t.role)}</td><td class="${t.kind === "open-market buy" ? "buy" : t.kind === "open-market sale" ? "sell" : ""}">${esc(t.kind)}</td>
      <td class="num">${(t.shares ?? 0).toLocaleString("en-US")}</td><td class="num">${t.price ? "$" + t.price.toFixed(2) : "–"}</td><td class="num">${t.value ? money(t.value) : "–"}</td>
      <td>${t.planned10b5_1 ? "10b5-1" : ""}</td><td><a href="${esc(t.filing)}" target="_blank" rel="noopener">filing</a></td></tr>`).join("");
}

$("#search").onsubmit = (e) => { e.preventDefault(); lookup($("#q").value.trim()); };
$("#hold").onsubmit = (e) => { e.preventDefault(); loadHoldings(); };
$("#days").onclick = (e) => { const d = e.target.dataset.d; if (!d) return; days = +d; document.querySelectorAll("#days button").forEach((b) => b.classList.toggle("on", b === e.target)); lookup(cur); };
document.addEventListener("click", (e) => { const el = e.target.closest("[data-t]"); if (el && el.dataset.t && !e.target.closest("a")) lookup(el.dataset.t); });
const q = new URLSearchParams(location.search).get("t");
loadBuys().then(loadSales); loadHoldings(); if (q) lookup(q);
