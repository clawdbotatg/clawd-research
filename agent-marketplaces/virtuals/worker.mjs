// One Dollar Audit — Virtuals ACP seller worker.
// Polls our ACP jobs and moves each one along:
//   OPEN (no budget)  -> quote $1
//   FUNDED            -> buy the audit from onedollaraudit.com via x402, then poll it
//   audit complete    -> submit the report URL as the deliverable
// Uses the `acp` CLI with whatever agent is active in ACP_CONFIG_DIR (default ~/.config/acp).
// Env: AUDIT_PAYER_PK — wallet holding USDC on Base that pays the $1 x402 audit.
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { wrapFetchWithPaymentFromConfig } from "@x402/fetch";
import { ExactEvmScheme } from "@x402/evm";
import { privateKeyToAccount } from "viem/accounts";

const run = promisify(execFile);
const CHAIN = "8453";
const PRICE = "1.00";
const AUDIT_URL = "https://www.onedollaraudit.com/api/audit";
const STATE = new URL("./state-worker.json", import.meta.url).pathname;
const POLL_MS = 30_000;
const SELLER = "0x0b4e9e5460d14ba7fc96691ded5463490d333624"; // One Dollar Audit agent wallet

const pay = wrapFetchWithPaymentFromConfig(fetch, {
  schemes: [{ network: "eip155:8453", client: new ExactEvmScheme(privateKeyToAccount(process.env.AUDIT_PAYER_PK)) }],
});

const state = existsSync(STATE) ? JSON.parse(readFileSync(STATE, "utf8")) : {};
const save = () => writeFileSync(STATE, JSON.stringify(state, null, 2));
const log = (...a) => console.log(new Date().toISOString(), ...a);

async function acp(...args) {
  const { stdout } = await run("acp", [...args, "--json"], { maxBuffer: 10 << 20, timeout: 600_000 });
  const line = stdout.trim().split("\n").filter(l => l.startsWith("{")).pop();
  return JSON.parse(line);
}

async function requirement(jobId) {
  const h = await acp("job", "history", "--job-id", jobId, "--chain-id", CHAIN);
  const m = h.entries.find(e => e.kind === "message" && e.contentType === "requirement");
  try {
    return JSON.parse(m.content);
  } catch {
    return { contract: m?.content ?? "" };
  }
}

async function startAudit(jobId) {
  const req = await requirement(jobId);
  const res = await pay(AUDIT_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      description: String(req.contract ?? "").slice(0, 12000),
      context: [req.context, `Ordered via Virtuals ACP job ${jobId}.`].filter(Boolean).join(" "),
    }),
  });
  const body = await res.json();
  if (!res.ok || !body.statusUrl) throw new Error(`audit order failed ${res.status}: ${JSON.stringify(body)}`);
  return body;
}

async function tick() {
  const { jobs } = await acp("job", "list");
  for (const j of jobs) {
    if (j.providerAddress.toLowerCase() !== SELLER) continue;
    const id = j.onChainJobId;
    const s = (state[id] ??= {});
    try {
      if (j.jobStatus === "OPEN" && (!j.budget || j.budget === "0") && !s.quoted) {
        await acp("provider", "set-budget", "--job-id", id, "--amount", PRICE, "--chain-id", CHAIN);
        s.quoted = true;
        log(id, "quoted $" + PRICE);
      } else if (j.jobStatus === "FUNDED" && !s.audit) {
        s.audit = await startAudit(id);
        log(id, "audit ordered", s.audit.jobId, s.audit.jobUrl);
      } else if (j.jobStatus === "FUNDED" && s.audit && !s.submitted) {
        const st = await (await fetch(s.audit.statusUrl)).json();
        if (st.status === "complete") {
          const deliverable = st.reportHtmlUrl || st.reportUrl || s.audit.jobUrl;
          await acp("provider", "submit", "--job-id", id, "--deliverable", deliverable, "--chain-id", CHAIN);
          s.submitted = deliverable;
          log(id, "submitted", deliverable);
        } else if (["declined", "cancelled"].includes(st.status)) {
          log(id, "audit", st.status, "— needs a human");
        }
      }
    } catch (e) {
      log(id, "error", e.message.slice(0, 300));
    }
    save();
  }
}

log("worker up");
for (;;) {
  await tick().catch(e => log("tick error", e.message.slice(0, 300)));
  await new Promise(r => setTimeout(r, POLL_MS));
}
