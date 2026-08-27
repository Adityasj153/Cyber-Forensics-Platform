/**
 * Browser verification — D16(g) RBAC frontend role gates (viewer).
 *
 * Logs into the live frontend as the VIEWER user and asserts the
 * "+ New Case", "+ Add Device", "+ Upload File" and anomaly
 * Confirm/Dismiss controls are genuinely ABSENT from the rendered page.
 *
 * Prereq:
 *  - frontend dev server running on :3000
 *  - backend running on :8000
 *  - viewer user assigned to the target case (seed data)
 *
 * Usage (from frontend/): node verify-rbac-viewer.mjs <caseId>
 */

import puppeteer from "puppeteer";

const BASE = "http://localhost:3000";
const VIEWER = {
  username: "rbac_test_viewer",
  password: "Viewer123!",
};
const CASE_ID = process.argv[2];
const LOGIN_URL = `${BASE}/login`;
const CASES_URL = `${BASE}/cases`;
const CASE_DETAIL_URL = `${BASE}/cases/${CASE_ID}`;
const ANOMALIES_URL = `${BASE}/cases/${CASE_ID}/anomalies`;

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

async function hasText(page, text) {
  return await page.evaluate((t) => document.body.innerText.includes(t), text);
}

async function login(page) {
  await page.goto(LOGIN_URL, { waitUntil: "networkidle0", timeout: 60000 });
  await page.waitForSelector("form", { timeout: 30000 });
  await page.type('input[type="text"]', VIEWER.username);
  await page.type('input[type="password"]', VIEWER.password);
  await page.click('button[type="submit"]');
  await page.waitForFunction(
    () => location.pathname.startsWith("/cases"),
    { timeout: 30000 }
  );
}

async function main() {
  let browser;
  try {
    browser = await puppeteer.launch({ headless: "new" });
    const page = await browser.newPage();

    // --- 1. Login as viewer ---
    await login(page);
    check("Login redirected to /cases", page.url().includes("/cases"));

    // --- 2. Cases list: "+ New Case" absent ---
    await page.waitForFunction(
      () => !document.body.innerText.includes("Loading cases..."),
      { timeout: 20000 }
    ).catch(() => {});
    check(
      "'+ New Case' absent on /cases",
      !(await hasText(page, "+ New Case"))
    );
    check(
      "Assigned case visible in list",
      await hasText(page, "RBAC Viewer Test")
    );

    // --- 3. Case detail: "+ Add Device" and "+ Upload File" absent ---
    await page.goto(CASE_DETAIL_URL, { waitUntil: "networkidle0", timeout: 60000 });
    await page.waitForFunction(
      () =>
        !["Loading case...", "Case not found."].some((t) => document.body.innerText.includes(t)),
      { timeout: 20000 }
    ).catch(() => {});

    check(
      "'+ Add Device' absent on case detail",
      !(await hasText(page, "+ Add Device"))
    );
    check(
      "'+ Upload File' absent on case detail",
      !(await hasText(page, "+ Upload File"))
    );
    check("Device renders on case detail", await hasText(page, "WORKSTATION-01"));

    // --- 4. Anomalies: Confirm/Dismiss absent for pending anomaly ---
    await page.goto(ANOMALIES_URL, { waitUntil: "networkidle0", timeout: 60000 });
    await page.waitForFunction(
      () => !document.body.innerText.includes("Loading anomalies..."),
      { timeout: 20000 }
    ).catch(() => {});
    check(
      "Pending anomaly renders",
      await hasText(page, "off hours")
    );

    // Expand the anomaly panel so review actions would render if authorized
    await page.evaluate(() => {
      const panels = Array.from(document.querySelectorAll("*")).filter((el) =>
        el.textContent && el.textContent.includes("off hours") && el.children.length < 8
      );
      const target = panels[panels.length - 1];
      if (target) target.click();
    }).catch(() => {});
    await new Promise((r) => setTimeout(r, 800));

    check("Confirm button absent on anomaly panel", !(await hasText(page, "✓ Confirm")));
    check("Dismiss button absent on anomaly panel", !(await hasText(page, "✕ Dismiss")));

    // --- Summary ---
    console.log(`\nVIEWER phase: ${passed} passed, ${failed} failed out of ${passed + failed}`);

    // ============================================================
    // Phase 2 — POSITIVE CONTROL: log in as INVESTIGATOR. The same
    // controls MUST be present for an investigator, proving the viewer
    // absence is role-driven, not a page-render failure.
    // ============================================================
    const invPassed = passed;
    const invFailed = failed;

    await page.goto(LOGIN_URL, { waitUntil: "networkidle0", timeout: 60000 });
    await page.waitForSelector("form", { timeout: 30000 });
    await page.type('input[type="text"]', "testuser");
    await page.type('input[type="password"]', "TestPass123!");
    await page.click('button[type="submit"]');
    await page.waitForFunction(
      () => location.pathname.startsWith("/cases"),
      { timeout: 30000 }
    );

    await page.waitForFunction(
      () => !document.body.innerText.includes("Loading cases..."),
      { timeout: 20000 }
    ).catch(() => {});
    check(
      "INVESTIGATOR: '+ New Case' present on /cases",
      await hasText(page, "+ New Case")
    );

    await page.goto(CASE_DETAIL_URL, { waitUntil: "networkidle0", timeout: 60000 });
    await page.waitForFunction(
      () =>
        !["Loading case...", "Case not found."].some((t) => document.body.innerText.includes(t)),
      { timeout: 20000 }
    ).catch(() => {});
    check(
      "INVESTIGATOR: '+ Add Device' present on case detail",
      await hasText(page, "+ Add Device")
    );
    check(
      "INVESTIGATOR: '+ Upload File' present on case detail",
      await hasText(page, "+ Upload File")
    );

    await page.goto(ANOMALIES_URL, { waitUntil: "networkidle0", timeout: 60000 });
    await page.waitForFunction(
      () => !document.body.innerText.includes("Loading anomalies..."),
      { timeout: 20000 }
    ).catch(() => {});
    await page.evaluate(() => {
      const panels = Array.from(document.querySelectorAll("*")).filter((el) =>
        el.textContent && el.textContent.includes("off hours") && el.children.length < 8
      );
      const target = panels[panels.length - 1];
      if (target) target.click();
    }).catch(() => {});
    await new Promise((r) => setTimeout(r, 800));
    check(
      "INVESTIGATOR: Confirm button present on anomaly panel",
      await hasText(page, "✓ Confirm")
    );

    console.log(`\nINVESTIGATOR phase +${passed - invPassed} passed / ${failed - invFailed} failed`);
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
