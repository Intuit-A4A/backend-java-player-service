# Craft Demo: Improving Availability (Player Service)

**Branch:** `craft-demo/availability` (changes) · **`main`** = initial setup only  
**Profiles:** `legacy` = problem/baseline · `hardened` = after (default)

---

## Speaker outline (map to 4 beats)

| Beat | Craft section | Time |
|------|---------------|------|
| 1. Initial setup on `main` | Context | ~8 min |
| 2. Problem + baseline metrics | Clearly defining the problem | ~12 min |
| 3. Code walk + live fail | Approach, Challenges, Solutions | ~25 min |
| 4. After metrics + close | Impact + Learnings | ~10 min |
| Buffer / Q&A | | ~5 min |

---

## Clearly defining the problem

### What broke (user-visible)

Player Service has two paths:

- **Core:** `GET /v1/players` (must stay up)
- **Secondary:** `GET /v1/chat/*` via local Ollama (nice-to-have)

In the **legacy** design, an Ollama outage was treated as a *service* outage:

1. **Readiness included Ollama** → probe returns **HTTP 503** → orchestrator/LB stops sending traffic even though players still work.
2. **Availability was “all endpoints”** → a small chat error share (realistic ~1% of traffic) pulled perceived availability from **99.9% → ~99.0%** (misses a 99.9% SLO). Equal traffic is only a teaching extreme (~50%).
3. **Slow fail** on LLM (long timeout) made the secondary path worse under failure.

### Problem statement (say this)

> We measured “is the JVM up?” and “did any route fail?” instead of “can users complete the core player API within SLO?” A non-critical dependency (Ollama) could drain healthy player traffic and tank perceived availability.

### Success criteria

- Core path availability (players) stays high when Ollama is down
- Readiness stays **UP** if DB is healthy, even if Ollama is down
- Chat fails fast and stays isolated (still `503` on chat only)
- Availability math matches that product definition

---

## How we measure availability (important)

### Definition used in this demo

For a time window after `POST /v1/reliability/sli/reset`:

\[
\text{availability} = 1 - \frac{\text{5xx}}{\text{total}} = \frac{\text{successes}}{\text{total}}
\]

where **success** = HTTP status **&lt; 500**.

Tracked separately:

| SLI | What | Role |
|-----|------|------|
| `players.*` | `/v1/players*` | **Core availability** (SLO target **99.9%**) |
| `chat.*` | `/v1/chat*` | Dependency / feature SLO (separate) |
| `coreAvailability` | players only | What we commit to for “the service” |
| `perceivedAvailability` | legacy: blend players+chat · hardened: = core | Wrong vs right definition |

Implementation: `SliRecordingFilter` + `SliTracker`; snapshot at `GET /v1/reliability/sli` (includes `*Pct` strings for presenting).

### Production-like traffic mix (default script)

To avoid the unrealistic **50% → 100%** jump, the default load is:

| Requests | Count | Why |
|----------|------:|-----|
| `GET /v1/players/{id}` | **1000** | Core traffic |
| `GET /v1/chat/list-models` | **9** | ~0.9% secondary traffic while Ollama is down |
| Injected player 5xx | **1 / 1000** | `demo-player-error-every=1000` → core noise |

**Expected math (Ollama down):**

| Mode | Formula | Result |
|------|---------|--------|
| Legacy perceived | \(999 / (1000 + 9)\) | **99.01%** (misses 99.9% SLO) |
| Hardened core / perceived | \(999 / 1000\) | **99.90%** (meets SLO) |

Optional teaching extreme (equal mix): `MIX=equal ./scripts/availability-demo.sh baseline` → ~50% blend.

### Complementary signal (not the same as availability %)

| Signal | Measures | Why it matters |
|--------|----------|----------------|
| `/actuator/health/readiness` | Should this instance receive traffic? | Ollama in readiness drains player traffic |
| `/v1/reliability/dependencies` | Ollama up/down without coupling | Observe LLM without failing readiness |
| Latency (`avgLatencyMs`) | Speed | Separate from availability % |

**Demo headline when Ollama is stopped (realistic mix):**

| | Legacy (wrong) | Hardened (right) |
|--|----------------|------------------|
| Readiness | **503 DOWN** | **200 UP** |
| Perceived availability | **~99.01%** | **99.90%** |
| Meets 99.9% SLO? | **No** | **Yes** |

Results: `craft-demo/results/` (`comparison-summary.json`).

---

## Approach, Challenges, Solutions

### Approach (3 levers)

1. **Define the SLO correctly** — core = players only; chat is a separate budget.
2. **Isolate the dependency from traffic control** — readiness = DB (+ readinessState), not Ollama.
3. **Fail fast on the secondary path** — shorter Ollama timeout; don’t block the process on LLM.

Optional for *showing* the story (demo instrumentation): in-process SLI counters, dual profiles, scripted outage.

### Challenges → Solutions

| Challenge | Solution |
|-----------|----------|
| Partial failure looks like total outage | Split SLIs; readiness excludes Ollama in hardened |
| “Health” endpoint conflated with “ready for traffic” | Use `/actuator/health/readiness` as the traffic signal; keep dependency check on `/v1/reliability/dependencies` |
| Need a crisp before/after in 60 min | `legacy` vs `hardened` profiles + `scripts/availability-demo.sh` |
| Metrics noise / “did we improve?” | Reset SLI window, fixed request counts (script), compare JSON artifacts |

### Must-have vs demo-only

**Must-have to actually improve availability (the fix):**

| Change | Why |
|--------|-----|
| Readiness **without** Ollama | Stops draining player traffic on LLM outage |
| Core SLO = players only (concept + alerts in real prod) | Stops chat failures from defining “service down” |
| Shorter Ollama timeout | Faster failure on chat; frees threads |

**Demo / teaching aids (not required for the fix itself):**

| Change | Why it’s here |
|--------|----------------|
| `SliTracker` / `SliRecordingFilter` / `/v1/reliability/sli` | Make availability % visible without Prometheus UI |
| `legacy` + `hardened` profiles | Toggle “before” and “after” without two codebases |
| `availability-demo.sh` + `craft-demo/results` | Repeatable outage + captured evidence |
| `demo-player-error-every=1000` | Deterministic 0.1% player 5xx so after = **99.9%** not 100% |
| Realistic 1000:10 traffic mix | Shows **99.01% → 99.90%** instead of 50% → 100% |
| `RequestIdFilter` | Ops hygiene; not required for the formula |
| Actuator Prometheus | Optional if SLI JSON is enough |
| ollama4j bump + import fix | Chat works with modern Ollama; separate from availability |

**For the Craft Demo, keep the dual profiles + SLI endpoint + readiness split.** You can skip deep-diving Prometheus/requestId if short on time.

---

## Impact

From a captured local run (`craft-demo/results/comparison-summary.json`) with Ollama stopped:

| Metric | Baseline | After |
|--------|----------|-------|
| Readiness HTTP | 503 | 200 |
| Perceived availability | **~99.01%** | **99.90%** |
| Core (players) availability | 99.90% | **99.90%** |
| Meets 99.9% SLO (perceived/core as defined) | **No** (blend) | **Yes** |

**Business framing:** same underlying player reliability, but the *definition* + readiness isolation stop a ~1% chat outage from burning the error budget and draining traffic.

---

## Learnings

1. **Availability is a definition, then a number** — wrong blend → wrong pages and wrong postmortems.
2. **Readiness ≠ “all dependencies green”** — only block traffic for dependencies on the critical path.
3. **Isolate non-critical features** — LLM outage must not own the core SLO.
4. **Measure what you promise** — SLI windows, success criteria (&lt;500), separate budgets.
5. **Instrumentation is how you prove impact** — but don’t confuse demo counters with the actual reliability change (readiness + isolation + timeouts).

---

## Demo logistics: terminal or not?

**Yes — plan to run from the terminal** (or IDE HTTP client). The story is stronger with a live Ollama stop and readiness flip.

### Recommended live path (minimal commands)

**Beat 1 — `main` (initial setup only)**

```bash
git checkout main
mvn spring-boot:run
# curl localhost:8080/v1/players
# curl localhost:8080/v1/chat/list-models
```

**Beat 2–4 — feature branch**

```bash
git checkout craft-demo/availability

# Baseline (problem)
mvn spring-boot:run -Dspring-boot.run.profiles=legacy
# other terminal:
./scripts/availability-demo.sh baseline

# After (fix) — restart app first
mvn spring-boot:run   # hardened default
./scripts/availability-demo.sh after
```

**Backup if live Docker/Ollama flakes:** open pre-captured JSON under `craft-demo/results/` and narrate the same table (don’t depend only on live).

### Manual “show the problem” without the script

```bash
curl -s localhost:8080/v1/reliability/mode
curl -s -X POST localhost:8080/v1/reliability/sli/reset
docker stop ollama
curl -s -o /dev/null -w "%{http_code}\n" localhost:8080/v1/players
curl -s -o /dev/null -w "%{http_code}\n" localhost:8080/v1/chat/list-models
curl -s -o /dev/null -w "%{http_code}\n" localhost:8080/actuator/health/readiness
curl -s localhost:8080/v1/reliability/sli
docker start ollama
```

---

## Profile cheat sheet

| Profile | Start | Readiness includes Ollama? | Timeout | SLI blend |
|---------|-------|----------------------------|---------|-----------|
| `legacy` | `-Dspring-boot.run.profiles=legacy` | Yes | 10s | players+chat |
| `hardened` | default / `profiles=hardened` | No | 3s | players only |
