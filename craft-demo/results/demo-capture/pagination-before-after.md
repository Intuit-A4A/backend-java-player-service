# Pagination — before vs after (captured test)

Generated: 2026-11-08 (dual jars live)

## Same load (both JVMs `-Xmx128m`, 30 concurrent full reads)

| Jar | `GET /v1/players` outcomes |
|-----|----------------------------|
| **1. Main** unbounded (`:18080`) | **10× HTTP 500** (`OutOfMemoryError`), 19× 200, 1 incomplete read |
| **2. Branch** paged (`:8080`) | **30× HTTP 200**, **0× 5xx** |

Source: [`../dashboard/pagination-load-compare.json`](../dashboard/pagination-load-compare.json)

Screenshot (left = main 5xx, right = branch 200 only): [`../dashboard/screenshots/grafana-pagination-side-by-side.png`](../dashboard/screenshots/grafana-pagination-side-by-side.png)

```bash
# both jars already on -Xmx128m
python3 scripts/pagination_load_compare.py
```

**After metadata (size=10):** `19370` players, `1937` pages, **10** rows on page.

Source: [`../dashboard/pagination-jar-metrics.json`](../dashboard/pagination-jar-metrics.json)

```bash
sh scripts/build_demo_main_jar.sh   # main-demo.jar (unbounded list)
sh scripts/start_dual_jars.sh       # branch :8080 + main :18080
```

## Grafana — side-by-side (pagination)

| File | Use |
|------|-----|
| [`../dashboard/screenshots/grafana-pagination-side-by-side.png`](../dashboard/screenshots/grafana-pagination-side-by-side.png) | **Primary** — main jar vs branch jar |
| [`../dashboard/screenshots/grafana-pagination-compare-annotated.png`](../dashboard/screenshots/grafana-pagination-compare-annotated.png) | Live dashboard `/d/pagination-compare/pagination-compare` |

Live URLs:

- http://localhost:3000/d/pagination-compare/pagination-compare
- http://localhost:3000/d/availability/availability

```bash
sh scripts/capture_grafana_live.sh
```

## Grafana — availability under chat load (separate axis)

| Profile | `GET /v1/players` outcomes (totals) |
|---------|---------------------------------------|
| **Before fix (baseline chat)** | 6× `http_200`, 22× `client_timeout` |
| **After fix (timeouts profile)** | 28× `http_200` |

[`../dashboard/presenter-scorecard.md`](../dashboard/presenter-scorecard.md) · [`../dashboard/screenshots/grafana-dashboard-live-annotated.png`](../dashboard/screenshots/grafana-dashboard-live-annotated.png)
