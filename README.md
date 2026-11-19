# Keyhole

What company insiders (CEOs, CFOs, directors, 10% owners) bought and sold, straight from SEC Form 4 filings, as an MCP server your AI agent can use, plus a dashboard. Read-only: it cannot place orders.

- **insider_activity**: everything insiders did in one company, with a plain-words read (net buying, routine 10b5-1 selling, or discretionary selling)
- **latest_insider_buys**: the newest open-market buys across the US market, ranked 0-100 (role, size, stake growth, clusters, 10b5-1 plans)
- **latest_insider_sales**: the biggest new sales, flagged when not pre-scheduled
- **check_holdings**: your tickers (or your Ballast portfolio), the ones that need attention first
- **explain_codes**: what each Form 4 code means

## Install

```
claude mcp add keyhole -- npx -y keyhole-mcp
```

Cursor / Claude Desktop / any MCP client:

```json
{ "mcpServers": { "keyhole": { "command": "npx", "args": ["-y", "keyhole-mcp"] } } }
```

Dashboard and CLI:

```
npx keyhole-mcp dashboard     # then open http://localhost:6300/app
npx keyhole-mcp NVDA 90       # one company, last 90 days
npx keyhole-mcp buys          # newest open-market buys, ranked
```

From a checkout: `npm install && npm start`.

SEC asks automated tools to declare who they are. Set `SEC_USER_AGENT="Your Name you@example.com"`; the default identifies the tool only. Requests stay under 8 per second and filings are cached on disk.

Data: SEC EDGAR. Information, not investment advice.
