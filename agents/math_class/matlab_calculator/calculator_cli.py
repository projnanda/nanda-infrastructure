#!/usr/bin/env python3
import sys
from pathlib import Path
import matlab.engine

def mat_to_py(val):
    import matlab  # type: ignore
    if isinstance(val, matlab.double):
        rows = [list(r) for r in val]
        return rows[0][0] if len(rows)==1 and len(rows[0])==1 else rows
    return val

def main():
    if len(sys.argv) < 2:
        print("Usage: calc_cli.py \"EXPR\""); sys.exit(1)
    expr = " ".join(sys.argv[1:])

    eng = matlab.engine.start_matlab("-nojvm")

    # ✅ Correct path: the directory that contains safe_calculator.m
    helpers = Path(__file__).resolve().parent
    if not helpers.joinpath("safe_calculator.m").exists():
        raise FileNotFoundError(f"safe_calculator.m not found in {helpers}")
    eng.addpath(str(helpers), nargout=0)           # or: eng.addpath(eng.genpath(str(helpers)), nargout=0)

    out = eng.safe_calculator(expr, nargout=1)
    print(out)   # convert if you want
    eng.quit()

if __name__ == "__main__":
    main()
