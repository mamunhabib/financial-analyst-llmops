"""
=============================================================================
FILE ROLE & CALL CHAIN CONTEXT:
- Role: ReAct Agent Tool Suite Registry
- Where this file is used / Who calls it:
    1. Imported by: src/handlers/react_core.py
       (Binds ALL_FINANCIAL_TOOLS to Groq Llama-3.3-70B model).
    2. Used by: serving/app.py
       (Exposes tool definitions for API telemetry).
=============================================================================
"""

from src.tools.market_tool import (
    get_company_news,
    get_live_stock_quote,
    get_us_treasury_yield,
)
from src.tools.rag_tool import execute_sec_search, sec_rag_search
from src.tools.sandbox_tool import execute_financial_math, run_financial_math

# Complete registry of tools provided to the ReAct agent
ALL_FINANCIAL_TOOLS = [
    sec_rag_search,
    run_financial_math,
    get_live_stock_quote,
    get_us_treasury_yield,
    get_company_news,
]

__all__ = [
    "sec_rag_search",
    "execute_sec_search",
    "run_financial_math",
    "execute_financial_math",
    "get_live_stock_quote",
    "get_us_treasury_yield",
    "get_company_news",
    "ALL_FINANCIAL_TOOLS",
]
