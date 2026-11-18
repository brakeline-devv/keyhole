import { test } from "node:test";
import assert from "node:assert/strict";
import { parseForm4, roleLabel } from "../src/form4.js";
import { rows, scoreBuy, summarize } from "../src/insider.js";

const xml = (o) => `<?xml version="1.0"?><ownershipDocument><documentType>4</documentType><periodOfReport>2026-11-10</periodOfReport>
<issuer><issuerCik>0000000001</issuerCik><issuerName>ACME CORP</issuerName><issuerTradingSymbol>acme</issuerTradingSymbol></issuer>
<reportingOwner><reportingOwnerId><rptOwnerCik>0000000009</rptOwnerCik><rptOwnerName>${o.name || "DOE JANE"}</rptOwnerName></reportingOwnerId>
<reportingOwnerRelationship><isDirector>${o.dir ? 1 : 0}</isDirector><isOfficer>${o.title ? 1 : 0}</isOfficer><officerTitle>${o.title || ""}</officerTitle><isTenPercentOwner>0</isTenPercentOwner></reportingOwnerRelationship></reportingOwner>
<aff10b5One>${o.plan ? 1 : 0}</aff10b5One>
<nonDerivativeTable><nonDerivativeTransaction><securityTitle><value>Common Stock</value></securityTitle><transactionDate><value>2026-11-10</value></transactionDate>
<transactionCoding><transactionCode>${o.code || "P"}</transactionCode>${o.fn ? '<footnoteId id="F1"/>' : ""}</transactionCoding>
<transactionAmounts><transactionShares><value>${o.shares || 10000}</value></transactionShares><transactionPricePerShare><value>${o.price ?? 50}</value></transactionPricePerShare>
<transactionAcquiredDisposedCode><value>${o.code === "S" ? "D" : "A"}</value></transactionAcquiredDisposedCode></transactionAmounts>
<postTransactionAmounts><sharesOwnedFollowingTransaction><value>${o.after || 20000}</value></sharesOwnedFollowingTransaction></postTransactionAmounts>
<ownershipNature><directOrIndirectOwnership><value>D</value></directOrIndirectOwnership></ownershipNature></nonDerivativeTransaction></nonDerivativeTable>
<footnotes>${o.fn ? `<footnote id="F1">${o.fn}</footnote>` : ""}</footnotes></ownershipDocument>`;
const one = (o) => rows({ ...parseForm4(xml(o)), filed: "2026-11-12", url: "u", accession: "a" })[0];

test("parses a CEO open-market buy: value, role, stake change", () => {
  const r = one({ title: "Chief Executive Officer" });
  assert.equal(r.ticker, "ACME"); assert.equal(r.code, "P"); assert.equal(r.kind, "open-market buy");
  assert.equal(r.value, 500000); assert.equal(r.role, "CEO"); assert.equal(r.holdingChangePct, 100); assert.equal(r.planned, false);
});

test("10b5-1 plan detected from the flag and from a footnote", () => {
  assert.equal(one({ code: "S", dir: true, plan: true }).planned, true);
  assert.equal(one({ code: "S", dir: true, fn: "Effected pursuant to a Rule 10b5-1 trading plan adopted on May 1." }).planned, true);
});

test("scores: a CEO doubling their stake beats a fund; a 10b5-1 buy weighs less", () => {
  const ceo = scoreBuy(one({ title: "CEO", shares: 20000, after: 40000 }));
  const fund = scoreBuy({ ...one({ name: "BIG CAPITAL PARTNERS LP", dir: false }), institution: true });
  const planned = scoreBuy({ ...one({ title: "CEO", shares: 20000, after: 40000 }), planned: true });
  assert.ok(ceo.score > fund.score); assert.ok(ceo.score > planned.score);
  assert.equal(scoreBuy(one({ code: "S", dir: true })), null);
});

test("summary calls routine selling routine", () => {
  const s = summarize([{ ...one({ code: "S", dir: true, plan: true }), insider: "A" }, { ...one({ code: "S", dir: true, plan: true }), insider: "B" }], 90);
  assert.match(s.read, /pre-scheduled/); assert.equal(s.openMarketSales.plannedPct, 100);
});

test("role labels", () => {
  assert.equal(roleLabel({ title: "EVP, Chief Financial Officer", roles: ["officer"] }), "CFO");
  assert.equal(roleLabel({ title: "", roles: ["director"] }), "Director");
});
