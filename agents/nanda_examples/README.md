# NANDA Adapter Examples 
**Goal:** 
**Endpoint:** `POST /a2a`

## Quick Start 
Within your `.venv` run: 
```
python3 langchain_pirate.py
```

## Curl Commands
```
curl -X POST http://localhost:8000/a2a \              
  -H "Content-Type: application/json" \
  -d '{
    "role": "user",
    "content": {
      "type": "text",
      "text": "@agent123 Hello, how are you doing today?"
    }
  }'
```