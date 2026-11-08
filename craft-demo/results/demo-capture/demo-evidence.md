# Demo evidence — before vs after

**Goal:** show fixes without decoding a dense Grafana screenshot. Use this page + [`../dashboard/presenter-scorecard.md`](../dashboard/presenter-scorecard.md) on screen; keep Grafana for optional drill-down.

| § | Before | After (this branch) | How we captured it |
|---|--------|---------------------|-------------------|
| **2.2 / 3.2 DB errors** | `getPlayerById` catches **any** `Exception` → **404** on dropped table ([`main` `PlayerService`](../../../src/main/java/com/app/playerservicejava/service/PlayerService.java)) | **500** `player data unavailable` | Live curl after `DROP TABLE` — see latest [`summary.md`](./20251108-084852-after/summary.md) §3.2 |
| **2.3 / 3.3 list bounds** | `findAll()` — one huge JSON (~19k rows on laptop) | Default **50**/page, max **100**; metadata `totalElements` / `totalPages` | Live: default **~23 KB** vs `size=10` **~4.7 KB** (same capture) |
| **2.1 / 3.1 observability** | No **8081**, no SLI, scrape competes with API pool | **8081** prometheus; `/v1/reliability/sli`; busy/max Tomcat metrics | Live curls in capture; peak busy **40** under ramp JSON |
| **2.4 / 3.4 chat vs players** | Sync chat, **120s** read; pool **40/40** | `timeouts` profile: async + **2s**; players **28/28** **200** | [`ramp-baseline.json`](../dashboard/ramp-baseline.json) vs [`ramp-timeouts.json`](../dashboard/ramp-timeouts.json) → scorecard |

---

## Live curl captures (after)

Latest automated run: **`craft-demo/results/demo-capture/20251108-084852-after/summary.md`**

Re-run (⚠️ **drops `PLAYERS`** — restart JVM after):

```bash
sh scripts/demo_capture.sh
```

### Highlights from 2026-11-08 capture

| Check | Result |
|-------|--------|
| Unknown id | **404** (empty body) |
| `?size=101` | **400** `size must not exceed 100` |
| Default list vs `?page=0&size=10` | **23332** vs **4691** bytes |
| After `DROP TABLE`, `aardsda01` | **500** + `InvalidDataAccessResourceUsageException` |
| `/v1/reliability/mode` (idle) | `stage: baseline`, `asyncEnabled: false` |
| Readiness | **UP**, includes **db** only |

---

## Ramp (before profile vs after profile)

Same hang peer on **11434**. Full tables: [`ramp-comparison.md`](../dashboard/ramp-comparison.md).

| Signal | Before (`baseline`) | After (`timeouts`) |
|--------|---------------------|---------------------|
| Peak Tomcat busy | **40** | **~2** |
| Player `http_200` | **6** each list + by-id | **28** each |
| Player `client_timeout` | **22** each | **0** |
| Chat | mostly `client_timeout` | **84** × `http_503` |

**Presenter one-pager:** [`presenter-scorecard.md`](../dashboard/presenter-scorecard.md) (includes **per player API** before/after).

**Grafana (frozen):** [`../dashboard/screenshots/`](../dashboard/screenshots/) — use `grafana-ramp-annotated.png` on screen; re-run `sh scripts/capture_grafana_screenshots.sh` after a fresh ramp if panels are empty.

**45 min script:** [`../../presenter-45min.md`](../../presenter-45min.md) · **Slides:** [`../../slides.md`](../../slides.md).

---

## Better than the Grafana screenshot

| Problem with screenshot | Use instead |
|-------------------------|-------------|
| Multiple time series, easy to misread | **`presenter-scorecard.md`** — one comparison table |
| `client_timeout` not an HTTP status — invisible in status panels | **`ramp-comparison.md`** / JSON **totalsByApi** |
| Busy thread spike is subtle | Say aloud: **“40 of 40”** from scorecard; optional Grafana only on Tomcat row |
| Annotated PNG goes stale | Re-run ramp + `render_ramp_scorecard.py`; commit JSON |

**Recommended live layout**

1. Terminal — one curl (404 vs 500, or small page JSON).
2. Browser tab — **`presenter-scorecard.md`** rendered in IDE or exported PDF.
3. Grafana — optional second monitor; last **15m**, point at **Tomcat busy** panel only.

**Optional Grafana tweak (future):** add a **stat** panel at top: `tomcat_threads_busy_threads` with threshold red at 40; add text panel linking to scorecard — keep time series below for engineers.
