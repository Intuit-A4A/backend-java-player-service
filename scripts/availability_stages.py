#!/usr/bin/env python3
"""Repeat the same overload test after each availability change.

Workload: a peer accepts LLM connections and never responds.
50 chat calls are held open. Then player calls must finish within 5s.
Player availability covers both GET /v1/players and GET /v1/players/{id}:
HTTP 200 within 5s, over all of those attempts.
Chat fast-fail = chat calls that returned within 2s (503/500), not still hanging.
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
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JAR = ROOT / "target" / "player-service-java-0.0.1-SNAPSHOT.jar"
OUT = ROOT / "craft-demo" / "results" / "stages"
BASE = "http://127.0.0.1:8080"
PLAYER_ID = "aardsda01"
STAGES = ["baseline", "decouple", "timeouts", "retry", "breaker"]
CHAT_BURST = 50
PLAYER_SAMPLES = 6
LIST_SAMPLES = 6
PLAYER_TIMEOUT = 5
CHAT_HOLD_TIMEOUT = 30

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


def http_call(path, timeout):
    started = time.time()
    code = 0
    body = ""
    try:
        with urllib.request.urlopen(BASE + path, timeout=timeout) as resp:
            code = resp.status
            body = resp.read(300).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        code = exc.code
        body = exc.read(300).decode("utf-8", "replace")
    except Exception as exc:
        code = 0
        body = type(exc).__name__
    return code, time.time() - started, body


def start_app(stage, extra_args=None):
    cmd = [JAVA, "-jar", str(JAR)]
    if stage != "baseline":
        cmd.append(f"--spring.profiles.active={stage}")
    if extra_args:
        cmd.extend(extra_args)
    proc = subprocess.Popen(
        cmd,
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    if not wait_until(BASE + "/v1/reliability/mode"):
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


def capped_chat(timeout):
    code, elapsed, body = http_call("/v1/chat/list-models", timeout)
    return {
        "http": code,
        "seconds": round(elapsed, 2),
        "finished": bool(code),
        "body": body[:180],
    }


def run_stage(stage):
    proc = start_app(stage)
    mode = json.load(urllib.request.urlopen(BASE + "/v1/reliability/mode", timeout=3))

    # One admitted call. Read timeout is 120s until the retry stage, so cap the wait at 8s.
    admitted = capped_chat(8)

    breaker_followup = None
    if stage == "breaker":
        capped_chat(8)
        capped_chat(8)
        breaker_followup = capped_chat(3)

    results = []

    def one_chat():
        code, elapsed, _body = http_call("/v1/chat/list-models", CHAT_HOLD_TIMEOUT)
        results.append((code, elapsed))

    threads = [threading.Thread(target=one_chat, daemon=True) for _ in range(CHAT_BURST)]
    for thread in threads:
        thread.start()
    time.sleep(1.5)

    by_id = []
    for _ in range(PLAYER_SAMPLES):
        code, elapsed, _body = http_call(f"/v1/players/{PLAYER_ID}", PLAYER_TIMEOUT)
        by_id.append((code, elapsed))
    listed = []
    for _ in range(LIST_SAMPLES):
        code, elapsed, _body = http_call("/v1/players", PLAYER_TIMEOUT)
        listed.append((code, elapsed))
    time.sleep(0.5)
    stop_proc(proc)
    for thread in threads:
        thread.join(timeout=2)

    players = by_id + listed
    player_attempts = len(players)
    player_ok = sum(1 for code, _ in players if code == 200)
    by_id_ok = sum(1 for code, _ in by_id if code == 200)
    list_ok = sum(1 for code, _ in listed if code == 200)
    chat_fast = sum(1 for code, elapsed in results if code and elapsed < 2)
    summary = {
        "stage": stage,
        "mode": mode,
        "admittedChat": admitted,
        "breakerFollowup": breaker_followup,
        "playerSamples": player_attempts,
        "playerByIdSamples": PLAYER_SAMPLES,
        "playerByIdSuccess": by_id_ok,
        "playerListSamples": LIST_SAMPLES,
        "playerListSuccess": list_ok,
        "playerSuccess": player_ok,
        "playerAvailabilityPct": round(100.0 * player_ok / player_attempts, 1),
        "playerLatencySec": [round(elapsed, 2) for _, elapsed in players],
        "chatBurst": CHAT_BURST,
        "chatFastFailWithin2s": chat_fast,
        "chatFastFailPct": round(100.0 * chat_fast / CHAT_BURST, 1),
    }
    print(json.dumps({
        "stage": stage,
        "playerAvailabilityPct": summary["playerAvailabilityPct"],
        "playerById": f"{by_id_ok}/{PLAYER_SAMPLES}",
        "playerList": f"{list_ok}/{LIST_SAMPLES}",
        "chatFastFailPct": summary["chatFastFailPct"],
        "admittedChat": admitted,
        "breakerFollowup": breaker_followup,
    }))
    return summary


def main():
    chosen = sys.argv[1:] or STAGES
    unknown = [name for name in chosen if name not in STAGES]
    if unknown:
        raise SystemExit("unknown stage %s; choose from %s" % (unknown, STAGES))
    OUT.mkdir(parents=True, exist_ok=True)
    subprocess.run(["docker", "stop", "ollama"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # free 8080
    subprocess.run("lsof -ti :8080 | xargs kill -9 2>/dev/null || true", shell=True)
    time.sleep(0.5)
    stop = threading.Event()
    hanger = threading.Thread(target=hang_server, args=(stop,), daemon=True)
    hanger.start()
    time.sleep(0.3)
    def connect_probe(stage):
        proc = start_app(stage, ["--app.chat.ollama-base-url=http://192.0.2.1:11434"])
        sample = capped_chat(6)
        stop_proc(proc)
        print(json.dumps({"stage": stage, "connectStall": sample}))
        return sample

    all_results = []
    try:
        for stage in chosen:
            print(f"== {stage} ==")
            summary = run_stage(stage)
            summary["connectStall"] = connect_probe(stage)
            all_results.append(summary)
            (OUT / f"{stage}.json").write_text(json.dumps(summary, indent=2))
            time.sleep(0.3)
    finally:
        stop.set()
        subprocess.run(["docker", "start", "ollama"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if chosen == STAGES:
        (OUT / "summary.json").write_text(json.dumps(all_results, indent=2))
        print("wrote", OUT / "summary.json")
    else:
        print("wrote", ", ".join(str(OUT / f"{stage}.json") for stage in chosen))


if __name__ == "__main__":
    main()
