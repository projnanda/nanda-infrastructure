#!/usr/bin/env python3
import os, time, statistics
from typing import List, Optional
from nanda_adapter import NANDA
from openai import OpenAI
# from langchain_core.prompts import PromptTemplate
# from langchain_core.output_parsers import StrOutputParser
# from langchain_anthropic import ChatAnthropic

LATENCY_HISTORY: List[float] = []

def compute_latency_metrics(this_run: float) -> dict:
    """Compute metrics based on this run and last 2 runs"""
    LATENCY_HISTORY.append(this_run)
    prior_two = LATENCY_HISTORY[-2:]  # two runs before this one

    if prior_two:
        p50 = statistics.median(prior_two)
        mean = statistics.mean(prior_two)
        p95 = max(prior_two) if len(prior_two) >= 2 else prior_two[0]
    else:
        p50 = mean = p95 = None

    return {
        "latency_this_run_ms": this_run,
        "latency_p50_last2_ms": p50,
        "latency_mean_last2_ms": mean,
        "latency_p95_last2_ms": p95,
        "residual": None  # not applicable for this agent
    }

def create_linearalgebra():
    """Create a ChatGPT-powered agent that explains the important concepts of linear algebra."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini") 

    SYSTEM_PROMPT = (
        "You are a helpful math tutor. Be clear, correct, and concise."
    )

    def tutor(message_text: str) -> str:
        """Teach the important concepts of Linear Algebra."""
        user_prompt = f"""Explain what linear algebra is and why it is an important subject to study.
Make sure to mention: matrix and vector algebra, Gaussian Elimination, vector spaces, linear independence, and eigenvectors.
Respond in language that is easy to understand, and try solving a simple math problem with Gaussian elimination.

Original message: {message_text}

Linear Algebra response:"""

        start = time.perf_counter()
        try:
            # Chat Completions API
            resp = client.chat.completions.create(
                model=model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            result = resp.choices[0].message.content or ""
        except Exception as e:
            print(f"Error calling ChatGPT: {e}")
            result = f"Count to 1, 2, 3 {message_text}, I don't know Linear Algebra!"
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        metrics = compute_latency_metrics(elapsed_ms)

        # Terminal metrics
        print("\nLatency summary:")
        print(f"  Latency (this run): {metrics['latency_this_run_ms']:.2f} ms")
        print(
            f"  Latency p50 (last 2 runs): {metrics['latency_p50_last2_ms']:.2f} ms"
            if metrics["latency_p50_last2_ms"] is not None else
            "  Latency p50 (last 2 runs): N/A"
        )
        print(
            f"  Latency mean (last 2 runs): {metrics['latency_mean_last2_ms']:.2f} ms"
            if metrics["latency_mean_last2_ms"] is not None else
            "  Latency mean (last 2 runs): N/A"
        )
        print(
            f"  Latency p95 (last 2 runs): {metrics['latency_p95_last2_ms']:.2f} ms"
            if metrics["latency_p95_last2_ms"] is not None else
            "  Latency p95 (last 2 runs): N/A"
        )
        print(f"  Residual: {metrics['residual']}")
        print("---\n")

        return result.strip()

    return tutor


def main():
    """Main function to start the Linear Algebra Agent"""

    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Please set your OPENAI_API_KEY environment variable")
        return

    # Create pirate improvement function
    pirate_logic = create_linearalgebra()

    # Initialize NANDA with pirate logic
    nanda = NANDA(pirate_logic)

    # Start the server
    print("Starting Linear Algebra Agent with ChatGPT...")
    print("We will teach you Linear Algebra in 3 seconds")

    domain = os.getenv("DOMAIN_NAME", "localhost")
    # debbie add
    # port = int(os.getenv("PORT", "6000"))

    if domain != "localhost":
        # Production with SSL
        nanda.start_server_api(os.getenv("OPENAI_API_KEY"), domain)
    else:
        # Development server
        nanda.start_server()
        

if __name__ == "__main__":
    main()