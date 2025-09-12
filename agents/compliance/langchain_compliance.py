#!/usr/bin/env python3
"""
Compliance Agent (Geo-fencing & Policy PDP)
MVP storage: JSON/JSONL on disk. Redaction: basic email/phone scrubber.
A2A actions:
  - policy.eval       {envelope, context?}
  - policy.rules.get  {}
  - policy.violation  {agent_id, envelope, reason}
"""

import os, re, json, hmac, hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from nanda_adapter import NANDA  # pip install nanda-adapter

# -----------------------------------------------------------------------------
# Config / storage
# -----------------------------------------------------------------------------
COMP_DIR       = Path(os.getenv("COMPLIANCE_DIR", "compliance_data"))
POLICY_FILE    = COMP_DIR / "policies.json"        # source of truth
DECISIONS_FILE = COMP_DIR / "decisions.jsonl"      # append log of decisions
VIOLATIONS_FILE= COMP_DIR / "violations.jsonl"     # append log of violations
SECRET         = os.getenv("COMPLIANCE_SECRET", "dev-compliance-secret")

for p in (COMP_DIR,):
    p.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def hmac_sign(data: Dict[str, Any]) -> str:
    msg = json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hmac.new(SECRET.encode("utf-8"), msg, hashlib.sha256).hexdigest()

def load_policies() -> Dict[str, Any]:
    if POLICY_FILE.exists():
        try:
            return json.loads(POLICY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    # ---- Default MVP ruleset (edit this file on disk to change behavior) ----
    default = {
        # Allowed region pairs (string "FROM->TO")
        "region_pairs_allow": ["US->US", "US->EU", "EU->EU"],
        # Capabilities allowed globally (MVP)
        "capability_allowlist": ["math.g1_g12", "qa.general", "chat.basic"],
        # If crossing into EU with personal data, require redaction + EU model
        "eu_personal_data_rule": {"apply": True, "actions": ["redact:pii", "route:eu-model"]},
        # Capabilities that always escalate (manual review)
        "escalate_capabilities": ["payments.transfer", "identity.verify"],
        # Capabilities denied outright (MVP)
        "deny_capabilities": [],
        # Simple region -> model route hint
        "model_route": {"EU": "eu-model", "US": "us-model"},
    }
    POLICY_FILE.write_text(json.dumps(default, indent=2, ensure_ascii=False), encoding="utf-8")
    return default

# -----------------------------------------------------------------------------
# PII Redaction (MVP): email + phone
# -----------------------------------------------------------------------------
EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+", re.IGNORECASE)
PHONE_RE = re.compile(r"\+?\d[\d\-\s]{7,}\d")

def redact_text(txt: str) -> str:
    txt = EMAIL_RE.sub("[REDACTED_EMAIL]", txt)
    txt = PHONE_RE.sub("[REDACTED_PHONE]", txt)
    return txt

def redact_envelope(envelope: Dict[str, Any]) -> Dict[str, Any]:
    env = json.loads(json.dumps(envelope))  # deep copy
    # NANDA-style: {role, parts:[{type:'text', text:'...'}], ...}
    parts = env.get("parts") or env.get("content") or []
    if isinstance(parts, list):
        for p in parts:
            if isinstance(p, dict) and p.get("type") == "text" and isinstance(p.get("text"), str):
                p["text"] = redact_text(p["text"])
    # if body stored elsewhere, add handlers here
    return env

# -----------------------------------------------------------------------------
# PDP (Policy Decision Point)
# -----------------------------------------------------------------------------
def evaluate_policy(envelope: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    envelope is expected to carry:
      from, to, from_region, to_region, capability, data_classes:[], tool_scopes:[]
      parts: [{type:'text', text:'...'}]   (optional, used if redaction required)
    """
    pol = load_policies()

    frm = envelope.get("from")
    to  = envelope.get("to")
    fr  = str(envelope.get("from_region", "")).upper()
    tr  = str(envelope.get("to_region", "")).upper()
    cap = str(envelope.get("capability", ""))
    data_classes = [str(x) for x in (envelope.get("data_classes") or [])]

    pair = f"{fr}->{tr}"
    allow_pairs = set(pol.get("region_pairs_allow", []))
    allow_caps  = set(pol.get("capability_allowlist", []))
    deny_caps   = set(pol.get("deny_capabilities", []))
    esc_caps    = set(pol.get("escalate_capabilities", []))

    reason = []
    actions: List[str] = []

    # 1) Region pair gate
    if pair not in allow_pairs:
        return {"decision":"DENY","actions":[], "reason":f"disallowed region pair {pair}"}

    # 2) Capability gates
    if cap in deny_caps:
        return {"decision":"DENY","actions":[], "reason":f"capability '{cap}' denied"}
    if cap in esc_caps:
        return {"decision":"ESCALATE","actions":["notify:policy"], "reason":f"capability '{cap}' requires review"}
    if cap and cap not in allow_caps:
        return {"decision":"DENY","actions":[], "reason":f"capability '{cap}' not in allowlist"}

    # 3) EU personal data rule (MVP)
    eu_rule = pol.get("eu_personal_data_rule", {})
    if eu_rule.get("apply") and ("personal_data" in data_classes) and (tr == "EU" or fr == "EU"):
        actions.extend(eu_rule.get("actions", []))
        # Add model route hint to EU if not already present
        mr = pol.get("model_route", {}).get("EU")
        if mr and ("route:eu-model" not in actions):
            actions.append("route:eu-model")
        reason.append("EU flow with personal_data")

        # Return ALLOW_WITH_REDACTION with transformed envelope
        transformed = redact_envelope(envelope)
        decision = {
            "decision":"ALLOW_WITH_REDACTION",
            "actions": actions,
            "reason": "; ".join(reason) if reason else "policy matched",
            "transformed_envelope": transformed
        }
        return decision

    # 4) Default allow
    # Add route hint to target region if present
    mr = pol.get("model_route", {}).get(tr)
    if mr:
        actions.append(f"route:{mr}")

    return {"decision":"ALLOW","actions":actions, "reason":"pair+cap allowed"}

# -----------------------------------------------------------------------------
# Logging / APIs
# -----------------------------------------------------------------------------
def log_decision(req: Dict[str, Any], res: Dict[str, Any]) -> None:
    append_jsonl(DECISIONS_FILE, {"ts": now_iso(), "request": req, "response": res})

def log_violation(payload: Dict[str, Any]) -> Dict[str, Any]:
    rec = {"ts": now_iso(), **payload}
    append_jsonl(VIOLATIONS_FILE, rec)
    return rec

def get_rules_signed() -> Dict[str, Any]:
    rules = load_policies()
    return {"rules": rules, "signature": hmac_sign(rules)}

# -----------------------------------------------------------------------------
# NANDA handler
# -----------------------------------------------------------------------------
def create_compliance_agent():
    def handle(message_text: str) -> str:
        """
        Accepts either raw JSON (with 'action') or commands:
          policy.eval {...}
          policy.rules.get {}
          policy.violation {...}
        """
        txt = message_text.strip()

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
            req = parse_req(txt)
        except Exception as e:
            return json.dumps({"error": f"bad JSON: {e}"})

        action = str(req.get("action","")).lower()

        if action in {"policy.eval", "policy/eval", "eval"}:
            envelope = req.get("envelope")
            if not envelope:
                return json.dumps({"error":"missing 'envelope'"})
            context = req.get("context", {})
            res = evaluate_policy(envelope, context)
            log_decision({"envelope": envelope, "context": context}, res)
            return json.dumps(res)

        if action in {"policy.rules.get", "policy/rules", "rules"}:
            return json.dumps(get_rules_signed())

        if action in {"policy.violation", "policy/violation", "violation"}:
            payload = {k: req.get(k) for k in ["agent_id","envelope","reason"] if k in req}
            if not payload.get("agent_id"):
                return json.dumps({"error":"missing agent_id"})
            rec = log_violation(payload)
            return json.dumps({"ok": True, "logged": rec})

        # help
        return json.dumps({
            "usage": {
                "policy.eval": {
                    "envelope": {
                        "from":"agent://alice", "to":"agent://bob",
                        "from_region":"US", "to_region":"EU",
                        "capability":"chat.basic",
                        "data_classes":["personal_data"],
                        "parts":[{"type":"text","text":"hi my email is a@b.com"}]
                    }
                },
                "policy.rules.get": {},
                "policy.violation": {"agent_id":"agent://alice","envelope":{ "...": "..." },"reason":"exceeded scope"}
            }
        })

    return handle

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main():
    handler = create_compliance_agent()
    nanda = NANDA(handler)
    print("Starting Compliance Agent (NANDA, /a2a)…")
    nanda.start_server()  # dev: http://127.0.0.1:6000

if __name__ == "__main__":
    main()
