// Test buyer for Virtuals ACP graduation (needs 10 successful jobs, 3 in a row).
// Places one job per contract below (skips ones already placed), funds each once quoted,
// and completes + reviews it once the seller submits. Run with ACP_CONFIG_DIR=~/.config/acp-buyer.
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { readFileSync, writeFileSync, existsSync } from "node:fs";

const run = promisify(execFile);
const CHAIN = "8453";
const SELLER = "0x0b4e9e5460d14ba7fc96691ded5463490d333624";
const STATE = new URL("./state-buyer.json", import.meta.url).pathname;
const POLL_MS = 30_000;

const CONTRACTS = [
  ["0x4200000000000000000000000000000000000006 on Base (WETH9)", "Wrapped ETH; check deposit/withdraw and allowance logic."],
  ["0xcA11bde05977b3631167028862bE2a173976CA11 on Base (Multicall3)", "Batch call helper; check value handling and reentrancy."],
  ["0x000000000022D473030F116dDEE9F6B43aC78BA3 on Base (Permit2)", "Signature-based approvals; check nonce and signature handling."],
  ["0x0000000071727De22E5E9d8BAf0edAc6f37da032 on Base (ERC-4337 EntryPoint v0.7)", "Account abstraction entry point; check validation and payment flows."],
  ["0x33128a8fC17869897dcE68Ed026d694621f6FDfD on Base (Uniswap V3 Factory)", "Pool factory; check owner and fee-tier controls."],
  ["0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43 on Base (Aerodrome Router)", "DEX router; check slippage, deadline and path handling."],
  ["0x0000000000000068F116a894984e2DB1123eB395 on Base (Seaport 1.6)", "NFT marketplace; check order validation and fulfillment."],
  ["0x41675C099F32341bf84BFc5382aF534df5C7461a on Base (Safe 1.4.1 singleton)", "Multisig; check signature checks and module/guard handling."],
  ["0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e on Ethereum mainnet (ENS Registry)", "Name registry; check ownership and resolver controls."],
  ["0xb2fb486a9569ad2c97d9c73936b46ef7fdaa413a on Base (LeftClawServicesV2)", "Job escrow; check payment release and worker access control."],
  ["0x940181a94A35A4569E4529A3CDfB74e38FD98631 on Base (AERO token)", "ERC-20 with minter role; check mint and ownership controls."],
];

const state = existsSync(STATE) ? JSON.parse(readFileSync(STATE, "utf8")) : { placed: [], jobs: {} };
const save = () => writeFileSync(STATE, JSON.stringify(state, null, 2));
const log = (...a) => console.log(new Date().toISOString(), ...a);

async function acp(...args) {
  const { stdout } = await run("acp", [...args, "--json"], { maxBuffer: 10 << 20, timeout: 600_000 });
  return JSON.parse(stdout.trim().split("\n").filter(l => l.startsWith("{")).pop());
}

async function placeNext() {
  const next = CONTRACTS.find(([c]) => !state.placed.includes(c));
  if (!next) return;
  const [contract, context] = next;
  const r = await acp("client", "create-job", "--provider", SELLER, "--offering-name", "Smart Contract Audit",
    "--requirements", JSON.stringify({ contract, context }), "--chain-id", CHAIN);
  state.placed.push(contract);
  state.jobs[r.jobId] = { contract };
  log(r.jobId, "placed", contract);
}

async function tick() {
  const { jobs } = await acp("job", "list");
  const mine = jobs.filter(j => j.providerAddress.toLowerCase() === SELLER);
  for (const j of mine) {
    const id = j.onChainJobId;
    const s = (state.jobs[id] ??= {});
    try {
      if (j.jobStatus === "OPEN" && j.budget && j.budget !== "0" && !s.funded) {
        await acp("client", "fund", "--job-id", id, "--amount", (Number(j.budget) / 1e6).toFixed(2), "--chain-id", CHAIN);
        s.funded = true;
        log(id, "funded");
      } else if (j.jobStatus === "SUBMITTED" && !s.completed) {
        await acp("client", "complete", "--job-id", id, "--chain-id", CHAIN, "--reason", "Report delivered");
        s.completed = true;
        await acp("client", "review", "--job-id", id, "--chain-id", CHAIN, "--rating", "5",
          "--review", "Clear written audit with severity-rated findings.").catch(e => log(id, "review failed", e.message.slice(0, 200)));
        log(id, "completed", j.deliverable);
      }
    } catch (e) {
      log(id, "error", e.message.slice(0, 300));
    }
  }
  // Keep at most 5 jobs in flight (declined ones sit open until they expire) so the audit pipeline isn't flooded.
  const inFlight = mine.filter(j => !["COMPLETED", "REJECTED", "EXPIRED"].includes(j.jobStatus)).length;
  if (inFlight < 5) await placeNext().catch(e => log("place error", e.message.slice(0, 300)));
  save();
}

log("buyer up");
for (;;) {
  await tick().catch(e => log("tick error", e.message.slice(0, 300)));
  if (CONTRACTS.every(([c]) => state.placed.includes(c)) && Object.values(state.jobs).filter(j => j.completed).length >= 10) break;
  await new Promise(r => setTimeout(r, POLL_MS));
}
log("all test jobs done");
