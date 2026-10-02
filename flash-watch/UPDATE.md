# Flash Price Watch — weekly update

Dashboard: https://claude.ai/artifact/Jb3YQVqJdF7QZXcxVkcY5p
Data lives in the artifact's database (ArtifactData tool). The page renders whatever is there.

Do these steps, then stop. Never republish the page. Only write to the database.

1. **Drive prices.** Fetch https://cheapestssd.com/8tb-ssd/ (Amazon US prices).
   Write one doc per item to `prices`, id `<item>_<YYYY-MM-DD>` (today):
   `{item, date, usd, note}`. Items: `sn850x` (WD Black SN850X 8TB),
   `pro9100` (Samsung 9100 Pro 8TB), `two4tb` (the page's cheapest 2×4TB total, note = drive name).
   Skip an item the page doesn't list.
2. **Spot prices.** Fetch https://www.dramexchange.com/ and read the "NAND Wafer Spot" table.
   Write `spot/<last-update date>`: `{date, tlc512, tlc256}` = session averages.
3. **Contract forecast.** Search for the newest TrendForce NAND Flash contract price
   forecast. If it covers a quarter not in `contract`, or revises one, write
   `contract/<YYYYQn>`: `{order:"YYYYQn", q:"nQyy", lo, hi, pub}` (lo/hi = % QoQ; negative if falling).
4. **Stocks.** Run `python3 stocks.py` in this folder. It writes `seed/stock_*.json`.
   Then `set` each into `stocks/<ID>` with `file_path` (IDs: MU SNDK LRCX SAMSUNG HYNIX KIOXIA).
5. **Status.** `set meta/status`: `{updated: today, note: one plain sentence on what changed}`.

Use one `batch` call for all writes.

6. **Ping.** If the newest contract midpoint is ≤ 5%, or SN850X is down 10%+ from its
   price 8 weeks ago, email Austin (Gmail connector), subject
   "Flash prices turning", with the numbers + link.

Runs as a cloud routine every Monday 9:03am Denver (`3 15 * * 1` UTC):
https://claude.ai/code/routines/trig_01JJiyqPXxJ3ARwdP2KmN237
The routine's prompt is self-contained (no repo checkout); this file is the reference copy.
