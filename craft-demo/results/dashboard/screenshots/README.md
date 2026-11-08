# Grafana screenshot results

## Primary (live capture)

| File | Use |
|------|-----|
| **`grafana-dashboard-live-annotated.png`** | Availability dashboard (enriched header + Tomcat + player APIs) |
| **`grafana-pagination-compare-annotated.png`** | Live dual-jar compare dashboard (full width) |
| **`grafana-pagination-side-by-side.png`** | **Pagination talk slide** — cropped panes + HTTP bytes |
| **`grafana-ramp-annotated.png`** | Same availability view + ramp JSON overlay (baseline vs timeouts) |

## Pagination jar panes

| File | Jar |
|------|-----|
| `grafana-pagination-main-jar.png` | Before — `player-service-java-main-demo.jar` @ **:18080** |
| `grafana-pagination-branch-jar.png` | After — branch jar @ **:8080** |

HTTP numbers: [`../pagination-jar-metrics.json`](../pagination-jar-metrics.json)

## Regenerate (live)

```bash
sh craft-demo/observability/up.sh
sh scripts/capture_grafana_live.sh
# or stepwise:
sh scripts/start_dual_jars.sh
open http://localhost:3000/d/pagination-compare/pagination-compare
open http://localhost:3000/d/availability/availability
```

**Do not** rely on Grafana `/render` without [image-renderer](https://grafana.com/grafana/plugins/grafana-image-renderer/).
