from pathlib import Path
import re
import matlab.engine

_ENGINE = None

def _get_engine():
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = matlab.engine.start_matlab("-nojvm")
        helpers = Path(__file__).resolve().parents[0] / "math_class" / "matlab_calculator"
        _ENGINE.addpath(str(helpers), nargout=0)
    return _ENGINE

_MATH_RE = re.compile(r"^[\s0-9.+\-*/^()\[\],:;eE]+(?:[A-Za-z_]\w+)?$")

def looks_like_calc(text: str) -> bool:
    t = text.strip()
    return t.startswith("=") or bool(_MATH_RE.fullmatch(t))

def _mat_to_py(val):
    import matlab  # type: ignore
    if isinstance(val, matlab.double):
        rows = [list(r) for r in val]
        return rows[0][0] if len(rows)==1 and len(rows[0])==1 else rows
    return val

def eval_calc(expr: str):
    eng = _get_engine()
    t = expr.strip()
    if t.startswith("="):
        t = t[1:].strip()
    result = eng.safe_calculator(t, nargout=1)  # <-- name matches .m file
    return _mat_to_py(result)
