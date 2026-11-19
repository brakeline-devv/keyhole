// Keyhole core: read Form 4 filings, turn them into trades people can read, score the buys that matter.
// Read-only by design: nothing here can place an order.
import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";
import * as sec from "./sec.js";
import { parseForm4, roleLabel } from "./form4.js";

const DAY = 864e5;
const iso = (d) => new Date(d).toISOString().slice(0, 10);
const daysAgo = (n) => iso(Date.now() - n * DAY);

// one filing → parsed Form 4 (+ where it lives)
export async function loadFiling(cik, accession, doc, filed) {
  let file = doc ? doc.split("/").pop() : null;
  if (!file) {
    const idx = await sec.filingIndex(cik, accession);
    const xml = (idx.directory?.item || []).map((i) => i.name).filter((n) => /\.xml$/i.test(n) && !/^(FilingSummary|MetaLinks)/i.test(n));
    file = xml[0];
    if (!file) return null;
  }
  const f = parseForm4(await sec.archive(cik, accession, file));
  return { ...f, accession, filed: filed || f.period, url: sec.filingUrl(cik, accession) };
}

// flatten a filing into one row per transaction, the shape every tool returns
export function rows(f) {
  const o = f.owners[0] || { name: "?", roles: [], title: "" };
  const who = f.owners.length > 1 ? `${o.name} +${f.owners.length - 1}` : o.name;
  return f.txs.map((t) => {
    const before = t.after != null && t.shares != null ? (t.acquired ? t.after - t.shares : t.after + t.shares) : null;
    return {
      ticker: /^(N\/?A|NONE|)$/i.test(f.issuer.ticker) ? null : f.issuer.ticker, company: f.issuer.name, cik: f.issuer.cik,
      insider: titleCase(who), insiderCik: o.cik, role: roleLabel(o), institution: ENTITY.test(o.name),
      date: t.date, filed: f.filed, code: t.code, kind: t.kind, shares: t.shares, price: t.price, value: t.value,
      side: t.code === "P" ? "buy" : t.code === "S" ? "sell" : t.acquired ? "in" : "out",
      holdingChangePct: before > 0 ? round1((t.shares / before) * 100) : null,
      after: t.after, planned: t.plan, direct: t.direct, url: f.url, accession: f.accession,
    };
  });
}
// funds, trusts and companies file Form 4s too; their buys say less about the business than a CEO's
const ENTITY = /\b(LLC|L\.?P\.?|LTD|LIMITED|INC|CORP|CO\.?|TRUST|FUND|CAPITAL|PARTNERS|HOLDINGS|MANAGEMENT|ADVISORS|GROUP|PTE|PLC|AG|SA|GMBH|BRANCH|FOUNDATION)\b/i;
const round1 = (x) => Math.round(x * 10) / 10;
const titleCase = (s) => s.toLowerCase().replace(/\b([a-z])/g, (m) => m.toUpperCase()).replace(/\b(Ii|Iii|Iv|Llc|Lp|Inc|Jr|Sr)\b/g, (m) => m.toUpperCase());

// how much an open-market buy should get your attention, 0-100, with the reasons
export function scoreBuy(r, othersBuying = 0) {
  if (r.code !== "P") return null;
  const why = [];
  let s = 0;
  const v = Math.max(0, Math.min(40, (Math.log10(Math.max(r.value, 1)) - 4) * 12)); s += v;
  why.push(`$${fmt(r.value)} bought`);
  const top = ["CEO", "CFO", "COO", "President", "Chair"].includes(r.role);
  const rp = r.institution ? 4 : top ? 25 : r.role === "Director" ? 12 : r.role === "10% owner" ? 8 : 18; s += rp;
  why.push(r.institution ? "a fund or company, not a person running the business" : top ? `${r.role}: the people closest to the numbers` : r.role === "Director" ? "a director" : r.role === "10% owner" ? "a 10% owner" : `an officer (${r.role})`);
  if (r.holdingChangePct >= 50) { s += 15; why.push(`grew their stake ${r.holdingChangePct}%`); }
  else if (r.holdingChangePct >= 20) { s += 10; why.push(`grew their stake ${r.holdingChangePct}%`); }
  else if (r.holdingChangePct >= 5) { s += 5; why.push(`grew their stake ${r.holdingChangePct}%`); }
  if (othersBuying) { s += Math.min(20, othersBuying * 10); why.push(`${othersBuying} other insider${othersBuying > 1 ? "s" : ""} bought too (cluster)`); }
  if (r.planned) { s -= 15; why.push("pre-scheduled (10b5-1 plan), so less of a signal"); }
  s = Math.max(0, Math.min(100, Math.round(s)));
  return { score: s, level: s >= 70 ? "strong" : s >= 45 ? "notable" : "minor", why };
}
export const fmt = (n) => (n >= 1e9 ? (n / 1e9).toFixed(2) + "B" : n >= 1e6 ? (n / 1e6).toFixed(n >= 1e8 ? 0 : 1) + "M" : n >= 1e3 ? (n / 1e3).toFixed(n >= 1e5 ? 0 : 1) + "K" : String(Math.round(n)));

// attach scores; a "cluster" = different insiders buying the same company in the same window
function withScores(all) {
  // the same trade can be reported twice (an amendment, or one filing per joint owner): keep one
  const seen = new Set(), list = all.filter((r) => { const k = [r.cik, r.insiderCik, r.date, r.code, r.shares, r.price].join("|"); if (seen.has(k)) return false; seen.add(k); return true; });
  const buyers = new Map();
  for (const r of list) if (r.code === "P" && !r.institution) { const s = buyers.get(r.ticker || r.cik) || new Set(); s.add(r.insiderCik || r.insider); buyers.set(r.ticker || r.cik, s); }
  return list.map((r) => (r.code === "P" ? { ...r, signal: scoreBuy(r, r.institution ? 0 : Math.max(0, (buyers.get(r.ticker || r.cik)?.size || 1) - 1)) } : r));
}

// everything insiders did in one company over the last `days`
export async function forTicker(ticker, { days = 180, max = 80 } = {}) {
  const co = await sec.lookup(ticker);
  if (!co) throw new Error(`unknown ticker ${ticker}: Keyhole covers US-listed companies that file with the SEC (no crypto, no ETFs)`);
  const sub = await sec.submissions(co.cik);
  const r = sub.filings.recent, since = daysAgo(days), list = [];
  for (let i = 0; i < r.form.length && list.length < max; i++) {
    if (r.filingDate[i] < since) break;
    if (r.form[i] === "4" || r.form[i] === "4/A") list.push({ acc: r.accessionNumber[i], doc: r.primaryDocument[i], filed: r.filingDate[i] });
  }
  const filings = [];
  for (const x of list) { try { const f = await loadFiling(co.cik, x.acc, x.doc, x.filed); if (f) filings.push(f); } catch {} }
  const trades = withScores(filings.flatMap(rows).filter((t) => t.date >= since || t.filed >= since)).sort((a, b) => (b.date || "").localeCompare(a.date || ""));
  return { company: { ticker: co.ticker, name: sub.name || co.name, cik: co.cik }, days, filings: filings.length, truncated: list.length >= max, trades, summary: summarize(trades, days) };
}

export function summarize(trades, days) {
  const buys = trades.filter((t) => t.code === "P"), sells = trades.filter((t) => t.code === "S");
  const sum = (a) => a.reduce((s, t) => s + (t.value || 0), 0);
  const people = (a) => new Set(a.map((t) => t.insider)).size;
  const plannedSell = sum(sells.filter((t) => t.planned)), sellV = sum(sells), buyV = sum(buys);
  const other = {};
  for (const t of trades) if (!["P", "S"].includes(t.code)) other[t.kind] = (other[t.kind] || 0) + 1;
  const best = buys.filter((t) => t.signal).sort((a, b) => b.signal.score - a.signal.score)[0];
  let read;
  if (!trades.length) read = `No insider filings in the last ${days} days.`;
  else if (buys.length && buyV >= sellV) read = `Insiders were net buyers in the open market: $${fmt(buyV)} bought by ${people(buys)} ${people(buys) === 1 ? "person" : "people"} vs $${fmt(sellV)} sold.`;
  else if (sells.length && !buys.length && sellV && plannedSell / sellV > 0.8) read = `Insiders only sold ($${fmt(sellV)}), but ${Math.round((plannedSell / sellV) * 100)}% of it was pre-scheduled under 10b5-1 plans. Routine selling, not a reaction to news.`;
  else if (sells.length && !buys.length) read = `Insiders only sold: $${fmt(sellV)} by ${people(sells)} ${people(sells) === 1 ? "person" : "people"}, ${sellV ? Math.round((plannedSell / sellV) * 100) : 0}% under 10b5-1 plans. No open-market buys.`;
  else if (sells.length) read = `Mostly selling: $${fmt(sellV)} sold vs $${fmt(buyV)} bought in the open market.`;
  else read = `No open-market buys or sales; only grants, option exercises, tax withholding or gifts.`;
  return {
    openMarketBuys: { count: buys.length, value: buyV, people: people(buys) },
    openMarketSales: { count: sells.length, value: sellV, people: people(sells), plannedPct: sellV ? Math.round((plannedSell / sellV) * 100) : 0 },
    otherTransactions: other, strongestBuy: best ? { insider: best.insider, role: best.role, value: best.value, date: best.date, score: best.signal.score } : null, read,
  };
}

// the newest Form 4 filings across the whole market (EDGAR live feed), as trades
export async function latest({ scan = 200, kind = "buys", minValue = 0, limit = 30 } = {}) {
  const feed = [];
  for (let start = 0; start < scan; start += 100) feed.push(...(await sec.latestForm4(100, start)));
  const filings = [];
  for (const x of feed) { try { const f = await loadFiling(x.cik, x.accession, null, x.filed); if (f) filings.push(f); } catch {} }
  let trades = withScores(filings.flatMap(rows));
  trades = trades.filter((t) => (kind === "buys" ? t.code === "P" : kind === "sells" ? t.code === "S" : ["P", "S"].includes(t.code)) && (t.value || 0) >= minValue);
  trades.sort((a, b) => (kind === "buys" ? (b.signal?.score ?? 0) - (a.signal?.score ?? 0) || b.value - a.value : b.value - a.value));
  return { scanned: filings.length, from: feed.at(-1)?.filed, to: feed[0]?.filed, trades: trades.slice(0, limit) };
}

// tickers someone holds → what insiders did in each (last `days`)
export async function checkHoldings(list, { days = 90 } = {}) {
  const out = [];
  for (const raw of list) {
    const t = String(raw).toUpperCase().replace(/^\$/, "");
    try {
      const r = await forTicker(t, { days, max: 40 });
      const s = r.summary;
      const flag = s.openMarketBuys.count && s.openMarketBuys.value >= s.openMarketSales.value ? "insiders buying"
        : s.openMarketSales.count && s.openMarketSales.plannedPct < 50 ? "unplanned selling"
        : s.openMarketSales.count ? "routine selling" : "quiet";
      out.push({ ticker: t, company: r.company.name, flag, read: s.read, buys: s.openMarketBuys, sales: s.openMarketSales, strongestBuy: s.strongestBuy });
    } catch (e) { out.push({ ticker: t, flag: "not covered", read: /unknown ticker/.test(e.message) ? "No SEC insider filings for this symbol (crypto, ETFs and funds have none)." : e.message }); }
  }
  const order = { "unplanned selling": 0, "insiders buying": 1, "routine selling": 2, quiet: 3, "not covered": 4 };
  return out.sort((a, b) => order[a.flag] - order[b.flag]);
}

// holdings from Ballast (if installed) so "check my portfolio" works with no typing
export function ballastHoldings() {
  const dirs = [process.env.BALLAST_HOME, join(homedir(), ".ballast")].filter(Boolean);
  for (const d of dirs) {
    const f = join(d, "portfolio.json");
    if (existsSync(f)) try { return Object.keys(JSON.parse(readFileSync(f, "utf8")).positions || {}); } catch {}
  }
  return null;
}
