# anon-rpc prototype spike

Proves the integration seam described in [../INTEGRATION.md](../INTEGRATION.md): the
published `@anon-rpc/browser-harness@0.3.0` booted against the **live mainnet specifier**
(`0x4fd77be300f31c5fe6ab266d35d27750a3478d27`), with `worker.fetch` wrapped in a **viem
`custom()` transport** — the exact shape a scaffold-eth-2 wagmi config consumes. All reads
below travel through the hash-verified, sandboxed worker (today: the passthrough, so
plumbing not anonymity).

## Run it

```bash
npm i
npx esbuild src/main.js --bundle --format=esm --outfile=dist/main.js
RPC_URL=https://eth-mainnet.g.alchemy.com/v2/<KEY> node probe.mjs   # headless verify
# or serve the dir and open index.html?rpc=<url> in a browser
```

No API key lives in this repo — the RPC URL is passed at runtime (`?rpc=` / `RPC_URL`).

## Verified result (2026-07-30, first run)

```
worker ready in 431 ms — bundle keccak-verified, running sandboxed
eth_chainId → 1
eth_blockNumber → 25650147
beacon deposit balance → 88932981 ETH
workerHash() via worker → 0x194f04…338d (matches out-of-band pin)
PASS
```

The last read is the fun one: the specifier's own `workerHash()` queried *through* the
worker it pinned, matching the hash we verified out-of-band in the research.

## Files

- `src/main.js` — boot + viem transport + reads (~100 lines; the whole integration).
- `index.html` — minimal page, logs to a `<pre>`.
- `probe.mjs` — serves the build, drives the machine's cached headless Chromium, asserts
  `chainId === 1` and the hash match (same launch strategy as clawd-harness's uiprobe).
