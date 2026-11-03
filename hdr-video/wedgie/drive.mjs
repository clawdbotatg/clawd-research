// node drive.mjs [all | preview N1,N2,...] — headless Chromium on the GPU drives index.html
import { chromium } from "playwright-core";
import { execSync } from "node:child_process";
const [mode = "all", arg = ""] = process.argv.slice(2);
const exe = execSync("ls -d ~/Library/Caches/ms-playwright/chromium-*/chrome-mac*/*.app/Contents/MacOS/* | tail -1", { shell: "/bin/zsh" }).toString().trim();
const b = await chromium.launch({ executablePath: exe, headless: true, args: ["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist", "--enable-unsafe-swiftshader"] });
const p = await b.newPage({ viewport: { width: +(process.env.VW || 1920), height: +(process.env.VH || 1080) } });
p.on("console", (m) => console.log("page:", m.text()));
p.on("pageerror", (e) => console.log("ERR:", e.message));
if (mode === "preview") {
  for (const f of arg.split(",")) {
    await p.goto(`http://127.0.0.1:8931/${process.env.PAGE || ""}?frame=${f}`); await p.waitForFunction("window.ready", null, { timeout: 60000 });
    await p.waitForTimeout(300);
    await p.screenshot({ path: `${process.env.PREV || "."}/prev_${f}.png` });
    console.log("preview", f, await p.title());
  }
} else {
  await p.goto(`http://127.0.0.1:8931/${process.env.PAGE || ""}${process.env.QS || ""}`); await p.waitForFunction("window.ready", null, { timeout: 60000 });
  console.log(await p.title());
  const t0 = Date.now(); const n = await p.evaluate(() => window.renderAll());
  console.log("rendered", n, "frames in", (Date.now() - t0) / 1000, "s");
}
await b.close();
