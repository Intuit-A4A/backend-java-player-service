# 45-minute plan

This is the run-of-show. Three other files, and nothing else, on the day:

| Role | File |
|------|------|
| Plan | this file |
| Slides | [`Player-Service-Availability_v3.pptx`](file:///Users/jidongchai/Downloads/Player-Service-Availability_v3.pptx) — 21 slides |
| Commands | [`commands.md`](commands.md) |
| Numbers | [`results/dashboard/presenter-scorecard.md`](results/dashboard/presenter-scorecard.md) |
| Frozen charts | [`results/dashboard/screenshots/`](results/dashboard/screenshots/) |

`demo.md` is the written design narrative. It is not part of the live set. `craft-demo/Player-Service-Availability.pptx` is the generated repo deck, not this talk.

---

## Before they walk in

| Tab | What |
|-----|------|
| 1 | Google Slides, the v3 deck, slide 1 |
| 2 | Terminal, [`commands.md`](commands.md) “Talk order” |
| 3 | `presenter-scorecard.md` |

Slides 17 and 18 are the proof. Slide 15 is the list-load numbers. Read them. Do not re-derive them.

App up on **8080** / **8081** (baseline is fine until the chat section). Grafana optional. Do not start from a JVM that just had `DROP TABLE`.

```bash
java -jar target/player-service-java-0.0.1-SNAPSHOT.jar
```

---

## Clock

| Min | Slides | What they see | Live |
|-----|--------|---------------|------|
| 0–3 | 1–2 | Agenda, two paths, one pool | Pitch only |
| 3–12 | 3–7 | Four failures | None |
| 12–15 | 8 | The bar: 200, 400, or 404 before the client gives up | None |
| 15–17 | 9–10 | Four ports, then the fix map | None |
| 17–21 | 11 | 3.1 second Tomcat on 8081 | Readiness + `/v1/reliability/mode` |
| 21–25 | 12 | 3.2 404 vs 500 | Unknown-id curl. Drop-table only if rehearsed |
| 25–30 | 13–15 | 3.3 bound the list, then the 30-call load | `size=10` and `size=101` |
| 30–34 | 16 | 3.4 chat leaves the request thread | Say the profile switch. Live 503 only if `timeouts` is already up |
| 34–40 | 17–18 | Ramp table, then the chart | Read them |
| 40–43 | 19–20 | Impact, then learnings | None |
| 43–45 | 21 | Beyond this JVM | Code only if they ask |

---

## What to say

### 0–3 — Open (slides 1–2)

“Player API and chat share one Tomcat. I kept player calls returning 200 while chat is stuck on a model that accepts the socket and never answers. Chat 503 is fine. A player client timeout is not.”

Slide 1 is the agenda: system overview, problem, the bar, approach, impact. Slide 2 is the starting shape. Both paths run on the request thread. Chat holds a worker up to 120s. The list is `findAll()`, about 19,370 rows and about 9 MB. By-id stays fast only if a worker is free. Ollama is another process.

### 3–12 — Problems (slides 3–7)

Slide 3 is the four. Slides 4–7 are about 90 seconds each.

- **2.1** On main there is no scrape, no SLI, and no liveness versus readiness. 8081 is a second Tomcat, and its pool is still max 40, so it saturates at 40/40. A finished chart has no client timeout. Process up and H2 up are still not a player 200.
- **2.2** Every exception becomes an empty Optional, and empty becomes 404. A missing table looks like a missing player. The SLI reads the outage as not found.
- **2.3** `findAll()` returns ~19k players, about 9 MB, on one worker. A 90s 200 still passes status below 500. The client timed out. The scorecard says available.
- **2.4** The hang peer accepts and never writes a body. Forty hung chats, 120 seconds each, fill the pool. The next player call never starts. The client sees `client_timeout`. A timeout is not a status. A refused connection fails in milliseconds.

### 12–17 — Bar, ports, map (slides 8–10)

Slide 8 is the bar. A player call is available when `GET /v1/players` or `GET /v1/players/{id}` returns **200**, **400**, or **404** before the client gives up. Process up, H2 up, or an empty scrape does not count. A client timeout is a miss. A stuck model that becomes **503** quickly is isolation, not an outage. Baseline waits 120s on the Tomcat thread for the hang on **11434**.

Slide 9 is four ports. **8080** is player and chat, one pool, and by-id sleeps 0–2s. **8081** is a second Tomcat: scrapes skip 8080, and that pool is still max 40. **11434** is Ollama or the hang peer. **5001** is the k-NN service and is not wired to 8080.

Slide 10 is the map. 3.1 metrics on 8081. 3.2 database errors stay 500. 3.3 offset pages, max size 100. 3.4 async chat and a 2s timeout.

### 17–21 — Observability (slide 11)

8081 is the second Tomcat. Busy threads are capacity. Status is finished work. `client_timeout` is only in the ramp. Readiness is the database, not Ollama. Liveness is the process. A stuck chat is not a restart.

Live, from [`commands.md`](commands.md):

```bash
curl -s localhost:8081/actuator/health/readiness
curl -s localhost:8080/v1/reliability/mode
```

### 21–25 — Errors (slide 12)

```bash
curl -si localhost:8080/v1/players/no-such-player | head -n 1
```

Expected: **404**. Then: “Drop the table and the same real id is **500**, `player data unavailable`, not another 404. I will not drop it now. Restart reloads the CSV.” Run the H2 block in `commands.md` only if you can restart before the next curl.

### 25–30 — Pagination (slides 13–15)

Slide 13 is the choice: offset now, cursor when deep pages matter. The win is one bounded response, not a faster page 20,000.

```bash
curl -s 'localhost:8080/v1/players?page=0&size=10'
curl -si 'localhost:8080/v1/players?size=101' | head -n 1
```

Slide 14 expects 10 rows, `totalElements` about **19370**, **4,691** bytes, then **400**. The default page is **23,332** bytes against a **~9 MB** full roster.

Hold the load for slide 15. Same 30 calls, both jars `-Xmx128m`. Main: **10×500**, **19×200**, **1** incomplete. Branch: **30×200**, **0×5xx**.

### 30–34 — Chat (slide 16)

“Baseline holds the Tomcat worker for the whole read, up to 120 seconds. The timeouts profile hands the read to an 8-thread pool with no queue and a 2 second timeout. The hang peer does not change. Chat becomes 503. The player worker is free.”

Full pool and read timeout return **503**. Skip `docker stop` unless that profile is already the running process.

### 34–40 — Proof (slides 17–18)

Slide 17 is the ramp. Slide 18 is the chart. Read them, do not re-derive them. Same hang peer on **11434**:

- `GET /v1/players` and `GET /v1/players/{id}`: **6×200** and **22×client timeout** → **28×200**
- Player totals: **12×200** and **44×client timeout** of 56 → **56×200**, **0** client timeouts
- Chat: client timeout, no HTTP status → **84×503** per route, about 2 seconds
- Tomcat busy: **40 / 40** → **2 / 40**

“Grafana counts responses the server finished. The timeouts the client felt are the numbers on slide 17.”

### 40–45 — Close (slides 19–21)

Slide 19 is the impact, one pass: see it on 8081 while 8080 is busy, name 500 versus 404, bound each list call to one page, isolate the hang so players stay 200.

Slide 20 can be one minute. Availability is a player response before the client gives up, not “the process is up.” Busy threads, finished status, and client timeout are three facts. More Tomcat threads do not fix a 120s read. A max page size fixes the common case before cursor paging is worth it. Readiness helps only when another replica can take the traffic.

Slide 21 is the leave-behind. Readiness is H2, not Ollama. One JVM can fail while another still serves. In-flight player calls can finish on shutdown. Split chat off the player process. A restart must not be the only copy of the roster.

If they want code: `PlayerExceptionHandler`, `PlayerController` page cap, `ChatController` `Callable`.

---

## If the clock slips

| They want | Cut | Keep |
|-----------|-----|------|
| More live | Slides 20–21 spoken, not read | Four curls + slides 17–18 |
| More slides | The drop-table story and the chat curl | Slides 17 and 18 |
| Code | Learnings spoken, not read | Slide 18 still goes on screen |

Do not run `ramp_load_test.py` in the room.

---

## Night before

```bash
python3 scripts/ramp_load_test.py baseline
python3 scripts/ramp_load_test.py timeouts
python3 scripts/render_ramp_scorecard.py
python3 scripts/render_talk_dashboards.py
```

Those refresh the scorecard and the frozen charts behind slides 15 and 17–18. `python3 scripts/build_google_slides.py` writes the repo pptx. It does not update the v3 deck. `sh scripts/demo_capture.sh` drops `PLAYERS`. Restart the app after it.

---

## Checklist

- [ ] The open deck is `Player-Service-Availability_v3.pptx`, starting on slide 1
- [ ] App answers `GET /v1/players/aardsda01` with **200**
- [ ] Scorecard matches `ramp-baseline.json` and `ramp-timeouts.json`
- [ ] Slides 17 and 18 match the scorecard
- [ ] `commands.md` talk-order block is the only terminal tab
