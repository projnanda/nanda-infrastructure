#!/usr/bin/env python3
import os, json, time, uuid, threading, math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from nanda_adapter import NANDA  # pip install nanda-adapter

# =============================================================================
# Config & Storage (MVP uses local JSONL; can swap to Mongo/ClickHouse later)
# =============================================================================
OBS_DATA_DIR = Path(os.getenv("OBS_DATA_DIR", "observer_data"))
TELEMETRY_FILE = OBS_DATA_DIR / "telemetry.jsonl"       # per-event metrics
PROBE_RUNS_FILE = OBS_DATA_DIR / "probe_runs.jsonl"     # summary per probe run
REPUTATION_FILE = OBS_DATA_DIR / "reputation.jsonl"     # snapshots by agent
AGENTS_REGISTRY = OBS_DATA_DIR / "agents.json"          # optional: list of agents to auto-probe

CERTS_FILE = Path(os.getenv("CERTS_FILE", "cert_data/certificates.jsonl"))  # from your certifier
CERTIFIER_A2A = os.getenv("CERTIFIER_A2A", "http://127.0.0.1:6000/a2a")     # certifier /a2a

# Reputation weights (tweak via env)
W_AVAIL = float(os.getenv("REP_W_AVAIL", "0.40"))
W_PROBE = float(os.getenv("REP_W_PROBE", "0.40"))
W_CERT  = float(os.getenv("REP_W_CERT",  "0.20"))
W_FLAGS = float(os.getenv("REP_W_FLAGS", "0.10"))  # subtract

# Trigger thresholds
RATE_LIMIT_THRESH = float(os.getenv("REP_RATE_LIMIT_THRESH", "0.50"))
RECERT_DELTA = float(os.getenv("REP_RECERT_DELTA", "0.15"))  # probe success lower than last cert by >= delta
RECERT_MIN_N = int(os.getenv("RECERT_MIN_N", "10"))          # need enough probes to consider drift

# Auto-probe scheduler (optional)
ENABLE_SCHEDULER = os.getenv("ENABLE_SCHEDULER", "false").lower() == "true"
PROBE_INTERVAL_SEC = int(os.getenv("PROBE_INTERVAL_SEC", "3600"))  # hourly by default
DEFAULT_PROBE_N = int(os.getenv("DEFAULT_PROBE_N", "5"))

for p in (OBS_DATA_DIR,):
    p.mkdir(parents=True, exist_ok=True)

# =============================================================================
# Utilities
# =============================================================================
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]

def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    k = (len(values) - 1) * (p / 100.0)
    f, c = math.floor(k), math.ceil(k)
    if f == c:
        return float(values[int(k)])
    return float(values[f] * (c - k) + values[c] * (k - f))

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

# =============================================================================
# Synthetic Probes (tiny MVP set; replace with your real capability probe sets)
# =============================================================================
SAMPLE_PROBES = {
    "math.g1_g12": [
        {"q": "Solve for x: 2x + 3 = 9", "check": "3"},
        {"q": "Derivative of x^2?", "check": "2x"},
        {"q": "What is 7 * 8?", "check": "56"},
    ],
    "qa.general": [
        {"q": "What gas do plants primarily absorb during photosynthesis?", "check": "carbon dioxide"},
        {"q": "Who wrote 'Pride and Prejudice'?", "check": "jane austen"},
    ],
}

def match_success(pred: str, gold: str) -> int:
    def norm(s: str) -> str:
        return " ".join(s.strip().lower().split())
    return 1 if norm(pred) == norm(gold) or norm(gold) in norm(pred) else 0

# =============================================================================
# Telemetry ingestion & health aggregates
# =============================================================================
def ingest_telemetry(agent_id: str, latency_ms: float, success: int, status_code: int,
                     fraud_flag: int = 0, note: str = "") -> Dict[str, Any]:
    rec = {
        "ts": now_iso(),
        "agent_id": agent_id,
        "latency_ms": float(latency_ms),
        "success": int(bool(success)),
        "status_code": int(status_code),
        "fraud_flag": int(bool(fraud_flag)),
        "note": note,
    }
    append_jsonl(TELEMETRY_FILE, rec)
    return rec

def health_for_agent(agent_id: str, lookback_events: int = 500) -> Dict[str, Any]:
    rows = [r for r in reversed(load_jsonl(TELEMETRY_FILE)) if r.get("agent_id") == agent_id]
    rows = list(reversed(rows[:lookback_events]))  # latest N in order
    if not rows:
        return {"agent_id": agent_id, "events": 0, "availability": 0, "p95_latency_ms": 0, "error_rate": 1.0}

    latencies = [float(r.get("latency_ms", 0.0)) for r in rows if "latency_ms" in r]
    successes = [int(r.get("success", 0)) for r in rows]
    flags = [int(r.get("fraud_flag", 0)) for r in rows]

    events = len(rows)
    success_rate = sum(successes) / max(1, events)
    error_rate = 1.0 - success_rate
    p95 = percentile(latencies, 95.0) if latencies else 0.0
    fraud_rate = sum(flags) / max(1, events)

    return {
        "agent_id": agent_id,
        "events": events,
        "availability": round(success_rate, 4),
        "error_rate": round(error_rate, 4),
        "fraud_rate": round(fraud_rate, 4),
        "p95_latency_ms": round(p95, 1),
        "window_events": lookback_events,
        "updated_at": now_iso(),
    }

# =============================================================================
# Probe runner (calls target agent via /a2a, measures latency & success)
# =============================================================================
def call_agent_a2a(endpoint: str, text: str, timeout: float = 30.0) -> str:
    payload = {"role": "user", "parts": [{"type": "text", "text": text}]}
    r = requests.post(endpoint, json=payload, timeout=timeout)
    r.raise_for_status()
    try:
        data = r.json()
        parts = data.get("parts") or []
        for p in parts:
            if p.get("type") == "text" and "text" in p:
                return str(p["text"])
        if isinstance(data, dict) and "text" in data:
            return str(data["text"])
        return json.dumps(data)
    except Exception:
        return r.text

def run_probe(agent_id: str, endpoint: str, capability: str, n: int = DEFAULT_PROBE_N) -> Dict[str, Any]:
    bank = SAMPLE_PROBES.get(capability, [])
    if not bank:
        return {"error": f"no probes for capability '{capability}'"}

    successes, lat_list = 0, []
    for i in range(n):
        item = bank[i % len(bank)]
        start = time.time()
        try:
            pred = call_agent_a2a(endpoint, item["q"])
            ok = match_success(pred, item["check"])
            successes += ok
            success_flag = 1 if ok else 0
            status_code = 200
        except Exception:
            success_flag = 0
            status_code = 500
        elapsed_ms = (time.time() - start) * 1000.0
        lat_list.append(elapsed_ms)

        # Also ingest telemetry per request
        ingest_telemetry(agent_id, elapsed_ms, success_flag, status_code, note=f"probe:{capability}")

        # Light pacing to avoid hammering
        time.sleep(0.05)

    success_rate = successes / max(1, n)
    p95_ms = percentile(lat_list, 95.0) if lat_list else 0.0

    run = {
        "ts": now_iso(),
        "probe_run_id": f"probe_{uuid.uuid4().hex}",
        "agent_id": agent_id,
        "endpoint": endpoint,
        "capability": capability,
        "n": n,
        "success": round(success_rate, 4),
        "p95_latency_ms": round(p95_ms, 1),
    }
    append_jsonl(PROBE_RUNS_FILE, run)
    return run

def last_probe(agent_id: str) -> Optional[Dict[str, Any]]:
    runs = [r for r in load_jsonl(PROBE_RUNS_FILE) if r.get("agent_id") == agent_id]
    return runs[-1] if runs else None

# =============================================================================
# Reputation
# rep = w_avail * availability + w_probe * last_probe_success + w_cert * last_cert_score - w_flags * fraud_rate
# =============================================================================
def last_cert_score(agent_id: str) -> float:
    certs = [c for c in load_jsonl(CERTS_FILE) if c.get("agent_id") == agent_id]
    if not certs:
        return 0.0
    return float(certs[-1].get("score", 0.0))

def compute_reputation(agent_id: str) -> Dict[str, Any]:
    health = health_for_agent(agent_id)
    probe = last_probe(agent_id) or {"n": 0, "success": 0.0, "p95_latency_ms": 0.0}
    cert_score = last_cert_score(agent_id)

    rep = (
        W_AVAIL * health["availability"]
        + W_PROBE * float(probe.get("success", 0.0))
        + W_CERT  * float(cert_score)
        - W_FLAGS * float(health.get("fraud_rate", 0.0))
    )
    rep = clamp01(rep)

    out = {
        "ts": now_iso(),
        "agent_id": agent_id,
        "rep": round(rep, 4),
        "health": health,
        "last_probe": {
            "n": int(probe.get("n", 0)),
            "success": float(probe.get("success", 0.0)),
            "p95_latency_ms": float(probe.get("p95_latency_ms", 0.0)),
        },
        "last_cert_score": round(float(cert_score), 4),
        "actions": decide_actions(rep, health, probe, cert_score),
    }
    append_jsonl(REPUTATION_FILE, out)
    return out

def decide_actions(rep: float, health: Dict[str, Any], probe: Dict[str, Any], cert_score: float) -> List[str]:
    actions: List[str] = ["monitor"]

    if rep < RATE_LIMIT_THRESH:
        actions.append("rate_limit")

    # Re-cert trigger on drift: only if we have enough probe n and a previous cert
    n = int(probe.get("n", 0))
    probe_success = float(probe.get("success", 0.0))
    if cert_score > 0.0 and n >= RECERT_MIN_N and (cert_score - probe_success) >= RECERT_DELTA:
        # Fire-and-forget request to the Certifier via /a2a
        try:
            payload = {
                "role": "user",
                "parts": [{
                    "type": "text",
                    "text": json.dumps({
                        "action": "start",
                        "agent_id": health["agent_id"],
                        # NOTE: you’ll need to maintain a registry mapping agent_id -> endpoint to fill this in,
                        # or pass endpoint to /reputation request (see handler below).
                        # Here we leave it blank to avoid misfiring; handler can override.
                    })
                }]
            }
            # We don't include endpoint here; the handler supports an override param.
            requests.post(CERTIFIER_A2A, json=payload, timeout=5)
            actions.append("recert_requested")
        except Exception:
            actions.append("recert_failed")

    return actions

# =============================================================================
# Optional: background scheduler to auto-probe agents from registry file
# agents.json format:
# [
#   {"agent_id":"agent://math.eu/002","endpoint":"http://127.0.0.1:7000/a2a","capabilities":["math.g1_g12"],"probe":true}
# ]
# =============================================================================
def _load_registry() -> List[Dict[str, Any]]:
    if not AGENTS_REGISTRY.exists():
        return []
    try:
        return json.loads(AGENTS_REGISTRY.read_text(encoding="utf-8"))
    except Exception:
        return []

def scheduler_loop():
    while True:
        try:
            agents = _load_registry()
            for a in agents:
                if not a.get("probe"):
                    continue
                agent_id = a.get("agent_id")
                endpoint = a.get("endpoint")
                caps = a.get("capabilities", [])
                for cap in caps:
                    run_probe(agent_id, endpoint, capability=cap, n=DEFAULT_PROBE_N)
        except Exception:
            pass
        time.sleep(PROBE_INTERVAL_SEC)

# =============================================================================
# NANDA Agent handler (exposes everything via /a2a actions)
# Actions:
#   telemetry.ingest {agent_id, latency_ms, success, status_code, fraud_flag?}
#   observer.health  {agent_id}
#   observer.probe.run {agent_id, endpoint, capability, n?}
#   reputation {agent_id, endpoint?}  # endpoint optional, used if triggering recert
# =============================================================================
def create_observer_evaluator():
    def handle(message_text: str) -> str:
        text = message_text.strip()

        # accept either raw JSON object or "cmd {json...}"
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

        action = str(req.get("action", "")).lower()

        if action in {"telemetry.ingest", "telemetry"}:
            rec = ingest_telemetry(
                agent_id=req.get("agent_id", "agent://unknown"),
                latency_ms=float(req.get("latency_ms", 0.0)),
                success=int(req.get("success", 0)),
                status_code=int(req.get("status_code", 0)),
                fraud_flag=int(req.get("fraud_flag", 0)),
                note=str(req.get("note", "")),
            )
            return json.dumps({"ok": True, "telemetry": rec})

        if action in {"observer.health", "health"}:
            agent_id = req.get("agent_id")
            if not agent_id:
                return json.dumps({"error": "missing agent_id"})
            return json.dumps(health_for_agent(agent_id))

        if action in {"observer.probe.run", "probe.run"}:
            agent_id = req.get("agent_id")
            endpoint = req.get("endpoint")
            capability = req.get("capability", "math.g1_g12")
            n = int(req.get("n", DEFAULT_PROBE_N))
            if not agent_id or not endpoint:
                return json.dumps({"error": "missing agent_id or endpoint"})
            run = run_probe(agent_id, endpoint, capability, n)
            return json.dumps(run)

        if action == "reputation":
            agent_id = req.get("agent_id")
            if not agent_id:
                return json.dumps({"error": "missing agent_id"})
            rep = compute_reputation(agent_id)

            # Optionally trigger re-cert WITH endpoint if provided
            endpoint = req.get("endpoint")
            if endpoint and "recert_requested" in rep.get("actions", []):
                try:
                    payload = {
                        "role": "user",
                        "parts": [{
                            "type": "text",
                            "text": json.dumps({
                                "action": "start",
                                "agent_id": agent_id,
                                "endpoint": endpoint,
                                "capabilities": ["math.g1_g12"],
                                "n": 50,
                                "rps": 1.0
                            })
                        }]
                    }
                    requests.post(CERTIFIER_A2A, json=payload, timeout=5)
                except Exception:
                    pass
            return json.dumps(rep)

        # Help / unknown
        return json.dumps({
            "usage": {
                "telemetry.ingest": {"agent_id":"...","latency_ms":123,"success":1,"status_code":200,"fraud_flag":0},
                "observer.health": {"agent_id":"..."},
                "observer.probe.run": {"agent_id":"...","endpoint":"http://host:port/a2a","capability":"math.g1_g12","n":5},
                "reputation": {"agent_id":"...","endpoint":"http://host:port/a2a (optional for recert trigger)"},
            }
        })

    return handle

# =============================================================================
# Main
# =============================================================================
def main():
    handler = create_observer_evaluator()
    nanda = NANDA(handler)
    print("Starting Observer/Evaluator Agent (NANDA, /a2a)…")
    if ENABLE_SCHEDULER:
        thr = threading.Thread(target=scheduler_loop, daemon=True)
        thr.start()
        print(f"Auto-probe scheduler enabled (interval={PROBE_INTERVAL_SEC}s)")
    nanda.start_server()  # dev: http://127.0.0.1:6000

if __name__ == "__main__":
    main()
