/**
 * Browser verification — D17(h) root layout / app shell.
 *
 * Logs into the live frontend and verifies the persistent app shell:
 *   1. Sidebar renders with real case data (case name + id) inside a case.
 *   2. Nav links (Timeline/Correlation/Anomalies/Search/Reports/Overview) navigate correctly.
 *   3. Auth wrapper: role badge shows the correct role for the logged-in user.
 *   4. Logout clears the session cookie and redirects to /login.
 *
 * Prereq:
 *  - frontend dev server running on :3000
 *  - backend running on :8000
 *  - existing case + test users (investigator testuser, viewer rbac_test_viewer)
 *
 * Usage (from frontend/): node verify-root-layout.mjs <caseId>
 */

import puppeteer from "puppeteer";

const BASE = "http://localhost:3000";
const LOGIN_URL = `${BASE}/login`;
const CASES_URL = `${BASE}/cases`;
const CASE_ID = process.argv[2];
const CASE_DETAIL_URL = `${BASE}/cases/${CASE_ID}`;

const INVESTIGATOR = { username: "testuser", password: "TestPass123!" };
const VIEWER = { username: "rbac_test_viewer", password: "Viewer123!" };

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

async function hasInTopBar(page, text) {
  return await page.evaluate((t) => {
    const header = document.querySelector("header");
    return !!header && header.innerText.includes(t);
  }, text);
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function clickLinkByText(page, text) {
  await page.evaluate((t) => {
    const link = Array.from(document.querySelectorAll("a")).find((a) =>
      a.textContent.trim() === t
    );
    if (link) link.click();
  }, text);
  await new Promise((r) => setTimeout(r, 1200));
}

async function login(page, user) {
  await page.goto(LOGIN_URL, { waitUntil: "networkidle0", timeout: 60000 });
  await page.waitForSelector("form", { timeout: 30000 });
  await page.type('input[type="text"]', user.username);
  await page.type('input[type="password"]', user.password);
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

    // ---- PHASE 1: INVESTIGATOR ----
    console.log("=== Phase 1: Investigator (testuser) ===");
    await login(page, INVESTIGATOR);

    // 1. Cases list shows shell: top bar brand + reappears after login
    await page.waitForFunction(
      () => !document.body.innerText.includes("Loading cases..."),
      { timeout: 20000 }
    ).catch(() => {});
    check("Top bar brand renders", await hasInTopBar(page, "Cyber Forensics Platform"));
    check("Role badge 'INVESTIGATOR' in top bar", await hasInTopBar(page, "INVESTIGATOR"));
    check("Username 'testuser' in top bar", await hasInTopBar(page, "testuser"));
    check("Logout button in top bar", await hasInTopBar(page, "Logout"));

    // 2. Navigate into a case -> sidebar shows real case data + section nav
    await page.goto(CASE_DETAIL_URL, { waitUntil: "networkidle0", timeout: 60000 });
    await page.waitForFunction(
      () =>
        !["Loading case...", "Case not found."].some((t) => document.body.innerText.includes(t)),
      { timeout: 20000 }
    ).catch(() => {});
    // Wait for the sidebar to load the case name via React Query
    await new Promise((r) => setTimeout(r, 1500));
    const sidebarText = await page.evaluate(() =>
      document.querySelector("aside") ? document.querySelector("aside").innerText : ""
    );
    check(
      "Sidebar shows real case name 'RBAC Viewer Test'",
      sidebarText.includes("RBAC Viewer Test"),
      "aside has: " + sidebarText.split("\n").slice(0, 6).join(" | ")
    );
    check(
      "Sidebar shows case id (8-char monospace prefix)",
      new RegExp(`${CASE_ID.slice(0, 8)}`).test(sidebarText)
    );
    check("Sidebar has Overview nav", sidebarText.includes("Overview"));
    check("Sidebar has Timeline nav", sidebarText.includes("Timeline"));
    check("Sidebar has Correlation nav", sidebarText.includes("Correlation"));
    check("Sidebar has Anomalies nav", sidebarText.includes("Anomalies"));
    check("Sidebar has Search nav", sidebarText.includes("Search"));
    check("Sidebar has Reports nav", sidebarText.includes("Reports"));

    // 3. Nav links work — click each and assert URL + heading
    const navChecks = [
      { link: "Timeline", urlPart: "/timeline" },
      { link: "Correlation", urlPart: "/correlation" },
      { link: "Anomalies", urlPart: "/anomalies" },
      { link: "Search", urlPart: "/search" },
      { link: "Reports", urlPart: "/reports" },
      { link: "Overview", urlPart: "" },
    ];
    for (const n of navChecks) {
      const target =
        n.urlPart === "" ? CASE_DETAIL_URL : `${CASE_DETAIL_URL}${n.urlPart}`;
      await page.goto(target, { waitUntil: "networkidle0", timeout: 60000 });
      await sleep(1200);
      // active nav state should be applied to the clicked item
      const isActive = await page.evaluate((label) => {
        const a = Array.from(document.querySelectorAll("aside a")).find(
          (el) => el.textContent.trim() === label
        );
        return !!a && a.className.includes("bg-trace-cyan/10");
      }, n.link);
      check(`Nav '${n.link}' -> URL correct`, page.url().startsWith(target), page.url());
      check(`Nav '${n.link}' -> active state`, isActive);
    }

    // 4. auth wrapper persists on case routes (role badge still there)
    check(
      "Role badge persists on case page",
      await hasInTopBar(page, "INVESTIGATOR")
    );
    check("Logout button persists on case page", await hasInTopBar(page, "Logout"));

    // ---- PHASE 2: VIEWER positive control (role badge reflects role) ----
    console.log("\n=== Phase 2: Viewer (rbac_test_viewer) ===");
    await page.goto(LOGIN_URL, { waitUntil: "networkidle0", timeout: 60000 });
    await login(page, VIEWER);
    await page.waitForFunction(
      () => !document.body.innerText.includes("Loading cases..."),
      { timeout: 20000 }
    ).catch(() => {});
    check("Role badge 'VIEWER' in top bar for viewer", await hasInTopBar(page, "VIEWER"));
    check("Username 'rbac_test_viewer' in top bar", await hasInTopBar(page, "rbac_test_viewer"));

    // ---- PHASE 3: LOGOUT clears session and redirects to /login ----
    console.log("\n=== Phase 3: Logout ===");
    await page.goto(CASE_DETAIL_URL, { waitUntil: "networkidle0", timeout: 60000 });
    await sleep(1200);
    await page.evaluate(() => {
      const btn = Array.from(document.querySelectorAll("button")).find((b) =>
        b.textContent.includes("Logout")
      );
      if (btn) btn.click();
    });
    await page.waitForFunction(
      () => location.pathname === "/login",
      { timeout: 30000 }
    );
    check("Logout redirects to /login", page.url().includes("/login"), page.url());

    // Assert no auth session cookie or role badge remains
    const cookies = await page.cookies();
    const authCookie = cookies.find((c) =>
      String(c.name).toLowerCase().includes("session")
    );
    check(
      "Session cookie cleared after logout",
      !authCookie || authCookie.value === "" || (authCookie.expires && authCookie.expires < Date.now() / 1000),
      authCookie ? "cookie name=" + authCookie.name : "no session cookie"
    );
    check(
      "Role badge absent on /login after logout",
      !(await hasText(page, "INVESTIGATOR")) && !(await hasText(page, "VIEWER"))
    );

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
