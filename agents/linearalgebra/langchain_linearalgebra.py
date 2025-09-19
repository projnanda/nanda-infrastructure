#!/usr/bin/env python3
import os, time, statistics
from typing import List, Optional
from nanda_adapter import NANDA
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_anthropic import ChatAnthropic

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
    """Create a LangChain-powered agent that explains the important concepts of linear algebra."""

    # Initialize the LLM
    llm = ChatAnthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        model="claude-3-haiku-20240307"
    )

    # Create a prompt template for pirate transformation
    prompt = PromptTemplate(
        input_variables=["message"],
        template="""Explain what linear algebra is and why it is an important subject to study. Make sure the mention the following topics: matrix and vector algebra, Gaussian Elimination, Vector Spaces, Linear. Independence, and Eigenvectors. 
        Respond in language that is easy to understand and try solving a simple math problem with Gaussian Elimination. 
        
        Original message: {message}
        
        Linear Algebra response:"""
    )

    # Create the chain
    chain = prompt | llm | StrOutputParser()

    def pirate_improvement(message_text: str) -> str:
        """Teach the important concepts of the math subject, Linear Algebra"""
        start = time.perf_counter()
        try:
            result = chain.invoke({"message": message_text})
            # return result.strip()
        except Exception as e:
            print(f"Error in teaching Linear Algebra: {e}")
            return f"Count to 1, 2, 3{message_text}, I don't know Linear Algebra!"  # Fallback pirate transformation
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        metrics = compute_latency_metrics(elapsed_ms)

        # Print metrics to terminal
        print("\nLatency summary:")
        print(f"  Latency (this run): {metrics['latency_this_run_ms']:.2f} ms")
        print(f"  Latency p50 (last 2 runs): {metrics['latency_p50_last2_ms']:.2f} ms" if metrics['latency_p50_last2_ms'] is not None else "  Latency p50 (last 2 runs): N/A")
        print(f"  Latency mean (last 2 runs): {metrics['latency_mean_last2_ms']:.2f} ms" if metrics['latency_mean_last2_ms'] is not None else "  Latency mean (last 2 runs): N/A")
        print(f"  Latency p95 (last 2 runs): {metrics['latency_p95_last2_ms']:.2f} ms" if metrics['latency_p95_last2_ms'] is not None else "  Latency p95 (last 2 runs): N/A")
        print(f"  Residual: {metrics['residual']}")
        print("---\n")

        return result.strip()
    return pirate_improvement

def main():
    """Main function to start the Linear Algebra Agent"""

    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Please set your ANTHROPIC_API_KEY environment variable")
        return

    # Create pirate improvement function
    pirate_logic = create_linearalgebra()

    # Initialize NANDA with pirate logic
    nanda = NANDA(pirate_logic)

    # Start the server
    print("Starting Linear Algebra Agent with LangChain...")
    print("We will teach you Linear Algebra in 3 seconds")

    domain = os.getenv("DOMAIN_NAME", "localhost")
    # debbie add
    # port = int(os.getenv("PORT", "6000"))

    if domain != "localhost":
        # Production with SSL
        nanda.start_server_api(os.getenv("ANTHROPIC_API_KEY"), domain)
    else:
        # Development server
        nanda.start_server()
        

if __name__ == "__main__":
    main()