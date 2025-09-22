# #!/usr/bin/env python3
# import os, time, statistics
# from typing import List
# from nanda_adapter import NANDA

# from crewai import Agent, Task, Crew
# from langchain_anthropic import ChatAnthropic 

# LATENCY_HISTORY: List[float] = []

# def compute_latency_metrics(this_run: float) -> dict:
#     """Compute metrics based on this run and last 2 runs"""
#     LATENCY_HISTORY.append(this_run)
#     prior_two = LATENCY_HISTORY[-2:] 

#     if prior_two:
#         p50 = statistics.median(prior_two)
#         mean = statistics.mean(prior_two)
#         p95 = max(prior_two) if len(prior_two) >= 2 else prior_two[0]
#     else:
#         p50 = mean = p95 = None

#     return {
#         "latency_this_run_ms": this_run,
#         "latency_p50_last2_ms": p50,
#         "latency_mean_last2_ms": mean,
#         "latency_p95_last2_ms": p95,
#         "residual": None 
#     }

# def create_linearalgebra():
#     """Create a CrewAI-powered agent that explains the important concepts of linear algebra."""

#     # LLM (Anthropic via LangChain wrapper, used inside CrewAI)
#     llm = ChatAnthropic(
#         api_key=os.getenv("ANTHROPIC_API_KEY"),
#         model="claude-3-haiku-20240307",
#         temperature=0.2,
#     )

#     tutor = Agent(
#         role="Linear Algebra Tutor",
#         goal=(
#             "Explain core linear algebra ideas clearly and correctly and, when asked, "
#             "demonstrate a simple Gaussian elimination example."
#         ),
#         backstory=(
#             "You are a precise but friendly math tutor who favors short, accurate explanations."
#         ),
#         llm=llm,
#         verbose=False,
#         allow_delegation=False,
#     )


#     explain_task = Task(
#         description=(
#             "Explain what linear algebra is and why it is important. "
#             "Be easy to understand and mention: matrix & vector algebra, Gaussian elimination, "
#             "vector spaces, linear independence, and eigenvectors. "
#             "Try solving a small math problem with Gaussian elimination.\n\n"
#             "Original message from user:\n{message}\n\n"
#             "Provide a concise, correct answer."
#         ),
#         expected_output="A short, easy-to-understand explanation including the requested topics.",
#         agent=tutor,
#     )

#     crew = Crew(
#         agents=[tutor],
#         tasks=[explain_task],
#         verbose=False,
#     )

#     def tutor_improvement(message_text: str) -> str:
#         """Teach the important concepts of Linear Algebra using CrewAI."""
#         start = time.perf_counter()
#         try:
#             # CrewAI returns a CrewOutput-like object or str; coerce to string
#             result = crew.kickoff(inputs={"message": message_text})
#             result_text = str(result) if result is not None else ""
#         except Exception as e:
#             print(f"Error in teaching Linear Algebra: {e}")
#             result_text = f"Count to 1, 2, 3 {message_text}, I don't know Linear Algebra!"
#         elapsed_ms = (time.perf_counter() - start) * 1000.0

#         metrics = compute_latency_metrics(elapsed_ms)

#         # Print metrics to terminal
#         print("\nLatency summary:")
#         print(f"  Latency (this run): {metrics['latency_this_run_ms']:.2f} ms")
#         print(
#             f"  Latency p50 (last 2 runs): {metrics['latency_p50_last2_ms']:.2f} ms"
#             if metrics['latency_p50_last2_ms'] is not None else
#             "  Latency p50 (last 2 runs): N/A"
#         )
#         print(
#             f"  Latency mean (last 2 runs): {metrics['latency_mean_last2_ms']:.2f} ms"
#             if metrics['latency_mean_last2_ms'] is not None else
#             "  Latency mean (last 2 runs): N/A"
#         )
#         print(
#             f"  Latency p95 (last 2 runs): {metrics['latency_p95_last2_ms']:.2f} ms"
#             if metrics['latency_p95_last2_ms'] is not None else
#             "  Latency p95 (last 2 runs): N/A"
#         )
#         print(f"  Residual: {metrics['residual']}")
#         print("---\n")

#         return result_text.strip()

#     return tutor_improvement

# def main():
#     """Start the Linear Algebra Agent (CrewAI)."""

#     if not os.getenv("ANTHROPIC_API_KEY"):
#         print("Please set your ANTHROPIC_API_KEY environment variable")
#         return

#     tutor_logic = create_linearalgebra()
#     nanda = NANDA(tutor_logic)

#     print("Starting Linear Algebra Agent with CrewAI...")
#     domain = os.getenv("DOMAIN_NAME", "localhost")
#     if domain != "localhost":
#         nanda.start_server_api(os.getenv("ANTHROPIC_API_KEY"), domain)
#     else:
#         nanda.start_server()

# if __name__ == "__main__":
#     main()
