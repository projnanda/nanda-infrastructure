# Capability Certifier Agent
**Goal:** 
**Endpoint:** `POST /a2a`

## Quick Start 
Terminal A: Run your target agent (the one you’re certifying)
```
export ANTHROPIC_API_KEY=sk-ant-...
export PORT=7000
python langchain_linearalgebra.py
# serves A2A at http://127.0.0.1:7000/a2a
```

Terminal B: Run the Capability Certifier
```
export CERT_SECRET=dev-secret-change-me
export PORT=6000
python capability_certifier.py
# serves A2A at http://127.0.0.1:6000/a2a
```

## Curl Commands

Curl Commands: Start a certification job (run once)
```
curl -sS -X POST 'http://127.0.0.1:6000/a2a' \
  -H 'Content-Type: application/json' \
  --data-binary '{"role":"user","parts":[{"type":"text","text":"{\"action\":\"status\",\"cert_job_id\":\"job_...\"}"}]}'
```

Curl Commands: Check status (poll this until status":"done")
```
curl -sS -X POST 'http://127.0.0.1:6000/a2a' \
  -H 'Content-Type: application/json' \
  --data-binary '{"role":"user","parts":[{"type":"text","text":"{\"action\":\"status\",\"cert_job_id\":\"job_...\"}"}]}'
```

Curl Commands: Fetch the signed certificate (when done)
```
curl -sS -X POST 'http://127.0.0.1:6000/a2a' \
  -H 'Content-Type: application/json' \
  --data-binary '{"role":"user","parts":[{"type":"text","text":"{\"action\":\"certificate\",\"agent_id\":\"agent://math.eu/002\"}"}]}'
```