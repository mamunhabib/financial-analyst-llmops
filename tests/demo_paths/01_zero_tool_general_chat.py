"""
Call Chain & Role:
------------------
Architecture Layer: Educational Demonstration — LLMOps Dynamic Routing
Path 1: Zero-Tool General Chat (Instant Conversational Pathway)
Concept Demonstrated:
    In production LLMOps, invoking vector stores, live APIs, or sandboxes for conversational queries
    wastes money and introduces 5-10s of unnecessary latency. 
    The Prompt Router recognizes zero-tool intent in <150ms and bypasses all execution tools.
Callers:
    - User terminal: python -m tests.demo_paths.01_zero_tool_general_chat
Observability:
    - Live Langfuse Web UI: http://localhost:8092 (Filtered by tag 'route:GENERAL_CHAT')
"""

import time

from src.agent.engine import financial_agent

DEMO_PROMPT = "Hello! Who are you and what financial analysis capabilities can you provide for institutional investors?"


def main():
    print("=" * 85)
    print("🎓 LLMOPS PATH 1: ZERO-TOOL GENERAL CHAT (COST & LATENCY MINIMIZATION)")
    print("=" * 85)
    print(f"Prompt: \"{DEMO_PROMPT}\"")
    print("-" * 85)

    start_time = time.perf_counter()
    session_id = f"demo-path-01-{int(time.time())}"

    # Execute agent pipeline
    response = financial_agent.process_query(
        query=DEMO_PROMPT,
        session_id=session_id,
    )
    latency_ms = (time.perf_counter() - start_time) * 1000.0

    print("📊 EXECUTION PATH ANALYSIS:")
    print(f"  • Classified Route:    {response.route}")
    print(f"  • Tools Executed:      {len(response.tool_calls)} (Zero tools called!)")
    print(f"  • Input Shield:        Passed={response.input_shield.get('passed')} (PII Scrubbed={response.input_shield.get('pii_detected')})")
    print(f"  • Output Shield:       Passed={response.output_shield.get('passed')} (Disclaimer Appended={response.output_shield.get('disclaimer_appended')})")
    print(f"  • End-to-End Latency:  {round(latency_ms, 1)}ms (Fast conversational path)")
    print(f"  • Session ID:          {response.session_id}")

    print("\n" + "=" * 85)
    print("🔍 VIEW IN LANGFUSE DASHBOARD:")
    print("  1. Open http://localhost:8092")
    print("  2. In the Traces table, click on the trace tagged with 'route:GENERAL_CHAT'")
    print("  3. Notice in the waterfall tree: Zero tool child spans are present!")
    print("=" * 85)

    print("\n📝 Agent Response Excerpt:\n")
    print(response.response[:350] + "...\n")


if __name__ == "__main__":
    main()
