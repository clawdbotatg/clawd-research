# factorio-plan — agents playing in a world you can watch

*Plan written 2026-07-19. Companion to [README.md](README.md) (the interface-landscape
research). Goal: run multiple AI agents in one Factorio world from this Mac, and
watch them live from the paid Factorio copy on **leftclaw**.*

## The shape of the thing (read this first)

Your paid copy on leftclaw is the **spectator window**, not the host. The world the
agents play in is a **free headless server** that FLE (Factorio Learning
Environment) spins up in Docker and drives over RCON. The agents never "join" as
players — FLE creates a character per agent server-side via Lua. So:

```
this Mac                                  leftclaw
┌─────────────────────────────┐           ┌──────────────────────┐
│ FLE (python)                │           │ your paid Factorio   │
│  └─ agent loops (LLM calls) │           │ client               │
│ Docker                      │  LAN UDP  │  Multiplayer →       │
│  └─ headless factorio 2.0.73│◄──34197───│  Connect to address  │
│     RCON tcp 27000          │           │  <mac-ip>:34197      │
└─────────────────────────────┘           └──────────────────────┘
```

Costs: $0 beyond what you already own. Agent count is free; only the watching
window needs a paid copy, and you have several.

## Hard facts pinned from the FLE source (2026-07, main branch)

- Docker image: **`factoriotools/factorio:2.0.73`** — so the server is Factorio
  **2.0.73 exactly**, and the compose command **strips Space Age content**
  (`rm -rf …/elevated-rails …/quality …/space-age` before launch). It's a
  base-game 2.0.73 server.
- Port scheme per instance *i* (0-based): game UDP `34197+i`, RCON TCP `27000+i`.
- Scenarios: `default_lab_scenario` (flat lab world, the benchmark default) or
  `open_world` (natural map — **use this one, it's the watchable one**). Can also
  boot from a save zip.
- CLI: `fle cluster start|stop|restart [-n NUM_INSTANCES] [-s SCENARIO]`.
- **`fle eval` is deprecated on main** (raises "Use `inspect-eval` instead"); the
  current runner is `fle inspect-eval` (Inspect AI framework). The pip release
  (0.4.3, 2026-04) may still carry the old `fle eval --config` path — check
  `fle --help` after install and use whichever exists.
- Multi-agent is a first-class env parameter: `num_agents` on the Factorio
  instance; each agent gets its own in-game character (Lua players 1..N) and an
  isolated Python namespace, plus a `send_message()` tool for agent↔agent chat.
  Shipped multi-agent run config shape (`fle/eval/configs/multiagent/claude_lab_free.json`):

  ```json
  [{ "task": "multiagent/iron_plate_throughput_free.json",
     "model": "claude-3-5-sonnet-latest",
     "num_agents": 2 }]
  ```

- Shipped multi-agent tasks (in `fle/eval/tasks/task_definitions/multiagent/multiagent_tasks.py`):
  `iron_plate_throughput_multiagent_free` (pure co-op),
  `…_impostor` (one agent is secretly a saboteur), `…_distrust` (mutual
  suspicion). The prompts literally open with "You've crash landed on an alien
  planet…" and require agents to narrate to each other via `send_message()`.
  These are written for `num_agents: 2`; going to 5 means editing/duplicating a
  task config (it's a small Pydantic model — copy `iron_plate_throughput_multiagent_free`,
  set `num_agents=5`, optionally give each agent its own `agent_instructions` entry).
- Apple Silicon note: on arm64 the cluster runs the x86 factorio binary under
  **box64 emulation** (`EMULATOR=/bin/box64`, `DOCKER_PLATFORM=linux/arm64`).
  It works; expect a slower tick ceiling than native. Irrelevant at 5-agent scale.

---

## Phase 0 — prerequisites (this Mac)

- [ ] Docker Desktop installed and running (`docker info` succeeds).
- [ ] Python 3.10+ (`python3 --version`) — use `uv` if available.
- [ ] An LLM API key for the agents. FLE reads a `.env` in the working dir:
  `ANTHROPIC_API_KEY=sk-ant-…` (and/or `OPENAI_API_KEY`, OpenRouter). **Note:
  agents bill metered API, not a Claude subscription** — there's no OAuth path
  in FLE. Budget accordingly (see "Cost & pacing" below).
- [ ] ~5 GB disk for the docker image + saves.

## Phase 1 — install FLE

```bash
mkdir -p ~/clawd/factorio-agents && cd ~/clawd/factorio-agents
uv venv && source .venv/bin/activate        # or python3 -m venv .venv
pip install "factorio-learning-environment[eval,mcp]"
fle --help                                   # note: does it list `eval`, `inspect-eval`, or both?
```

Drop the API key(s) in `./.env`. There's also an interactive helper:
`python -m fle.eval.infra.setup_api_keys` (path may vary by release — optional).

If the pip release turns out to be stale vs. what we verified on main (e.g. no
`inspect-eval`, no multiagent configs), install from git instead:
`pip install "factorio-learning-environment[eval,mcp] @ git+https://github.com/JackHopkins/factorio-learning-environment"`.

## Phase 2 — start the world

```bash
fle cluster start -n 1 -s open_world
```

Verify:

```bash
docker ps                                    # expect factoriotools/factorio:2.0.73 up
# game UDP 34197, RCON TCP 27000 published on the host
```

`-n 1` = one world. (More instances = more *parallel worlds*, not more agents in
one world — remember multiple machines/instances don't speed up a single shared
world; the simulation is one process.)

## Phase 3 — smoke test: one agent, watch it think

Current-main path (Inspect AI):

```bash
fle inspect-eval --env-id open_play_production \
    --model anthropic/claude-sonnet-4-5 \
    --trajectory-length 100 \
    --view          # opens Inspect's live log viewer on :8000
```

(Model string uses Inspect's `provider/model` naming. If the installed release
still has the old runner, the equivalent is `fle eval --config cfg.json` with
`[{"env_id": "open_play_production", "model": "claude-sonnet-4-5"}]`.)

Success = the Inspect view shows the agent writing Python, and
`docker logs <container>` shows RCON activity. Don't tune anything yet; just
confirm the loop turns.

## Phase 4 — point leftclaw's client at it (the payoff)

1. Get this Mac's LAN IP: `ipconfig getifaddr en0`.
2. On leftclaw, **match the client to 2.0.73 exactly** — Factorio multiplayer
   requires an exact version match:
   - Steam: right-click Factorio → Properties → Betas → pick the `2.0.73`
     branch (Steam keeps old versions as beta branches).
   - factorio.com installs: download 2.0.73 from the archive at
     factorio.com/download/archive.
3. **Disable Space Age** on the client before joining (Main menu → Mods →
   disable `space-age`, `quality`, `elevated-rails`) — the server runs base
   game only. The join dialog will otherwise complain about mod mismatch (it
   may offer to sync/disable for you — accepting is fine).
4. Multiplayer → Connect to address → `<mac-ip>:34197`.
5. macOS will prompt to allow Docker/com.docker.backend to accept incoming
   connections — allow it. If the connect times out, that firewall prompt is
   the first suspect (System Settings → Network → Firewall).
6. You're now a character standing in the agents' world. Watching kit:
   - `M` = map view; you can see the whole factory grow.
   - The agents appear as extra player characters ("player 1..N" style names).
   - Console `/editor` flips you into the map editor's free camera / god mode
     (this disables achievements on that save — who cares, it's an agent world).
   - For a stream-ready smooth camera later: spectator/camera mods exist, but
     mods on the client must match the server (base-game server = keep the
     client vanilla; do camera work via `/editor` and map view first).

Note on auth: your copy is legit, so it doesn't matter much, but if the join is
rejected on verification grounds, the knob is `require_user_verification` in
FLE's `server-settings.json` (in the package's `fle/cluster/docker/config/`) —
set false for pure-LAN play.

## Phase 5 — multiple agents, one world

Two routes; try A first.

**Route A — shipped multi-agent eval (2 agents, zero code).** If the installed
version still runs the classic eval harness:

```bash
# config: two Claudes co-building an iron plate factory, narrating via send_message()
cat > multiagent.json <<'EOF'
[{ "task": "multiagent/iron_plate_throughput_free.json",
   "model": "claude-sonnet-4-5",
   "num_agents": 2 }]
EOF
fle eval --config multiagent.json
```

Then connect from leftclaw and watch two characters divide up the work. The
`…_impostor` variant (one agent secretly sabotages, the other has to catch it)
is the single most watchable thing in the repo — run that second.

**Route B — 5 agents via the gym/instance API (a ~50-line script).** The env
takes `num_agents` directly; each agent is a character + isolated namespace.
Sketch:

```python
from fle.env import FactorioInstance   # exact import path per installed version

inst = FactorioInstance(address="localhost", tcp_port=27000, num_agents=5)
# per agent: its own conversation loop with your LLM of choice;
# step(agent_idx=i, code=<python the model wrote>) round-robin,
# feed each result back to that agent's context.
```

Write the loop so agents act **concurrently but committed one at a time**
(round-robin or as-ready). To go past 2 agents with the *task* framing (goals,
scoring, the crash-landed narrative), copy
`fle/eval/tasks/task_definitions/multiagent/multiagent_tasks.py`'s
`iron_plate_throughput_multiagent_free` and set `num_agents=5` — optionally give
each of the 5 its own `agent_instructions` entry (5 personalities > 5 clones).

**Route C — fallback if multi-agent fights us:** 5 parallel *worlds*
(`fle cluster start -n 5`, one agent each) still demos everything except
agent↔agent interaction, and works with plain `inspect-eval`.

## Phase 6 — make it a show (ties into agent-arena)

- Give the 5 agents distinct models/personas and let `send_message()` traffic be
  the commentary track — it's already structured text, trivially streamable.
- The impostor/distrust tasks are ready-made formats: co-op speedrun,
  social-deduction, sabotage. This is the agent-esports content loop from
  `agent-arena-landscape/` with zero game-dev work.
- Overlay data: FLE exposes production stats/flows as structured observations —
  a scoreboard (plates/min per agent) is a poll away. `fle://render` (MCP) or
  the headless renderer can produce map images without a client.
- OBS on leftclaw pointed at the client = a stream, today.

## Cost & pacing expectations

- The game ticks at 60 UPS regardless; **agents act at LLM speed** — one
  observe→think→code→execute round-trip per agent per step. With 5 agents
  polling, expect a leisurely, watchable build pace (steps are seconds-to-a-minute
  each). This is a feature for spectating.
- Token burn is the real meter: FLE trajectories are code-heavy; a 100-step run
  per agent on a frontier model is real API money. Start with 2 agents × short
  trajectories, measure, then scale to 5. `--cache-prompt` (inspect-eval) helps.
- UPS/compute on the Mac is a non-issue at this scale, even under box64.

## Troubleshooting quick refs

| Symptom | Fix |
|---|---|
| Client can't see/join server | Exact version match (2.0.73), Space Age disabled, macOS firewall allow, correct LAN IP, UDP 34197 |
| "mod mismatch" on join | Disable space-age/quality/elevated-rails on the client |
| `fle eval` errors "not supported" | You're on main-lineage code — use `fle inspect-eval`, or Route B |
| Agents idle / no RCON traffic | Check `.env` keys loaded (run from the dir containing `.env`); `docker logs` for RCON auth errors (port 27000, not 27015 — 27015 is container-internal) |
| Everything slow on Apple Silicon | box64 emulation is expected; fine at this scale |
| Want events pushed, not polled | RCON is request/reply only — by design. Poll (FLE does) or add a file/socket-writing mod later |

## Open items (decide during execution, not before)

- [ ] Pip 0.4.3 vs git-main install — pick whichever runs the multiagent config cleanly.
- [ ] Where the server lives long-term: this Mac (simplest, agents co-located) vs
      leftclaw (if it's beefier / always-on) — FLE has a remote-cluster module
      (`fle/cluster/remote/`) but local-first is the fast path.
- [ ] 5-agent task file: extend `multiagent_tasks.py` vs raw gym loop.
- [ ] Camera/stream rig on leftclaw (Phase 6) — only after Phase 5 looks good.
