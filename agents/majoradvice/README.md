# Major Advice Agent
**Goal:** 
**Endpoint:** `POST /a2a`

## Quick Start 
Within your `.venv` run: 
```
python3 langchain_majoradvice.py
```

## Curl Commands

```
curl -sS -X POST 'http://127.0.0.1:6000/a2a' \
  -H 'Content-Type: application/json' \
  --data-binary '{"role":"user","parts":[{"type":"text","text":"@agent123 I need help selecting a college major"}]}'
```