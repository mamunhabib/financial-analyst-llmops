"""
=============================================================================
FILE ROLE & CALL CHAIN CONTEXT:
- Role: SEC 10-K RAG Knowledge Retrieval ReAct Tool
- Where this file is used / Who calls it:
    1. Registered in: src/tools/__init__.py
       (Bundled with other analyst tools into ALL_FINANCIAL_TOOLS list).
    2. Bound to LLM in: src/handlers/react_core.py
       (Groq Llama-3.3-70B model inspects this tool schema and invokes it
        when answering queries requiring official 10-K disclosures).
    3. Invokes: src/rag/vector_client.py
       (Calls UpstashVectorClient.query() to fetch 384-dim semantic chunks).
    4. Traced in: observability/langfuse_tracker.py
       (Captures query text, retrieved chunks, and scores for audit).
=============================================================================
"""

import logging
from typing import Optional

from langchain_core.tools import tool

from src.rag.vector_client import UpstashVectorClient

logger = logging.getLogger(__name__)


def execute_sec_search(
    query: str,
    ticker: Optional[str] = None,
    top_k: int = 3,
) -> str:
    """
    Search official SEC Form 10-K annual reports for substantive financial disclosures.
    
    Args:
        query: Specific financial search query (e.g. 'capital expenditures for AI infrastructure').
        ticker: Optional company ticker filter (e.g. 'AAPL', 'MSFT', 'NVDA').
        top_k: Number of relevant passages to retrieve (default: 3).

    Returns:
        Structured string containing ranked excerpts, sections, and similarity scores.
    """
    try:
        client = UpstashVectorClient()
        filter_expr = f"ticker = '{ticker.upper()}'" if ticker else None

        results = client.query(
            vector=query,
            top_k=top_k,
            filter_expr=filter_expr,
        )

        if not results:
            filter_msg = f" for ticker {ticker}" if ticker else ""
            return f"No relevant SEC 10-K disclosures found{filter_msg} matching query: '{query}'."

        formatted_outputs = []
        for i, r in enumerate(results, start=1):
            meta = r.get("metadata", {})
            ticker_name = r.get("ticker") or meta.get("ticker", "Unknown")
            company_name = meta.get("company_name", ticker_name)
            section = r.get("section") or meta.get("section", "General")
            year = r.get("year") or meta.get("year", "2024")
            score = r.get("score", 0.0)
            text = r.get("text", "").strip()

            snippet = (
                f"[Source #{i}] {company_name} ({ticker_name}) — Form 10-K (FY{year})\n"
                f"Section: {section} (Similarity Match: {score:.2%})\n"
                f"Excerpts:\n\"{text}\"\n"
            )
            formatted_outputs.append(snippet)

        return "\n---\n".join(formatted_outputs)

    except Exception as e:
        logger.error(f"Error executing SEC RAG search: {e}")
        return f"SEC 10-K Search Error: {str(e)}"


@tool("sec_10k_search")
def sec_rag_search(query: str, ticker: Optional[str] = None) -> str:
    """
    Search official SEC 10-K annual reports filed with the U.S. Securities and Exchange Commission (SEC).
    Contains verified audited information for Apple (AAPL), Microsoft (MSFT), and NVIDIA (NVDA),
    including Item 1 (Business Model), Item 1A (Risk Factors & Supply Chain), and Item 7 (MD&A & Financial Guidance).
    Use this tool whenever you need verified financial facts, revenue figures, risk factors, or historical capex.
    """
    return execute_sec_search(query=query, ticker=ticker, top_k=3)
