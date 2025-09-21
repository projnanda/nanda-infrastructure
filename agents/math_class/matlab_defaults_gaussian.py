import os, time, ast, re, json, pathlib, statistics as stats
from typing import Tuple, Optional, List

import numpy as np
from nanda_adapter import NANDA


# \LLM hard-disable for this agent only
def _scrub_llm_env():
    # Do not rely on env alone (we also inject a Noop provider below),
    # but scrub anyway to reduce accidental pickup in this process.
    for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "TOGETHER_API_KEY"):
        os.environ.pop(k, None)
    os.environ["NANDA_IMPROVEMENT_ENABLED"] = "0"
    os.environ["DISABLE_IMPROVE_MESSAGE"] = "1"
    # If your NANDA build honors these, they help too (harmless if unknown):
    os.environ["NANDA_ALLOW_LLM"] = "0"
    os.environ["NANDA_BLOCK_PROVIDER"] = "1"

class _NoopLLM:
    """A provider object that satisfies NANDA's provider shape but never calls out."""
    name = "noop"
    def __init__(self, *a, **kw): pass
    # Common method names; include the ones your NANDA version expects
    def chat(self, *a, **kw):
        raise RuntimeError("LLM disabled for this agent (noop provider).")
    def stream(self, *a, **kw):
        raise RuntimeError("LLM disabled for this agent (noop provider).")
    def __call__(self, *a, **kw):
        raise RuntimeError("LLM disabled for this agent (noop provider).")

def force_no_llm(nanda_obj):
    """
    Force the adapter to never use an LLM by setting a Noop provider,
    covering different NANDA versions/shapes.
    """
    # v1-style: explicit setter
    if hasattr(nanda_obj, "set_llm_provider"):
        try:
            nanda_obj.set_llm_provider(_NoopLLM())
            return
        except Exception:
            pass
    # common attributes seen across versions
    for attr in ("llm", "_llm", "provider", "_provider"):
        if hasattr(nanda_obj, attr):
            try:
                setattr(nanda_obj, attr, _NoopLLM())
                return
            except Exception:
                pass
    # registry or config bag patterns
    for attr in ("providers", "_providers", "config", "_config"):
        if hasattr(nanda_obj, attr):
            try:
                bag = getattr(nanda_obj, attr)
                # best-effort: typical keys
                for k in ("llm", "default_llm", "provider", "model"):
                    if isinstance(bag, dict) and k in bag:
                        bag[k] = _NoopLLM()
                return
            except Exception:
                pass
    # If none of these worked, we still have env + intent guard as backstops.
# Metrics and Stats
METRICS_PATH = pathlib.Path(__file__).with_name("gaussian_metrics.jsonl")
DEFAULT_WINDOW = 10  # last N runs to chart

def log_metric(latency_s: float, residual_2: float, n: int) -> None:
    row = {
        "ts": time.time(),
        "latency_s": float(latency_s),
        "residual_2": float(residual_2),
        "n": int(n),
        "provider": "MATLAB (no Claude)",
        "methodology": "MATLAB",
    }
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with METRICS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")

def load_metrics(limit: int) -> List[dict]:
    if not METRICS_PATH.exists():
        return []
    with METRICS_PATH.open("r", encoding="utf-8") as f:
        lines = f.readlines()
    # Load only a small tail for speed
    lines = lines[-max(limit, DEFAULT_WINDOW):]
    out: List[dict] = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except Exception:
            pass
    return out

def ascii_bar_chart(values: List[float], width: int = 40) -> str:
    if not values:
        return "  (no prior runs)"
    vmax = max(values) or 1e-9
    bars = []
    for i, v in enumerate(values, 1):
        w = int(round((v / vmax) * width))
        bars.append(f"{i:02d} | {'█' * w} {v:.4f}s")
    return "\n".join(bars)

def parse_window(text: str) -> int:
    m = re.search(r"chart\s*=\s*(\d+)", text, re.I)
    if not m:
        return DEFAULT_WINDOW
    try:
        N = int(m.group(1))
        return max(3, min(200, N))
    except Exception:
        return DEFAULT_WINDOW

# MatLab Setup
try:
    import matlab.engine
    _ENG = None
    def get_matlab():
        """Start MATLAB once and add this folder to the path."""
        global _ENG
        if _ENG is None:
            print("[matlab] starting engine…")
            _ENG = matlab.engine.start_matlab()
            matlab_dir = os.path.dirname(__file__)  # folder containing any .m files
            _ENG.addpath(_ENG.genpath(matlab_dir), nargout=0)
            print("[matlab] added path:", matlab_dir)
        return _ENG
except Exception as e:
    matlab = None
    print("[matlab] engine unavailable:", e)

USAGE = (
    "Send a body that includes A=... and b=... like:\n"
    "A=[[2,1,-1],[-3,-1,2],[-2,1,2]]\n"
    "b=[8,-11,-3]\n"
    "Optional: 'chart=N' to change chart window; 'reset' to clear metrics."
)

def _extract_bracket_block(s: str, start_idx: int) -> Tuple[str, int]:
    """Return substring '[…]' with bracket matching and the index after it."""
    assert s[start_idx] == "["
    depth, i = 0, start_idx
    while i < len(s):
        if s[i] == "[":
            depth += 1
        elif s[i] == "]":
            depth -= 1
            if depth == 0:
                return s[start_idx:i+1], i+1
        i += 1
    raise ValueError("Unbalanced brackets")

def parse_Ab(text: str) -> Optional[Tuple[np.ndarray, np.ndarray]]:
    """Parse A= [...] and b= [...] from free text."""
    try:
        A_pos = text.find("A=")
        b_pos = text.find("b=")
        if A_pos == -1 or b_pos == -1:
            return None
        Ai = text.find("[", A_pos)
        bi = text.find("[", b_pos)
        if Ai == -1 or bi == -1:
            return None
        A_str, _ = _extract_bracket_block(text, Ai)
        b_str, _ = _extract_bracket_block(text, bi)

        A = np.array(ast.literal_eval(A_str), dtype=float)
        b = np.array(ast.literal_eval(b_str), dtype=float).reshape(-1)
        if A.ndim != 2 or A.shape[0] != A.shape[1] or b.shape[0] != A.shape[0]:
            return None
        return A, b
    except Exception:
        return None

def _preview_matrix(M: np.ndarray, max_rows=8, max_cols=6, fmt="{:8.4f}") -> str:
    r, c = M.shape
    rr, cc = min(r, max_rows), min(c, max_cols)
    lines = []
    for i in range(rr):
        row = " ".join(fmt.format(M[i, j]) for j in range(cc))
        if cc < c:
            row += "  …"
        lines.append(row)
    if rr < r:
        lines.append("…")
    return "\n".join(lines)

# Agent
def create_agent():
    def agent_logic(message_text: str) -> str:
        # reset metrics if asked
        if re.search(r"\breset\b", message_text, re.I):
            try:
                if METRICS_PATH.exists():
                    METRICS_PATH.unlink()
                return "✅ Metrics cleared."
            except Exception as e:
                return f"Could not clear metrics: {e}"

        if 'matlab' not in globals() or matlab is None:
            return "MATLAB Engine not available. Did you install it into this Python and venv?"

        # Parse inputs
        Ab = parse_Ab(message_text)
        if not Ab:
            return f"❓ Couldn’t find A=… and b=…\n\n{USAGE}"

        A, b = Ab
        window = parse_window(message_text)

        try:
            # MATLAB defaults: A\b + rref([A|b])
            eng = get_matlab()
            A_ml = matlab.double(A.tolist())
            b_ml = matlab.double(b.reshape(-1, 1).tolist())

            t0 = time.perf_counter()
            x_ml = eng.mldivide(A_ml, b_ml, nargout=1)   # x = A \ b
            dt = time.perf_counter() - t0

            Ab_ml = eng.horzcat(A_ml, b_ml, nargout=1)   # [A | b]
            RREF_ml, piv_ml = eng.rref(Ab_ml, nargout=2)
            rank_ml = eng.rank(A_ml)
            rcond_ml = eng.rcond(A_ml)

            # Convert
            x = np.array(x_ml).reshape(-1)
            RREF = np.array(RREF_ml)
            pivots = [int(p) for p in np.array(piv_ml).reshape(-1)]
            residual = float(np.linalg.norm(A @ x - b, 2))

            # Metrics
            log_metric(dt, residual, A.shape[0])
            rows = load_metrics(window)
            lat_list = [r["latency_s"] for r in rows if "latency_s" in r]
            p50 = stats.median(lat_list) if lat_list else float("nan")
            mean = stats.fmean(lat_list) if lat_list else float("nan")
            p95 = (np.percentile(lat_list, 95) if lat_list else float("nan"))
            chart = ascii_bar_chart(lat_list[-window:], width=40)

            # Response
            header = [
                "— MATLAB Default Solver (A \\ b) —",
                f"Size: {A.shape[0]}×{A.shape[1]}",
                f"Latency (this run): {dt:.4f} s",
                f"Solution x: {np.round(x, 6).tolist()}",
                f"Residual ||Ax-b||₂: {residual:.3e}",
                f"rank(A) = {int(rank_ml)},  rcond(A) = {float(rcond_ml):.3e}",
                "",
                f"Latency summary over last {len(lat_list)} runs:",
                f"  p50={p50:.4f}s   mean={mean:.4f}s   p95={p95:.4f}s",
                "",
                "RREF([A|b]) preview (final reduced form):",
                _preview_matrix(RREF),
                f"Pivot columns (1-based): {pivots}",
            ]
            return "\n".join(header)

        except Exception as e:
            return f"MATLAB error: {e}\n\n{USAGE}"

    return agent_logic

def main():
    # 1) Lock this process to MATLAB-only
    _scrub_llm_env()

    # 2) Build agent + NANDA, and force no-LLM provider
    agent = create_agent()
    nanda = NANDA(agent)
    force_no_llm(nanda)

    # 3) Bind & domain settings
    host = os.getenv("BIND_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "6060"))            # <- use 6060 to avoid X11 conflicts
    domain = os.getenv("DOMAIN_NAME", "localhost")   # set to your real domain in cloud

    print(f"[startup] MATLAB Gaussian agent (NANDA, NO-LLM)")
    print(f"[startup] host={host} port={port} domain={domain!r}")

    # 4) Start server (cloud if domain != localhost)
    try:
        if domain and domain != "localhost":
            print("[startup] using start_server_api (cloud mode, NO LLM key)")
            try:
                nanda.start_server_api(None, domain, host=host, port=port)
            except TypeError:
                # older NANDA signatures
                nanda.start_server_api(None, domain)
        else:
            print("[startup] using start_server (local/dev)")
            try:
                nanda.start_server(host=host, port=port)
            except TypeError:
                nanda.start_server()
    except Exception as e:
        print(f"[startup] FAILED to start server: {e}")
        raise

if __name__ == "__main__":
    main()