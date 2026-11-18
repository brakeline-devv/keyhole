// Parses a Form 4 (ownershipDocument XML) into plain objects. No dependencies: the schema is flat and stable.

// SEC transaction codes, in words people understand
export const CODES = {
  P: "open-market buy", S: "open-market sale", A: "grant / award", M: "option exercise", X: "option exercise",
  F: "shares withheld for tax", G: "gift", D: "returned to the company", C: "conversion", J: "other",
  I: "discretionary", W: "will / inheritance", K: "swap", V: "voluntary report", Z: "trust deposit",
};

const tag = (s, name) => { const m = new RegExp(`<${name}>\\s*([\\s\\S]*?)\\s*</${name}>`).exec(s); return m ? m[1] : ""; };
const val = (s, name) => { const inner = tag(s, name); const v = /<value>\s*([\s\S]*?)\s*<\/value>/.exec(inner); return (v ? v[1] : inner).trim(); };
const num = (x) => { const n = Number(String(x).replace(/,/g, "")); return Number.isFinite(n) ? n : null; };
const flag = (x) => /^(1|true)$/i.test(String(x).trim());
const unesc = (s) => s.replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&#39;|&apos;/g, "'");

export function parseForm4(xml) {
  const issuer = tag(xml, "issuer");
  const footnotes = {};
  for (const m of xml.matchAll(/<footnote id="([^"]+)">([\s\S]*?)<\/footnote>/g)) footnotes[m[1]] = unesc(m[2].replace(/\s+/g, " ").trim());
  const owners = [...xml.matchAll(/<reportingOwner>([\s\S]*?)<\/reportingOwner>/g)].map(([, o]) => {
    const rel = tag(o, "reportingOwnerRelationship");
    const roles = [];
    if (flag(tag(rel, "isDirector"))) roles.push("director");
    if (flag(tag(rel, "isOfficer"))) roles.push("officer");
    if (flag(tag(rel, "isTenPercentOwner"))) roles.push("10% owner");
    if (flag(tag(rel, "isOther"))) roles.push("other");
    return { cik: Number(tag(o, "rptOwnerCik")), name: unesc(tag(o, "rptOwnerName")), roles, title: unesc(tag(rel, "officerTitle")) };
  });
  const plan = flag(tag(xml, "aff10b5One"));
  const txs = [...xml.matchAll(/<nonDerivativeTransaction>([\s\S]*?)<\/nonDerivativeTransaction>/g)].map(([, t]) => {
    const code = val(t, "transactionCode"), shares = num(val(t, "transactionShares")), price = num(val(t, "transactionPricePerShare"));
    const notes = [...t.matchAll(/<footnoteId id="([^"]+)"\s*\/>/g)].map((m) => footnotes[m[1]]).filter(Boolean);
    return {
      date: val(t, "transactionDate"), code, kind: CODES[code] || code, security: unesc(val(t, "securityTitle")),
      shares, price, acquired: val(t, "transactionAcquiredDisposedCode") === "A",
      after: num(val(t, "sharesOwnedFollowingTransaction")), direct: val(t, "directOrIndirectOwnership") !== "I",
      value: shares != null && price ? Math.round(shares * price) : 0,
      plan: plan || notes.some((n) => /10b5-1/i.test(n)),
    };
  });
  return {
    issuer: { cik: Number(tag(issuer, "issuerCik")), name: unesc(tag(issuer, "issuerName")), ticker: tag(issuer, "issuerTradingSymbol").toUpperCase() },
    owners, period: tag(xml, "periodOfReport"), plan, txs,
    amendment: tag(xml, "documentType") === "4/A",
  };
}

// short, readable role: "CEO", "CFO", "Director", "10% owner"
export function roleLabel(o) {
  const t = (o.title || "").toLowerCase();
  if (/chief executive|\bceo\b/.test(t)) return "CEO";
  if (/chief financial|\bcfo\b/.test(t)) return "CFO";
  if (/chief operating|\bcoo\b/.test(t)) return "COO";
  if (/president/.test(t)) return "President";
  if (/chair/.test(t)) return "Chair";
  if (o.title) return o.title.length > 28 ? o.title.slice(0, 26) + "…" : o.title;
  if (o.roles.includes("director")) return "Director";
  if (o.roles.includes("10% owner")) return "10% owner";
  if (o.roles.includes("officer")) return "Officer";
  return "Insider";
}
