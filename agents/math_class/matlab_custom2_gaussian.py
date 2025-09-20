import os, time, ast, re, json, pathlib, statistics as stats
from typing import Tuple, Optional, List

import numpy as np
from nanda_adapter import NANDA

# Metrics and Stats
METRICS_PATH = pathlib.Path(__file__).with_name("gaussian_metrics.jsonl")
DEFAULT_WINDOW = 10  # last N runs to chart

def log_metric(latency_s: float, residual_2: float, n: int):
    row = {
        "ts": time.time(),
        "latency_s": float(latency_s),
        "residual_2": float(residual_2),
        "n": int(n),
        "provider": "MATLAB (Claude)",
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
    lines = lines[-max(limit, DEFAULT_WINDOW):]  # small tail
    out = []
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
        bars.append(f"{i:02d} | {'█'*w} {v:.4f}s")
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

# MatLab setup
try:
    import matlab.engine
    _ENG = None
    def get_matlab():
        """Start MATLAB once and add this folder to the path."""
        global _ENG
        if _ENG is None:
            print("[matlab] starting engine…")
            _ENG = matlab.engine.start_matlab()
            matlab_dir = os.path.dirname(__file__)   # this folder (contains .m file)
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
    "Optional: 'steps=full' to print all row ops; 'chart=N' to change chart window; 'reset' to clear metrics."
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
        # find first '[' after A= and b=
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

def format_steps(steps_ml, full: bool, limit: int = 12) -> str:
    steps_py = [str(s) for s in steps_ml]
    if full or len(steps_py) <= limit:
        return "\n".join(f"  {i+1}. {s}" for i, s in enumerate(steps_py))
    head = steps_py[:limit]
    return "\n".join(f"  {i+1}. {s}" for i, s in enumerate(head)) + "\n  … (truncated)"

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
        full_steps = bool(re.search(r"steps\s*=\s*full", message_text, re.I))
        window = parse_window(message_text)

        # Call MATLAB
        try:
            eng = get_matlab()
            A_ml = matlab.double(A.tolist())
            b_ml = matlab.double(b.reshape(-1,1).tolist())

            t0 = time.perf_counter()
            # Try your function name; fall back to gauss_steps if needed
            try:
                x_ml, Ab_final, steps_ml = eng.gaussian_custom1(A_ml, b_ml, nargout=3)
            except Exception:
                x_ml, Ab_final, steps_ml = eng.gaussian_custom1(A_ml, b_ml, nargout=3)
            dt = time.perf_counter() - t0

            x = np.array(x_ml).reshape(-1)
            residual = float(np.linalg.norm(A @ x - b, 2))

            # log & load rolling window
            log_metric(dt, residual, A.shape[0])
            rows = load_metrics(window)
            lat_list = [r["latency_s"] for r in rows if "latency_s" in r]
            p50 = stats.median(lat_list) if lat_list else float("nan")
            mean = stats.fmean(lat_list) if lat_list else float("nan")
            p95 = (np.percentile(lat_list, 95) if lat_list else float("nan"))
            chart = ascii_bar_chart(lat_list[-window:], width=40)

            # Build response
            header = [
                "— MATLAB Gaussian Elimination Agent —",
                f"Size: {A.shape[0]}×{A.shape[1]}",
                f"Latency (this run): {dt:.4f} s",
                f"Solution x: {np.round(x, 6).tolist()}",
                f"Residual ||Ax-b||₂: {residual:.3e}",
                "",
                f"Latency summary over last {len(lat_list)} runs:",
                f"  p50={p50:.4f}s   mean={mean:.4f}s   p95={p95:.4f}s",
                "",
                "Latency chart (most recent first by index):",
                chart,
                "-"*44,
                "Row operations:"
            ]
            body = format_steps(steps_ml, full=full_steps)
            return "\n".join(header + [body])

        except Exception as e:
            return f"MATLAB error: {e}\n\n{USAGE}"

    return agent_logic

def main():
    agent = create_agent()
    nanda = NANDA(agent)
    domain = os.getenv("DOMAIN_NAME", "localhost")
    print("Starting MATLAB Gaussian agent…")
    if domain != "localhost":
        nanda.start_server_api(os.getenv("ANTHROPIC_API_KEY"), domain)
    else:
        nanda.start_server()

if __name__ == "__main__":
    main()
