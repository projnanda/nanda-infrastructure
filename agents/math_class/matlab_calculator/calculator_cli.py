# Python command-line interface wrapper around MATLAB

import sys, re
from pathlib import Path
import matlab.engine
import matlab 

ENGINE = None
MATH_RE = re.compile(r"^[\s0-9.+\-*/^()\[\],:;eE]+(?:[A-Za-z_]\w+)?$")

def matlab_engine():
    global ENGINE
    if ENGINE is None:
        ENGINE = matlab.engine.start_matlab("-nojvm")
        helpers = Path(__file__).resolve().parents[0] / "math_class" / "matlab_calculator"
        ENGINE.addpath(str(helpers), nargout=0)
    return ENGINE

def mat_to_py(val):
    import matlab
    if isinstance(val, matlab.double):
        rows = [list(r) for r in val]
        return rows[0][0] if len(rows)==1 and len(rows[0])==1 else rows
    return val

def eval_calc(expr: str):
    eng = matlab_engine()
    t = expr.strip()
    if t.startswith("="):
        t = t[1:].strip()
    result = eng.safe_calculator(t, nargout=1)
    return mat_to_py(result)
def mat_to_py(val):
    if isinstance(val, matlab.double):
        rows = [list(r) for r in val]
        return rows[0][0] if len(rows)==1 and len(rows[0])==1 else rows
    return val

def main():
    if len(sys.argv) < 2:
        print("Usage: calc_cli.py \"EXPR\""); sys.exit(1)
    expr = " ".join(sys.argv[1:])
    eng = matlab.engine.start_matlab("-nojvm")

    helpers = Path(__file__).resolve().parent
    if not helpers.joinpath("matlab_evaluator.m").exists():
        raise FileNotFoundError(f"matlab_evaluator.m not found in {helpers}")
    eng.addpath(str(helpers), nargout=0) 

    out = eng.matlab_evaluator(expr, nargout=1)
    print(out) 
    eng.quit()

if __name__ == "__main__":
    main()
