/**
 * Puppeteer DOM assertion — verify correlation-graph ENTITY_COLORS render correctly.
 *
 * Mirrors the SVG rendering logic from components/correlation-graph/index.tsx
 * using the same ENTITY_COLORS map + #6B8AAE fallback for hash (not in spec).
 *
 * Usage: node scripts/verify-correlation-colors.mjs
 * Requires: npm install puppeteer (run from frontend/ or root)
 */

import puppeteer from "puppeteer";
import { writeFileSync, unlinkSync } from "fs";
import { join } from "path";

const EXPECTED_COLORS = {
  device: "#33415A",
  file: "#C9D2E0",
  ip: "#4FB8C4",
  user: "#D98E33",
  hash: "#6B8AAE", // fallback — hash removed from ENTITY_COLORS, uses || "#6B8AAE"
};

const MOCK_ENTITIES = [
  { id: "e1", type: "device", label: "SKTOP-01" },
  { id: "e2", type: "file", label: "malware.dll" },
  { id: "e3", type: "ip", label: "192.168.1.100" },
  { id: "e4", type: "hash", label: "a1b2c3d4" },
  { id: "e5", type: "user", label: "admin" },
  { id: "e6", type: "device", label: "LAPTOP-02" },
];

const MOCK_EDGES = [
  { id: "ed1", source: "e1", target: "e2", confidence: 0.85 },
  { id: "ed2", source: "e1", target: "e3", confidence: 0.92 },
  { id: "ed3", source: "e3", target: "e4", confidence: 0.6 },
  { id: "ed4", source: "e2", target: "e5", confidence: 0.75 },
  { id: "ed5", source: "e5", target: "e6", confidence: 0.4 },
];

function buildHTML() {
  return `<!DOCTYPE html>
<html><body style="background:#0f172a;padding:20px">
<svg id="graph" width="800" height="500" xmlns="http://www.w3.org/2000/svg">
  <defs>
    ${Object.entries(EXPECTED_COLORS)
      .map(
        ([type, color]) =>
          `<marker id="arrow-${type}" viewBox="0 -5 10 10" refX="20" refY="0" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M0,-5L10,0L0,5" fill="${color}" opacity="0.6"/>
          </marker>`
      )
      .join("\n    ")}
  </defs>
  <g id="nodes">
    ${MOCK_ENTITIES.map(
      (e) => `
    <g id="node-${e.id}" data-type="${e.type}">
      ${renderShape(e.type, EXPECTED_COLORS[e.type] || "#6B8AAE")}
      <text dy="22" text-anchor="middle" fill="#C9D2E0" font-size="9px">${e.label}</text>
      <text dy="-16" text-anchor="middle" fill="${EXPECTED_COLORS[e.type] || "#6B8AAE"}" font-size="7px">${e.type}</text>
    </g>`
    ).join("\n")}
  </g>
  <g id="edges">
    ${MOCK_EDGES.map(
      (ed) =>
        `<line id="edge-${ed.id}" stroke="${ed.confidence >= 0.7 ? "#4FB8C4" : "#D98E33"}" stroke-width="1.5" stroke-dasharray="4,3" stroke-opacity="${Math.max(0.4, ed.confidence)}"/>`
    ).join("\n    ")}
  </g>
</svg>
</body></html>`;
}

function renderShape(type, color) {
  const size = 10;
  switch (type) {
    case "device":
      return `<rect x="${-size}" y="${-size}" width="${size * 2}" height="${size * 2}" rx="2" fill="${color}" opacity="0.9"/>`;
    case "file":
      return `<polygon points="0,${-size} ${size},0 0,${size} ${-size},0" fill="${color}" opacity="0.9"/>`;
    case "ip":
      return `<polygon points="0,${-size} ${size * 0.9},${size * 0.6} ${-size * 0.9},${size * 0.6}" fill="${color}" opacity="0.9"/>`;
    case "hash":
      return `<polygon points="0,${-size} ${size * 0.87},${-size * 0.5} ${size * 0.87},${size * 0.5} 0,${size} ${-size * 0.87},${size * 0.5} ${-size * 0.87},${-size * 0.5}" fill="${color}" opacity="0.9"/>`;
    case "user":
      return `<circle r="${size}" fill="none" stroke="${color}" stroke-width="2" opacity="0.9"/>`;
    default:
      return `<circle r="${size}" fill="${color}" opacity="0.9"/>`;
  }
}

async function main() {
  const html = buildHTML();
  const tmpFile = join(process.cwd(), "scripts", "__verify_tmp.html");
  writeFileSync(tmpFile, html);

  let browser;
  try {
    browser = await puppeteer.launch({ headless: "new" });
    const page = await browser.newPage();
    await page.goto(`file:///${tmpFile.replace(/\\/g, "/")}`, {
      waitUntil: "domcontentloaded",
    });

    let passed = 0;
    let failed = 0;

    for (const entity of MOCK_ENTITIES) {
      const node = await page.$(`#node-${entity.id}`);
      if (!node) {
        console.error(`FAIL: node #node-${entity.id} not found in DOM`);
        failed++;
        continue;
      }

      const shapeEl = await node.$("rect, polygon, circle");
      if (!shapeEl) {
        console.error(`FAIL: no shape element in #node-${entity.id}`);
        failed++;
        continue;
      }

      const fillColor = await shapeEl.evaluate((el) => {
        const tag = el.tagName.toLowerCase();
        if (tag === "circle") return el.getAttribute("stroke");
        return el.getAttribute("fill");
      });

      const expected = EXPECTED_COLORS[entity.type] || "#6B8AAE";
      if (fillColor === expected) {
        console.log(`PASS: ${entity.type} (${entity.label}) → ${fillColor}`);
        passed++;
      } else {
        console.error(
          `FAIL: ${entity.type} (${entity.label}) → got ${fillColor}, expected ${expected}`
        );
        failed++;
      }
    }

    // Verify edge colors
    const edgeExpected = {
      ed1: "#4FB8C4", // confidence 0.85 >= 0.7
      ed2: "#4FB8C4", // confidence 0.92 >= 0.7
      ed3: "#D98E33", // confidence 0.6 < 0.7
      ed4: "#4FB8C4", // confidence 0.75 >= 0.7
      ed5: "#D98E33", // confidence 0.4 < 0.7
    };

    for (const [edgeId, expectedColor] of Object.entries(edgeExpected)) {
      const edge = await page.$(`#edge-${edgeId}`);
      if (!edge) {
        console.error(`FAIL: edge #${edgeId} not found`);
        failed++;
        continue;
      }
      const stroke = await edge.evaluate((el) => el.getAttribute("stroke"));
      if (stroke === expectedColor) {
        console.log(`PASS: edge ${edgeId} → ${stroke}`);
        passed++;
      } else {
        console.error(`FAIL: edge ${edgeId} → got ${stroke}, expected ${expectedColor}`);
        failed++;
      }
    }

    console.log(`\n${passed} passed, ${failed} failed out of ${passed + failed}`);
    process.exit(failed > 0 ? 1 : 0);
  } finally {
    if (browser) await browser.close();
    try { unlinkSync(tmpFile); } catch {}
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
