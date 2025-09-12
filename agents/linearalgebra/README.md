# Linear Algebra Agent
**Goal:** Explain core Linear Algebra ideas and walk through simple problems.  
**Endpoint:** `POST /a2a`

## Quick Start 
Within your `.venv` run: 
```
python3 langchain_linearalgebra.py
```

## Curl Commands

```
curl -sS -X POST 'http://127.0.0.1:6000/a2a' \
  -H 'Content-Type: application/json' \
  --data-binary '{"role":"user","parts":[{"type":"text","text":"Please explain what linear algebra is and show Gaussian elimination on [[2,1],[5,3]]."}]}'
```