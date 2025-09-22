import os, re, json, requests
from calculator_cli import eval_calc

#  Agent endpoints
LINEAR_URL = os.getenv("LINEAR_URL", "http://localhost:6101/a2a")
HYPE_URL   = os.getenv("HYPE_URL",   "http://localhost:6102/a2a")

def a2a_send(url: str, text: str) -> dict:
    """Post a user message to an agent's /a2a endpoint and return the JSON reply."""
    payload = {"role": "user", "content": {"type": "text", "text": text}}
    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()

def get_reply_text(resp: dict) -> str:
    """Try to extract a plain text reply from a NANDA-style envelope."""
    if isinstance(resp, dict):
        c = resp.get("content") or {}
        if isinstance(c, dict) and "text" in c:
            return c["text"]
    return json.dumps(resp)[:1000]

# Manual math detection
FN_HINTS  = ("eig(", "svd(", "inv(", "det(", "rank(", "rref(", "qr(", "lu(", "chol(")
MATH_LIKE = re.compile(r"[0-9\[\]\s,;:\.\+\-\*/\^()eE]")

def is_raw_math(msg: str) -> bool:
    t = msg.strip()
    if t.startswith("="): return True
    if any(fn in t for fn in FN_HINTS): return True
    return bool(MATH_LIKE.search(t)) and ("[" in t or "(" in t)

def route_message(msg: str, explain_after=True, encourage_after=True) -> str:
    # Force MATLAB for expressions
    if is_raw_math(msg):
        try:
            result = eval_calc(msg)
            out = f"MATLAB result: {result}"
        except Exception as e:
            return f"MATLAB error: {e}"

        # A2A follow-ups to agents
        if explain_after:
            try:
                resp = a2a_send(
                    LINEAR_URL,
                    f"Explain this result step-by-step for a student.\n"
                    f"Expression: {msg}\nResult: {result}"
                )
                out += f"\nExplain: {get_reply_text(resp)}"
            except Exception as e:
                out += f"\n(Note: explanation agent unreachable: {e})"

        if encourage_after:
            try:
                resp = a2a_send(
                    HYPE_URL,
                    "Give a one-sentence, upbeat encouragement about learning math."
                )
                out += f"\nHype: {get_reply_text(resp)}"
            except Exception as e:
                out += f"\n(Note: hype agent unreachable: {e})"

        return out

    # Non-math content, send to A2A directly to the appropriate agent
    lower = msg.lower()
    url = LINEAR_URL if any(k in lower for k in (
        "eigen", "gaussian elimination", "matrix", "vector", "linear algebra", "svd", "rank"
    )) else HYPE_URL

    try:
        resp = a2a_send(url, msg)
        return get_reply_text(resp)
    except Exception as e:
        return f"Could not reach agent at {url}: {e}"

def main():
    print("Manual router (MATLAB for math; NANDA for agent A2A). Type 'exit' to quit.")
    while True:
        try:
            msg = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if msg.lower() in {"exit", "quit"}:
            break
        print(route_message(msg))

if __name__ == "__main__":
    main()
