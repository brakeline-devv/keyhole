// SEC EDGAR client: polite (≤ 8 requests/second, as SEC asks for at most 10), declared User-Agent, disk cache.
// SEC requires a User-Agent with a name and a contact address. Set SEC_USER_AGENT="Your Name you@example.com"
// to use your own; the default identifies the tool without any personal data.
import { readFileSync, writeFileSync, existsSync, statSync } from "node:fs";
import { createHash } from "node:crypto";
import { cacheFile } from "./paths.js";

const UA = process.env.SEC_USER_AGENT || "InsiderRadar open-source-tool dev@insider-radar.invalid";
const GAP_MS = 130;
let nextSlot = 0;
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
async function slot() { const now = Date.now(); const at = Math.max(now, nextSlot); nextSlot = at + GAP_MS; if (at > now) await wait(at - now); }

const key = (url) => createHash("sha1").update(url).digest("hex").slice(0, 20);

// ttl in seconds; Infinity for immutable documents (a filed Form 4 never changes)
export async function get(url, { ttl = 3600, json = false } = {}) {
  const f = cacheFile(key(url) + (json ? ".json" : ".txt"));
  if (existsSync(f) && (ttl === Infinity || (Date.now() - statSync(f).mtimeMs) / 1000 < ttl)) {
    const s = readFileSync(f, "utf8"); return json ? JSON.parse(s) : s;
  }
  let lastErr;
  for (let attempt = 0; attempt < 3; attempt++) {
    await slot();
    try {
      const r = await fetch(url, { headers: { "User-Agent": UA, "Accept-Encoding": "gzip, deflate" }, signal: AbortSignal.timeout(20000) });
      if (r.status === 429 || r.status >= 500) { lastErr = new Error(`SEC ${r.status}`); await wait(1000 * (attempt + 1)); continue; }
      if (r.status === 403) throw new Error("SEC refused the request (403). Set SEC_USER_AGENT to \"Your Name you@example.com\".");
      if (!r.ok) throw new Error(`SEC ${r.status} for ${url}`);
      const s = await r.text();
      writeFileSync(f, s);
      return json ? JSON.parse(s) : s;
    } catch (e) { lastErr = e; if (/403|SEC \d{3} for/.test(e.message)) throw e; await wait(500 * (attempt + 1)); }
  }
  if (existsSync(f)) { const s = readFileSync(f, "utf8"); return json ? JSON.parse(s) : s; } // stale beats nothing
  throw lastErr;
}

// ticker ↔ CIK
let tickerMap = null;
export async function tickers() {
  if (tickerMap) return tickerMap;
  const j = await get("https://www.sec.gov/files/company_tickers.json", { ttl: 86400, json: true });
  tickerMap = { bySym: new Map(), byCik: new Map() };
  for (const v of Object.values(j)) {
    const sym = String(v.ticker).toUpperCase(), cik = Number(v.cik_str);
    if (!tickerMap.bySym.has(sym)) tickerMap.bySym.set(sym, { cik, name: v.title, ticker: sym });
    if (!tickerMap.byCik.has(cik)) tickerMap.byCik.set(cik, { cik, name: v.title, ticker: sym });
  }
  return tickerMap;
}
export async function lookup(ticker) {
  const t = await tickers();
  return t.bySym.get(String(ticker).toUpperCase().replace(/^\$/, "")) || null;
}

const pad = (cik) => String(cik).padStart(10, "0");
export const submissions = (cik) => get(`https://data.sec.gov/submissions/CIK${pad(cik)}.json`, { ttl: 6 * 3600, json: true });
export const filingIndex = (cik, acc) => get(`https://www.sec.gov/Archives/edgar/data/${Number(cik)}/${acc.replace(/-/g, "")}/index.json`, { ttl: Infinity, json: true });
export const archive = (cik, acc, file) => get(`https://www.sec.gov/Archives/edgar/data/${Number(cik)}/${acc.replace(/-/g, "")}/${file}`, { ttl: Infinity });
export const filingUrl = (cik, acc) => `https://www.sec.gov/Archives/edgar/data/${Number(cik)}/${acc.replace(/-/g, "")}/${acc}-index.htm`;

// the live feed of the newest Form 4 filings (EDGAR "current events"), newest first
export async function latestForm4(count = 100, start = 0) {
  const s = await get(`https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&owner=only&count=${count}&start=${start}&output=atom`, { ttl: 600 });
  const out = [], seen = new Set();
  for (const e of s.matchAll(/<entry>([\s\S]*?)<\/entry>/g)) {
    const title = (/<title>([\s\S]*?)<\/title>/.exec(e[1]) || [])[1] || "";
    const href = (/<link[^>]*href="([^"]+)"/.exec(e[1]) || [])[1] || "";
    const updated = (/<updated>([\s\S]*?)<\/updated>/.exec(e[1]) || [])[1] || "";
    const m = /\/data\/(\d+)\/\d+\/([\d-]+)-index\.htm/.exec(href);
    if (!m || !/\(Issuer\)/.test(title) || seen.has(m[2])) continue;
    seen.add(m[2]);
    out.push({ cik: Number(m[1]), accession: m[2], filed: updated.slice(0, 10), issuerName: title.replace(/^4 - /, "").replace(/\s*\(\d+\)\s*\(Issuer\)$/, "") });
  }
  return out;
}
