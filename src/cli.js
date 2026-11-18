#!/usr/bin/env node
// insider-radar               → MCP server on stdio (what Claude / Cursor start)
// insider-radar dashboard     → dashboard on http://localhost:6300/app
// insider-radar buys          → newest open-market insider buys, ranked
// insider-radar NVDA [days]   → what insiders did in one company
const cmd = process.argv[2] ?? "mcp";
const money = (n) => "$" + Math.round(n).toLocaleString("en-US");
if (cmd === "mcp") (await import("./mcp.js")).startMcp();
else if (cmd === "dashboard") (await import("./server.js")).startServer();
else {
  const { handle } = await import("./mcp.js");
  if (cmd === "buys") {
    const r = await handle("latest_insider_buys", { limit: 15 });
    console.log(`newest open-market insider buys · ${r.window} · ${r.scannedFilings} filings read`);
    for (const t of r.buys) console.log(`${String(t.signal.score).padStart(3)} ${t.signal.level.padEnd(8)} ${(t.ticker || "-").padEnd(6)} ${t.insider} (${t.role}) ${money(t.value)}${t.stakeChangePct ? ` · +${t.stakeChangePct}% stake` : ""}`);
  } else {
    const r = await handle("insider_activity", { ticker: cmd, days: Number(process.argv[3]) || 180 });
    console.log(`${r.company.name} (${r.company.ticker}) · last ${r.days} days · ${r.filings} filings`);
    console.log(r.summary.read);
    for (const t of r.trades.filter((t) => ["open-market buy", "open-market sale"].includes(t.kind)).slice(0, 12))
      console.log(`  ${t.date} ${t.kind === "open-market buy" ? "BUY " : "SELL"} ${t.insider} (${t.role}) ${money(t.value)}${t.planned10b5_1 ? " · 10b5-1 plan" : ""}`);
  }
  process.exit(0);
}
