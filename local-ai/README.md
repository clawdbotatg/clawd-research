# local-ai — DGX Spark clustering + price outlook

*Research date: 2026-08-03. Prompted by 0xsero's advice that a good local setup = two DGX
Sparks. Questions: how do they pair? Do they become one machine? Can you do 4? And where
does the price go over the next couple of years?*

---

## TL;DR

- **Pairing = one ~$160–180 QSFP cable** between the ConnectX-7 ports on each box.
  200 Gbps RDMA (RoCE v2). No dock, no special chassis.
- **They do NOT become one machine.** Two separate computers, two OS images, doing
  distributed inference over the cable. "256GB unified" is marketing for "you can shard a
  model across both." The cross-box link is ~25 GB/s vs 273 GB/s local memory bandwidth.
- **Yes, you can do 4** — this became official in NVIDIA's April–June 2026 software.
  2–3 boxes direct-cable, 4 boxes need a 200GbE switch (~$1,100 MikroTik) → 512GB aggregate.
- **Price has gone UP, not down**: $3,999 launch (Oct 2025) → **$4,699 (Feb 2026)**, blamed
  on the global memory shortage. Forecast: flat-to-up through 2027 (DRAM crunch widens),
  falling in 2028 when the Rubin-based successor + new memory fab capacity land.
- **Honest take**: 2x Spark today = ~$9,400 at the top of a shortage cycle, ~12 months
  before a successor that fixes its one real weakness (memory bandwidth). The rational
  plays are OEM GB10 deals at $3,000–3,500, or waiting for fall-2026 "RTX Spark" Windows
  boxes (~$2,500–2,900, near-identical silicon).

---

## 1. How two Sparks "pair"

Every DGX Spark (and every OEM GB10 clone) has a **dual-port ConnectX-7 NIC** with two
QSFP cages, 200 Gbps each. Pairing two boxes:

1. One passive DAC cable, any port to any port. NVIDIA-certified stacking cable is
   **$179.99 at Micro Center** (Amphenol NJAAKK-N911 / Luxshare QSFP112 400G DAC);
   a generic 200G QSFP56 DAC from FS.com works for much less.
2. Static IPs + SSH keys between the boxes — ~1 hour manual via NVIDIA's
   [connect-two-sparks playbook](https://github.com/NVIDIA/dgx-spark-playbooks), or
   automated by **NVIDIA Sync "Cluster Assistant"** (shipped April 2026 system software):
   auto-discovers nodes, validates link speed, configures interfaces + SSH.
3. Run distributed inference on top: vLLM tensor-parallel (TP=2) + Ray, TensorRT-LLM,
   SGLang, or llama.cpp RPC.

**The gotcha nobody tells you:** on GB10 the ConnectX-7 hangs off two independent PCIe
Gen5 x4 links, so **one physical QSFP port shows up as two Linux interfaces**, each capped
at ~110 Gbps. You only get the full ~200G (196 Gbps measured, July 2026 field report) by
configuring **both** interfaces and letting NCCL alternate across them. Configure one and
you've silently halved the fabric.

**Software maturity note:** the native NVIDIA stack was genuinely broken on GB10 into
early 2026 (vLLM+Ray GPU-type mismatch; TensorRT-LLM NVFP4 kernels compiled for Hopper,
not Spark's SM121) — early adopters fell back to llama.cpp RPC and it *beat* NVIDIA's own
published numbers. By mid-2026 vLLM TP=2 is verified working. The stack matured a lot
between Dec 2025 and mid-2026; expect residual sharp edges.

## 2. Do they become one machine? No.

Precisely: it's a **2-node distributed cluster**, not a single system image.

- Within one box: 128GB genuinely unified (CPU+GPU coherent, NVLink-C2C).
- Across boxes: **no shared address space**. Models bigger than 128GB get **sharded**
  (tensor / pipeline / expert parallel), with activations and KV traffic crossing the
  200Gb link.
- Scale check: 200 Gbps ≈ 25 GB/s ≈ **9% of one node's local memory bandwidth**. Fine for
  exchanging activations at these model sizes; nothing like memory pooling.
- NVIDIA's own Cluster Assistant docs say it configures networking + SSH and "does not
  set up workloads" — orchestration (Ray/Slurm/K8s) is your problem.

What 2x buys you is **capacity, not speed**: a small model does NOT run 2x faster on two
Sparks (TP overhead over Ethernet eats the gain single-stream; batching recovers it).
What it unlocks is models that don't fit in 128GB:

| Model | 1x Spark | 2x Spark |
|---|---|---|
| gpt-oss-120B MXFP4 | ~35 tok/s | ~55–75 tok/s (batched gains) |
| Qwen3-235B-A22B Q4 (134GB) | 1.8 tok/s (thrashing) | **12.5 tok/s** |
| Qwen3.5-397B INT4 | doesn't fit | **~27 tok/s** |
| Llama 3.1 405B NVFP4 | doesn't fit | fits (NVIDIA's flagship claim) |
| DeepSeek R1 671B Q4 (~380GB) | no | **no** — needs the 4-node/512GB tier |

## 3. Can you do 4 instead of 2? Yes (as of mid-2026)

The launch-era "NVIDIA supports only 2" is obsolete. Official support since the
April–June 2026 software releases:

- **2 nodes**: direct, 1 cable.
- **3 nodes**: direct **ring** using both QSFP ports per node, 3 cables, no switch.
- **4 nodes**: **switch required**, 512GB aggregate. Cluster Assistant caps at 4 devices.

Switch economics: the community favorite is the **MikroTik CRS804-4DDQ** (4× 400G ports,
each breaking out to 2× 200G) at **~$1,100 street** — enough for up to 8 Sparks. So a
4-node fabric is ~$1,100 switch + 4 cables ≈ **$1,800 on top of ~$16–19K of Sparks**.
Hobbyists have built switchless 4-node meshes with SR4 transceivers + MPO breakouts, but
with only 2 ports per box it can't be full-bandwidth everywhere; the supported answer is
the switch.

(Trivia: EXO Labs' famous cluster demo was NOT 4 Sparks — it was 2× Spark doing prefill +
an M3 Ultra Mac Studio doing decode, playing each machine to its strength: Spark has ~4x
the Mac's compute, the Mac has 3x the Spark's memory bandwidth. 2.8x speedup vs Mac alone.)

## 4. The bottleneck to understand before buying

**Decode speed is memory-bandwidth-bound, and the Spark only has 273 GB/s LPDDR5x.**
Its compute is wildly oversized relative to that (~100 FP16 TFLOPS vs M3 Ultra's ~26), so:

- **Prefill** (compute-bound): Spark crushes — ~4x an M3 Ultra on long prompts.
- **Decode** (bandwidth-bound): Spark loses — M3 Ultra's 819 GB/s generates ~3x faster.
  Textbook math: 70GB of FP8 weights ÷ 273 GB/s ≈ 3.9 tok/s ceiling ≈ the measured 2.7.

Value comparison at the 2x-Spark price point (~$9,400 post-hike):

- **Mac Studio M3 Ultra 256GB (~$5,600)**: same capacity class, ~3x bandwidth → faster
  single-stream decode on big models; but far slower prefill, no CUDA, MLX/GGUF tooling.
  The 512GB Ultra (~$9,500) fits DeepSeek R1 Q4 **on one box** — no 2-Spark config can.
- **4× used 3090 (~$3–4K)**: 96GB VRAM at ~936 GB/s each — much faster tokens/$ for
  models that fit, but can't touch 235B+, and it's a 1.5kW consumer-rig science project.
- **The honest Spark pitch**: CUDA-native 256–512GB capacity at 100–400W in a shoebox.
  You buy it for model *size* + the NVIDIA software path (NVFP4, TRT-LLM, fine-tuning
  playbooks), not tokens/sec per dollar.

## 5. Price: history and 2026–2028 trajectory

### What's happened so far

| Date | Event | Price |
|---|---|---|
| Jan 2025 (CES) | Announced as "Project DIGITS" | ~$3,000 |
| Oct 15, 2025 | Ships as DGX Spark Founders Edition (128GB/4TB) | **$3,999** |
| **Feb 23, 2026** | NVIDIA raises MSRP +$700 citing "memory supply constraints" | **$4,699** |
| Jul 2026 | Street: Amazon 3P $4,650, Newegg PNY $4,724, frequent OOS | ~$4,650–4,725 |

OEM GB10 clones (identical silicon, cluster interchangeably) are the value floor:
**MSI EdgeXpert / ASUS Ascent GX10 1TB at ~$3,000–3,100**; Dell/Acer/Gigabyte ~$3,700–4,000;
HP ZGX Nano the outlier at ~$6,000. A June 2026 Amazon deal put the ASUS at **$3,499** —
those deals recur.

### Why it went UP (the answer to "Moore's law vs demand")

Neither Moore's law nor Spark-specific demand is the driving force — **the global DRAM/
LPDDR5X supercycle is**. LPDDR5X contract prices rose ~90% QoQ in Q1 2026 and ~80% again
in Q2; AI datacenters may consume ~70% of world memory output in 2026. Everyone repriced:
Jetson +33–101% (July 2026), RTX 5090 street >$4,300, Apple raised the 96GB Mac Studio
$3,999→$5,299, Framework +$460. A 128GB-unified-memory prosumer box is exactly the product
that loses memory allocation to datacenter Grace/HBM — NVIDIA repriced rather than scaled
supply. TrendForce sees the DRAM gap **widening in 2027**, normalizing 2028–2029.

### The downward pressure queued up behind it

- **"RTX Spark" (Computex 2026)**: NVIDIA+MediaTek N1/N1X Windows boxes shipping fall 2026
  — Jensen called N1X "technically very close to GB10" (same-class 20 Arm cores, Blackwell
  GPU, up to 128GB unified, 1 PFLOP FP4) at an estimated **$1,800–2,900**. Near-identical
  silicon at ~60% of the DGX price, differing mainly in Windows vs DGX OS.
- **True successor**: **Vera Rubin Spark, 2027–2028, on LPDDR6** — which fixes the one real
  weakness (bandwidth) and will make GB10 look sharply dated overnight.
- **Competition**: Strix Halo 128GB boxes at $2,000–3,500 today; AMD "Medusa Halo" is the
  2027 threat; M5 Ultra Mac Studio ~Oct 2026.

### Verdict

- **New prices**: flat at $4,699 with mild *upside* risk through 2026 (DRAM still rising;
  NVIDIA has shown it reprices upward mid-cycle) — but capped by RTX Spark at ~$2,900.
  2027: street erosion via OEM deals to ~$3,500–4,000. **2028: real drops** ($2,500–3,500
  new-old-stock) when Rubin Spark ships and memory fabs catch up.
- **Used/resale**: unusually strong right now (75–90% of MSRP — the shortage put a
  commodity floor under any 128GB LPDDR5X machine, and the MSRP hike marked up the whole
  installed base). Best exit window: now through mid-2027. After Rubin Spark saturates:
  ~$2,000–2,800 by end-2028.
- **Appreciation scenario** (the "will it go up like 3090s/4090s?" question): low
  probability, ~10–15%. The 4090 appreciated because nothing else offered its VRAM after
  production ended. The Spark has no such moat — Strix Halo matches its capacity for less
  and Macs beat its bandwidth. It would take the shortage worsening beyond forecasts AND
  Rubin slipping to 2028+ AND a local-LLM demand spike.

### Practical read for Austin

Buying 2x FE today = ~$9,400 + $180 cable, at the top of the shortage cycle, ~12 months
before the bandwidth-fixed successor. If the goal is the 0xsero setup:

1. **Cheapest correct version of it**: 2× OEM GB10 (MSI/ASUS, watch for $3,000–3,500
   deals) + one $160 FS.com DAC ≈ **$6,200–7,200** for the identical 256GB CUDA cluster.
2. **If decode speed for big dense models matters more than CUDA**: a single Mac Studio
   M3 Ultra 512GB (~$9,500) runs DeepSeek R1 Q4 on one box, faster per token.
3. **If you can wait**: fall-2026 RTX Spark boxes (~$2,500–2,900) or the 2027 Rubin Spark
   are both strictly better value stories; the DRAM crunch is the only force pushing the
   other way.

---

## Sources

Clustering: [NVIDIA Spark Stacking docs](https://docs.nvidia.com/dgx/dgx-spark/spark-clustering.html) ·
[dgx-spark-playbooks](https://github.com/NVIDIA/dgx-spark-playbooks) ·
[Sync Cluster Assistant](https://docs.nvidia.com/sync/latest/cluster-assistant.html) ·
[NVIDIA multi-node blog, Jun 2026](https://developer.nvidia.com/blog/run-local-ai-agents-with-faster-models-and-multi-node-clustering-on-nvidia-dgx-spark/) ·
[LMSYS Spark review](https://www.lmsys.org/blog/2025-10-13-nvidia-dgx-spark/) ·
[EXO Sparks+Mac demo](https://blog.exolabs.net/nvidia-dgx-spark/) ·
[Qwen3-235B 2-node field report](https://forums.developer.nvidia.com/t/dgx-spark-multi-node-llm-inference-report-for-qwen3-235b-model/355126) ·
[dual-interface CX-7 measurement, Jul 2026](https://note.com/gb10_tsurumitsu/n/n1c5efc62a92e) ·
[Corti 2-Spark write-up](https://corti.com/two-sparks-one-cluster-why-stacking-nvidia-dgx-spark-units-unlocks-local-frontier-scale-inference/) ·
[96 hours with dual Sparks](https://alooftwaffle.substack.com/p/96-hours-with-dual-dgx-sparks-and) ·
[MikroTik CRS804 @ STH](https://www.servethehome.com/mikrotik-crs804-ddq-announced-4-port-400gbe-switch/)

Pricing: [NVIDIA 2/23/26 price-change announcement](https://forums.developer.nvidia.com/t/2-23-2026-price-change-announcement/361713) ·
[Tom's Hardware on the hike](https://www.tomshardware.com/desktops/mini-pcs/nvidia-dgx-spark-gets-18-percent-price-increase-as-memory-shortages-bite-founders-edition-now-usd4-699-up-from-usd3-999) ·
[TrendForce Q2'26 mobile DRAM](https://www.trendforce.com/presscenter/news/20260514-13044.html) ·
[TrendForce 2027 outlook](https://www.trendforce.com/presscenter/news/20260730-13158.html) ·
[Jetson price hikes, Jul 2026](https://www.cnx-software.com/2026/07/22/nvidia-increases-the-price-of-jetson-modules-and-devkits-by-up-to-101/) ·
[RTX Spark roadmap (Rubin 2027, Feynman 2029)](https://videocardz.com/newz/nvidia-confirms-rtx-spark-roadmap-with-rubin-in-2027-and-rosa-feynman-in-2029) ·
[PCWorld RTX Spark pricing](https://www.pcworld.com/article/3156219/the-price-of-nvidia-rtx-spark-pcs-is-going-to-hurt.html) ·
[InsiderLLM GB10 box comparison](https://insiderllm.com/guides/gb10-boxes-compared/) ·
[GB10 EU price tracker](https://rubentorney.com/blog/en/dgx-spark-asus-gx10-mini-pc-ia-nvidia-gb10.html)
