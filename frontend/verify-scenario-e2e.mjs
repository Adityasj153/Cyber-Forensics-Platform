/**
 * Browser verification — Scenario 1/2 real ingested data renders in the UI.
 *
 * Logs in as investigator and verifies:
 *   Timeline: SVG renders real events (event-markers), anomaly triangle markers,
 *             custody-thread dotted lines, and the events counter.
 *   Correlation: List view shows the expected relation_type + confidence; graph
 *             view renders connected entity nodes + edge lines.
 *
 * Usage (from frontend/): node verify-scenario-e2e.mjs <caseId> <expectedEdges>
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

async function svgLineStrokes(page) {
  return await page.evaluate(() => {
    const svg = document.querySelector("svg");
    if (!svg) return [];
    return Array.from(svg.querySelectorAll("line")).map((l) => l.getAttribute("stroke"));
  });
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

    // ---- Correlation ----
    console.log("\n=== Correlation ===");
    const corrUrl = `${BASE}/cases/${CASE_ID}/correlation`;
    await page.goto(corrUrl, { waitUntil: "networkidle0", timeout: 60000 });
    await page.waitForFunction(
      () => !document.body.innerText.includes("No correlations found"),
      { timeout: 30000 }
    ).catch(() => {});
    await sleep(1500);

    // Graph view: connected nodes + edges
    const graphNodeCount = await countInSvg(page, "g");
    const graphEdgeCount = await countInSvg(page, "line");
    check("Correlation graph renders connected nodes", graphNodeCount >= 2, `node-groups=${graphNodeCount}`);
    check("Correlation graph renders edges", graphEdgeCount >= 1, `edges=${graphEdgeCount}`);
    const edgeStrokes = await svgLineStrokes(page);
    const cyanEdges = edgeStrokes.filter((s) => s === "#4FB8C4").length;
    check("Correlation graph edge is cyan (confirmed >=70%)", cyanEdges >= 1, `cyanEdges=${cyanEdges}`);

    // Switch to List view and assert the expected correlation
    await page.evaluate(() => {
      const btn = Array.from(document.querySelectorAll("button")).find((b) =>
        b.textContent.trim() === "List"
      );
      if (btn) btn.click();
    });
    await sleep(1200);
    const listText = await page.evaluate(() => document.body.innerText);
    check("Correlation List view shows file_transfer_chain", listText.includes("file_transfer_chain"));
    check("Correlation List view shows 85% confidence", listText.includes("85%"));

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
