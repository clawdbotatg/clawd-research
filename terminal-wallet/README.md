# Terminal Wallet (terminal-wallet.com)

Checked 2026-10-04. Source: tweet by @alexanderchopan quoting @RAILGUN_Project's shoutout.
Repo: https://github.com/Terminal-Wallet/terminal-wallet-cli (cloned and read at v2.0.2, 806e804).

## What it is
- Open-source TypeScript CLI/TUI wallet built on the RAILGUN SDK.
- Public `0x` addresses and private `0zk` addresses: shield, unshield, private transfers, private swaps (0x API), public sends/swaps.
- Private txs go out through Waku broadcasters (RAILGUN relayers), so no public gas address is linked.
- Chains: Ethereum, BNB, Polygon, Arbitrum, Sepolia.
- v2.0 (Aug 2026): "terminal deck" UI, private DeFi positions (Morpho), EIP-7702 ephemeral accounts for relay-adapt calls.
- Ships as Linux/macOS/Windows binaries (Node app packed with caxa, built in GitHub Actions).

## Who
- Repo since Aug 2023. 93 commits, 96 stars, 21 forks. Essentially one dev: `linkismissing`.
- The tweet author (accountless.eth, ex-Trust/MetaMask/Pimlico) just reposted it. No sign he builds it.
- License mismatch: repo says GPL-3.0, package.json says LGPL-3.0-or-later.

## Security notes
1. **Remote config is one EOA.** On boot the wallet reads a JSON string from
   `0x5e982525d50046A813DBf55Ae72a3E00e99fbC94` (`getConfig()`), owned by EOA
   `0x21f9420691Dd2a6AB1c3e6A35C55Bf02046a2691` (nonce 10, ~0.25 ETH).
   That JSON sets: RPC list per chain, POI aggregator URL, trusted broadcaster
   fee signers, blacklist, min version, and a 0x API key.
   Signing stays local, so this key can't take funds directly. But it can point
   users at logging RPCs or chosen broadcasters, which hurts privacy.
   Override with `REMOTE_CONFIG_RPC` and per-network RPCs in `twallet.config.json`.
2. **Default RPCs are all public** (publicnode, drpc, blastapi, cloudflare, merkle).
   The remote config itself is fetched from publicnode by default. For a privacy
   wallet that leaks IP ↔ address links. Use your own RPC.
3. **Release signing stopped.** README says SHA256SUMS are GPG-signed. v1.3.x had
   `SHA256SUMS.sha.sig`; v1.5.0 and later (incl. 2.0.2) do not. Website torrent still
   points at 1.3.4. Build from source if you care.
4. **Key storage is fine.** Seed encrypted under scrypt (N=2^17, r=8, p=1) with a
   random per-keychain salt. Min password 8 chars.
5. **Pre-release deps:** `@railgun-community/wallet 10.10.0-rc.1`, cookbook and
   broadcaster client are also RCs.
6. **Stale on-chain config:** says current/min version 1.5.0 while 2.0.2 is out.
7. **Open issues mostly unanswered:** wallet creation fails (#36, 08-28, 0 replies),
   unshield to base token reverts (#21), Sepolia swap chain-id error (#37).

## Verdict
Real, long-running RAILGUN client, one-person project. Fine to try with small
amounts: build from source, set your own RPCs and `REMOTE_CONFIG_RPC`.
Not something to hold real size in without a closer audit of the 7702 relay-adapt path.

Live remote config dump (2026-10-04) — 5 trusted fee signers, POI = ppoi.fdi.network,
chains 1/56/137/42161/11155111, all public RPCs.
