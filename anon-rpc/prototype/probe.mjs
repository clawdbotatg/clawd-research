// Headless verification of the spike: serve the built page, load it in the
// machine's cached playwright Chromium, and assert the reads land.
// Usage: RPC_URL=https://eth-mainnet.g.alchemy.com/v2/KEY node probe.mjs
import { chromium } from "playwright-core";
import { createServer } from "node:http";
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

const RPC_URL = process.env.RPC_URL;
if (!RPC_URL) { console.error("set RPC_URL"); process.exit(2); }

// Find the cached headless shell (same strategy as clawd-harness/tools/uiprobe.mjs).
const cache = join(homedir(), "Library/Caches/ms-playwright");
const shells = readdirSync(cache).filter((d) => d.startsWith("chromium_headless_shell-")).sort().reverse();
let exec;
for (const s of shells) {
  for (const p of [
    join(cache, s, "chrome-headless-shell-mac-arm64", "chrome-headless-shell"),
    join(cache, s, "chrome-mac", "headless_shell"),
  ]) {
    if (existsSync(p)) { exec = p; break; }
  }
  if (exec) break;
}
if (!exec) { console.error("no cached chromium; run npx playwright install chromium"); process.exit(2); }

const MIME = { ".html": "text/html", ".js": "text/javascript", ".map": "application/json" };
const server = createServer((req, res) => {
  const path = req.url.split("?")[0];
  const file = join(process.cwd(), path === "/" ? "index.html" : path.slice(1));
  try {
    const body = readFileSync(file);
    res.writeHead(200, { "content-type": MIME[file.slice(file.lastIndexOf("."))] ?? "application/octet-stream" });
    res.end(body);
  } catch {
    res.writeHead(404).end("nope");
  }
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const port = server.address().port;

const browser = await chromium.launch({ executablePath: exec });
const page = await browser.newPage();
page.on("console", (m) => console.log("  [page]", m.text()));
await page.goto(`http://127.0.0.1:${port}/index.html?rpc=${encodeURIComponent(RPC_URL)}`);

try {
  await page.waitForFunction(() => window.__RESULT__ || window.__ERROR__, null, { timeout: 60_000 });
  const err = await page.evaluate(() => window.__ERROR__);
  if (err) { console.error("PAGE ERROR:\n" + err); process.exit(1); }
  const result = await page.evaluate(() => window.__RESULT__);
  console.log("RESULT " + JSON.stringify(result, null, 2));
  if (!result.hashMatches || result.chainId !== 1) { console.error("assertions failed"); process.exit(1); }
  console.log("PASS");
} finally {
  await browser.close();
  server.close();
}
