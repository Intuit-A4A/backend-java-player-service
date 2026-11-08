# Craft demo

| Use this | For |
|----------|-----|
| [`presenter-45min.md`](presenter-45min.md) | The 45-minute plan |
| [`Player-Service-Availability.pptx`](Player-Service-Availability.pptx) | The slides (import into Google Slides) |
| [`commands.md`](commands.md) | Every command and curl |

[`demo.md`](demo.md) is the written design narrative behind the slides.

**Branch:** `craft-demo/availability` · **Profiles:** default baseline · `--spring.profiles.active=timeouts`

**Observability:** `sh craft-demo/observability/up.sh` → http://localhost:3000/d/availability/availability

**Ramp load:** `python3 scripts/ramp_load_test.py baseline` then `timeouts` — results under `craft-demo/results/dashboard/`.

**Before/after (presenter):** [`results/demo-capture/demo-evidence.md`](results/demo-capture/demo-evidence.md) · on-screen table [`results/dashboard/presenter-scorecard.md`](results/dashboard/presenter-scorecard.md) · `sh scripts/demo_capture.sh` (live curls).
