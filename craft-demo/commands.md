# Commands

Copy-paste for the talk and the night-before rebuild. The plan is [`presenter-45min.md`](presenter-45min.md). Do not run the ramp or `DROP TABLE` live unless you have rehearsed the restart.

```bash
export JAVA_HOME="/opt/homebrew/opt/openjdk@17"
export PATH="$JAVA_HOME/bin:$PATH"
cd ~/git/player-service-java
```

---

## Start

Branch app, baseline profile (chat on the Tomcat thread, 120s read):

```bash
mvn -DskipTests package
java -jar target/player-service-java-0.0.1-SNAPSHOT.jar
```

Same jar, `timeouts` profile (async chat, 2s read):

```bash
java -jar target/player-service-java-0.0.1-SNAPSHOT.jar --spring.profiles.active=timeouts
```

Prometheus + Grafana:

```bash
sh craft-demo/observability/up.sh
# http://localhost:3000/d/availability/availability
# http://localhost:3000/d/pagination-compare/pagination-e28094-same-list-load
```

Ollama, when you want a real model instead of the hang peer:

```bash
colima start
docker start ollama
until curl -sf http://127.0.0.1:11434/api/tags >/dev/null; do sleep 2; done
```

Smoke:

```bash
curl -s -o /dev/null -w "list %{http_code}\n" localhost:8080/v1/players
curl -s -o /dev/null -w "by-id %{http_code}\n" localhost:8080/v1/players/aardsda01
curl -si localhost:8080/v1/players/no-such-player | head -n 1
```

---

## Talk order

### 3.2 — 404 vs 500

Unknown id stays 404:

```bash
curl -si localhost:8080/v1/players/no-such-player | head -n 1
```

Dropped table is 500 on this branch. This destroys in-memory `PLAYERS`. Restart the JVM afterward so the CSV reloads.

```bash
jsession=$(curl -s http://localhost:8080/h2-console/ | sed -n 's/.*jsessionid=\([a-f0-9]*\).*/\1/p')
curl -s -o /dev/null "http://localhost:8080/h2-console/login.jsp?jsessionid=$jsession"
curl -s -o /dev/null \
  --data-urlencode 'language=en' \
  --data-urlencode 'setting=Generic H2 (Embedded)' \
  --data-urlencode 'name=Generic H2 (Embedded)' \
  --data-urlencode 'driver=org.h2.Driver' \
  --data-urlencode 'url=jdbc:h2:mem:playerdb' \
  --data-urlencode 'user=sa' \
  --data-urlencode 'password=' \
  "http://localhost:8080/h2-console/login.do?jsessionid=$jsession"
curl -s -o /dev/null \
  --data-urlencode 'sql=DROP TABLE PLAYERS' \
  "http://localhost:8080/h2-console/query.do?jsessionid=$jsession"
curl -si localhost:8080/v1/players/aardsda01 | head -n 20
```

### 3.3 — pagination

```bash
curl -s 'localhost:8080/v1/players?page=0&size=10' | python3 -c 'import sys,json; d=json.load(sys.stdin); print({k:d[k] for k in ("page","size","totalElements","totalPages")}, "rows", len(d["players"]))'
curl -s -o /dev/null -w "default %{http_code} %{size_download}B %{time_total}s\n" localhost:8080/v1/players
curl -s -o /dev/null -w "size10 %{http_code} %{size_download}B %{time_total}s\n" 'localhost:8080/v1/players?page=0&size=10'
curl -si 'localhost:8080/v1/players?size=101' | head -n 1
```

Same load on the unbounded jar and the paged jar (both `-Xmx128m`). Not a live step.

```bash
sh scripts/build_demo_main_jar.sh
sh scripts/start_dual_jars.sh
python3 scripts/pagination_load_compare.py
```

### 3.1 — observability

```bash
curl -s localhost:8081/actuator/health/liveness | python3 -m json.tool
curl -s localhost:8081/actuator/health/readiness | python3 -m json.tool
curl -s localhost:8081/actuator/prometheus | grep -E 'tomcat_threads_busy_threads|tomcat_threads_config_max_threads'
curl -s localhost:8080/v1/reliability/mode | python3 -m json.tool
curl -s -X POST localhost:8080/v1/reliability/sli/reset >/dev/null
curl -s -o /dev/null localhost:8080/v1/players/aardsda01
curl -s localhost:8080/v1/reliability/sli | python3 -m json.tool
```

### 3.4 — chat

Refused TCP fails fast. The ramp uses a hang peer instead (accepts, never replies).

```bash
docker stop ollama
curl -s -m 5 -w "models %{http_code} in %{time_total}s\n" localhost:8080/v1/chat/list-models
curl -s -o /dev/null -w "player %{http_code}\n" localhost:8080/v1/players/aardsda01
docker start ollama
```

On the `timeouts` profile the same chat call returns **503** in about 2s while the player call stays **200**. Readiness stays **UP** with Ollama down, because readiness is the database only.

---

## Ramp (night before, not live)

Stop the jar first. The script starts its own JVM and a hang peer on **11434**.

```bash
python3 scripts/ramp_load_test.py baseline
python3 scripts/ramp_load_test.py timeouts
python3 scripts/render_ramp_scorecard.py
```

Checked-in result: player routes **6×200 + 22×client_timeout** → **28×200**; Tomcat busy **40** → **2**.

---

## Rebuild slides and screenshots

```bash
python3 scripts/build_google_slides.py
sh scripts/capture_grafana_screenshots.sh
```

Import `craft-demo/Player-Service-Availability.pptx` into Google Slides.

`sh scripts/demo_capture.sh` rewrites curl evidence and **drops `PLAYERS`**. Restart the app after it.

---

## Optional, if asked

Second JVM. Terminal 1 stays on **8080**. Terminal 2:

```bash
java -jar target/player-service-java-0.0.1-SNAPSHOT.jar \
  --server.port=8082 --management.server.port=8083 --spring.profiles.active=timeouts
curl -s -o /dev/null -w "8080 %{http_code}\n" localhost:8080/v1/players/aardsda01
curl -s -o /dev/null -w "8082 %{http_code}\n" localhost:8082/v1/players/aardsda01
```
