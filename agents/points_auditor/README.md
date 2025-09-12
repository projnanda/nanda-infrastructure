# Point Auditor Agent
**Goal:** 
**Endpoint:** `POST /a2a`

## Quick Start 
Within your `.venv` run: 
```
python3 langchain_points_auditor.py
```

## Curl Commands

Command 1: Create an intent (payer promises to pay)
```
curl -sS -X POST 'http://127.0.0.1:6003/a2a' -H 'Content-Type: application/json' \
  --data-binary '{"role":"user","parts":[{"type":"text","text":"audit.intent {\"payer\":\"agent://alice\",\"payee\":\"agent://bob\",\"amount\":10.0,\"memo\":\"weekly stipend\",\"nonce\":\"n-42\"}"}]}'
```

Command 2: Submit a settlement tx
For the mock signature, compute: `sig = HMAC(RADIUS_SECRET`, `"tx_hash|from|to|amount|ts")`. Quick one-liner in bash:
```
TX_HASH=0xabc
FROM=agent://alice
TO=agent://bob
AMOUNT=10.0
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
SIG=$(python - <<PY
import hmac,hashlib,os,sys
secret=os.environ.get("RADIUS_SECRET","dev-radius-secret").encode()
msg="|".join([os.environ["TX_HASH"],os.environ["FROM"],os.environ["TO"],os.environ["AMOUNT"],os.environ["TS"]]).encode()
print(hmac.new(secret,msg,hashlib.sha256).hexdigest())
PY
)
curl -sS -X POST 'http://127.0.0.1:6003/a2a' -H 'Content-Type: application/json' \
  --data-binary "{\"role\":\"user\",\"parts\":[{\"type\":\"text\",\"text\":\"audit.tx {\\\"tx_hash\\\":\\\"$TX_HASH\\\",\\\"frm\\\":\\\"$FROM\\\",\\\"to\\\":\\\"$TO\\\",\\\"amount\\\":$AMOUNT,\\\"ts\\\":\\\"$TS\\\",\\\"sig\\\":\\\"$SIG\\\"}\"}]}"
```

Command 3: Check status any time
```
curl -sS -X POST 'http://127.0.0.1:6003/a2a' -H 'Content-Type: application/json' \
  --data-binary '{"role":"user","parts":[{"type":"text","text":"audit.status {\"intent_id\":\"i_xxx\"}"}]}'
```