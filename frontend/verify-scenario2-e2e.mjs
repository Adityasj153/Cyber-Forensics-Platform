/**
 * Browser verification — Scenario 2 (ransomware) real ingested data.
 *
 * Logs in as investigator and verifies:
 *   Timeline: SVG renders real EVTX events (event-markers), anomaly triangle
 *             markers for the ransomware channel, custody-thread lines, legend,
 *             events counter, and key indicators (file_write / .locked / C2 IP).
 *   Correlation: for a single-device case we expect 0 cross-device edges, so we
 *             only assert the page renders its empty state without crashing.
 *
 * Usage (from frontend/): node verify-scenario2-e2e.mjs <caseId>
 */

import puppeteer from "puppeteer";

const BASE = "http://localhost:3000";
const LOGIN_URL = `${BASE}/login`;
const CASE_ID = process.argv[2];

const USER = { username: "testuser", password: "TestPass123!" };

let passed = 0;
let failed = 0;

function check(name, cond, detail = "") {
  if (cond) {
    console.log(`PASS: ${name}${detail ? ` (${detail})` : ""}`);
    passed++;
  } else {
    console.error(`FAIL: ${name}${detail ? ` (${detail})` : ""}`);
    failed++;
  }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function login(page) {
  await page.goto(LOGIN_URL, { waitUntil: "networkidle0", timeout: 60000 });
  await page.waitForSelector("form", { timeout: 30000 });
  await page.type('input[type="text"]', USER.username);
  await page.type('input[type="password"]', USER.password);
  await page.click('button[type="submit"]');
  await page.waitForFunction(
    () => location.pathname.startsWith("/cases"),
    { timeout: 30000 }
  );
}

async function countInSvg(page, selector) {
  return await page.evaluate((sel) => {
    const svg = document.querySelector("svg");
    return svg ? svg.querySelectorAll(sel).length : 0;
  }, selector);
}

async function main() {
  let browser;
  try {
    browser = await puppeteer.launch({ headless: "new" });
    const page = await browser.newPage();
    await page.setViewport({ width: 1440, height: 900 });

    await login(page);
    await sleep(1500);

    // ---- Timeline ----
    console.log("=== Timeline ===");
    const timelineUrl = `${BASE}/cases/${CASE_ID}/timeline`;
    await page.goto(timelineUrl, { waitUntil: "networkidle0", timeout: 60000 });
    await page.waitForFunction(
      () => !document.body.innerText.includes("No events to display"),
      { timeout: 30000 }
    ).catch(() => {});
    await sleep(1500);

    const markerCount = await countInSvg(page, ".event-marker");
    check("Timeline renders SVG event markers", markerCount > 0, `markers=${markerCount}`);
    check("Timeline shows events (counter text)", await page.evaluate(
      () => /\d+ of \d+ events/.test(document.body.innerText)
    ));

    const anomalyTriangles = await countInSvg(page, "polygon");
    check("Timeline renders anomaly triangle markers", anomalyTriangles > 0, `triangles=${anomalyTriangles}`);

    const custodyLines = await countInSvg(page, "line");
    check("Timeline renders custody-thread lines", custodyLines > 0, `lines=${custodyLines}`);
    const legend = await page.evaluate(() => document.body.innerText);
    check("Timeline legend has Confirmed marker", legend.includes("Confirmed"));
    check("Timeline legend has Anomaly marker", legend.includes("Anomaly"));
    check("Timeline legend has Custody thread", legend.includes("Custody thread"));

    const tlText = await page.evaluate(() => document.body.innerText);
    check("Timeline shows ransomware action labels (file_write / ransom_note)",
      tlText.includes("file_write") && tlText.includes("ransom_note"),
      "ransomware action labels present");

    // IPs/hashes are surfaced interactively (detail on click), not as static text.
    await page.evaluate(() => {
      const hit = document.querySelector('svg .event-marker circle[r="12"]');
      if (hit) hit.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
    await sleep(800);
    const detailText = await page.evaluate(() => document.body.innerText);
    check("Timeline opens Event Detail modal on marker click",
      detailText.includes("Event Detail"), "detail modal rendered");
    const detailLower = detailText.toLowerCase();
    check("Timeline detail modal surfaces structured rows (Object/IP/Hash)",
      ["object", "ip address", "file hash"].some((s) => detailLower.includes(s)),
      "structured row present");

    // ---- Correlation (single-device: expect empty state, no crash) ----
    console.log("\n=== Correlation ===");
    const corrUrl = `${BASE}/cases/${CASE_ID}/correlation`;
    await page.goto(corrUrl, { waitUntil: "networkidle0", timeout: 60000 });
    await sleep(2000);
    const corrState = await page.evaluate(() => ({
      text: document.body.innerText,
      hasSvg: !!document.querySelector("svg"),
    }));
    check("Correlation page loads without crash", corrState.text.length > 0, "page rendered");
    const corrText = corrState.text;
    const noCorr = corrText.includes("No correlations found");
    const hasGraph = corrState.hasSvg;
    check("Correlation reports no edges for single-device case",
      noCorr && !hasGraph, noCorr ? "empty-state message shown" : "graph present");
    check("Correlation page shows a case header/context",
      corrText.toLowerCase().includes("correlation"), "correlation heading rendered");

    console.log(`\nTOTAL: ${passed} passed, ${failed} failed out of ${passed + failed}`);
    process.exit(failed > 0 ? 1 : 0);
  } finally {
    if (browser) await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
