# Craft demo

Presentation (no commands): [`demo.md`](demo.md)

Speaker notes (commands and monitoring design): [`demo-note.md`](demo-note.md)

**Branch:** `craft-demo/availability` · **Profiles:** default baseline · `--spring.profiles.active=timeouts`

**Observability:** `sh craft-demo/observability/up.sh` → http://localhost:3000/d/availability/availability

**Ramp load:** `python3 scripts/ramp_load_test.py baseline` then `timeouts` — results under `craft-demo/results/dashboard/`.
