#!/usr/bin/env python3
"""Ramp traffic from idle to Tomcat saturation and record HTTP status per API.

Hang simulation: `docker stop ollama`, then a Python listener on 127.0.0.1:11434
accepts TCP but never sends an HTTP body, so chat does not get 200 until the
client or server gives up.

Usage:
  python3 scripts/ramp_load_test.py baseline
  python3 scripts/ramp_load_test.py timeouts

Writes: craft-demo/results/dashboard/ramp-<stage>.json
Outcome labels: http_200, http_503, client_timeout (no HTTP status from the app).
"""
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JAR = ROOT / "target" / "player-service-java-0.0.1-SNAPSHOT.jar"
JAVA = os.environ.get("JAVA_HOME", "/opt/homebrew/opt/openjdk@17") + "/bin/java"


def hang_server(stop: threading.Event):
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 11434))
    server.listen(256)
    server.settimeout(0.5)

    def hold(conn):
        try:
            conn.settimeout(1)
            try:
                conn.recv(4096)
            except OSError:
                pass
            while not stop.is_set():
                time.sleep(0.2)
        finally:
            try:
                conn.close()
            except OSError:
                pass

    while not stop.is_set():
        try:
            conn, _ = server.accept()
        except socket.timeout:
            continue
        except OSError:
            break
        threading.Thread(target=hold, args=(conn,), daemon=True).start()
    server.close()


def wait_until(url, timeout=40):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if resp.status < 500:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


def start_app(stage):
    cmd = [JAVA, "-jar", str(JAR)]
    if stage != "baseline":
        cmd.append(f"--spring.profiles.active={stage}")
    proc = subprocess.Popen(
        cmd,
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    if not wait_until("http://127.0.0.1:8080/v1/reliability/mode"):
        os.killpg(proc.pid, signal.SIGKILL)
        raise SystemExit(f"app failed to start for stage {stage}")
    return proc


def stop_proc(proc):
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=8)
    except Exception:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except Exception:
            pass

BASE = "http://127.0.0.1:8080"
OUT = ROOT / "craft-demo" / "results" / "dashboard"
PLAYER_ID = "aardsda01"
STEP_SEC = 5
STEPS = 14
CHAT_PER_STEP = 6
PLAYER_PER_STEP = 2
CHAT_CLIENT_TIMEOUT = 12
PLAYER_CLIENT_TIMEOUT = 6
PROM = "http://127.0.0.1:9090"

APIS = [
    ("GET /v1/players", "GET", "/v1/players", None),
    ("GET /v1/players/{id}", "GET", f"/v1/players/{PLAYER_ID}", None),
    ("GET /v1/chat/list-models", "GET", "/v1/chat/list-models", None),
    ("POST /v1/chat", "POST", "/v1/chat", b""),
]

lock = threading.Lock()
events = []


def http(method, path, body=None, timeout=10):
    started = time.time()
    code = 0
    detail = ""
    req = urllib.request.Request(BASE + path, data=body, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = resp.status
            detail = resp.read(200).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        code = exc.code
        detail = exc.read(200).decode("utf-8", "replace")
    except Exception as exc:
        code = 0
        detail = type(exc).__name__
    elapsed = time.time() - started
    return code, elapsed, detail


def outcome_label(code, detail):
    if code == 200:
        return "http_200"
    if code == 503:
        return "http_503"
    if code == 500:
        return "http_500"
    if code == 0:
        d = detail.lower()
        if "timeout" in d or "timed out" in d:
            return "client_timeout"
        return "no_http_response"
    return f"http_{code}"


def record(step, api, code, elapsed, detail=""):
    with lock:
        events.append({
            "t": round(time.time(), 3),
            "step": step,
            "api": api,
            "http": code,
            "outcome": outcome_label(code, detail),
            "seconds": round(elapsed, 3),
            "detail": detail[:120],
        })


def worker(step, api_name, method, path, body, timeout):
    code, elapsed, detail = http(method, path, body, timeout)
    record(step, api_name, code, elapsed, detail)


def prom_value(expr):
    url = PROM + "/api/v1/query?" + urllib.parse.urlencode({"query": expr})
    try:
        with urllib.request.urlopen(url, timeout=3) as resp:
            payload = json.load(resp)
        series = payload.get("data", {}).get("result", [])
        if not series:
            return None
        return float(series[0]["value"][1])
    except Exception:
        return None


def actuator_busy():
    try:
        with urllib.request.urlopen("http://127.0.0.1:8081/actuator/prometheus", timeout=2) as resp:
            for line in resp.read().decode().splitlines():
                if line.startswith("tomcat_threads_busy_threads "):
                    return float(line.rsplit(" ", 1)[1])
    except Exception:
        return None
    return None


def summarize(events_list):
    by_step = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    totals = defaultdict(lambda: defaultdict(int))
    for ev in events_list:
        label = ev.get("outcome") or outcome_label(ev["http"], ev.get("detail", ""))
        by_step[ev["step"]][ev["api"]][label] += 1
        totals[ev["api"]][label] += 1
    return {
        "byStep": {
            str(step): {api: dict(codes) for api, codes in apis.items()}
            for step, apis in sorted(by_step.items())
        },
        "totalsByApi": {api: dict(codes) for api, codes in totals.items()},
    }


def run_stage(stage):
    subprocess.run(["docker", "stop", "ollama"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run("lsof -ti :8080 | xargs kill -9 2>/dev/null || true", shell=True)
    time.sleep(0.5)
    stop = threading.Event()
    hanger = threading.Thread(target=hang_server, args=(stop,), daemon=True)
    hanger.start()
    time.sleep(0.3)

    proc = start_app(stage)
    mode_url = BASE + "/v1/reliability/mode"
    mode = json.load(urllib.request.urlopen(mode_url, timeout=3))

    step_snapshots = []
    inflight = []
    t0 = time.time()

    for step in range(STEPS):
        step_start = time.time()
        launched = []
        for _ in range(CHAT_PER_STEP):
            for api_name, method, path, body in APIS[2:]:
                t = threading.Thread(
                    target=worker,
                    args=(step, api_name, method, path, body, CHAT_CLIENT_TIMEOUT),
                    daemon=True,
                )
                t.start()
                launched.append(t)
        for _ in range(PLAYER_PER_STEP):
            for api_name, method, path, body in APIS[:2]:
                t = threading.Thread(
                    target=worker,
                    args=(step, api_name, method, path, body, PLAYER_CLIENT_TIMEOUT),
                    daemon=True,
                )
                t.start()
                launched.append(t)
        inflight.extend(launched)
        time.sleep(1.0)
        busy = prom_value("tomcat_threads_busy_threads")
        if busy is None:
            busy = actuator_busy()
        snap = {
            "step": step,
            "elapsedSec": round(time.time() - t0, 1),
            "launchedThisStep": len(launched),
            "tomcatThreadsBusy": busy,
            "tomcatThreadsCurrent": prom_value("tomcat_threads_current_threads"),
            "eventsSoFar": len(events),
        }
        step_snapshots.append(snap)
        if step == 8:
            print(
                f"GRAFANA_SNAPSHOT step={step} tomcat_busy={busy} events={len(events)}",
                flush=True,
            )
            time.sleep(25)
        sleep_left = STEP_SEC - (time.time() - step_start)
        if sleep_left > 0:
            time.sleep(sleep_left)

    time.sleep(2)
    stop_proc(proc)
    stop.set()
    for t in inflight:
        t.join(timeout=1)

    subprocess.run(["docker", "start", "ollama"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return {
        "stage": stage,
        "mode": mode,
        "stepSec": STEP_SEC,
        "steps": STEPS,
        "chatPerStep": CHAT_PER_STEP,
        "playerPerStep": PLAYER_PER_STEP,
        "durationSec": round(time.time() - t0, 1),
        "stepSnapshots": step_snapshots,
        "events": events,
        "summary": summarize(events),
    }


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("baseline", "timeouts"):
        raise SystemExit("usage: ramp_load_test.py baseline|timeouts")
    if not JAR.is_file():
        raise SystemExit(f"missing jar: {JAR}")
    stage = sys.argv[1]
    global events
    events = []
    OUT.mkdir(parents=True, exist_ok=True)
    result = run_stage(stage)
    path = OUT / f"ramp-{stage}.json"
    path.write_text(json.dumps(result, indent=2) + "\n")

    totals = result["summary"]["totalsByApi"]
    print(f"wrote {path}")
    print(f"stage={stage} duration={result['durationSec']}s events={len(result['events'])}")
    print("--- response codes by API (totals) ---")
    for api in [a[0] for a in APIS]:
        counts = totals.get(api, {})
        parts = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items(), key=lambda x: -x[1]))
        print(f"  {api}: {parts or '(none finished)'}")
    print("Baseline: Tomcat busy → 40 → player client_timeout. Timeouts: chat 503 (read/connect timeout or pool full); player http_200.")
    peak = max(result["stepSnapshots"], key=lambda s: s["tomcatThreadsBusy"] or 0)
    print(f"peak tomcat busy: {peak['tomcatThreadsBusy']} at step {peak['step']} (~{peak['elapsedSec']}s)")


if __name__ == "__main__":
    main()
