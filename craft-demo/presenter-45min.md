# 45-minute plan

This is the run-of-show. Three other files, and nothing else, on the day:

| Role | File |
|------|------|
| Plan | this file |
| Slides | [`Player-Service-Availability.pptx`](Player-Service-Availability.pptx) — import into Google Slides |
| Commands | [`commands.md`](commands.md) |
| Numbers | [`results/dashboard/presenter-scorecard.md`](results/dashboard/presenter-scorecard.md) |
| Frozen charts | [`results/dashboard/screenshots/`](results/dashboard/screenshots/) |

`demo.md` is the written design narrative. It is not part of the live set.

---

## Before they walk in

| Tab | What |
|-----|------|
| 1 | Google Slides, slide 1 |
| 2 | Terminal, [`commands.md`](commands.md) “Talk order” |
| 3 | `presenter-scorecard.md` |
| 4 | `screenshots/grafana-pagination-side-by-side.png` |
| 5 | `screenshots/grafana-ramp-annotated.png` |

App up on **8080** / **8081** (baseline is fine until the chat section). Grafana optional. Do not start from a JVM that just had `DROP TABLE`.

```bash
java -jar target/player-service-java-0.0.1-SNAPSHOT.jar
```

---

## Clock

| Min | Slides | What they see | Live |
|-----|--------|---------------|------|
| 0–4 | 1–4 | Bar for the talk, then the ports and the two paths | Pitch only |
| 4–12 | 5–9 | Four problems, one slide each | None |
| 12–14 | 10 | Problem → fix map | None |
| 14–18 | 11–13 | Observability path and the three signals | Readiness + `/v1/reliability/mode` |
| 18–22 | 14 | 404 vs 500 | Unknown-id curl. Drop-table only if rehearsed |
| 22–28 | 15–17 | Offset paging, then the two-jar load | `size=10` and `size=101`, then the pagination PNG |
| 28–32 | 18–19 | Chat leaves the request thread | Say the profile switch. Live 503 only if `timeouts` is already up |
| 32–38 | 20–21 | Scorecard | Read the player rows. Then the ramp PNG |
| 38–42 | 22–24 | Impact, learnings, second JVM | None |
| 42–45 | 25 | Q&A | Code only if they ask |

---

## What to say

### 0–4 — Open (slides 1–4)

“Player API and chat share one Tomcat. I kept player calls returning 200 while chat is stuck on a model that accepts the socket and never answers. Chat 503 is fine. A player client timeout is not.”

Slide 3 is the port picture. Slide 4 is why they share a fate: one pool, list and chat both hold a worker.

### 4–12 — Problems (slides 5–9)

About 90 seconds each.

- **2.1** A scrape on 8080 goes blank when the pool is full. You lose the picture at the moment you need it.
- **2.2** Every exception becomes an empty Optional, and empty becomes 404. A missing table looks like a missing player.
- **2.3** `findAll()` returns ~19k players, about 9 MB, on one worker. A slow 200 still counts as success.
- **2.4** Forty hung chats, 120 seconds each, fill the pool. The next player call never starts.

### 12–18 — Observability (slides 10–13)

Slide 10 is the map. Then the scrape path: finished responses and busy threads leave on **8081**, so the picture survives a full pool.

Live, from [`commands.md`](commands.md):

```bash
curl -s localhost:8081/actuator/health/readiness
curl -s localhost:8080/v1/reliability/mode
```

Say the three signals out loud: busy threads are capacity, status bars are work that finished, `client_timeout` is only in the ramp JSON.

### 18–22 — Errors (slide 14)

```bash
curl -si localhost:8080/v1/players/no-such-player | head -n 1
```

Expected: **404**. Then: “Drop the table and the same real id is **500**, not another 404. I will not drop it now; the capture is in the evidence note.” Run the H2 block in `commands.md` only if you can restart before the next curl.

### 22–28 — Pagination (slides 15–17)

Slide 15 is the choice: offset now, cursor when deep pages matter.

```bash
curl -s 'localhost:8080/v1/players?page=0&size=10'
curl -si 'localhost:8080/v1/players?size=101' | head -n 1
```

Expected: 10 rows, `totalElements` about **19370**, then **400**.

Slide 17 is the load, not a live run. Open `grafana-pagination-side-by-side.png`. Left, unbounded jar, **10×500**. Right, paged jar, **30×200** and no 5xx. Both heaps were 128 MB.

### 28–32 — Chat (slides 18–19)

“Baseline holds the Tomcat worker for the whole read, up to 120 seconds. The timeouts profile hands the read to an 8-thread pool with no queue and a 2 second timeout. The hang peer does not change. Chat becomes 503. The player worker is free.”

Skip `docker stop` unless that profile is already the running process.

### 32–38 — Proof (slides 20–21)

Read the scorecard, do not re-derive it:

- `GET /v1/players` and `GET /v1/players/{id}`: **6×200** and **22×client_timeout** → **28×200**
- Tomcat busy: **40 / 40** → **2 / 40**
- Chat: client timeout → **503**

Then `grafana-ramp-annotated.png`. “Grafana counts responses the server finished. The timeouts the client felt are the JSON, which is why the scorecard is the slide.”

### 38–45 — Close and questions (slides 22–25)

Impact and learnings can be one minute each. Slide 24 only if they ask about replicas. Slide 25 is the leave-behind: readiness is H2, offset before cursor, client timeouts are not HTTP status, the team model is a separate process.

If they want code: `PlayerExceptionHandler`, `PlayerController` page cap, `ChatController` `Callable`.

---

## If the clock slips

| They want | Cut | Keep |
|-----------|-----|------|
| More live | Slides 22–24 | Four curls + scorecard |
| More slides | The drop-table story and the chat curl | Pagination PNG + scorecard |
| Code | Learnings spoken, not read | Scorecard still goes on screen |

Do not run `ramp_load_test.py` in the room.

---

## Night before

```bash
python3 scripts/ramp_load_test.py baseline
python3 scripts/ramp_load_test.py timeouts
python3 scripts/render_ramp_scorecard.py
python3 scripts/build_google_slides.py
```

Re-import the pptx if the slide text changed. `sh scripts/demo_capture.sh` drops `PLAYERS`; restart the app after it.

---

## Checklist

- [ ] Google Slides deck is the pptx, starting on slide 1
- [ ] App answers `GET /v1/players/aardsda01` with **200**
- [ ] Scorecard matches `ramp-baseline.json` and `ramp-timeouts.json`
- [ ] Pagination PNG and ramp PNG open at projector width
- [ ] `commands.md` talk-order block is the only terminal tab
