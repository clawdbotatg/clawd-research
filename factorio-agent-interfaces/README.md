# State of the art: interfacing with Factorio (mid-2026)

*Deep-research report, 2026-07-15. 20 sources fetched, 96 claims extracted, top 25
adversarially verified (3-vote panels): 24 confirmed, 1 refuted. Method: fan-out
web search → source fetch → claim extraction → adversarial verification → synthesis.*

## TL;DR

The state of the art is the **structured Lua-mod + RCON stack**, not screen capture
or memory hooks. Factorio ships a first-class runtime Lua API, a free headless
dedicated-server mode, and built-in RCON with a reply channel — together giving
external software full read/write access to game state. The dominant research
layer on top is the **Factorio Learning Environment (FLE)** (NeurIPS 2025 Datasets
& Benchmarks), where agents act by writing Python in a REPL against a ~23-method
tool API and observe structured state objects, not pixels. FLE ships an MCP server
that lets **Claude Code play Factorio** (livestreamed on Twitch). If you're
building an agent today: run the headless server in Docker, drive it via
RCON-injected Lua, and build on FLE rather than reinventing the interface.

## 1. Built-in interfaces (the substrate)

**Runtime Lua API** — [lua-api.factorio.com](https://lua-api.factorio.com/latest/index-runtime.html)
(covering game 2.1.x) is the game's first-class programmatic surface. The `game`
object (`LuaGameScript`) is the main entry point; `LuaEntity`, `LuaPlayer`,
`LuaSurface`, `LuaForce` give direct read/write access to entities, players,
terrain, and factions — mutating methods (`create_entity`, `set_recipe`,
`destroy`) and observation methods (`find_entities_filtered`, `get_tile`). A
Lua-layer agent can both observe and act with no screen capture. *(verified 3-0)*

**Headless server + RCON** — `factorio --start-server FILE --rcon-port N
--rcon-password X` runs a GUI-less dedicated server with native RCON
([wiki: command line parameters](https://wiki.factorio.com/Command_line_parameters)).
The Lua global `rcon` ([`LuaRCON`](https://lua-api.factorio.com/latest/classes/LuaRCON.html))
with `rcon.print(message)` lets injected Lua reply to the calling RCON client.
The universal round-trip every framework builds on:

```
RCON client  →  /silent-command <lua that ends in rcon.print(serialized state)>
game         →  structured data back on the same connection
```

**Key limitation:** this is synchronous request/reply only — the game cannot push
unsolicited events to an RCON client. Polling (or a mod writing to files/sockets)
is required for event-driven designs. *(verified 3-0 ×5)*

**Replay/save formats** — notably, *no* surviving verified claims. Nobody
prominent appears to be parsing saves/replays directly for agent I/O; it remains
an open corner (see Open questions).

## 2. Research environments: FLE is the center of gravity

The **[Factorio Learning Environment](https://github.com/JackHopkins/factorio-learning-environment)**
([arXiv 2503.09617](https://arxiv.org/abs/2503.09617), NeurIPS 2025 Datasets &
Benchmarks) is the dominant open-source benchmark: long-term planning, program
synthesis, and resource optimization, with exponentially scaling challenges from
basic automation to factories processing millions of units/sec — positioned as a
non-saturating, open-ended benchmark (tracked by Epoch AI). *(3-0 ×2)*

Architecture *(3-0 ×4)*:

- Python client ↔ Lua server inside the game, **RCON over TCP**, headless server.
- Agents **write Python in a REPL loop** against a tool API (~10 observation +
  13 action methods), accumulating state in a persistent namespace (episodic
  symbolic memory).
- Observations are structured `Observation` objects (entities, inventory,
  research, flows, optional `map_image`) plus stdout/stderr — **not raw pixels**.

Since **v0.3.0 (Oct 2025)** *(3-0 ×3)*:

- **Fully headless** — no game client needed, only the free headless server
  (typically Docker). Measured 1.75× speedup, ~218 ops/sec; massively parallel
  experiments feasible.
- **OpenAI-Gym-conformant** (`reset`/`step`/registry). Caveat: the action space
  is still code synthesis, so off-the-shelf discrete-action RL needs adaptation.
- Optional **headless pixel renderer** for multimodal research.

Actively maintained: **v0.4.3 shipped 2026-04-06** (Inspect AI sandbox evals),
v0.4.0 migrated to Factorio 2.0 (2.0.73+ for rendering), commits through June
2026. *(3-0)*

## 3. Agent projects and their interface layers

| Project | Interface layer |
|---|---|
| **FLE agents** (paper + leaderboard) | Python REPL → RCON → Lua; structured obs |
| **[claude-code-plays-factorio](https://github.com/JackHopkins/claude-code-plays-factorio)** | FLE **MCP server**: read-only `fle://` resources (status, entities, inventory, position, recipe, metrics, render) + tools `execute(code)`, `commit`, `restore`, `render` — git-like save-state rollback as a first-class agent capability. Livestreamed at twitch.tv/playsfactorio. Built by the FLE team (not Anthropic). *(3-0 ×4 + 2-1)* |
| **[factorioctl](https://github.com/MarkMcCaskey/factorioctl)** (Rust CLI + MCP) | Pure Lua-over-RCON to a headless server; no vision, no hooks. Self-described weekend hobby project — evidence the pattern is accessible, not that the tool is mature. *(3-0)* |
| Others surfaced (not fully verified) | `airi-factorio` (YOLO vision + LLM hybrid), SUPCON's MQTT/Unified-Namespace industrial-IoT bridge, `factorio-ai-companion` (Lua mod + RCON + Bun MCP server), the "AI Player" mod on the mod portal (in-game LLM agent) |

Note on `fle://render`: it returns an API-generated visualization from structured
state — not client screen capture. *(the 2-1 vote)*

**Benchmark results are thin.** The official leaderboard scores six paper-era
models (Claude 3.5-Sonnet, Gemini-2-Flash, GPT-4o, Llama-3.3-70b, DeepSeek-v3,
GPT-4o-Mini) on five metrics (production score, milestones, automation
milestones, lab-task success, most complex item). Best lab-task success ~21.9%;
most complex item crafted: plastic bar — agents remain far from "beating" the
game. The specific claim that Claude 3.5-Sonnet tops the board was **refuted
0-3**; the leaderboard is stale relative to frontier models. *(3-0 metrics /
0-3 ranking)*

## 4. Tradeoffs between approaches

| Approach | Verdict |
|---|---|
| **Lua-mod / RCON structured access** | The unanimous winner: officially supported, headless (no GPU/client), faster (1.75× in FLE's measurements), parallelizable, lossless structured state. Every verified notable project uses it. |
| **Screen capture + vision** | Only appears as an *optional supplement* (FLE's headless renderer, `map_image`). Costs a client/GPU, lossy, slower. Useful for multimodal research questions, not as the primary channel. |
| **Memory hooks / injection** | No verified project uses them. Unnecessary given the official Lua surface; fragile across updates. |

Caveat: the surviving claim set is FLE-heavy, so "nobody uses vision/memory
hooks" is absence of evidence in this sample, not proof of absence.

## 5. Recommendations for building an agent today

1. **Run the official headless server in Docker** with RCON enabled — free
   download, no game client or GPU needed.
2. **Build on FLE** (`pip install factorio-learning-environment`; `fle init` →
   `fle cluster` spins up the Docker headless cluster) rather than raw RCON —
   you get the gym interface, the tool API, checkpoint/rollback, and the MCP
   server for free.
3. **Use the code-synthesis REPL pattern** for LLM agents — it's what the whole
   verified ecosystem converged on.
4. For a Claude-Code-driven agent specifically, start from the **FLE MCP
   server** (`fle://` resources + `execute`/`commit`/`restore`) — the
   commit/restore rollback is the standout agent-ergonomics feature.
5. Add the **pixel renderer only if doing multimodal research**; go raw
   Lua-over-RCON only if FLE's abstraction genuinely doesn't fit.

## Open questions

- **Save/replay file parsing** — the one built-in interface with zero surviving
  claims. Does anyone use it for offline learning or dataset generation?
- **Pure-RL (non-LLM) or vision-first agents** outside the FLE ecosystem — do
  they exist, and how do they compare to code-synthesis LLM agents?
- **Which frontier model currently tops FLE?** The six-model leaderboard is
  stale and the one ranking claim tested was refuted.
- **Has anyone trained a conventional RL policy end-to-end** against FLE's
  gym interface, given its code-synthesis action space?

## Caveats

Field moves fast; versions cited were current at verification (2026-07-15).
Findings are FLE-centric by evidence availability. Published critiques of FLE
exist (reward-hacking risk, single-agent scope). Whether the Twitch stream is
still live is unverified. "First-party" for the Claude Code integration means
the FLE team, not Anthropic or Wube.

## Sources (top-cited)

- https://lua-api.factorio.com/latest/index-runtime.html (primary)
- https://lua-api.factorio.com/latest/classes/LuaRCON.html (primary)
- https://wiki.factorio.com/Command_line_parameters (primary)
- https://arxiv.org/abs/2503.09617 — FLE paper (primary)
- https://github.com/JackHopkins/factorio-learning-environment (primary)
- https://jackhopkins.github.io/factorio-learning-environment/ — docs, v0.3.0 notes, leaderboard (primary)
- https://github.com/JackHopkins/claude-code-plays-factorio (primary)
- https://github.com/MarkMcCaskey/factorioctl (primary)
- https://github.com/lveillard/factorio-ai-companion (primary)
- https://mods.factorio.com/mod/ai-player (primary)
- https://github.com/moeru-ai/airi-factorio (primary)
- https://epoch.ai/benchmarks/factorio-learning-environment (secondary)
- https://news.ycombinator.com/item?id=43331582 — FLE Show HN (forum)
- https://news.ycombinator.com/item?id=45466865 — Claude Code plays Factorio HN (forum)
