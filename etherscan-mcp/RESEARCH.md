# Etherscan MCP — researched + live-tested 2026-08-31

Announced by @etherscan (tweet 2094398659475784054). Official hosted MCP server
for onchain data. We tested it raw over the wire with our real free-tier API key.
**It works.** Details and gotchas below.

## What it is

- Endpoint: `https://mcp.etherscan.io/mcp` (streamable HTTP, server: `etherscan-mcp v2.0.0`, MCP protocol 2025-03-26)
- Auth: `Authorization: Bearer <ETHERSCAN_API_KEY>` — no OAuth, just your normal API key
- Read-only. Every tool call burns your normal API quota (free tier: 3 calls/sec — we hit that limit in testing)
- Docs: https://docs.etherscan.io/build-with-ai/mcp
- Etherscan warns: only ONE official server exists — marketplace copycats are credential-theft bait

## Add to Claude Code

```bash
claude mcp add --transport http etherscan https://mcp.etherscan.io/mcp \
  --header "Authorization: Bearer $ETHERSCAN_API_KEY"
```

Key lives in several of our foundry `.env` files (e.g. `~/clawd/clawd-pfp/packages/foundry/.env`).

## The 20 tools

| Category | Tools | Free tier? |
|---|---|---|
| Balances | get_native_balance | ✅ |
| Transactions | get_transactions, get_internal_transactions, get_transaction_by_hash, get_transaction_receipt, get_transaction_receipt_status, get_transaction_status | ✅ |
| Transfers | get_token_transfers (erc20/721/1155 via `standard` param) | ✅ |
| Tokens | get_token_info, get_token_balances (w/ USD values), get_token_top_holders | info ✅ · balances/holders ❌ Pro |
| Contracts | get_contract_source, get_contract_abi, get_contract_creation | ✅ |
| Address intel | get_address_labels (nametags), get_funded_by (first funder) | ❌ labels = "API Exclusive", funded_by = Pro |
| Misc | get_gas_oracle, get_block_by_timestamp, get_supported_chains, get_logs | ✅ |

## Live test results (our free key)

- ✅ `get_native_balance` vitalik.eth → 6.642 ETH, matches explorer
- ✅ `get_transactions` → full normal-tx objects, latest-first, clean JSON
- ✅ `get_gas_oracle` → safe/propose/fast + base fee (~0.19 gwei at test time)
- ✅ `get_contract_source` USDC → full verified Solidity source (WARNING: huge tool
  result, whole source inlined — token bomb for agent context)
- ✅ `get_supported_chains` → 61 chains listed with status
- ✅ `get_transaction_receipt_status` → works
- ❌ `get_address_labels`, `get_funded_by`, `get_token_balances`, `get_token_top_holders`
  → paid-plan gated (the tools Etherscan is marketing hardest — "address
  intelligence", USD balances — are exactly the ones a free key can't use)
- ❌ **Base (chainid 8453) balance refused on free tier**: "Free API access is not
  supported for this chain. Please upgrade." Free key ≠ full 60-chain coverage,
  despite the "60+ chains" pitch.
- Unauthenticated → clean 401 with instructions.

## Gotchas found

1. **Inconsistent param typing**: `chainid` must be a *string* ("8453"), but
   `limit` on top-holders must be a *number*. Zod validation rejects the wrong
   type with a verbose error. Agents will trip on this.
2. **3 req/sec free rate limit** surfaces as a NOTOK tool error mid-conversation;
   an agent doing parallel calls will hit it instantly.
3. **Contract source responses are enormous** — no truncation server-side.
4. Session handshake required: initialize → capture `Mcp-Session-Id` response
   header → send it on every subsequent call.

## Verdict

Solid for mainnet/testnet reads on a free key: balances, txs, logs, ABIs,
source, gas. The differentiated stuff (labels, funded-by, USD portfolios, top
holders, most L2s) is paywalled. For our own agents we already route chain reads
through Alchemy RPCs; this MCP's unique value over raw RPC is verified
source/ABI lookup and (if we ever pay) address intelligence.

Raw test scripts: session scratchpad (`mcp_test.sh`, `mcp_call.sh`) — plain
curl JSON-RPC, trivial to recreate from the snippets above.
