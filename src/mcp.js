// Insider Radar MCP server (stdio): what company insiders (CEOs, CFOs, directors, 10% owners) bought and sold,
// straight from SEC Form 4 filings. Read-only: it has no tool that can place an order.
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import { forTicker, latest, checkHoldings, ballastHoldings } from "./insider.js";
import { CODES } from "./form4.js";

const TOOLS = [
  { name: "insider_activity", description: "Everything insiders did in one US-listed company over the last N days, from SEC Form 4 filings: open-market buys and sales (with value, role, % of their stake, and whether the trade was pre-scheduled under a 10b5-1 plan), plus grants, option exercises, tax withholding and gifts. Returns a plain-words read of the pattern and a 0-100 score for each open-market buy.",
    inputSchema: { type: "object", properties: { ticker: { type: "string", description: "US stock ticker, e.g. NVDA" }, days: { type: "number", description: "look-back window in days (default 180, max 730)" } }, required: ["ticker"] } },
  { name: "latest_insider_buys", description: "The newest open-market insider buys across the whole US market (EDGAR live feed, usually the last day or two), ranked by a 0-100 signal score: who bought (CEO/CFO weigh most, funds least), how much, how much it grew their stake, whether other insiders bought the same company (cluster), and whether it was pre-scheduled (10b5-1, weighs less).",
    inputSchema: { type: "object", properties: { min_value: { type: "number", description: "only buys worth at least this many dollars (default 25000)" }, limit: { type: "number", description: "max rows (default 20)" }, scan: { type: "number", description: "how many recent filings to read, 100-400 (default 200; more is slower the first time)" } } } },
  { name: "latest_insider_sales", description: "The newest open-market insider sales across the US market, largest first, with whether each was pre-scheduled under a 10b5-1 plan (routine) or not (discretionary).",
    inputSchema: { type: "object", properties: { min_value: { type: "number", description: "default 1000000" }, limit: { type: "number", description: "default 20" }, scan: { type: "number" } } } },
  { name: "check_holdings", description: "For a list of tickers someone holds, what insiders did in each over the last N days, sorted so the ones that need attention come first (unplanned selling, then insider buying). Leave tickers empty to use the Ballast portfolio if Ballast is installed. Crypto, ETFs and funds have no insider filings and are reported as not covered.",
    inputSchema: { type: "object", properties: { tickers: { type: "array", items: { type: "string" } }, days: { type: "number", description: "default 90" } } } },
  { name: "explain_codes", description: "What each SEC Form 4 transaction code means and which ones are real signals (P open-market buy, S open-market sale) vs paperwork (grants, exercises, tax withholding, gifts).",
    inputSchema: { type: "object", properties: {} } },
];

const out = (x) => ({ content: [{ type: "text", text: JSON.stringify(x, null, 2) }] });
const slim = (t) => ({ date: t.date, filed: t.filed, ticker: t.ticker, company: t.company, insider: t.insider, role: t.role, kind: t.kind, shares: t.shares, price: t.price, value: t.value,
  stakeChangePct: t.holdingChangePct, planned10b5_1: t.planned, signal: t.signal || undefined, filing: t.url });

export async function handle(name, a = {}) {
  if (name === "insider_activity") {
    const r = await forTicker(a.ticker, { days: Math.min(730, a.days || 180) });
    return { company: r.company, days: r.days, filings: r.filings, summary: r.summary, trades: r.trades.slice(0, 60).map(slim), note: r.truncated ? "only the most recent filings were read; ask for fewer days for full detail" : undefined };
  }
  if (name === "latest_insider_buys") {
    const r = await latest({ kind: "buys", minValue: a.min_value ?? 25000, limit: a.limit || 20, scan: Math.min(400, a.scan || 200) });
    return { scannedFilings: r.scanned, window: `${r.from} → ${r.to}`, buys: r.trades.map(slim) };
  }
  if (name === "latest_insider_sales") {
    const r = await latest({ kind: "sells", minValue: a.min_value ?? 1e6, limit: a.limit || 20, scan: Math.min(400, a.scan || 200) });
    return { scannedFilings: r.scanned, window: `${r.from} → ${r.to}`, sales: r.trades.map(slim) };
  }
  if (name === "check_holdings") {
    let list = a.tickers?.length ? a.tickers : ballastHoldings();
    if (!list?.length) return { error: "no tickers given and no Ballast portfolio found. Pass tickers, e.g. [\"NVDA\",\"AAPL\"]." };
    return { days: a.days || 90, source: a.tickers?.length ? "given" : "Ballast portfolio", holdings: await checkHoldings(list, { days: a.days || 90 }) };
  }
  if (name === "explain_codes") return { codes: CODES, signals: ["P (open-market buy) is the strongest signal: an insider spent their own cash at the market price.", "S (open-market sale) matters most when it is NOT under a 10b5-1 plan and is a large share of the insider's stake.", "A, M, X, F, G are mostly compensation and paperwork."] };
  throw new Error("unknown tool " + name);
}

export async function startMcp() {
  const server = new Server({ name: "insider-radar", version: "0.1.0" }, { capabilities: { tools: {} } });
  server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: TOOLS }));
  server.setRequestHandler(CallToolRequestSchema, async (req) => {
    try { return out(await handle(req.params.name, req.params.arguments || {})); }
    catch (e) { return { isError: true, content: [{ type: "text", text: e.message }] }; }
  });
  await server.connect(new StdioServerTransport());
}
