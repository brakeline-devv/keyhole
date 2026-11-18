// Dashboard: http://localhost:6300/app (and the site on /). JSON API under /api.
import { createServer } from "node:http";
import { readFileSync, existsSync, statSync } from "node:fs";
import { join, extname, normalize } from "node:path";
import { fileURLToPath } from "node:url";
import { handle } from "./mcp.js";

const WEB = fileURLToPath(new URL("../web/", import.meta.url));
const TYPES = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".ico": "image/x-icon", ".mp4": "video/mp4", ".json": "application/json" };

export function startServer(port = Number(process.env.PORT) || 6300) {
  createServer(async (req, res) => {
    const u = new URL(req.url, "http://x");
    try {
      if (u.pathname.startsWith("/api/")) {
        const q = Object.fromEntries(u.searchParams);
        const map = { "/api/ticker": ["insider_activity", { ticker: q.t, days: Number(q.days) || 180 }], "/api/buys": ["latest_insider_buys", { min_value: Number(q.min ?? 25000), limit: Number(q.limit) || 25 }],
          "/api/sales": ["latest_insider_sales", { min_value: Number(q.min ?? 1e6), limit: Number(q.limit) || 25 }], "/api/holdings": ["check_holdings", { tickers: q.t ? q.t.split(/[\s,]+/).filter(Boolean) : [], days: Number(q.days) || 90 }] };
        const m = map[u.pathname];
        if (!m) { res.writeHead(404); return res.end("{}"); }
        const r = await handle(...m);
        res.writeHead(200, { "content-type": "application/json" }); return res.end(JSON.stringify(r));
      }
      let p = u.pathname === "/" ? "index.html" : u.pathname === "/app" ? "app.html" : u.pathname.slice(1);
      const f = normalize(join(WEB, p));
      if (!f.startsWith(normalize(WEB)) || !existsSync(f) || statSync(f).isDirectory()) { res.writeHead(404); return res.end("not found"); }
      res.writeHead(200, { "content-type": TYPES[extname(f)] || "application/octet-stream", "cache-control": "no-cache" });
      res.end(readFileSync(f));
    } catch (e) { res.writeHead(500, { "content-type": "application/json" }); res.end(JSON.stringify({ error: e.message })); }
  }).listen(port, "127.0.0.1", () => console.log(`Insider Radar → dashboard http://localhost:${port}/app`));
}
