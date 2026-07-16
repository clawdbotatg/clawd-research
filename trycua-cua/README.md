# trycua/cua — open-source infrastructure for computer-use agents

*Research report, 2026-07-15. Sources: the GitHub repo + README, cua.ai docs,
DeepWiki architecture pages, the cua-bench HuggingFace blog post, and web search.*

## TL;DR

[Cua](https://github.com/trycua/cua) (pronounced "koo-ah", short for **Computer-Use
Agent**) is a YC-backed, MIT-licensed platform for letting AI agents **control full
desktop environments** — click, type, screenshot, run shells — across macOS,
Windows, Linux, and Android, with the same API whether the desktop is a local VM,
a Docker container, or their managed cloud. It's roughly "Docker for computer-use
agents": a sandbox layer, an agent-loop SDK that speaks to every major
computer-use model behind one interface, a benchmark/RL-environment suite
(cua-bench), and a newer "Cua Drivers" product that drives native apps **in the
background without stealing your cursor** — pluggable into Claude Code and Cursor
via MCP. ~19.8k stars, very active (559 releases; latest July 2026).

## What problem it solves

Computer-use agents (Claude computer use, OpenAI computer-use-preview, UI-TARS,
etc.) all follow the same loop — screenshot → VLM decides an action → OS-level
click/type → repeat — but every OS, VM stack, and model provider has a different
interface. Cua unifies three fragmented layers:

1. **Where the agent runs** — one `Computer`/`Sandbox` API over local VMs (Apple
   Virtualization.Framework via Lume, Docker, QEMU, bare host) and their cloud
   (Linux/Windows/macOS/Android), so agent code runs unchanged anywhere.
2. **Which model drives it** — one `ComputerAgent` interface over Anthropic,
   OpenAI, Gemini, UI-TARS, plus "composed agents" (a grounding model like
   OpenCUA/Moondream3 paired with any planning LLM) and local inference
   (mlx-vlm on Apple Silicon, transformers on GPU).
3. **How you measure it** — cua-bench wraps OSWorld, Windows Agent Arena,
   ScreenSpot, MiniWoB++ and custom tasks, with trajectory export for RL training.

## Core components

- **Computer SDK (`cua-computer`, Python + TypeScript)** — VM/container lifecycle
  plus a standardized interface for cursor, keyboard, screen, clipboard, files,
  shell. Quickstart shape:

  ```python
  from cua import Sandbox, Image

  async with Sandbox.ephemeral(Image.linux()) as sb:
      result = await sb.shell.run("echo hello")
      screenshot = await sb.screenshot()
      await sb.mouse.click(100, 200)
      await sb.keyboard.type("Hello from Cua!")
  ```

- **Agent SDK (`cua-agent`)** — the agentic loop (perception → reasoning →
  action → iterate) with liteLLM-style model strings, so swapping Claude for
  UI-TARS is a config change.
- **Computer Server** — a FastAPI app running *inside* each sandbox, exposing
  WebSocket + HTTP endpoints for actions; platform handlers are PyObjC (macOS),
  python-xlib (Linux), pywin32 (Windows). Also exposes MCP tools directly.
- **Cua Drivers** (newer, notable) — background computer-use for macOS, Windows,
  Linux: agents drive *native* apps without taking over the user's cursor or
  focus. Installs as a daemon/CLI and plugs into Claude Code, Cursor, or custom
  clients over MCP. Install: `curl -fsSL https://cua.ai/driver/install.sh | bash`.
- **Lume / Lumier** — Lume is their CLI for near-native macOS/Linux VMs on Apple
  Silicon via Apple's Virtualization.Framework; Lumier is the Docker image
  (XFCE + noVNC) used for Linux container sandboxes.
- **SOM (`cua-som`)** — Set-of-Mark visual grounding utilities for locating UI
  elements in screenshots.
- **cua-bench** — benchmark + RL-environment framework. Key insight from their
  [blog post](https://huggingface.co/blog/cua-ai/cua-bench): agent success rates
  can differ **>10×** across minor UI variations (theme, resolution, platform),
  so they generate training data by replotting one demonstrated trajectory
  across many visual themes, and replace 20-minute VM-snapshot loads with
  lightweight "webtop" environments and declarative task definitions
  (`@setup_task` / `@solve_task` / `@evaluate_task`). Their own KiCad benchmark
  shows frontier agents clearing only 6 of 25 expert tasks — the field is early.

## Local vs cloud

| | Local | Cua Cloud |
|---|---|---|
| Linux | Docker (Lumier), QEMU | containers + VMs |
| macOS | Lume (Apple Silicon VMs) | managed macOS |
| Windows | QEMU | managed Windows |
| Android | QEMU / custom images | managed Android |
| Custom images | .qcow2 / .iso BYOI | — |

Same `Computer` API on every provider. Cloud is the paid product (SOC 2 Type I);
everything local is MIT open source. `pip install cua` to start.

## Why it's interesting for us

- **Cua Drivers ≈ a hands layer for the harness.** Background, focus-preserving
  native-app control over MCP is exactly the missing piece when a Claude Code
  session needs to drive a GUI app on this Mac without fighting the user for the
  cursor — an alternative/complement to our `browser-automation` CDP approach,
  which only covers Chrome.
- **Lume** is independently useful: disposable macOS VMs on Apple Silicon for
  risky agent work (a stronger isolation story than scratchpad dirs).
- **cua-bench's trajectory-replotting** idea (one oracle demo → many themed
  training examples) is a clever, reusable pattern for anyone generating agent
  training data.
- The stack is Python + Rust + Swift, MIT, and healthy (19.8k★, 1.3k forks,
  weekly releases), so building on it is low-risk.

## Hands-on notes (Cua Driver 0.8.3 on macOS 26.2, 2026-07-16)

We installed the Driver on this machine and ran the canonical demo end-to-end:
launch Calculator backgrounded → click All Clear, 6, ×, 7, = via AX elements →
read `6×7 = 42` back out of the accessibility tree. **It works**, with real quirks:

- **Setup**: installer → `open -n -g -a CuaDriver --args serve` →
  `cua-driver permissions grant` (Accessibility via dialog; **Screen Recording
  needs a manual System Settings toggle** and stayed ungranted for us — the AX
  path works fine without it, only screenshots/pixel clicks need it). MCP:
  `claude mcp add-json --scope user cua-computer-use
  '{"args":["mcp"],"command":"~/.local/bin/cua-driver"}'`.
- **The AX path is the good path**: `get_window_state` returns an indexed
  element tree with stable AX ids (`id=Six`, `id=Equals`); `click` by
  `element_index` needs no cursor, no focus, no screen recording.
- **Trap 1 — stale element indices**: the index cache is replaced by every new
  snapshot. Clicking with indices from an older snapshot hit arbitrary elements —
  one stray click landed on "Quit Calculator" and killed the app. Snapshot once,
  then do all clicks against that one snapshot (or re-resolve per click).
- **Trap 2 — phantom windows**: `launch_app` returned a 30px phantom
  `window_id`; the real window had to be found via `list_windows`
  (`is_on_screen: true`, sane bounds).
- **Trap 3 — empty AX tree until first activation**: a freshly backgrounded
  Calculator exposed only the menu bar to AX; one `bring_to_front` populated the
  full tree (windows may need re-activation after losing foreground).
- **Trap 4 — daemon flakiness**: the daemon dropped a connection mid-sequence
  and the CLI silently fell back to a cacheless in-process run
  (`daemon proxy … failed; running 'click' in-process`) — watch stderr for that
  warning and retry through the daemon.
- **Verdict**: the primitives are strong (background launch really doesn't steal
  focus — `self_activation_suppressed: true`) but 0.8.x needs retry-mindedness.
  Driving it via the MCP tools from an agent that re-snapshots every turn (as
  the tool descriptions instruct) sidesteps most of what we hit scripting it raw.

## Sources

- [github.com/trycua/cua](https://github.com/trycua/cua) — repo + README
- [cua.ai/docs](https://cua.ai/docs) — product docs (Driver, Sandbox, Bench)
- [deepwiki.com/trycua/cua](https://deepwiki.com/trycua/cua) — architecture deep-dive
- [cua-bench blog post](https://huggingface.co/blog/cua-ai/cua-bench) — benchmark/RL framework
- [cua-agent on PyPI](https://pypi.org/project/cua-agent/)
- [trycua/acu](https://github.com/trycua/acu) — their curated computer-use-agent resource list
