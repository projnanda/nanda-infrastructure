#!/usr/bin/env python3
import os, json, time, uuid, hmac, hashlib, threading, math
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path

from nanda_adapter import NANDA   # pip install nanda-adapter
# This agent doesn't need an LLM itself; it evaluates another agent via HTTP.

# -------------------------------
# Config / storage
# -------------------------------
DATA_DIR = Path(os.getenv("CERT_DATA_DIR", "cert_data"))        # ./cert_data/
EVIDENCE_DIR = DATA_DIR / "evidence"                            # ./cert_data/evidence/
JOBS_FILE = DATA_DIR / "cert_jobs.jsonl"                        # append-only log
RESULTS_FILE = DATA_DIR / "trial_results.jsonl"                 # append-only log
CERTS_FILE = DATA_DIR / "certificates.jsonl"                    # append-only log
SECRET = os.getenv("CERT_SECRET", "dev-secret-change-me")       # HMAC for signatures
DEFAULT_RPS = float(os.getenv("CERT_RPS", "1.0"))               # requests/second to target agent

for p in (DATA_DIR, EVIDENCE_DIR):
    p.mkdir(parents=True, exist_ok=True)


# -------------------------------
# Utilities
# -------------------------------
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

def hmac_sign(payload: Dict[str, Any], secret: str = SECRET) -> str:
    msg = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

def normalize(txt: str) -> str:
    return " ".join(txt.strip().lower().split())

def wilson_ci(successes: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    # 95% CI by default
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z**2 / n
    center = (p + z*z/(2*n)) / denom
    margin = (z * math.sqrt(p*(1-p)/n + z*z/(4*n*n))) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


# -------------------------------
# Minimal test suites (replace with your real datasets)
# Each item: capability, topic, difficulty, question, answer
# -------------------------------
SAMPLE_TESTS: List[Dict[str, Any]] = [
    # Math G1–G12 tiny sample (exact-match grading)
    {"capability":"math.g1_g12","topic":"algebra","difficulty":"easy",
     "question":"Solve for x: 2x + 3 = 9", "answer":"3"},
    {"capability":"math.g1_g12","topic":"geometry","difficulty":"easy",
     "question":"What is the sum of interior angles of a triangle?", "answer":"180"},
    {"capability":"math.g1_g12","topic":"calc","difficulty":"easy",
     "question":"Derivative of x^2?", "answer":"2x"},
    # QA sample (F1 grading)
    {"capability":"qa.general","topic":"science","difficulty":"easy",
     "question":"What gas do plants primarily absorb during photosynthesis?",
     "answer":"carbon dioxide"},
]

TOPIC_LABELS = {
    "algebra":"algebra",
    "geometry":"geometry",
    "calc":"calc",
    "science":"science",
}

def load_tests_for(capabilities: List[str]) -> List[Dict[str, Any]]:
    # In production: read from disk or DB. Here we filter the in-memory sample.
    return [t for t in SAMPLE_TESTS if t["capability"] in capabilities]


# -------------------------------
# Grading
# -------------------------------
def grade_math_exact(pred: str, gold: str) -> float:
    return 1.0 if normalize(pred) == normalize(gold) else 0.0

def f1_score(pred: str, gold: str) -> float:
    # whitespace-token F1
    p_set = set(normalize(pred).split())
    g_set = set(normalize(gold).split())
    if not p_set or not g_set:
        return 0.0
    tp = len(p_set & g_set)
    if tp == 0:
        return 0.0
    precision = tp / len(p_set)
    recall = tp / len(g_set)
    return 2 * precision * recall / (precision + recall)

def grade_item(capability: str, pred: str, gold: str) -> float:
    if capability == "math.g1_g12":
        return grade_math_exact(pred, gold)
    # Simple QA fallback
    return 1.0 if f1_score(pred, gold) >= 0.6 else 0.0


# -------------------------------
# Invoke target agent (A2A)
# -------------------------------
import requests

def call_agent_a2a(endpoint: str, text: str, timeout: float = 30.0) -> str:
    """
    Calls a NANDA-style agent endpoint (/a2a) with a user text message.
    Expects response JSON with 'parts' -> [{'type':'text','text': ...}] or plain text.
    """
    payload = {"role":"user","parts":[{"type":"text","text":text}]}
    r = requests.post(endpoint, json=payload, timeout=timeout)
    r.raise_for_status()
    try:
        data = r.json()
        # NANDA typically returns {"role": "...", "parts": [{"type":"text","text":"..."}]}
        parts = data.get("parts") or []
        for p in parts:
            if p.get("type") == "text" and "text" in p:
                return str(p["text"])
        # Fallback to top-level text
        if isinstance(data, dict) and "text" in data:
            return str(data["text"])
        return json.dumps(data)
    except Exception:
        return r.text


# -------------------------------
# Job runner
# -------------------------------
class JobRunner:
    def __init__(self):
        self._lock = threading.Lock()
        self._threads: Dict[str, threading.Thread] = {}
        self._progress: Dict[str, Dict[str, Any]] = {}  # {job_id: {done, total, by_topic, ...}}

    def start_job(self, job: Dict[str, Any]) -> str:
        job_id = job["cert_job_id"]
        t = threading.Thread(target=self._run, args=(job,), daemon=True)
        with self._lock:
            self._threads[job_id] = t
            self._progress[job_id] = {"done": 0, "total": job["n"], "status": "queued"}
        t.start()
        return job_id

    def get_status(self, job_id: str) -> Dict[str, Any]:
        with self._lock:
            return self._progress.get(job_id, {"error":"unknown job_id"})

    def _update(self, job_id: str, upd: Dict[str, Any]) -> None:
        with self._lock:
            self._progress[job_id] = {**self._progress.get(job_id, {}), **upd}

    def _run(self, job: Dict[str, Any]) -> None:
        job_id = job["cert_job_id"]
        agent_id = job["agent_id"]
        endpoint = job["endpoint"]
        caps = job["capabilities"]
        n = job["n"]
        rps = float(job.get("rps", DEFAULT_RPS))
        sleep_s = 1.0 / max(0.01, rps)

        tests = load_tests_for(caps)
        if not tests:
            self._update(job_id, {"status":"error", "message":"no tests for requested capabilities"})
            return

        # stratified-ish sample by cycling topics
        sample = (tests * ((n // len(tests)) + 1))[:n]

        by_topic_scores: Dict[str, List[int]] = {}
        successes = 0
        evidence_path = (EVIDENCE_DIR / f"{agent_id}-{job_id}.jsonl")
        self._update(job_id, {"status":"running", "evidence_uri": str(evidence_path)})

        for i, item in enumerate(sample, start=1):
            q, gold = item["question"], item["answer"]
            topic = item.get("topic", "unknown")
            try:
                pred = call_agent_a2a(endpoint, q)
                score = grade_item(item["capability"], pred, gold)
                ok = int(score >= 1.0) if item["capability"] == "math.g1_g12" else int(score >= 1.0)
            except Exception as e:
                pred = f"<error: {e}>"
                score, ok = 0.0, 0

            successes += ok
            by_topic_scores.setdefault(topic, []).append(ok)

            trial_rec = {
                "ts": now_iso(),
                "job_id": job_id,
                "agent_id": agent_id,
                "capability": item["capability"],
                "topic": topic,
                "question": q,
                "gold": gold,
                "prediction": pred,
                "ok": ok,
            }
            append_jsonl(evidence_path, trial_rec)
            append_jsonl(RESULTS_FILE, trial_rec)

            self._update(job_id, {"done": i, "total": n})
            time.sleep(sleep_s)

        # aggregate
        by_topic = {t: (sum(v) / max(1, len(v))) for t, v in by_topic_scores.items()}
        score = successes / max(1, n)
        lo, hi = wilson_ci(successes, max(1, n))
        passed = score >= float(job.get("pass_threshold", 0.8))

        cert = {
            "ts": now_iso(),
            "agent_id": agent_id,
            "capability": ",".join(caps) if len(caps) > 1 else caps[0],
            "score": round(score, 4),
            "by_topic": {k: round(v, 4) for k, v in by_topic.items()},
            "n": n,
            "passed": passed,
            "ci95": [round(lo, 4), round(hi, 4)],
            "expires_at": (datetime.now(timezone.utc)
                           .replace(microsecond=0)
                           .isoformat(timespec="seconds")),
            "evidence_uri": str(evidence_path),
        }
        cert["signature"] = hmac_sign(cert)
        append_jsonl(CERTS_FILE, cert)

        self._update(job_id, {"status":"done", "result": cert})


JOB_RUNNER = JobRunner()


# -------------------------------
# Capability Certifier "agent" (NANDA-compatible). It routes actions over /a2a.
# Actions:
#   start  -> kicks off a job
#   status -> returns progress
#   certificate -> returns latest cert for an agent
# -------------------------------
def create_capability_certifier():
    def handle(message_text: str) -> str:
        """
        Accepts either:
          - Raw text with JSON object, e.g. {"action":"start", ...}
          - Or a tiny command "start {...}"
        Returns JSON (string) for easy consumption by clients.
        """
        text = message_text.strip()
        try:
            if text.startswith("{"):
                req = json.loads(text)
            else:
                # allow "start {json...}" style
                parts = text.split(None, 1)
                if len(parts) == 2 and parts[0].lower() in {"start","status","certificate"}:
                    req = {"action": parts[0].lower(), **json.loads(parts[1])}
                else:
                    return json.dumps({"error":"unrecognized command; send JSON with action=start|status|certificate"})
        except Exception as e:
            return json.dumps({"error": f"bad JSON: {e}"})

        action = req.get("action")
        if action == "start":
            agent_id = req.get("agent_id") or f"agent://unknown/{uuid.uuid4().hex[:6]}"
            endpoint = req.get("endpoint") or "http://127.0.0.1:6001/a2a"
            capabilities = req.get("capabilities") or ["math.g1_g12"]
            n = int(req.get("n", 50))
            rps = float(req.get("rps", DEFAULT_RPS))
            job = {
                "cert_job_id": f"job_{uuid.uuid4().hex}",
                "agent_id": agent_id,
                "endpoint": endpoint,
                "capabilities": capabilities,
                "n": n,
                "rps": rps,
                "requested_at": now_iso(),
                "pass_threshold": float(req.get("pass_threshold", 0.8)),
            }
            append_jsonl(JOBS_FILE, job)
            job_id = JOB_RUNNER.start_job(job)
            return json.dumps({"cert_job_id": job_id, "status":"queued"})

        elif action == "status":
            job_id = req.get("cert_job_id")
            if not job_id:
                return json.dumps({"error":"missing cert_job_id"})
            return json.dumps(JOB_RUNNER.get_status(job_id))

        elif action == "certificate":
            agent_id = req.get("agent_id")
            if not agent_id:
                return json.dumps({"error":"missing agent_id"})
            certs = [c for c in load_jsonl(CERTS_FILE) if c.get("agent_id") == agent_id]
            if not certs:
                return json.dumps({"error":"no certificate found"})
            latest = certs[-1]
            return json.dumps(latest)

        else:
            return json.dumps({"error":"unknown action; expected start|status|certificate"})

    return handle


# -------------------------------
# Main: run as a NANDA agent server
# -------------------------------
def main():
    # No API key needed here; this agent orchestrates/grades.
    cert_logic = create_capability_certifier()
    nanda = NANDA(cert_logic)

    print("Starting Capability Certifier Agent (NANDA, /a2a)…")
    print("Actions: start | status | certificate   (send as JSON text to /a2a)")
    nanda.start_server()  # dev server on http://127.0.0.1:6000

if __name__ == "__main__":
    main()
