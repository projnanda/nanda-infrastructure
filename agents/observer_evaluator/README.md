# Observer Evaluator Agent
**Goal:** 
**Endpoint:** `POST /a2a`

## Quick Start 
Within your `.venv` run: 
```
python3 langchain_observer_evaluator.py
```

## Curl Commands

Command 1: Ingest a telemetry event
```
curl -sS -X POST 'http://127.0.0.1:6002/a2a' \
  -H 'Content-Type: application/json' \
  --data-binary '{"role":"user","parts":[{"type":"text","text":"telemetry.ingest {\"agent_id\":\"agent://math.eu/002\",\"latency_ms\":840,\"success\":1,\"status_code\":200}"}]}'

```

Command 2: Ingest a telemetry event
```
curl -sS -X POST 'http://127.0.0.1:6002/a2a' \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON'
{
  "role": "user",
  "parts": [
    {"type":"text","text":"observer.probe.run {\"agent_id\":\"agent://math.eu/002\",\"endpoint\":\"http://127.0.0.1:7000/a2a\",\"capability\":\"math.g1_g12\",\"n\":5}"}
  ]
}
JSON
```

Command 3: Check health
```
curl -sS -X POST 'http://127.0.0.1:6002/a2a' \
  -H 'Content-Type: application/json' \
  --data-binary '{"role":"user","parts":[{"type":"text","text":"observer.health {\"agent_id\":\"agent://math.eu/002\"}"}]}'
```

Command 4: Compute reputation (and optionally trigger re-cert if drift)
```
curl -sS -X POST 'http://127.0.0.1:6002/a2a' \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON'
{
  "role": "user",
  "parts": [
    {"type":"text","text":"reputation {\"agent_id\":\"agent://math.eu/002\",\"endpoint\":\"http://127.0.0.1:7000/a2a\"}"}
  ]
}
JSON
```
