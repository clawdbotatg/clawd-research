#!/usr/bin/env python3
"""Generate synthetic session-naming training data with labels by construction.

The task (from clawd-harness server.py NAME_SYS_PROMPT): given a transcript,
emit ONLY compact JSON {"title": <=5 words, "desc": <=12 words, "tab": 1-2 words},
naming the session by its MAIN objective and ignoring side-quest tangents.

Because the generator picks the topic, the correct label is known by
construction. Topics are split train/heldout so the test set only contains
objects the model never saw — the eval measures generalization, not recall.

Outputs data/train.jsonl, data/valid.jsonl, data/test.jsonl (mlx_lm chat format)
plus data/test_meta.jsonl (keywords + side-quest info for the grader).
"""
import json, random, re, os

SYS = ("You name software-engineering sessions. Given a transcript, "
       "reply with ONLY compact JSON and nothing else: "
       '{"title": "<max 5 words>", "desc": "<max 12 words>", '
       '"tab": "<1-2 words>"}. '
       "Name the session by its MAIN objective — the overarching task "
       "it was set up to accomplish, usually established in the opening "
       "messages. Treat later one-off questions or tangents (a passing "
       "pricing/how-to/model question) as side-quests: do NOT let them "
       "redefine the name unless the session's whole focus has clearly "
       "and durably shifted to a new task. "
       "The title is a terse label; the desc is a one-line summary; "
       "the tab is the tightest possible handle for a narrow browser "
       "tab — one or two words that still identify the task (e.g. "
       '"local projects", "tab ages", "router port").')

def T(req, plan, title, tab, desc, kw):
    return dict(req=req, plan=plan, title=title, tab=tab, desc=desc, kw=kw)

# ---- topic bank: label fields are hand-written (the "teacher" knowledge) ----
TOPICS = [
    # frontend
    T("add a swipe-to-dismiss gesture to the photo gallery",
      "I'll track horizontal touch delta on touchstart/touchmove and animate the card off-screen past a threshold.",
      "Gallery swipe to dismiss", "swipe dismiss",
      "Add swipe-to-dismiss touch gesture to the photo gallery", ["swipe", "dismiss", "gallery"]),
    T("add a dark mode toggle to the settings page",
      "I'll add a CSS variable theme layer and a toggle that persists to localStorage.",
      "Dark mode toggle", "dark mode",
      "Add persistent dark mode toggle to settings", ["dark", "theme", "toggle"]),
    T("the dropdown menu clips behind the modal, fix the z-index mess",
      "The stacking contexts are nested wrong — I'll flatten the overlay layers and set explicit z-index tiers.",
      "Fix dropdown z-index clipping", "z-index fix",
      "Fix dropdown clipping behind modal via stacking context cleanup", ["dropdown", "z-index", "clip", "modal"]),
    T("make the data table columns sortable and resizable",
      "I'll add click-to-sort headers with direction indicators and drag handles for column width.",
      "Sortable resizable table columns", "table columns",
      "Add sorting and drag-resize to data table columns", ["table", "column", "sort", "resiz"]),
    T("infinite scroll on the feed is janky, virtualize the list",
      "I'll swap the feed to a windowed renderer so only visible rows mount.",
      "Virtualize feed list", "feed virtualize",
      "Fix janky infinite scroll by virtualizing the feed list", ["feed", "virtual", "scroll"]),
    T("build a drag and drop kanban board for the tasks view",
      "I'll implement draggable cards with drop zones per column and optimistic reorder persistence.",
      "Kanban drag and drop", "kanban",
      "Build drag-and-drop kanban board for tasks view", ["kanban", "drag", "board"]),
    T("the onboarding form loses state when you go back a step",
      "I'll lift the wizard state into a single store keyed by step so back navigation restores fields.",
      "Fix onboarding form state", "onboarding fix",
      "Preserve multi-step onboarding form state across back navigation", ["onboarding", "form", "state", "wizard"]),
    T("add keyboard shortcuts for the editor, cmd-k command palette style",
      "I'll add a global keydown handler with a fuzzy-searchable command palette overlay.",
      "Editor command palette", "cmd-k palette",
      "Add cmd-k command palette keyboard shortcuts to editor", ["palette", "keyboard", "shortcut", "cmd"]),
    T("hook up the file upload with a progress bar and drag-drop zone",
      "I'll use XHR upload progress events driving a bar, plus a dropzone with highlight states.",
      "File upload progress UI", "file upload",
      "Add drag-drop file upload with live progress bar", ["upload", "progress", "drag"]),
    T("charts flash unstyled on load, add loading skeletons",
      "I'll render skeleton placeholders sized to each chart until its data resolves.",
      "Chart loading skeletons", "skeletons",
      "Add loading skeleton placeholders to charts", ["skeleton", "chart", "load"]),
    # backend / api
    T("refactor the auth middleware to use JWT refresh tokens",
      "I'll split access/refresh tokens, add a rotation endpoint and httpOnly cookies.",
      "JWT refresh token auth", "jwt refresh",
      "Refactor auth middleware to rotating JWT refresh tokens", ["jwt", "refresh", "auth", "token"]),
    T("add rate limiting to the public api endpoints",
      "I'll add a sliding-window limiter keyed by api key with 429s and retry-after headers.",
      "API rate limiting", "rate limit",
      "Add sliding-window rate limiting to public API", ["rate", "limit", "api"]),
    T("the webhook handler double-processes events, make it idempotent",
      "I'll dedupe on the event id with an idempotency table and short-circuit repeats.",
      "Idempotent webhook handler", "webhook dedupe",
      "Make webhook handler idempotent via event id dedupe", ["webhook", "idempoten", "dedupe", "event"]),
    T("build a csv export endpoint for the orders report",
      "I'll stream rows with a generator so large exports don't buffer in memory.",
      "Orders CSV export", "csv export",
      "Build streaming CSV export endpoint for orders report", ["csv", "export", "order"]),
    T("paginate the search results api, it returns everything at once",
      "I'll add cursor-based pagination with stable sort keys and a next_cursor field.",
      "Paginate search API", "pagination",
      "Add cursor pagination to search results API", ["pagina", "search", "cursor"]),
    T("emails go out synchronously and block requests, move them to a queue",
      "I'll push sends onto a worker queue with retries and exponential backoff.",
      "Queue email sending", "email queue",
      "Move blocking email sends to background worker queue", ["email", "queue", "worker"]),
    T("add soft delete to the documents model instead of hard deletes",
      "I'll add a deleted_at column, filter default scopes, and a restore endpoint.",
      "Soft delete documents", "soft delete",
      "Replace hard deletes with soft delete on documents", ["soft", "delete", "document"]),
    T("the session store leaks memory, expired sessions never get purged",
      "I'll add a TTL sweep job and switch lookups to check expiry lazily.",
      "Purge expired sessions", "session purge",
      "Fix session store leak by purging expired sessions", ["session", "expire", "purge", "leak"]),
    T("write a graphql resolver for the notifications feed with subscriptions",
      "I'll add the query resolver plus a pubsub-backed subscription for live pushes.",
      "Notifications GraphQL resolver", "notifications",
      "Add GraphQL resolver and subscription for notifications feed", ["graphql", "notification", "subscription"]),
    T("harden the file download endpoint against path traversal",
      "I'll resolve the requested path against the root and reject anything escaping it.",
      "Fix path traversal", "path traversal",
      "Harden download endpoint against path traversal attacks", ["path", "traversal", "download"]),
    # infra / devops
    T("the deploy keeps failing on vercel with a 404 on the api routes",
      "Usually a rewrites/output-dir mismatch — let me check vercel.json and the framework preset.",
      "Vercel API 404 deploy", "vercel 404",
      "Fix Vercel deploy 404s on API routes", ["vercel", "404", "deploy"]),
    T("set up a github action to run pytest on every PR",
      "I'll add a workflow with a python version matrix and a pip cache.",
      "Pytest CI action", "pytest ci",
      "Add GitHub Action running pytest on every PR", ["pytest", "action", "ci", "workflow"]),
    T("dockerize the app with a multi-stage build to shrink the image",
      "I'll split builder and runtime stages and copy only the built artifacts.",
      "Multi-stage Docker build", "dockerfile",
      "Dockerize app with slim multi-stage build", ["docker", "multi-stage", "image"]),
    T("nginx returns 502 under load, tune the upstream keepalive",
      "I'll raise upstream keepalive connections and align proxy timeouts with the app server.",
      "Fix nginx 502s", "nginx 502",
      "Tune nginx upstream keepalive to stop 502s under load", ["nginx", "502", "keepalive", "upstream"]),
    T("add prometheus metrics and a grafana dashboard for the worker",
      "I'll export queue depth and job latency histograms and wire a dashboard.",
      "Worker metrics dashboard", "metrics",
      "Add Prometheus metrics and Grafana dashboard for worker", ["prometheus", "grafana", "metric", "dashboard"]),
    T("rotate the tls certs automatically, letsencrypt keeps expiring",
      "I'll set up certbot with a renew timer and a deploy hook that reloads nginx.",
      "Auto-renew TLS certs", "tls renew",
      "Automate Let's Encrypt TLS cert renewal", ["tls", "cert", "renew", "letsencrypt"]),
    T("terraform apply wants to destroy the database, figure out the state drift",
      "I'll diff the state against reality and import the drifted resources before planning again.",
      "Terraform state drift", "tf drift",
      "Resolve Terraform state drift threatening the database", ["terraform", "state", "drift"]),
    T("cut a staging environment that mirrors prod with seeded data",
      "I'll clone the prod topology with scaled-down instances and a sanitized seed dump.",
      "Staging environment setup", "staging env",
      "Stand up prod-mirroring staging environment with seed data", ["staging", "environment", "seed"]),
    T("the cron backup job silently stopped, add alerting on it",
      "I'll add a heartbeat check that pages when the backup doesn't report in.",
      "Backup job alerting", "backup alert",
      "Alert when the cron backup job stops running", ["backup", "cron", "alert", "heartbeat"]),
    # database
    T("the orders query does a full table scan, add the right indexes",
      "EXPLAIN shows a seq scan on status+created_at — I'll add a composite index.",
      "Index orders query", "orders index",
      "Add composite index to stop orders full table scan", ["index", "order", "scan", "query"]),
    T("write a migration to split the users name column into first and last",
      "I'll add the columns, backfill with a split heuristic, then drop the old one.",
      "Split name column migration", "name migration",
      "Migrate users.name into first and last columns", ["migration", "name", "column", "split"]),
    T("dedupe the contacts table, we have thousands of near-duplicate rows",
      "I'll match on normalized email/phone, merge references, and delete the losers in batches.",
      "Dedupe contacts table", "dedupe contacts",
      "Merge and delete near-duplicate contacts rows", ["dedupe", "contact", "duplicate"]),
    T("move the analytics events out of postgres into clickhouse",
      "I'll double-write during the cutover, backfill history, then flip reads.",
      "Events to ClickHouse", "clickhouse",
      "Migrate analytics events from Postgres to ClickHouse", ["clickhouse", "event", "analytic", "migrat"]),
    T("the connection pool exhausts under peak traffic, tune it",
      "I'll size the pool to the db's max, add a queue timeout, and find the leaking checkout.",
      "Fix connection pool exhaustion", "conn pool",
      "Tune database connection pool exhausting under load", ["pool", "connection", "exhaust"]),
    # auth / security
    T("add two factor auth with totp to the login flow",
      "I'll add TOTP enrollment with QR provisioning and backup codes.",
      "TOTP two-factor auth", "2fa totp",
      "Add TOTP two-factor authentication to login", ["totp", "two", "factor", "2fa"]),
    T("implement magic link login instead of passwords",
      "I'll issue single-use signed tokens by email with short expiry and device binding.",
      "Magic link login", "magic link",
      "Replace password login with emailed magic links", ["magic", "link", "login"]),
    T("audit the app for xss, the comment field renders raw html",
      "I'll sanitize on render with an allowlist and add a CSP as a backstop.",
      "Fix comment XSS", "xss fix",
      "Sanitize comment rendering and audit app for XSS", ["xss", "sanitiz", "comment"]),
    T("scope the api keys with per-key permissions instead of full access",
      "I'll add a scopes column, enforce per-route required scopes, and migrate existing keys.",
      "Scoped API key permissions", "key scopes",
      "Add per-key permission scopes to API keys", ["scope", "key", "permission"]),
    # testing
    T("the checkout e2e test is flaky, it fails one run in five",
      "I'll replace the sleeps with event-based waits and stub the payment sandbox.",
      "Fix flaky checkout test", "flaky test",
      "Deflake checkout e2e test with proper waits", ["flaky", "checkout", "test", "e2e"]),
    T("add property based tests for the pricing calculator",
      "I'll generate random carts with hypothesis and assert the invariants hold.",
      "Pricing property tests", "property tests",
      "Add property-based tests for pricing calculator invariants", ["property", "pricing", "test", "hypothesis"]),
    T("mock the stripe api in the test suite, tests hit the real sandbox",
      "I'll wrap the client behind an interface and swap in a recorded fake.",
      "Mock Stripe in tests", "stripe mock",
      "Replace real Stripe sandbox calls with mocks in tests", ["stripe", "mock", "test"]),
    T("measure and raise the unit test coverage on the billing module",
      "I'll run coverage, list the untested branches, and fill the gaps worst-first.",
      "Billing test coverage", "coverage",
      "Raise unit test coverage on billing module", ["coverage", "billing", "test"]),
    # mobile
    T("push notifications never arrive on android, debug the fcm setup",
      "I'll check the token registration flow and the channel config against the FCM console.",
      "Android FCM notifications", "fcm debug",
      "Debug missing Android push notifications via FCM", ["fcm", "android", "notification", "push"]),
    T("the app cold start takes six seconds, profile and fix it",
      "I'll trace startup, defer non-critical init, and lazy-load the heavy modules.",
      "App cold start time", "cold start",
      "Profile and cut six-second app cold start", ["cold", "start", "startup", "profile"]),
    T("add offline mode so the notes app works without connectivity",
      "I'll cache to a local store and sync with a last-write-wins merge on reconnect.",
      "Notes offline mode", "offline mode",
      "Add offline cache and sync to notes app", ["offline", "sync", "cache", "note"]),
    # ethereum / web3
    T("write a solidity contract for an erc20 token with a vesting schedule",
      "I'll extend OpenZeppelin ERC20 with a cliff-plus-linear vesting wallet per grantee.",
      "ERC20 vesting contract", "erc20 vesting",
      "Write ERC20 token contract with vesting schedule", ["erc20", "vesting", "contract", "token"]),
    T("the mint function is vulnerable to reentrancy, fix and add tests",
      "I'll apply checks-effects-interactions, add a reentrancy guard, and a foundry PoC test.",
      "Fix mint reentrancy", "reentrancy",
      "Fix reentrancy in mint function with guard and tests", ["reentrancy", "mint", "guard"]),
    T("index transfer events off the contract into a postgres table",
      "I'll backfill with eth_getLogs in block ranges and tail new blocks via websocket.",
      "Index transfer events", "event indexer",
      "Index contract transfer events into Postgres", ["event", "index", "transfer", "log"]),
    T("estimate and optimize gas on the batch claim function",
      "I'll profile per-op gas, pack the storage slots, and switch to calldata arrays.",
      "Optimize claim gas", "gas golf",
      "Optimize gas usage of batch claim function", ["gas", "claim", "optimiz", "batch"]),
    T("wire the frontend to the wallet with viem, connect and sign flows",
      "I'll add a connect button with account watching and typed-data signing.",
      "Wallet connect with viem", "viem wallet",
      "Wire frontend wallet connect and signing with viem", ["viem", "wallet", "sign", "connect"]),
    # data / scripts
    T("write a script that scrapes the pricing pages of five competitors weekly",
      "I'll fetch each page, extract prices with per-site selectors, and diff against last week.",
      "Competitor price scraper", "price scraper",
      "Scrape and diff competitor pricing pages weekly", ["scrape", "pricing", "competitor"]),
    T("parse these bank csv exports and categorize the transactions",
      "I'll normalize the columns across banks and classify with a rules-then-fallback approach.",
      "Categorize bank transactions", "bank csv",
      "Parse bank CSVs and categorize transactions", ["bank", "csv", "transaction", "categor"]),
    T("build an etl job that pulls the crm api into the warehouse nightly",
      "I'll page through the API with incremental cursors and upsert into staging tables.",
      "Nightly CRM ETL", "crm etl",
      "Build nightly ETL from CRM API to warehouse", ["etl", "crm", "warehouse", "nightly"]),
    T("generate a weekly kpi report pdf from the metrics database",
      "I'll query the KPIs, render charts, and template them into a PDF on a schedule.",
      "Weekly KPI report", "kpi report",
      "Generate scheduled weekly KPI report PDF", ["kpi", "report", "weekly", "pdf"]),
    # build tooling / perf / misc
    T("the webpack build takes four minutes, speed it up",
      "I'll add persistent caching, split the vendor chunk, and check for duplicate deps.",
      "Speed up webpack build", "webpack speed",
      "Cut four-minute webpack build time", ["webpack", "build", "cache", "speed"]),
    T("migrate the project from javascript to typescript incrementally",
      "I'll enable allowJs with strict on new files and convert module by module.",
      "Incremental TypeScript migration", "ts migration",
      "Migrate codebase from JavaScript to TypeScript incrementally", ["typescript", "migrat", "js"]),
    T("upgrade react from 17 to 19 and fix what breaks",
      "I'll upgrade in two hops, run the codemods, and fix the event/strict-mode breakage.",
      "React 19 upgrade", "react upgrade",
      "Upgrade React 17 to 19 and fix breakage", ["react", "upgrade", "19"]),
    T("profile the api, the p99 latency doubled last week",
      "I'll pull traces, compare flame graphs week over week, and isolate the regressing span.",
      "Debug p99 latency regression", "p99 latency",
      "Profile and fix doubled API p99 latency", ["p99", "latency", "profil", "regress"]),
    T("set up eslint and prettier with a shared config across the monorepo",
      "I'll add a root config package, wire editor and CI checks, and format once.",
      "Monorepo lint config", "eslint setup",
      "Share ESLint and Prettier config across monorepo", ["eslint", "prettier", "lint", "monorepo"]),
    T("write the readme and quickstart docs for the sdk",
      "I'll write install/auth/first-call sections with runnable snippets per language.",
      "SDK readme and quickstart", "sdk docs",
      "Write SDK README and quickstart documentation", ["readme", "sdk", "doc", "quickstart"]),
    T("localize the app into spanish and german",
      "I'll extract strings to message catalogs and wire a locale switcher with fallbacks.",
      "Spanish German localization", "i18n",
      "Localize app strings into Spanish and German", ["localiz", "spanish", "german", "i18n"]),
    T("the image thumbnails are huge, generate resized webp variants",
      "I'll add an on-upload resize pipeline emitting webp at three breakpoints.",
      "WebP thumbnail pipeline", "thumbnails",
      "Generate resized WebP thumbnail variants on upload", ["webp", "thumbnail", "resize", "image"]),
    T("hook up stripe subscriptions with a customer portal",
      "I'll add checkout sessions, webhook-driven state sync, and the hosted portal link.",
      "Stripe subscriptions setup", "stripe subs",
      "Add Stripe subscriptions with customer portal", ["stripe", "subscription", "portal"]),
    T("build a cli tool that tails logs from all three services at once",
      "I'll multiplex the three streams with per-service color prefixes and a filter flag.",
      "Multi-service log tail CLI", "log tail",
      "Build CLI tailing logs from three services", ["log", "tail", "cli", "service"]),
    # dense/long requests that must compress to short titles
    T("the security review flagged an unvalidated redirect in the oauth callback handler",
      "I'll validate the redirect target against an allowlist and reject external URLs.",
      "Fix open redirect", "open redirect",
      "Fix unvalidated redirect flagged in OAuth callback", ["redirect", "oauth", "callback"]),
    T("the pentest report says the password reset token is predictable, fix the entropy",
      "I'll switch to a CSPRNG token with expiry and single-use enforcement.",
      "Fix reset token entropy", "reset token",
      "Make password reset tokens cryptographically random", ["reset", "token", "entropy"]),
    T("customer exports containing emoji crash the excel report generator in the billing admin",
      "I'll normalize to a unicode-safe writer and add a regression case with emoji rows.",
      "Fix emoji export crash", "emoji crash",
      "Fix emoji crashing Excel export in billing admin", ["emoji", "export", "excel", "crash"]),
    T("the load balancer health checks mark the api pods unhealthy during rolling deploys",
      "I'll add a readiness gate with a drain delay so pods finish in-flight requests first.",
      "Fix rolling deploy health", "deploy health",
      "Stop health checks failing pods during rolling deploys", ["health", "deploy", "rolling", "pod"]),
    T("the analytics dashboard shows duplicate revenue numbers after the currency conversion refactor",
      "I'll dedupe the join introduced by the conversion table and add an invariant test.",
      "Fix duplicate revenue numbers", "revenue dupes",
      "Fix duplicated revenue after currency conversion refactor", ["revenue", "duplicate", "currency"]),
    T("the accessibility audit flagged missing focus states on all the interactive elements",
      "I'll add visible focus rings via a shared style and audit tab order.",
      "Add focus states", "focus states",
      "Add missing focus states flagged by accessibility audit", ["focus", "accessib", "a11y"]),
    T("the compliance team needs pii redacted from the application logs before they ship to the vendor",
      "I'll add a redaction filter at the log formatter with patterns for the PII fields.",
      "Redact PII from logs", "pii redact",
      "Redact PII from application logs for compliance", ["pii", "redact", "log"]),
    T("the code review bot flagged an unchecked return value on the s3 upload call",
      "I'll check the response, retry on transient failures, and surface hard errors.",
      "Fix unchecked s3 upload", "s3 upload",
      "Handle unchecked return value on S3 upload", ["s3", "upload", "unchecked", "return"]),
]

# held-out topics: NEVER in training; the test set is built only from these
HELDOUT = [
    T("add voice input to the search bar using the web speech api",
      "I'll wire SpeechRecognition with interim results into the query box with a mic button.",
      "Voice search input", "voice search",
      "Add Web Speech API voice input to search bar", ["voice", "speech", "search", "mic"]),
    T("the calendar widget shows events in the wrong timezone",
      "I'll store UTC, convert at render with the viewer's zone, and audit the DST edges.",
      "Fix calendar timezone bug", "timezone bug",
      "Fix calendar events rendering in wrong timezone", ["timezone", "calendar", "utc", "event"]),
    T("implement websocket reconnect with exponential backoff in the client",
      "I'll add jittered backoff, resubscribe on reconnect, and a max-retry surface state.",
      "WebSocket reconnect backoff", "ws reconnect",
      "Add exponential backoff reconnect to WebSocket client", ["websocket", "reconnect", "backoff"]),
    T("migrate the blog from wordpress to a static astro site",
      "I'll export the posts to markdown, map the URLs with redirects, and port the theme.",
      "WordPress to Astro migration", "astro migration",
      "Migrate WordPress blog to static Astro site", ["astro", "wordpress", "migrat", "blog"]),
    T("add a redis cache in front of the product catalog queries",
      "I'll cache per-query with short TTLs and invalidate on product writes.",
      "Redis catalog cache", "redis cache",
      "Cache product catalog queries in Redis", ["redis", "cache", "catalog", "product"]),
    T("the pdf invoice generator mangles unicode customer names",
      "I'll switch to a unicode-capable font and normalize the text before rendering.",
      "Fix invoice unicode names", "invoice unicode",
      "Fix unicode name mangling in PDF invoices", ["unicode", "invoice", "pdf", "font"]),
    T("write a github bot that labels PRs by the files they touch",
      "I'll map path globs to labels and apply them from a webhook-triggered action.",
      "PR auto-label bot", "pr labels",
      "Build bot labeling PRs by touched paths", ["label", "pr", "bot", "path"]),
    T("deploy the ml model behind a fastapi endpoint with batching",
      "I'll load the model once, micro-batch requests, and add a warmup and health check.",
      "FastAPI model serving", "model serving",
      "Serve ML model via FastAPI with request batching", ["fastapi", "model", "serv", "batch"]),
    T("track down why the ios app gets rejected for background location",
      "I'll audit the location usage strings and entitlements against the review guideline.",
      "iOS location rejection", "ios reject",
      "Fix App Store rejection over background location", ["ios", "location", "reject", "app store"]),
    T("add fuzzy search over the docs with typo tolerance",
      "I'll index with trigrams and rank by edit-distance-weighted relevance.",
      "Fuzzy docs search", "fuzzy search",
      "Add typo-tolerant fuzzy search over docs", ["fuzzy", "search", "typo", "doc"]),
    T("the smart contract audit flagged an unchecked transfer return value",
      "I'll switch to SafeERC20 and add tests for tokens that return false.",
      "Fix unchecked transfer", "safeerc20",
      "Fix audit finding on unchecked ERC20 transfer returns", ["transfer", "unchecked", "safeerc20", "audit"]),
    T("batch the rpc calls on the portfolio page with multicall",
      "I'll aggregate the balance reads into one multicall3 request per block.",
      "Multicall portfolio reads", "multicall",
      "Batch portfolio RPC reads with Multicall3", ["multicall", "rpc", "batch", "portfolio"]),
]

OPENERS = ["", "hey, ", "ok so ", "can you ", "please ", "i need to ", "we need to ",
           "next up: ", "today's job: ", "alright, "]
FOLLOWUPS = [
    ("hmm, getting a console error after that change", "Let me look — likely the handler binds before the element mounts; I'll guard it."),
    ("looks good. also make sure it works on mobile", "I'll test the touch path and adjust the hit targets."),
    ("can you add a test for that", "Adding a unit test covering the main path and the edge case."),
    ("it works but feels slow", "I'll profile it and memoize the hot path."),
    ("ship it once the lint passes", "Lint is clean — done."),
    ("what about the edge case where the input is empty", "Good catch — I'll early-return and show the placeholder state."),
    ("rename things to match the codebase conventions", "Renamed to match the existing module naming."),
]
# side-quests: off-task tangents the model must NOT name the session after.
# (quest text, keywords that must NOT appear in the title)
SIDEQUESTS = [
    ("btw can you write a haiku about debugging", "Sure — here's one about the late-night hunt for a null pointer.", ["haiku"]),
    ("random q: how much does claude pro cost these days", "Claude Pro is a monthly subscription; check the pricing page for the current rate.", ["claude", "pricing", "pro"]),
    ("unrelated - how do i exit vim again", "Press Escape, then type :q! and Enter to quit without saving.", ["vim"]),
    ("side note, what's the capital of mongolia", "Ulaanbaatar.", ["mongolia", "capital", "ulaanbaatar"]),
    ("quick tangent: is rust worth learning this year", "If you do systems work, yes — the borrow checker pays off after the first month.", ["rust"]),
    ("also what model are you running on", "I'm an AI coding assistant; the exact model depends on your plan settings.", ["model"]),
    ("off topic but recommend a mechanical keyboard", "A tenkeyless with tactile switches is a safe default; try a few switch samples first.", ["keyboard", "mechanical"]),
    ("hey what's the eth price looking like today", "I don't have live prices — check your exchange or a price feed.", ["eth price", "price"]),
    ("btw settle a debate: tabs or spaces", "Whatever the repo's formatter says — consistency beats preference.", ["tabs", "spaces"]),
    ("can you also tell me a programming joke", "Why do programmers prefer dark mode? Because light attracts bugs.", ["joke"]),
]

def build_transcript(rng, topic, with_sidequest):
    lines = [f"User: {rng.choice(OPENERS)}{topic['req']}", f"Claude: {topic['plan']}"]
    n_follow = rng.randint(0, 2)
    follows = rng.sample(FOLLOWUPS, k=n_follow)
    sq = rng.choice(SIDEQUESTS) if with_sidequest else None
    segs = [f"User: {u}\nClaude: {a}" for u, a in follows]
    if sq:
        pos = rng.randint(0, len(segs))
        segs.insert(pos, f"User: {sq[0]}\nClaude: {sq[1]}")
    for s in segs:
        lines.append(s)
    return "\n".join(lines), (sq[2] if sq else [])

def label_json(topic):
    return json.dumps({"title": topic["title"], "desc": topic["desc"], "tab": topic["tab"]},
                      separators=(", ", ": "))

def example(rng, topic, with_sidequest):
    text, sq_kw = build_transcript(rng, topic, with_sidequest)
    msgs = [{"role": "system", "content": SYS},
            {"role": "user", "content": text},
            {"role": "assistant", "content": label_json(topic)}]
    meta = {"kw": topic["kw"], "sq_kw": sq_kw, "title": topic["title"]}
    return {"messages": msgs}, meta

def main():
    rng = random.Random(1337)
    for t in TOPICS + HELDOUT:  # label sanity: obey the limits we're teaching
        assert len(t["title"].split()) <= 5, t["title"]
        assert len(t["desc"].split()) <= 12, t["desc"]
        assert len(t["tab"].split()) <= 2, t["tab"]
    os.makedirs("data", exist_ok=True)

    train, valid = [], []
    for i in range(14):  # 14 passes x 66 topics ≈ 920 examples
        for topic in TOPICS:
            ex, _ = example(rng, topic, with_sidequest=(rng.random() < 0.35))
            (valid if rng.random() < 0.07 else train).append(ex)
    rng.shuffle(train)

    # dedicated rng: editing the train topic bank must never shift the test set
    # (data/test*.jsonl in git is canonical — regenerating still changes vs the
    # original tangled-stream files, so diff before trusting a regen)
    trng = random.Random(9999)
    test, test_meta = [], []
    for i in range(10):  # 10 passes x 12 held-out topics = 120 test examples
        for topic in HELDOUT:
            ex, meta = example(trng, topic, with_sidequest=(trng.random() < 0.5))
            ex_eval = {"messages": ex["messages"][:2]}  # no answer — model must produce it
            test.append(ex_eval); test_meta.append(meta)

    for name, rows in [("train", train), ("valid", valid), ("test", test), ("test_meta", test_meta)]:
        with open(f"data/{name}.jsonl", "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
    print(f"train={len(train)} valid={len(valid)} test={len(test)}")

if __name__ == "__main__":
    main()
