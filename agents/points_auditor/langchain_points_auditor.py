#!/usr/bin/env python3
"""
Points Auditor Agent (Radius-aware Transaction Verifier)
MVP storage: JSONL files. Mock Radius signature: HMAC over tx fields.
A2A actions exposed via /a2a:
  - audit.intent   {intent_id?, payer, payee, amount, memo?, nonce?, window_sec?}
  - audit.tx       {tx_hash, frm, to, amount, ts?, sig?}
  - audit.status   {intent_id}
"""

import os, json, time, uuid, hmac, hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from nanda_adapter import NANDA  # pip install nanda-adapter

# -----------------------------------------------------------------------------
# Config / storage
# -----------------------------------------------------------------------------
AUDIT_DIR      = Path(os.getenv("AUDIT_DIR", "audit_data"))
INTENTS_FILE   = AUDIT_DIR / "intents.jsonl"
TX_FILE        = AUDIT_DIR / "settlements.jsonl"
RECON_FILE     = AUDIT_DIR / "reconciliations.jsonl"
WALLETS_FILE   = AUDIT_DIR / "wallets.json"

RADIUS_SECRET  = os.getenv("RADIUS_SECRET", "dev-radius-secret")  # mock signer
DEFAULT_WINDOW = int(os.getenv("AUDIT_MATCH_WINDOW_SEC", "3600"))  # 1h
AMOUNT_TOL     = float(os.getenv("AUDIT_AMOUNT_TOL", "0.0"))       # allow tiny rounding, e.g. 0.000001

for p in (AUDIT_DIR,):
    p.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Utils
# -----------------------------------------------------------------------------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def load_wallets() -> Dict[str, float]:
    if not WALLETS_FILE.exists():
        return {}
    try:
        return json.loads(WALLETS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_wallets(w: Dict[str, float]) -> None:
    WALLETS_FILE.write_text(json.dumps(w, indent=2, ensure_ascii=False), encoding="utf-8")

def hmac_sign(fields: List[str]) -> str:
    msg = "|".join(fields).encode("utf-8")
    return hmac.new(RADIUS_SECRET.encode("utf-8"), msg, hashlib.sha256).hexdigest()

def verify_mock_radius_sig(tx: Dict[str, Any]) -> bool:
    """
    Mock verification: sig = HMAC(RADIUS_SECRET, "tx_hash|from|to|amount|ts")
    In real Radius, replace with on-chain proof + signature verification.
    """
    ts = str(tx.get("ts", ""))
    expect = hmac_sign([str(tx.get("tx_hash","")), str(tx.get("frm","")),
                        str(tx.get("to","")), str(tx.get("amount","")), ts])
    return (tx.get("sig") == expect)

def to_dt(ts: Optional[str]) -> datetime:
    if ts:
        try:
            return datetime.fromisoformat(ts.replace("Z","+00:00"))
        except Exception:
            pass
    return datetime.now(timezone.utc)

# -----------------------------------------------------------------------------
# Core: Intent creation, TX ingest, matching, reconciliation
# -----------------------------------------------------------------------------
def create_intent(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    payload: {intent_id?, payer, payee, amount, memo?, nonce?, window_sec?}
    """
    intent_id = payload.get("intent_id") or f"i_{uuid.uuid4().hex[:8]}"
    now = now_iso()
    rec = {
        "ts": now,
        "intent_id": intent_id,
        "payer": str(payload["payer"]),
        "payee": str(payload["payee"]),
        "amount": float(payload["amount"]),
        "memo": payload.get("memo", ""),
        "nonce": str(payload.get("nonce", "")),
        "window_sec": int(payload.get("window_sec", DEFAULT_WINDOW)),
        "status": "open",
        "matched_tx": None,
    }
    append_jsonl(INTENTS_FILE, rec)
    return rec

def ingest_tx(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    payload: {tx_hash, frm, to, amount, ts?, sig?}
    Returns stored tx with verification flags.
    """
    ts = payload.get("ts") or now_iso()
    tx = {
        "ts": ts,
        "tx_hash": str(payload["tx_hash"]),
        "frm": str(payload["frm"]),
        "to": str(payload["to"]),
        "amount": float(payload["amount"]),
        "sig": payload.get("sig", None),
        "verified": False,
    }
    tx["verified"] = verify_mock_radius_sig(tx)
    append_jsonl(TX_FILE, tx)
    return tx

def _match_intent(intents: List[Dict[str, Any]], tx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Strategy:
      - candidate intents are OPEN
      - payer == tx.frm, payee == tx.to
      - amount within tolerance
      - nonce matches when provided
      - tx.ts within [intent.ts, intent.ts + window_sec]
      - choose the earliest matching open intent
    """
    tx_t = to_dt(tx.get("ts"))
    candidates = []
    for it in intents:
        if it.get("status") != "open": 
            continue
        if str(it["payer"]) != tx["frm"] or str(it["payee"]) != tx["to"]:
            continue
        if abs(float(it["amount"]) - float(tx["amount"])) > AMOUNT_TOL:
            # allow partial: consider if tx amount < intent amount (flag later)
            pass
        # nonce iff provided
        if it.get("nonce") and tx.get("nonce") and str(it["nonce"]) != str(tx["nonce"]):
            continue
        it_t = to_dt(it.get("ts"))
        window = int(it.get("window_sec", DEFAULT_WINDOW))
        if not (it_t <= tx_t <= it_t + timedelta(seconds=window)):
            continue
        candidates.append(it)

    if not candidates:
        return None
    # earliest open intent
    candidates.sort(key=lambda r: r.get("ts",""))
    return candidates[0]

def reconcile(intent: Dict[str, Any], tx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Double-entry: debit payer, credit payee with tx['amount'] actually settled.
    Verdicts:
      - settled (exact match & verified)
      - partial (tx < intent; mark remaining open)
      - mismatch (payer/payee ok but amount > intent, OR signature invalid)
      - no_show (handled by out-of-band sweeper; not here)
    """
    payer, payee = intent["payer"], intent["payee"]
    want = float(intent["amount"])
    got = float(tx["amount"])
    verified = bool(tx.get("verified"))

    wallets = load_wallets()
    wallets.setdefault(payer, 0.0)
    wallets.setdefault(payee, 0.0)

    if not verified:
        verdict = "mismatch"
        notes = "signature verification failed"
        settled_amt = 0.0
    elif abs(got - want) <= AMOUNT_TOL:
        verdict = "settled"
        notes = "ok"
        settled_amt = want
        intent["status"] = "settled"
        intent["matched_tx"] = tx["tx_hash"]
    elif got < want:
        verdict = "partial"
        notes = f"partial: got {got} < want {want}"
        settled_amt = got
        # keep intent open with reduced remaining
        intent["amount"] = round(want - got, 9)
        intent["status"] = "open"
        intent["matched_tx"] = tx["tx_hash"]
    else:  # got > want
        verdict = "mismatch"
        notes = f"overpay: got {got} > want {want}"
        settled_amt = 0.0
        # do NOT change balances for overpays in MVP (policy-dependent)

    # Apply balances only for settled/partial
    if settled_amt > 0:
        wallets[payer] = round(wallets[payer] - settled_amt, 9)
        wallets[payee] = round(wallets[payee] + settled_amt, 9)
        save_wallets(wallets)

    # log reconciliation snapshot
    latency_ms = max(0, int((to_dt(tx["ts"]) - to_dt(intent["ts"])).total_seconds() * 1000))
    rec = {
        "ts": now_iso(),
        "intent_id": intent["intent_id"],
        "tx_hash": tx["tx_hash"],
        "payer": payer,
        "payee": payee,
        "wanted": want,
        "got": got,
        "verified": verified,
        "verdict": verdict,
        "latency_ms": latency_ms,
        "notes": notes,
        "balances": {payer: wallets.get(payer, 0.0), payee: wallets.get(payee, 0.0)},
    }
    append_jsonl(RECON_FILE, rec)

    # persist updated intent (append-only log)
    append_jsonl(INTENTS_FILE, intent)

    return rec

def status_for_intent(intent_id: str) -> Dict[str, Any]:
    intents = [r for r in load_jsonl(INTENTS_FILE) if r.get("intent_id") == intent_id]
    if not intents:
        return {"error": "unknown intent_id"}
    # last snapshot of this intent
    intent = intents[-1]
    # last reconciliation (if any)
    recs = [r for r in load_jsonl(RECON_FILE) if r.get("intent_id") == intent_id]
    last_rec = recs[-1] if recs else None
    out = {
        "intent": intent,
        "reconciliation": last_rec,
        "wallets": {**load_wallets()},
    }
    # condense to target “Output” shape if reconciled:
    if last_rec:
        return {
            "intent_id": intent_id,
            "status": last_rec["verdict"],
            "tx_hash": last_rec["tx_hash"],
            "latency_ms": last_rec["latency_ms"],
            "notes": last_rec["notes"],
            "balances": last_rec["balances"],
        }
    return out

# -----------------------------------------------------------------------------
# NANDA A2A handler
# -----------------------------------------------------------------------------
def create_points_auditor():
    def handle(message_text: str) -> str:
        """
        Accepts either raw JSON (with 'action') or commands like:
          audit.intent {...}
          audit.tx {...}
          audit.status {"intent_id":"i_123"}
        """
        text = message_text.strip()

        # parse
        def parse_req(s: str) -> Dict[str, Any]:
            if s.startswith("{"):
                return json.loads(s)
            parts = s.split(None, 1)
            if len(parts) == 2:
                try:
                    obj = json.loads(parts[1])
                    obj["action"] = parts[0]
                    return obj
                except Exception:
                    pass
            return {"action": "help"}

        try:
            req = parse_req(text)
        except Exception as e:
            return json.dumps({"error": f"bad JSON: {e}"})

        action = str(req.get("action","")).lower()

        if action in {"audit.intent", "intent"}:
            required = ["payer","payee","amount"]
            missing = [k for k in required if k not in req]
            if missing:
                return json.dumps({"error": f"missing fields: {missing}"})
            created = create_intent(req)
            return json.dumps({"ok": True, "intent": created})

        if action in {"audit.tx", "tx"}:
            required = ["tx_hash","frm","to","amount"]
            missing = [k for k in required if k not in req]
            if missing:
                return json.dumps({"error": f"missing fields: {missing}"})
            tx = ingest_tx(req)

            # attempt to match to an open intent
            intents = load_jsonl(INTENTS_FILE)
            match = _match_intent(intents, tx)
            if not match:
                return json.dumps({"ok": True, "tx": tx, "verdict": "no_match"})

            rec = reconcile(match, tx)
            # condense to target output shape
            out = {
                "intent_id": match["intent_id"],
                "status": rec["verdict"],
                "tx_hash": rec["tx_hash"],
                "latency_ms": rec["latency_ms"],
                "notes": rec["notes"],
            }
            return json.dumps(out)

        if action in {"audit.status", "status"}:
            intent_id = req.get("intent_id")
            if not intent_id:
                return json.dumps({"error": "missing intent_id"})
            return json.dumps(status_for_intent(intent_id))

        # help
        return json.dumps({
            "usage": {
                "audit.intent": {"payer":"agent://a","payee":"agent://b","amount":10.0,"memo":"optional","nonce":"opt"},
                "audit.tx": {"tx_hash":"0xabc","frm":"agent://a","to":"agent://b","amount":10.0,"ts":"<ISO>","sig":"<hmac>"},
                "audit.status": {"intent_id":"i_123"}
            }
        })

    return handle

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main():
    handler = create_points_auditor()
    nanda = NANDA(handler)
    print("Starting Points Auditor Agent (NANDA, /a2a)…")
    nanda.start_server()  # dev: http://127.0.0.1:6000

if __name__ == "__main__":
    main()
