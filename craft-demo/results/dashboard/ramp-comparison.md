# Ramp: baseline vs timeouts

Traffic ramps from **0** (+16 calls every 5s for 14 steps). Hang peer on **11434** (see README). Latest run after ollama4j timeout profile.

## Totals

| API | baseline | timeouts |
|-----|----------|----------|
| GET /v1/players | **6** `http_200`, **22** `client_timeout` | **28** `http_200` |
| GET /v1/players/{id} | **6** `http_200`, **22** `client_timeout` | **28** `http_200` |
| GET /v1/chat/list-models | **78** `client_timeout`, **6** `no_http_response` | **84** `http_503` |
| POST /v1/chat | **78** `client_timeout`, **6** `no_http_response` | **84** `http_503` |

## Indicators

| Signal | baseline saturated | timeouts |
|--------|-------------------|----------|
| **Tomcat busy** (peak in JSON) | **40** (step ~3) | **2** |
| **Player outcomes** | **`client_timeout`** after pool fills | **`http_200` only** |
| **Chat outcomes** | **`client_timeout`** | **`http_503`** (2s ollama4j timeout) |
| **Grafana** | Busy → 40; player 200 count stalls | Busy low; player 200 keeps growing; chat **503** stack |
