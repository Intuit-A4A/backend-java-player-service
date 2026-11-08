#!/usr/bin/env python3
"""Build craft-demo/Player-Service-Availability.pptx for Google Slides import."""
from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "craft-demo" / "Player-Service-Availability.pptx"

W, H = 13.333, 7.5
BG = RGBColor(0xF6, 0xF4, 0xF0)
INK = RGBColor(0x1C, 0x19, 0x17)
MUTED = RGBColor(0x57, 0x53, 0x4E)
ACCENT = RGBColor(0x9A, 0x34, 0x12)
NAVY = RGBColor(0x1E, 0x3A, 0x5F)
GREEN = RGBColor(0x16, 0x65, 0x34)
RED = RGBColor(0x99, 0x1B, 0x1B)
CARD = RGBColor(0xFF, 0xFC, 0xF8)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LINE = RGBColor(0xE7, 0xE5, 0xE4)
SAND = RGBColor(0xFD, 0xF2, 0xE9)
MINT = RGBColor(0xEC, 0xFD, 0xF3)
ROSE = RGBColor(0xFE, 0xF2, 0xF2)
NAVY_SOFT = RGBColor(0xE8, 0xEE, 0xF5)


def set_run(run, text, size, color, bold=False, font="Arial"):
    run.text = text
    run.font.size = Pt(size)
    run.font.color.rgb = color
    run.font.bold = bold
    run.font.name = font


def fill_shape(shape, color):
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()


def add_text(slide, l, t, w, h, text, size=16, color=INK, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    tf.margin_left = Inches(0.04)
    tf.margin_right = Inches(0.04)
    tf.margin_top = Inches(0.02)
    p = tf.paragraphs[0]
    p.alignment = align
    set_run(p.add_run(), text, size, color, bold)
    # paragraph was empty; we added a run. Clear default empty run if any.
    # python-pptx paragraphs start with no runs when using add_run only — good.
    box.text_frame.paragraphs[0].alignment = align
    try:
        tf._txBody.bodyPr.set("anchor", {MSO_ANCHOR.TOP: "t", MSO_ANCHOR.MIDDLE: "ctr", MSO_ANCHOR.BOTTOM: "b"}[anchor])
    except Exception:
        pass
    return box


def add_lines(slide, l, t, w, h, lines, size=16, color=INK, bold=False, spacing=6):
    box = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.space_after = Pt(spacing)
        text, is_bold, col = line if isinstance(line, tuple) else (line, bold, color)
        set_run(p.add_run(), text, size, col, is_bold)
    return box


def card(slide, l, t, w, h, fill=CARD):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(l), Inches(t), Inches(w), Inches(h))
    fill_shape(shape, fill)
    shape.adjustments[0] = 0.08
    return shape


def label_in(shape, text, size, color, bold=True, align=PP_ALIGN.CENTER):
    tf = shape.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    tf.margin_left = Inches(0.08)
    tf.margin_right = Inches(0.08)
    tf.margin_top = Inches(0.06)
    p = tf.paragraphs[0]
    p.alignment = align
    set_run(p.add_run(), text, size, color, bold)
    tf._txBody.bodyPr.set("anchor", "ctr")


def new_slide(prs, kicker, title):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(W), Inches(H))
    fill_shape(bg, BG)
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(0.12), Inches(H))
    fill_shape(bar, ACCENT)
    if kicker:
        add_text(slide, 0.45, 0.22, 12, 0.32, kicker.upper(), 12, ACCENT, True)
        add_text(slide, 0.45, 0.48, 12.3, 0.7, title, 28, INK, True)
        top = 1.28
    else:
        add_text(slide, 0.45, 0.32, 12.3, 0.8, title, 32, INK, True)
        top = 1.2
    n = len(prs.slides)
    add_text(slide, 0.45, 7.12, 8, 0.28, "Player service  ·  availability", 11, MUTED)
    add_text(slide, 11.4, 7.12, 1.5, 0.28, str(n), 11, MUTED, align=PP_ALIGN.RIGHT)
    return slide, top


def flow(slide, items, top, height=1.15, left=0.45, width=12.4, fills=None, colors=None):
    """items: list of strings. Draw a horizontal flow."""
    n = len(items)
    gap = 0.28
    box_w = (width - gap * (n - 1)) / n
    fills = fills or [NAVY_SOFT] * n
    colors = colors or [NAVY] * n
    for i, text in enumerate(items):
        x = left + i * (box_w + gap)
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(top), Inches(box_w), Inches(height))
        fill_shape(shape, fills[i])
        shape.adjustments[0] = 0.12
        label_in(shape, text, 13 if len(text) < 40 else 12, colors[i], True)
        if i < n - 1:
            arr = slide.shapes.add_shape(
                MSO_SHAPE.RIGHT_ARROW,
                Inches(x + box_w - 0.02),
                Inches(top + height / 2 - 0.1),
                Inches(0.32),
                Inches(0.2),
            )
            fill_shape(arr, ACCENT)


def bullets(slide, left, top, width, height, items, size=16):
    lines = []
    for item in items:
        if isinstance(item, tuple):
            lines.append(item)
        else:
            lines.append(("•  " + item, False, INK))
    add_lines(slide, left, top, width, height, lines, size=size, spacing=8)


def build():
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    prs.slide_layouts[6]

    # 1 title
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(W), Inches(H))
    fill_shape(bg, RGBColor(0x1C, 0x19, 0x17))
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(0.18), Inches(H))
    fill_shape(bar, ACCENT)
    add_text(s, 0.7, 1.7, 11.5, 0.4, "CRAFT DEMO", 14, RGBColor(0xFD, 0xBA, 0x74), True)
    add_text(s, 0.7, 2.15, 11.5, 1.6, "Player service\navailability", 48, WHITE, True)
    add_text(s, 0.7, 4.5, 11, 1.1, "One JVM. Player API and chat share Tomcat.\nA hung model must not take player calls down with it.", 20, RGBColor(0xD6, 0xD3, 0xD1))
    add_text(s, 0.7, 6.5, 11, 0.4, "Success: player 200 within the client deadline. Chat 503 is acceptable.", 16, RGBColor(0xA8, 0xA2, 0x9E))

    # 2 criterion
    s, top = new_slide(prs, "The bar", "What “available” means here")
    cards = [
        (SAND, ACCENT, "Player API", "GET /v1/players and\nGET /v1/players/{id}\nreturn 200 before the\nclient gives up."),
        (ROSE, RED, "Not this", "Process up, H2 up, or an\nempty metrics scrape.\nA client timeout is a miss\neven if the JVM is healthy."),
        (MINT, GREEN, "Chat may fail", "A stuck model should\nbecome HTTP 503 quickly.\nThat is a successful\nisolation, not an outage."),
    ]
    for i, (fill, color, title, body) in enumerate(cards):
        x = 0.45 + i * 4.2
        c = card(s, x, 1.5, 3.95, 3.6, fill)
        add_text(s, x + 0.25, 1.75, 3.45, 0.5, title, 20, color, True)
        add_text(s, x + 0.25, 2.4, 3.45, 2.3, body, 16, INK)
    add_text(s, 0.5, 5.4, 12.2, 1.3, "The hang peer accepts TCP on :11434 and never sends a body. That is a read stall, not “connection refused.” Baseline ollama4j waits up to 120s on the Tomcat thread.", 16, MUTED)

    # 3 architecture
    s, top = new_slide(prs, "Architecture", "One JVM, three ports")
    flow(
        s,
        ["Clients", "Tomcat :8080\nmax 40 workers", "PlayerController\nChatController", "H2  /  Ollama :11434"],
        1.5,
        1.35,
        fills=[NAVY, SAND, NAVY_SOFT, SAND],
        colors=[WHITE, ACCENT, NAVY, ACCENT],
    )
    # fix first box white text - flow uses colors[0]=WHITE on NAVY. Good.
    rows = [
        (":8080", "Player + chat. Same pool. By-id sleeps 0–2s on purpose."),
        (":8081", "Health, info, Prometheus. Scrape does not take an API worker."),
        (":11434", "Ollama, or the hang peer in this demo."),
        (":5001", "player-service-model (k-NN teams). Not wired to 8080."),
    ]
    for i, (port, desc) in enumerate(rows):
        y = 3.2 + i * 0.85
        c = card(s, 0.45, y, 1.6, 0.72, NAVY)
        label_in(c, port, 16, WHITE, True)
        add_text(s, 2.25, y + 0.12, 10.4, 0.55, desc, 16, INK)

    # 4 request paths
    s, top = new_slide(prs, "Architecture", "Two paths, one thread pool")
    add_text(s, 0.45, 1.35, 6, 0.4, "Player path", 16, NAVY, True)
    flow(s, ["GET /v1/players", "PlayerService", "H2"], 1.85, 0.95, left=0.45, width=6.1, fills=[NAVY_SOFT, NAVY_SOFT, MINT], colors=[NAVY, NAVY, GREEN])
    add_text(s, 6.9, 1.35, 6, 0.4, "Chat path", 16, ACCENT, True)
    flow(s, ["POST /v1/chat", "ChatClientService", "Ollama"], 1.85, 0.95, left=6.9, width=6.0, fills=[SAND, SAND, ROSE], colors=[ACCENT, ACCENT, RED])
    card(s, 0.45, 3.2, 12.4, 3.4, CARD)
    bullets(s, 0.7, 3.4, 11.9, 3.0, [
        "On main, both paths run on the request thread. A chat read holds a worker until ollama4j returns or the 120s read timeout fires.",
        "List on main is findAll() — the whole ~19k-row roster in one JSON (~9 MB).",
        "By-id is the latency-sensitive player call. It only stays fast if a worker is free.",
        "If metrics were scraped on 8080, the scrape would go blank at the moment the pool fills.",
    ], 16)

    # 5 four problems
    s, top = new_slide(prs, "Problems on main", "Four ways the player API becomes invisible or unavailable")
    problems = [
        ("2.1", "No observability", "No Prometheus, no SLI, no split between liveness and readiness. Under saturation you have logs and curls."),
        ("2.2", "DB outage looks like 404", "getPlayerById swallows every exception and returns empty. A missing PLAYERS table is “player not found.”"),
        ("2.3", "Unbounded list", "One GET /v1/players holds a worker for the full read, mapping, and JSON. Cost grows with the table."),
        ("2.4", "Sync chat, 120s lease", "40 hung chats fill the pool. The next player call never starts. The client times out."),
    ]
    for i, (num, title, body) in enumerate(problems):
        col, row = i % 2, i // 2
        x, y = 0.45 + col * 6.4, 1.45 + row * 2.6
        c = card(s, x, y, 6.15, 2.4, CARD)
        add_text(s, x + 0.25, y + 0.2, 1.2, 0.45, num, 20, ACCENT, True)
        add_text(s, x + 1.4, y + 0.22, 4.4, 0.45, title, 20, INK, True)
        add_text(s, x + 0.25, y + 0.9, 5.65, 1.2, body, 15, MUTED)

    # 6 2.1 detail
    s, top = new_slide(prs, "Problem 2.1", "You cannot see player availability while it is failing")
    bullets(s, 0.5, 1.4, 7.4, 5.2, [
        "No scrape, no Grafana dashboard, no /v1/reliability.",
        "No documented meaning of liveness vs readiness.",
        "Question you cannot answer: how many player calls finished, with what status, and was the pool full?",
        "A scrape on 8080 needs a worker. At 40/40 the series go blank exactly when you need them.",
        "Completed-request charts miss the calls that never finished. Those show up only as client timeouts.",
    ], 16)
    card(s, 8.15, 1.5, 4.7, 4.8, ROSE)
    add_text(s, 8.4, 1.75, 4.2, 0.5, "Failure mode", 18, RED, True)
    add_text(s, 8.4, 2.4, 4.2, 3.5, "Process is up.\nH2 is up.\nPrometheus on the API port is empty.\n\nNone of that means a player client got a 200.", 16, INK)

    # 7 2.2
    s, top = new_slide(prs, "Problem 2.2", "A database failure is returned as 404")
    flow(s, ["GET /v1/players/{id}", "catch Exception\n→ Optional.empty()", "Controller\n→ HTTP 404"], 1.55, 1.3, fills=[NAVY_SOFT, ROSE, ROSE], colors=[NAVY, RED, RED])
    add_text(s, 0.5, 3.15, 12.2, 0.4, "Same response for two different facts", 16, INK, True)
    pair = [
        ("Missing id", "404 is correct.\nThe player is not in the table."),
        ("DROP TABLE PLAYERS", "Still 404 on main.\nClients and the SLI treat an outage as “not found.”"),
    ]
    for i, (t, b) in enumerate(pair):
        x = 0.45 + i * 6.4
        c = card(s, x, 3.7, 6.15, 2.5, CARD if i == 0 else ROSE)
        add_text(s, x + 0.3, 3.9, 5.6, 0.45, t, 18, NAVY if i == 0 else RED, True)
        add_text(s, x + 0.3, 4.45, 5.6, 1.4, b, 16, INK)

    # 8 2.3
    s, top = new_slide(prs, "Problem 2.3", "GET /v1/players does not stay safe as the table grows")
    flow(s, ["findAll()", "Map every row", "One JSON\n~9 MB / 19,370 players", "One Tomcat worker\nfor the whole call"], 1.5, 1.25, fills=[ROSE, ROSE, ROSE, SAND], colors=[RED, RED, RED, ACCENT])
    bullets(s, 0.5, 3.1, 12.2, 3.6, [
        "Thread time, bytes, and GC grow with row count. A 90s 200 still counts as success if the SLI only checks status < 500.",
        "Clients have already timed out. The scorecard says available.",
        "A few full-roster downloads plus hung chats make pool exhaustion easy to hit on a laptop.",
        "The fix is a bound per request, not “download the catalog faster.”",
    ], 16)

    # 9 2.4
    s, top = new_slide(prs, "Problem 2.4", "A stuck chat call leases a Tomcat worker for 120s")
    flow(s, ["Hang peer\naccepts TCP", "ollama4j reads\nup to 120s", "Worker stays busy", "41st player call\nnever starts"], 1.5, 1.3, fills=[ROSE, ROSE, SAND, ROSE], colors=[RED, RED, ACCENT, RED])
    card(s, 0.45, 3.15, 6.15, 3.4, CARD)
    add_text(s, 0.7, 3.3, 5.7, 0.4, "Pool math, max 40", 18, INK, True)
    add_text(s, 0.7, 3.85, 5.7, 2.4, "40 concurrent hung chats fill the pool.\n\nConnection refused would fail in milliseconds. The hang peer does not refuse. It never writes a body.", 16, INK)
    card(s, 6.85, 3.15, 6.0, 3.4, SAND)
    add_text(s, 7.1, 3.3, 5.5, 0.4, "What the client sees", 18, ACCENT, True)
    add_text(s, 7.1, 3.85, 5.5, 2.4, "Player client_timeout.\n\nGrafana may show nothing finished, because a timed-out client never became an HTTP status.", 16, INK)

    # 10 solution map
    s, top = new_slide(prs, "This branch", "Each problem has one fix")
    fixes = [
        ("3.1", "2.1", "Metrics on 8081, SLI, Grafana, probes"),
        ("3.2", "2.2", "Data-access errors propagate as 500"),
        ("3.3", "2.3", "Offset pages, max size 100"),
        ("3.4", "2.4", "Async chat + 2s timeout"),
    ]
    for i, (sol, prob, text) in enumerate(fixes):
        y = 1.45 + i * 1.3
        c = card(s, 0.45, y, 1.7, 1.1, NAVY)
        label_in(c, sol, 20, WHITE)
        c2 = card(s, 2.35, y, 1.7, 1.1, SAND)
        label_in(c2, prob, 20, ACCENT)
        c3 = card(s, 4.25, y, 8.6, 1.1, CARD)
        label_in(c3, text, 18, INK, False, PP_ALIGN.LEFT)

    # 11 3.1 flow
    s, top = new_slide(prs, "Solution 3.1", "Watch the API from a port the pool cannot block")
    flow(
        s,
        [":8080\nfinishes a request", "Micrometer\nstatus + URI", "Tomcat MBean\nbusy threads", ":8081\nPrometheus scrape", "Grafana\nAvailability"],
        1.5,
        1.35,
        fills=[NAVY, NAVY_SOFT, SAND, MINT, MINT],
        colors=[WHITE, NAVY, ACCENT, GREEN, GREEN],
    )
    bullets(s, 0.5, 3.2, 12.2, 3.4, [
        "SLI is player successes ÷ player requests that reached the app. Chat is tracked and excluded.",
        "Busy threads = capacity. Status bars = work that finished. Ramp JSON = client_timeout, which Grafana never sees.",
        "Readiness includes the database, not Ollama. A dead model must not pull this instance out of player traffic.",
        "Liveness is the process. A stuck chat thread is not a reason to restart.",
    ], 16)

    # 12 3.1 what we watch
    s, top = new_slide(prs, "Solution 3.1", "Three signals, on purpose")
    cols = [
        (NAVY_SOFT, NAVY, "Saturation", "tomcat_threads_busy_threads\nagainst the configured max of 40.\n\nThis is the gauge that says the pool is full."),
        (SAND, ACCENT, "Completed work", "http_server_requests_seconds_count\nby URI and status.\n\n200, 503, and 500 only. Nothing in flight."),
        (MINT, GREEN, "What the user felt", "Ramp JSON: client_timeout.\n\nSame attempt count before and after, so the comparison is fair."),
    ]
    for i, (fill, color, title, body) in enumerate(cols):
        x = 0.45 + i * 4.2
        card(s, x, 1.5, 4.0, 4.9, fill)
        add_text(s, x + 0.25, 1.75, 3.5, 0.6, title, 20, color, True)
        add_text(s, x + 0.25, 2.55, 3.5, 3.4, body, 15, INK)

    # 13 3.1 shipped
    s, top = new_slide(prs, "Solution 3.1", "What shipped")
    rows = [
        ("Metrics port", "management.server.port: 8081. Health, info, prometheus."),
        ("Tomcat visibility", "mbeanregistry enabled. Max threads pinned at 40 so a laptop can fill the pool."),
        ("SLI", "SliRecordingFilter + /v1/reliability/mode and /sli."),
        ("Probes", "Liveness = process. Readiness = db. Ollama omitted."),
        ("Dashboard", "Busy threads and per-API completed status. No latency panels in the story."),
    ]
    for i, (k, v) in enumerate(rows):
        y = 1.4 + i * 1.05
        c = card(s, 0.45, y, 3.1, 0.9, NAVY_SOFT)
        label_in(c, k, 14, NAVY, True)
        add_text(s, 3.75, y + 0.2, 9.0, 0.6, v, 16, INK)

    # 14 3.2
    s, top = new_slide(prs, "Solution 3.2", "Let the data-layer failure stay a failure")
    add_text(s, 0.45, 1.35, 6, 0.35, "Before", 14, RED, True)
    flow(s, ["Any exception", "empty Optional", "404"], 1.8, 1.05, left=0.45, width=6.1, fills=[ROSE, ROSE, ROSE], colors=[RED, RED, RED])
    add_text(s, 6.9, 1.35, 6, 0.35, "After", 14, GREEN, True)
    flow(s, ["Unknown id", "404", "DataAccessException", "500"], 1.8, 1.05, left=6.9, width=6.0, fills=[NAVY_SOFT, NAVY_SOFT, ROSE, ROSE], colors=[NAVY, NAVY, RED, RED])
    card(s, 0.45, 3.3, 12.4, 3.3, CARD)
    bullets(s, 0.7, 3.5, 11.9, 2.9, [
        "PlayerService.getPlayerById no longer catches Exception and returns empty.",
        "PlayerExceptionHandler maps DataAccessException to 500 “player data unavailable.”",
        "A real missing id is still 404.",
        "Live check: DROP TABLE PLAYERS, then GET /v1/players/aardsda01. Restart the JVM to reload the CSV.",
    ], 16)

    # 15 3.3 choice
    s, top = new_slide(prs, "Solution 3.3", "Bound each list call. Offset now, cursor later.")
    # table-like cards
    headers = ["", "Offset  page + size", "Cursor  after=playerId"]
    xs = [0.45, 4.3, 8.8]
    ws = [3.7, 4.35, 4.05]
    for x, w, htxt in zip(xs, ws, headers):
        if not htxt:
            continue
        c = card(s, x, 1.4, w, 0.7, NAVY)
        label_in(c, htxt, 14, WHITE)
    rows = [
        ("API", "Spring Pageable, LIMIT/OFFSET", "Stable if rows move between pages"),
        ("Deep pages", "Large OFFSET gets expensive", "Indexed keyset stays cheap"),
        ("This demo", "Shipped. Caps bytes and thread time.", "Defer until deep scans or churn matter"),
    ]
    for i, (a, b, ctext) in enumerate(rows):
        y = 2.25 + i * 1.15
        vals = [a, b, ctext]
        fills = [SAND, CARD, CARD]
        cols = [ACCENT, INK, INK]
        for x, w, val, fill, col in zip(xs, ws, vals, fills, cols):
            box = card(s, x, y, w, 1.0, fill)
            label_in(box, val, 13, col, i == 0 or x == xs[0], PP_ALIGN.LEFT if x != xs[0] else PP_ALIGN.CENTER)
    add_text(s, 0.5, 5.85, 12.2, 0.9, "The availability win is “not the whole table in one response,” not faster access to page 20,000.", 16, MUTED)

    # 16 3.3 shipped
    s, top = new_slide(prs, "Solution 3.3", "What the list API does now")
    items = [
        ("Default", "page=0, size=50, sort=playerId"),
        ("Cap", "size > 100 → 400"),
        ("Query", "findAll(pageable), not findAll()"),
        ("Body", "players[] plus page, size, totalElements, totalPages"),
        ("One page", "size=10 → 4,691 bytes, 10 of 19,370"),
        ("Default page", "23,332 bytes vs ~9 MB for the full roster"),
    ]
    for i, (k, v) in enumerate(items):
        col, row = i % 2, i // 2
        x, y = 0.45 + col * 6.4, 1.45 + row * 1.7
        c = card(s, x, y, 6.15, 1.5, CARD)
        add_text(s, x + 0.25, y + 0.18, 5.7, 0.4, k, 14, ACCENT, True)
        add_text(s, x + 0.25, y + 0.65, 5.7, 0.65, v, 18, INK, True)

    # 17 3.3 proof
    s, top = new_slide(prs, "Solution 3.3", "Same load, two jars, both -Xmx128m")
    add_text(s, 0.45, 1.35, 12, 0.45, "30 concurrent full reads of GET /v1/players", 16, MUTED)
    left = card(s, 0.45, 1.95, 6.15, 4.4, ROSE)
    add_text(s, 0.7, 2.15, 5.7, 0.4, "Main  ·  unbounded  ·  :18080", 16, RED, True)
    add_text(s, 0.7, 2.7, 5.7, 3.2, "10 × HTTP 500\nOutOfMemoryError\n\n19 × 200\n1 incomplete read\n\nThe full roster does not fit\n30 times in a 128 MB heap.", 18, INK)
    right = card(s, 6.85, 1.95, 6.0, 4.4, MINT)
    add_text(s, 7.1, 2.15, 5.5, 0.4, "Branch  ·  one page  ·  :8080", 16, GREEN, True)
    add_text(s, 7.1, 2.7, 5.5, 3.2, "30 × HTTP 200\n\n0 × 5xx\n\nEach call returns one page.\nThread time and bytes stay capped.", 18, INK)

    # 18 3.4 flow
    s, top = new_slide(prs, "Solution 3.4", "Chat leaves the request thread")
    add_text(s, 0.45, 1.3, 6, 0.35, "Baseline", 14, RED, True)
    flow(s, ["Tomcat worker", "ollama4j\n120s", "Pool at 40", "Player\nclient_timeout"], 1.75, 1.15, left=0.45, width=12.4, fills=[ROSE, ROSE, ROSE, ROSE], colors=[RED, RED, RED, RED])
    add_text(s, 0.45, 3.2, 6, 0.35, "timeouts profile", 14, GREEN, True)
    flow(s, ["Tomcat accepts", "chat-exec\n8 threads, queue 0", "Read timeout 2s", "Chat 503\nPlayer 200"], 3.65, 1.15, left=0.45, width=12.4, fills=[MINT, NAVY_SOFT, SAND, MINT], colors=[GREEN, NAVY, ACCENT, GREEN])
    add_text(s, 0.5, 5.15, 12.2, 1.5, "Callable releases the Tomcat thread while chat runs. Pool full, connect failure, and read timeout all become 503. The hang peer is unchanged.", 16, INK)

    # 19 3.4 shipped
    s, top = new_slide(prs, "Solution 3.4", "What changed, and what did not")
    rows = [
        ("async-enabled", "On in the timeouts profile. Off in baseline, so the before picture is real."),
        ("chat-exec", "8 workers, queue length 0. Overflow is 503, not an unbounded wait."),
        ("Read timeout", "2s, applied to OllamaAPI. Baseline stays at 120s."),
        ("Controller", "Returns Callable when async. Tomcat can serve players during the wait."),
        ("Same hang", "The peer still accepts and never responds. Only our side of the lease changed."),
    ]
    for i, (k, v) in enumerate(rows):
        y = 1.4 + i * 1.05
        c = card(s, 0.45, y, 3.3, 0.9, SAND)
        label_in(c, k, 14, ACCENT, True)
        add_text(s, 3.95, y + 0.18, 8.8, 0.6, v, 16, INK)

    # 20 scorecard
    s, top = new_slide(prs, "Proof", "Same ramp, hang peer on :11434")
    headers = ["", "Baseline", "timeouts"]
    data = [
        ("GET /v1/players", "6 × 200\n22 × client_timeout", "28 × 200"),
        ("GET /v1/players/{id}", "6 × 200\n22 × client_timeout", "28 × 200"),
        ("Player totals", "12 × 200, 44 timeouts\nof 56", "56 × 200\n0 timeouts"),
        ("Chat", "client_timeout", "84 × 503 per route"),
        ("Tomcat busy, peak", "40 / 40", "2 / 40"),
    ]
    xs = [0.4, 4.5, 8.9]
    ws = [4.0, 4.3, 4.0]
    for x, w, htxt in zip(xs, ws, headers):
        if not htxt:
            continue
        box = card(s, x, 1.35, w, 0.55, NAVY if htxt == "timeouts" else SAND)
        label_in(box, htxt, 14, WHITE if htxt == "timeouts" else ACCENT)
    for i, (a, b, c) in enumerate(data):
        y = 2.0 + i * 0.95
        fill = CARD if i % 2 == 0 else RGBColor(0xFA, 0xF8, 0xF5)
        for x, w, val, col, bold in (
            (xs[0], ws[0], a, INK, True),
            (xs[1], ws[1], b, RED, False),
            (xs[2], ws[2], c, GREEN, True),
        ):
            box = card(s, x, y, w, 0.88, fill if x != xs[2] else MINT)
            label_in(box, val, 13, col, bold)

    # 21 story
    s, top = new_slide(prs, "Proof", "How to read the scorecard")
    flow(s, ["Hang peer", "Baseline:\nbusy = 40", "Players stop\nfinishing", "client_timeout\nin the ramp JSON"], 1.5, 1.2, fills=[ROSE, ROSE, ROSE, SAND], colors=[RED, RED, RED, ACCENT])
    flow(s, ["Same hang", "Chat on side pool\n2s timeout", "busy ≈ 2", "Players 200\nChat 503"], 3.15, 1.2, fills=[NAVY_SOFT, MINT, MINT, MINT], colors=[NAVY, GREEN, GREEN, GREEN])
    add_text(s, 0.5, 4.7, 12.2, 2.0, "Pagination and chat decoupling are different axes. Pagination caps list cost so one roster download cannot exhaust the heap or hold a worker for the whole table. The timeouts profile caps chat cost so a hung model cannot lease all 40 workers. The ramp proves the second. The two-jar load proves the first.", 16, INK)

    # 22 impact
    s, top = new_slide(prs, "Impact", "What changed for the player API")
    impacts = [
        ("See it", "Saturation and finished status codes stay visible on 8081 while 8080 is busy."),
        ("Name it", "A dropped table is 500. A missing player is 404. The SLI can tell them apart."),
        ("Bound it", "Each list call is one page. Roster growth does not become a multi-megabyte worker lease."),
        ("Isolate it", "Under the same hang, player calls stay 200. Chat fails in about 2 seconds."),
    ]
    for i, (t, b) in enumerate(impacts):
        y = 1.4 + i * 1.3
        c = card(s, 0.45, y, 2.4, 1.15, NAVY)
        label_in(c, t, 16, WHITE)
        add_text(s, 3.1, y + 0.28, 9.6, 0.7, b, 16, INK)

    # 23 learnings
    s, top = new_slide(prs, "Learnings", "What this demo is for")
    bullets(s, 0.55, 1.45, 12.2, 5.3, [
        "Define availability for the player API, not for “the process is up.”",
        "Observability is part of the fix: metrics port, MBean registry, SLI, dashboard.",
        "Busy threads, completed statuses, and client timeouts are three different facts.",
        "More Tomcat threads do not fix a 120s read on the request thread.",
        "Unbounded findAll() is an availability bug once the table is large. A max page size fixes the common case before cursor paging is worth it.",
        "Readiness only helps when another replica can take the traffic.",
    ], 18)

    # 24 beyond
    s, top = new_slide(prs, "Beyond this JVM", "Probes describe this process. They do not raise availability alone.")
    rows = [
        ("Readiness is H2, not Ollama", "A dead model does not remove player traffic from this instance."),
        ("Second JVM", "One process can fail while the other still serves players."),
        ("Graceful shutdown", "In-flight player calls can finish on deploy."),
        ("Split deployments", "Chat load cannot saturate the player process."),
        ("Durable database", "A restart does not destroy the only copy of the roster."),
    ]
    for i, (k, v) in enumerate(rows):
        y = 1.4 + i * 1.05
        c = card(s, 0.45, y, 5.3, 0.9, NAVY_SOFT if i % 2 == 0 else CARD)
        label_in(c, k, 14, NAVY, True, PP_ALIGN.LEFT)
        add_text(s, 5.95, y + 0.22, 6.8, 0.55, v, 15, INK)

    # 25 q&a
    s, top = new_slide(prs, "Q&A", "Likely follow-ups")
    qa = [
        ("Why not put Ollama on readiness?", "A model outage would drain the only player instance."),
        ("Why offset, not cursor?", "The bug is one unbounded response. Deep-page cost can wait."),
        ("Where do client timeouts go?", "Ramp JSON. Grafana only counts responses the server finished."),
        ("Why was Tomcat busy a thin spike?", "It is a gauge. A short list burst is one scrape wide."),
        ("player-service-model?", "Separate Flask process on :5001. A future v1/team proxy, not this ramp."),
    ]
    for i, (q, a) in enumerate(qa):
        y = 1.35 + i * 1.08
        add_text(s, 0.5, y, 12.2, 0.35, q, 16, NAVY, True)
        add_text(s, 0.5, y + 0.35, 12.2, 0.45, a, 15, MUTED)

    # silence unused import warning path
    _ = (Emu, qn)
    prs.save(OUT)
    print(f"Wrote {OUT} ({len(prs.slides)} slides)")


if __name__ == "__main__":
    build()
