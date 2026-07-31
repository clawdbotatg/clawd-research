// anon-rpc prototype spike: boot the published browser harness against the
// mainnet passthrough specifier, wrap worker.fetch in a viem custom transport
// (the same seam a scaffold-eth-2 wagmi config would use), and read real
// mainnet state through the sandboxed worker.
//
// The RPC URL arrives via ?rpc= so no API key ever lives in this repo.

import { AnonRpcWorker } from "@anon-rpc/browser-harness";
import { createPublicClient, custom, formatEther } from "viem";
import { mainnet } from "viem/chains";

// The EF's live mainnet specifier (currently pins the passthrough worker).
const SPECIFIER = "0x4fd77be300f31c5fe6ab266d35d27750a3478d27";
// Beacon deposit contract: a huge, always-moving balance to read.
const BEACON = "0x00000000219ab540356cBB839Cbe05303d7705Fa";
// keccak256 of the pinned bundle, as verified in ../README.md.
const EXPECTED_HASH = "0x194f04bde4925f6bbb0bd8bdfceca7251125eaa0664ce3c0c25dce2a1545338d";

const logEl = document.getElementById("log");
function log(line) {
  logEl.textContent += line + "\n";
  console.log(line);
}

function jsonRpcVia(fetchImpl, url) {
  let id = 0;
  return async (method, params = []) => {
    const resp = await fetchImpl(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: ++id, method, params }),
    });
    const body = await resp.json();
    if (body.error) throw new Error(body.error.message ?? "RPC error");
    return body.result;
  };
}

async function main() {
  const rpcUrl = new URLSearchParams(location.search).get("rpc");
  if (!rpcUrl) throw new Error("pass ?rpc=<mainnet RPC URL>");

  // --- boot: bootstrap RPC reads the specifier, harness verifies the bundle ---
  const t0 = performance.now();
  log(`booting harness against specifier ${SPECIFIER} …`);
  const bootstrapCall = jsonRpcVia(fetch, rpcUrl);
  const worker = new AnonRpcWorker({
    address: SPECIFIER,
    preExisting: {
      rpcProvider: { request: ({ method, params }) => bootstrapCall(method, params ?? []) },
    },
  });
  await worker.ready;
  const bootMs = Math.round(performance.now() - t0);
  log(`worker ready in ${bootMs} ms — bundle keccak-verified, running sandboxed`);

  // --- the seam: worker.fetch as a viem transport (what wagmi would consume) ---
  const workerCall = jsonRpcVia(worker.fetch, rpcUrl);
  const client = createPublicClient({
    chain: mainnet,
    transport: custom({ request: ({ method, params }) => workerCall(method, params ?? []) }),
  });

  // --- reads through the sandboxed worker ---
  const chainId = await client.getChainId();
  log(`eth_chainId → ${chainId}`);

  const block = await client.getBlockNumber();
  log(`eth_blockNumber → ${block}`);

  const wei = await client.getBalance({ address: BEACON });
  log(`beacon deposit balance → ${formatEther(wei).split(".")[0]} ETH`);

  // Ouroboros check: read the specifier's own workerHash() through the worker
  // it pinned, and compare with the hash we verified out-of-band.
  const hash = await client.call({ to: SPECIFIER, data: "0x3898587d" }); // workerHash()
  const match = hash.data === EXPECTED_HASH;
  log(`workerHash() via worker → ${hash.data} (${match ? "matches" : "MISMATCH vs"} out-of-band pin)`);

  window.__RESULT__ = {
    bootMs,
    chainId,
    block: block.toString(),
    beaconEth: formatEther(wei).split(".")[0],
    workerHash: hash.data,
    hashMatches: match,
  };
  document.title = "anon-rpc spike: OK";
  log("DONE");
}

main().catch((e) => {
  window.__ERROR__ = String(e?.stack ?? e);
  document.title = "anon-rpc spike: ERROR";
  log("ERROR: " + e.message);
});
