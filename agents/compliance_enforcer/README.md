# Compliance Agent
**Goal:** 
**Endpoint:** `POST /a2a`

## Quick Start 
Within your `.venv` run: 
```
python3 langchain_compliance.py
```

## Curl Commands

Curl Commands: Evaluate a US→EU message with personal data
```
curl -sS -X POST 'http://127.0.0.1:6004/a2a' \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON'
{
  "role": "user",
  "parts": [
    {
      "type": "text",
      "text": "policy.eval {
        \"envelope\": {
          \"from\": \"agent://alice\",
          \"to\": \"agent://bob\",
          \"from_region\": \"US\",
          \"to_region\": \"EU\",
          \"capability\": \"chat.basic\",
          \"data_classes\": [\"personal_data\"],
          \"parts\": [{\"type\":\"text\",\"text\":\"My phone is +1 415 555 1212 and email a@b.com\"}]
        }
      }"
    }
  ]
}
JSON
```

Command 2: Fetch the signed ruleset
```
curl -sS -X POST 'http://127.0.0.1:6004/a2a' \
  -H 'Content-Type: application/json' \
  --data-binary '{"role":"user","parts":[{"type":"text","text":"policy.rules.get {}"}]}'
```

Command 3: File a policy violation (from Observer)
```
curl -sS -X POST 'http://127.0.0.1:6004/a2a' \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON'
{
  "role": "user",
  "parts": [
    {"type":"text","text":"policy.violation {\"agent_id\":\"agent://alice\",\"reason\":\"tool:search used in EU-restricted flow\",\"envelope\":{\"from\":\"agent://alice\",\"to\":\"agent://bob\"}}"}
  ]
}
JSON
```