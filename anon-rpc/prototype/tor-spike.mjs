// tor-js spike: real Tor circuits from plain JS (Arti compiled to WASM), then
// the money shot — an Ethereum JSON-RPC read whose origin is a Tor exit node.
//
// Node.js needs no KPS gateway (it has raw TCP to reach relays directly); in a
// browser the same TorClient API needs `gateway: "ip:port:certhash"`.
//
// The RPC target is deliberately KEYLESS (publicnode): routing a keyed Alchemy
// URL through Tor would re-identify the app — see ../INTEGRATION.md, "the
// API-key trap". This is the anon lane, not the normal lane.
//
// Usage: node tor-spike.mjs
import { TorClient } from "tor-js/wasm-file";

const RPC = "https://ethereum-rpc.publicnode.com";

const t0 = Date.now();
const client = new TorClient({ logLevel: "warn" });

// Where do we appear from *without* Tor?
const clearIp = (await (await fetch("https://check.torproject.org/api/ip")).json()).IP;

await client.ready();
console.log(`tor bootstrap: ${((Date.now() - t0) / 1000).toFixed(1)}s`);

// 1. Prove the circuit: torproject's own checker.
const check = await (await client.fetch("https://check.torproject.org/api/ip")).json();
console.log(`clearnet IP: ${clearIp}`);
console.log(`via tor:     ${JSON.stringify(check)}`);
if (!check.IsTor || check.IP === clearIp) {
  console.error("FAIL: not exiting through Tor");
  process.exit(1);
}

// 2. The point of it all: an Ethereum read the RPC provider can't tie to us.
let id = 0;
const rpc = async (method, params = []) => {
  const r = await client.fetch(RPC, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: ++id, method, params }),
    signal: AbortSignal.timeout(60_000),
  });
  const body = await r.json();
  if (body.error) throw new Error(body.error.message);
  return body.result;
};

const t1 = Date.now();
const chainId = parseInt(await rpc("eth_chainId"), 16);
const block = parseInt(await rpc("eth_blockNumber"), 16);
const wei = BigInt(await rpc("eth_getBalance", ["0x00000000219ab540356cBB839Cbe05303d7705Fa", "latest"]));
console.log(
  `eth via tor: chainId=${chainId} block=${block} beacon=${wei / 10n ** 18n} ETH ` +
    `(3 reads in ${Date.now() - t1} ms, exit ${check.IP})`,
);

if (chainId !== 1) process.exit(1);
console.log("PASS");
client.close();
process.exit(0);
