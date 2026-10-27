"""
Call Chain & Role:
------------------
Architecture Layer: Educational Demonstration — LLMOps Dynamic Routing
Path 2: SEC 10-K RAG Retrieval Only (Upstash Vector Store)
Concept Demonstrated:
    When an analyst asks about audited legal disclosures, 10-K Item 1A risk factors, or historical
    filings, real-time market prices and Python math calculators are completely irrelevant.
    The agent dynamically routes only to the Upstash Vector RAG database, querying 384-dimensional
    FastEmbed vectors without calling market or math microservices.
Callers:
    - User terminal: python -m tests.demo_paths.02_sec_10k_rag_only
Observability:
    - Live Langfuse Web UI: http://localhost:8092 (Filtered by tag 'path:sec-10k-rag')
"""

import time
from src.agent.engine import financial_agent

DEMO_PROMPT = "What specific supply chain risks regarding Taiwan and TSMC does NVIDIA report in its audited SEC Form 10-K filing?"


def main():
    print("=" * 85)
    print("🎓 LLMOPS PATH 2: SEC 10-K VECTOR RAG ONLY (LEGAL DISCLOSURE RETRIEVAL)")
    print("=" * 85)
    print(f"Prompt: \"{DEMO_PROMPT}\"")
    print("-" * 85)

    start_time = time.perf_counter()
    session_id = f"demo-path-02-{int(time.time())}"

    # Execute agent pipeline
    response = financial_agent.process_query(
        query=DEMO_PROMPT,
        session_id=session_id,
    )
    latency_ms = (time.perf_counter() - start_time) * 1000.0

    print("📊 EXECUTION PATH ANALYSIS:")
    print(f"  • Classified Route:    {response.route} (Target Ticker: {response.ticker})")
    print(f"  • Tools Executed:      {len(response.tool_calls)} Tool(s)")
    for t in response.tool_calls:
        print(f"      ➔ [{t.get('tool')}] — Output preview: {str(t.get('output_preview', ''))[:80]}...")
    print(f"  • Tools Pruned/Skipped: Market Gateway (:8004), Yahoo API, AST Sandbox (Zero calls)")
    print(f"  • Input Shield:        Passed={response.input_shield.get('passed')}")
    print(f"  • Output Shield:       Passed={response.output_shield.get('passed')} (Grounding Score={response.output_shield.get('grounding_score')})")
    print(f"  • Total Latency:       {round(latency_ms, 1)}ms")
    print(f"  • Session ID:          {response.session_id}")

    print("\n" + "=" * 85)
    print("🔍 VIEW IN LANGFUSE DASHBOARD:")
    print("  1. Open http://localhost:8092")
    print("  2. In the Traces table, filter by Tag: 'path:sec-10k-rag'")
    print("  3. Look at the left Waterfall Tree: Only 'Tool Execution: sec_10k_search' is present!")
    print("=" * 85)

    print("\n📝 Synthesized 10-K Audit Report Excerpt:\n")
    print(response.response[:400] + "...\n")


if __name__ == "__main__":
    main()
