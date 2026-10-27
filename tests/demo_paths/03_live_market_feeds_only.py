"""
Call Chain & Role:
------------------
Architecture Layer: Educational Demonstration — LLMOps Dynamic Routing
Path 3: Live Market Gateway Feeds Only (Real-Time Microservice Ingress)
Concept Demonstrated:
    When a trader requests real-time stock prices or interest rate benchmarks,
    historical 10-K filings are obsolete. The agent bypasses vector search entirely
    and routes only to the standalone Market Gateway microservice on ClusterIP :8004.
Callers:
    - User terminal: python -m tests.demo_paths.03_live_market_feeds_only
Observability:
    - Live Langfuse Web UI: http://localhost:8092 (Filtered by tag 'path:live-quote')
"""

import time
from src.agent.engine import financial_agent

DEMO_PROMPT = "What is Microsoft current stock price, today price change, and the current yield on the US 10-Year Treasury?"


def main():
    print("=" * 85)
    print("🎓 LLMOPS PATH 3: LIVE MARKET GATEWAY FEEDS ONLY (REAL-TIME DATA INGRESS)")
    print("=" * 85)
    print(f"Prompt: \"{DEMO_PROMPT}\"")
    print("-" * 85)

    start_time = time.perf_counter()
    session_id = f"demo-path-03-{int(time.time())}"

    # Execute agent pipeline
    response = financial_agent.process_query(
        query=DEMO_PROMPT,
        session_id=session_id,
    )
    latency_ms = (time.perf_counter() - start_time) * 1000.0

    print("📊 EXECUTION PATH ANALYSIS:")
    print(f"  • Classified Route:    {response.route} (Target Ticker: {response.ticker})")
    print(f"  • Tools Executed:      {len(response.tool_calls)} Market Tool(s)")
    for t in response.tool_calls:
        print(f"      ➔ [{t.get('tool')}] — Output preview: {str(t.get('output_preview', ''))[:80]}...")
    print(f"  • Tools Pruned/Skipped: SEC 10-K RAG (0 vectors fetched), AST Sandbox (0 formulas run)")
    print(f"  • Input Shield:        Passed={response.input_shield.get('passed')}")
    print(f"  • Output Shield:       Passed={response.output_shield.get('passed')} (Grounding Score={response.output_shield.get('grounding_score')})")
    print(f"  • Total Latency:       {round(latency_ms, 1)}ms")
    print(f"  • Session ID:          {response.session_id}")

    print("\n" + "=" * 85)
    print("🔍 VIEW IN LANGFUSE DASHBOARD:")
    print("  1. Open http://localhost:8092")
    print("  2. In the Traces table, filter by Tag: 'path:live-quote'")
    print("  3. Notice in the waterfall tree: Only Market Gateway child spans appear!")
    print("=" * 85)

    print("\n📝 Live Market Valuation Table Excerpt:\n")
    print(response.response[:400] + "...\n")


if __name__ == "__main__":
    main()
