"""
Call Chain & Role:
------------------
Architecture Layer: Educational Demonstration — LLMOps Dynamic Routing
Path 6: Omni-Path Institutional Valuation (Full Multi-Tool Multi-Model Orchestration)
Concept Demonstrated:
    The contrast to isolated tool paths: When an institutional query requires legal SEC filings,
    real-time market prices, interest rate benchmarks, corporate news, and verified DCF calculations,
    the autonomous ReAct engine orchestrates all 5 tools sequentially into a unified research report.
Callers:
    - User terminal: python -m tests.demo_paths.06_omni_path_full_valuation
Observability:
    - Live Langfuse Web UI: http://localhost:8092 (Filtered by tag 'route:COMPLEX_VALUATION')
"""

import time

from src.agent.engine import financial_agent

DEMO_PROMPT = (
    "Conduct a comprehensive institutional DCF valuation and equity risk assessment for Apple Inc. (AAPL). "
    "1. Search Apple FY2024 Form 10-K filing for supply chain dependencies and free cash flow notes. "
    "2. Retrieve Apple live market quote, market capitalization, and current P/E ratio. "
    "3. Pull the latest US 10-Year Treasury yield to establish the benchmark risk-free rate. "
    "4. Pull recent corporate headlines for AAPL. "
    "5. Execute a 5-year DCF calculation in the sandbox using cash flows [100.0, 115.0, 130.0, 145.0, 160.0], "
    "a discount rate of 0.085, and a terminal growth rate of 0.025. "
    "Synthesize all findings into a structured institutional report with regulatory disclaimers."
)


def main():
    print("=" * 85)
    print("🎓 LLMOPS PATH 6: OMNI-PATH FULL MULTI-TOOL ORCHESTRATION (THE CONTRAST PATH)")
    print("=" * 85)
    print(f"Master Prompt: \"{DEMO_PROMPT}\"")
    print("-" * 85)

    start_time = time.perf_counter()
    session_id = f"demo-path-06-{int(time.time())}"

    # Execute agent pipeline across all tools
    response = financial_agent.process_query(
        query=DEMO_PROMPT,
        session_id=session_id,
    )
    latency_ms = (time.perf_counter() - start_time) * 1000.0

    print("📊 EXECUTION PATH ANALYSIS:")
    print(f"  • Classified Route:    {response.route} (Target Ticker: {response.ticker})")
    print(f"  • Tools Executed:      {len(response.tool_calls)} Tools (All 5 Microservices Invoked!)")
    for idx, t in enumerate(response.tool_calls, 1):
        print(f"      {idx}. [{t.get('tool')}] ➔ {str(t.get('output_preview', ''))[:70]}...")
    print(f"  • Input Shield:        Passed={response.input_shield.get('passed')}")
    print(f"  • Output Shield:       Passed={response.output_shield.get('passed')} (Grounding Score={response.output_shield.get('grounding_score')})")
    print(f"  • Disclaimer Added:    {response.output_shield.get('disclaimer_appended')}")
    print(f"  • Total Latency:       {round(latency_ms, 1)}ms")
    print(f"  • Session ID:          {response.session_id}")

    print("\n" + "=" * 85)
    print("🔍 VIEW IN LANGFUSE DASHBOARD:")
    print("  1. Open http://localhost:8092")
    print("  2. In the Traces table, click on the trace tagged with 'route:COMPLEX_VALUATION'")
    print("  3. Notice in the waterfall tree: All 5 tools appear as individual clickable child spans!")
    print("=" * 85)

    print("\n📝 Synthesized Research Report Excerpt:\n")
    print(response.response[:450] + "...\n")


if __name__ == "__main__":
    main()
