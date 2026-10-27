"""
Call Chain & Role:
------------------
Architecture Layer: Educational Demonstration — LLMOps Dynamic Routing
Path 4: Deterministic Python Math Sandbox Only (Zero Hallucination Arithmetic)
Concept Demonstrated:
    LLMs frequently hallucinate complex financial calculations and multi-step compounding.
    In enterprise LLMOps, mathematical formulas are never left to stochastic next-token prediction;
    they are delegated to a restricted, AST-verified Python sandbox executing in <1ms.
Callers:
    - User terminal: python -m tests.demo_paths.04_math_sandbox_only
Observability:
    - Live Langfuse Web UI: http://localhost:8092 (Filtered by tag 'path:sandbox-math')
"""

import time

from src.agent.engine import financial_agent

DEMO_PROMPT = "Calculate the Weighted Average Cost of Capital (WACC) where Equity value is 800.0, Debt value is 200.0, Cost of Equity is 0.10, Cost of Debt is 0.05, and Corporate Tax Rate is 0.21."


def main():
    print("=" * 85)
    print("🎓 LLMOPS PATH 4: DETERMINISTIC PYTHON MATH SANDBOX ONLY (ZERO HALLUCINATIONS)")
    print("=" * 85)
    print(f"Prompt: \"{DEMO_PROMPT}\"")
    print("-" * 85)

    start_time = time.perf_counter()
    session_id = f"demo-path-04-{int(time.time())}"

    # Execute agent pipeline
    response = financial_agent.process_query(
        query=DEMO_PROMPT,
        session_id=session_id,
    )
    latency_ms = (time.perf_counter() - start_time) * 1000.0

    print("📊 EXECUTION PATH ANALYSIS:")
    print(f"  • Classified Route:    {response.route}")
    print(f"  • Tools Executed:      {len(response.tool_calls)} Sandbox Tool(s)")
    for t in response.tool_calls:
        print(f"      ➔ [{t.get('tool')}] — Output preview: {str(t.get('output_preview', ''))[:80]}...")
    print("  • Tools Pruned/Skipped: SEC 10-K RAG (0 vectors), Live Feeds (0 calls)")
    print(f"  • Input Shield:        Passed={response.input_shield.get('passed')}")
    print(f"  • Output Shield:       Passed={response.output_shield.get('passed')}")
    print(f"  • Total Latency:       {round(latency_ms, 1)}ms")
    print(f"  • Session ID:          {response.session_id}")

    print("\n" + "=" * 85)
    print("🔍 VIEW IN LANGFUSE DASHBOARD:")
    print("  1. Open http://localhost:8092")
    print("  2. In the Traces table, filter by Tag: 'path:sandbox-math'")
    print("  3. Click on the span 'Tool Execution: run_financial_math' to see the exact AST-verified Python formula!")
    print("=" * 85)

    print("\n📝 Deterministic Math Report Excerpt:\n")
    print(response.response[:400] + "...\n")


if __name__ == "__main__":
    main()
