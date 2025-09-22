#!/usr/bin/env python3
import re
import sys
from pathlib import Path
import json
import requests

# --- 1) Your MATLAB backend (manual compute) ---
# Adjust the import path to where your eval_calc lives.
# e.g., from agents.math_class.matlab_calculator import eval_calc
import calculator_cli  # if you put it under tools/

# --- 2) Your LangChain agents (kept separate) ---
import langchain_hypemath
# import langchain_linearalgebra

# --- 3) NANDA A2A helper (uses your earlier /a2a POST shape) ---
A2A_URL = "http://localhost:6000/a2a"  # change if your NANDA bus is elsewhere
from langchain_linearalgebra import create_linearalgebra
LA_TUTOR = create_linearalgebra()

from langchain_hypemath import hype_math
HYPE_TUTOR = hype_math()

def a2a_send(agent_tag: str, text: str) -> dict:
    """
    Send a message to another agent via NANDA A2A bus.
    agent_tag: e.g., "@HYPE" or "@LINEAR"
    """
    payload = {
        "role": "user",
        "content": {
            "type": "text",
            "text": f"{agent_tag} {text}"
        }
    }
    r = requests.post(A2A_URL, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()

# --- 4) Manual routing rules (hard guarantee MATLAB does the math) ---
FN_HINTS = ("eig(", "svd(", "inv(", "det(", "rank(", "rref(", "qr(", "lu(", "chol(")
MATH_LIKE = re.compile(r"[0-9\[\]\s,;:\.\+\-\*/\^()eE]")

def is_raw_math(msg: str) -> bool:
    t = msg.strip()
    if t.startswith("="):
        return True
    if any(fn in t for fn in FN_HINTS):
        return True
    # simple matrix/expression sniff (not perfect, but safe because MATLAB validates again)
    return bool(MATH_LIKE.search(t)) and ("[" in t or "(" in t)

# --- 5) Router logic ---
def route_message(msg: str, explain_after=True, encourage_after=True) -> str:
    if is_raw_math(msg):
        # 5a. Compute with MATLAB ONLY (no LLM math)
        try:
            result = calculator_cli(msg)
            out = f"MATLAB result: {result}"
        except Exception as e:
            return f"MATLAB error: {e}"

        # 5b. (Optional) Use NANDA to ask your linear-algebra agent to explain
        if explain_after:
            try:
                _ = a2a_send("@LINEAR",
                             f"Explain this result to a student in simple steps: {result}. "
                             f"Original expression: {msg}")
            except Exception as e:
                out += f"\n(Note: explanation agent unreachable: {e})"

        # 5c. (Optional) Use NANDA to ask your hype agent to encourage
        if encourage_after:
            try:
                _ = a2a_send("@HYPE",
                             "Give a brief, upbeat encouragement for successfully trying the problem.")
            except Exception as e:
                out += f"\n(Note: hype agent unreachable: {e})"

        return out

    # Non-math text → pick an agent manually (still no math here)
    if any(k in msg.lower() for k in ("eigen", "matrix", "vector", "linear algebra", "svd", "rank")):
        agent = LA_TUTOR
    else:
        agent = HYPE_TUTOR
    return agent.invoke({"message": msg})

# --- 6) Simple terminal loop ---
def main():
    print("Manual router (MATLAB for math; NANDA for agent A2A). Type 'exit' to quit.")
    while True:
        try:
            msg = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if msg.lower() in {"exit", "quit"}:
            break

        reply = route_message(msg)
        print(reply)

if __name__ == "__main__":
    main()
