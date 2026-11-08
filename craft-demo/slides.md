---
marp: true
theme: default
paginate: true
title: Player Service — Availability Craft Demo
---

# Player Service
## Availability under shared Tomcat + hung LLM

**Success criterion:** Player API returns **200** within client deadline while chat is stuck on a hang peer. Chat **503** is OK; player **client_timeout** is not.

---

# Architecture

- **8080** — Player + Chat (Tomcat, max **40**)
- **8081** — Metrics & health (scrape does not steal API workers)
- **11434** — Ollama (or hang peer in demo)
- **H2** — In-memory players from CSV
- **5001** (optional) — `player-service-model` team ML — **not wired to 8080**

---

# Four problems

| # | Problem |
|---|---------|
| **2.1** | No observability — blind under saturation |
| **2.2** | DB outage returned as **404** |
| **2.3** | Unbounded player **list** — availability at scale |
| **2.4** | Sync chat holds Tomcat up to **120s** |

---

# Four solutions (this branch)

| # | Fix |
|---|-----|
| **3.1** | Metrics on **8081**, SLI, Grafana, probes |
| **3.2** | DB errors → **500** |
| **3.3** | Offset pagination — bounded list |
| **3.4** | Async chat + **2s** timeout (`timeouts` profile) |

---

# Player API — ramp scorecard

See **`presenter-scorecard.md`** (from `ramp-*.json`)

| | **Before (baseline)** | **After (timeouts)** |
|---|----------------------|----------------------|
| `GET /v1/players` | 6×200, 22×client_timeout | 28×200 |
| `GET /v1/players/{id}` | 6×200, 22×client_timeout | 28×200 |
| Tomcat busy (peak) | **40** / 40 | **~2** / 40 |

**Story:** Pool fills → players stop finishing → fix decouples chat → players complete.

---

# Evidence (curl + screenshots)

- **`demo-evidence.md`** — before/after curls (404 vs 500, paging bytes)
- **`screenshots/grafana-pagination-side-by-side.png`** — two jars (main vs branch)
- **`screenshots/grafana-dashboard-live-annotated.png`** — availability ramp (live Grafana)
- Do not rely on live Grafana refresh in a 45m slot

---

# Learnings

- Define availability for **player API**, not “process up”
- Observability is part of the fix (8081, MBean, SLI)
- **Busy threads** = capacity; **ramp JSON** = user felt timeouts
- Decouple + short timeout beats “more Tomcat threads”

---

# Q&A hooks

- Readiness: **db** only, not Ollama  
- Pagination: offset now, cursor later  
- `player-service-model` → future `v1/team/*` proxy  
- Replicas & split deployments (§6 in demo.md)
