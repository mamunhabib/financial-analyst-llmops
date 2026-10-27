"""
=============================================================================
FILE ROLE & CALL CHAIN CONTEXT:
- Role: Live Market Gateway REST Consumer ReAct Tool
- Where this file is used / Who calls it:
    1. Registered in: src/tools/__init__.py
       (Bundled into ALL_FINANCIAL_TOOLS list for the ReAct Agent).
    2. Bound to LLM in: src/handlers/react_core.py
       (Groq Llama-3.3-70B invokes this tool when user asks for real-time
        stock quotes, valuation multiples, or risk-free benchmark rates).
    3. Invokes: market_gateway/feeds.py OR HTTP http://market-gateway:8004
       (Queries the local FastAPI microservice / feeds with 60s cache).
    4. Traced in: observability/langfuse_tracker.py
       (Captures market ticker requested and price returned).
=============================================================================
"""

from typing import Any, Dict, List, Optional
import os
import logging
import httpx
from langchain_core.tools import tool

from market_gateway import feeds

logger = logging.getLogger(__name__)

# Default Market Gateway host (in-cluster: http://market-gateway:8004; local: http://localhost:8004)
GATEWAY_URL = os.getenv("MARKET_GATEWAY_URL", "http://localhost:8004")


def fetch_quote_data(ticker: str) -> Dict[str, Any]:
    """
    Fetches real-time quote for a given ticker from the Market Gateway service.
    Falls back gracefully to in-process feeds module if HTTP service is offline.
    """
    clean_sym = ticker.strip().upper()
    try:
        # Attempt HTTP call to Market Gateway microservice
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{GATEWAY_URL}/api/v1/market/quote/{clean_sym}")
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        # Microservice not yet running on port 8004; use in-process engine directly
        pass

    return feeds.get_stock_quote(clean_sym)


def fetch_rate_data() -> Dict[str, Any]:
    """
    Fetches the benchmark US 10-Year Treasury Yield (^TNX).
    """
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{GATEWAY_URL}/api/v1/market/risk-free-rate")
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass

    return feeds.get_risk_free_rate()


@tool("get_live_stock_quote")
def get_live_stock_quote(ticker: str) -> str:
    """
    Fetch real-time stock price and valuation multiples for a publicly traded company.
    Returns current trading price, dollar & percentage day change, market capitalization,
    trailing and forward P/E ratios, 52-week high/low range, and beta.
    
    Args:
        ticker: Equity ticker symbol (e.g. 'AAPL', 'MSFT', 'NVDA').
    """
    data = fetch_quote_data(ticker)

    if "error" in data:
        return f"Market Data Error for {ticker}: {data['error']}"

    return (
        f"📊 Live Market Quote: {data['company_name']} ({data['ticker']})\n"
        f"• Current Price: ${data['current_price']} {data['currency']} {data['change_str']}\n"
        f"• Market Capitalization: ${data['market_cap_billions']} Billion\n"
        f"• Trailing P/E: {data['trailing_pe']} | Forward P/E: {data['forward_pe']}\n"
        f"• 52-Week Range: ${data['fifty_two_week_low']} – ${data['fifty_two_week_high']}\n"
        f"• Beta (Volatility): {data['beta']}\n"
        f"• Source: {data.get('source', 'market_gateway')} (as of {data['timestamp'][:19]}Z)"
    )


@tool("get_us_treasury_yield")
def get_us_treasury_yield() -> str:
    """
    Fetch the live benchmark US 10-Year Treasury Yield (^TNX).
    This represents the standard risk-free rate (Rf) required for financial models
    including Capital Asset Pricing Model (CAPM), WACC, and DCF terminal valuations.
    """
    data = fetch_rate_data()

    return (
        f"🏛️ Benchmark Risk-Free Rate: {data['name']} ({data['symbol']})\n"
        f"• Current Yield: {data['formatted']}\n"
        f"• Decimal Equivalent for Formulas (Rf): {data['decimal_rate']}\n"
        f"• Timestamp: {data['timestamp'][:19]}Z"
    )


@tool("get_company_news")
def get_company_news(ticker: str) -> str:
    """
    Fetch the latest financial news headlines and market developments for a company.
    
    Args:
        ticker: Equity ticker symbol (e.g. 'AAPL', 'MSFT', 'NVDA').
    """
    articles = feeds.get_company_news(ticker, limit=3)
    if not articles:
        return f"No recent headlines found for {ticker}."

    lines = [f"📰 Recent Market Headlines for {ticker.upper()}:"]
    for i, a in enumerate(articles, start=1):
        lines.append(f"{i}. [{a['publisher']}] {a['title']} ({a['published_at']})")

    return "\n".join(lines)
