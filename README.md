# Insider Radar (working name)

What company insiders (CEOs, CFOs, directors, 10% owners) bought and sold, straight from SEC Form 4 filings, as an MCP server your AI agent can use, plus a dashboard. Read-only: it cannot place orders.

- **insider_activity**: everything insiders did in one company, with a plain-words read (net buying, routine 10b5-1 selling, or discretionary selling)
- **latest_insider_buys**: the newest open-market buys across the US market, ranked 0-100 (role, size, stake growth, clusters, 10b5-1 plans)
- **latest_insider_sales**: the biggest new sales, flagged when not pre-scheduled
- **check_holdings**: your tickers (or your Ballast portfolio), the ones that need attention first
- **explain_codes**: what each Form 4 code means

```
npm install && npm start      # dashboard on http://localhost:6300/app
node src/cli.js NVDA          # one company
node src/cli.js buys          # ranked newest buys
claude mcp add insider-radar -- node /path/to/insider-radar/src/cli.js mcp
```

SEC asks automated tools to declare who they are. Set `SEC_USER_AGENT="Your Name you@example.com"`; the default identifies the tool only. Requests stay under 8 per second and filings are cached on disk.

Data: SEC EDGAR. Information, not investment advice.
