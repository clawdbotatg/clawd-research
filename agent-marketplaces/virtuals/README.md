# One Dollar Audit on Virtuals ACP

- Seller agent "One Dollar Audit": id `01a1364e-2662-77df-aea7-fa922d852153`, wallet `0x0b4e9e5460d14ba7fc96691ded5463490d333624`, offering "Smart Contract Audit" $1, 480 min SLA.
- Test buyer "ODA Test Buyer": id `01a13667-c396-7984-89ab-a27a42a3ac8d`, wallet `0x7fe02617dcf1740147e6cded78290b00bd4f3463`.
- Owner: atg.eth. Both signers are "unrestricted" — Virtuals' "restricted" (ACP_ONLY) policy blocked set-budget and create-job (2026-10-13).
- CLI config: seller `~/.config/acp`, buyer `~/.config/acp-buyer` (signer keys in the macOS keychain).

## Run

    AUDIT_PAYER_PK=<WALLET_RESEARCHER_PRIVATE_KEY from .env.clawd> node worker.mjs   # seller: quote → buy x402 audit → submit report
    ACP_CONFIG_DIR=~/.config/acp-buyer node buyer.mjs                               # graduation test jobs (10 total)

Worker pays $1 per audit from the researcher wallet `0x1d26…cbce` via onedollaraudit.com x402.

## Graduation
10 successful sandbox jobs (3 in a row) with our own test buyer, then "Graduate Agent" on the agent page → Virtuals reviews in ~7 working days.

## TODO
Worker runs on Austin's laptop (nohup). For real buyers it must move to an always-on box.
