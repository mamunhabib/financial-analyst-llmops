"""
=============================================================================
FILE ROLE & CALL CHAIN CONTEXT:
- Role: Handler 2 — Sub-150ms Intent Classifier & Execution Router
- Where this file is used / Who calls it:
    1. Called by: src/agent/engine.py
       (Executed immediately after input_shield approves the prompt).
    2. Dispatches to: src/handlers/react_core.py
       (Provides the classified route: RAG_QUERY, MARKET_LIVE, COMPLEX_VALUATION, or GENERAL_CHAT,
        along with recommended tools and extracted ticker).
    3. Monitored by: observability/langfuse_tracker.py
       (Audits routing accuracy, latency, and intent classification confidence).
=============================================================================
"""

import json
import logging
import re
import time
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from config.settings import settings

logger = logging.getLogger(__name__)


class RouteCategory(str, Enum):
    COMPLEX_VALUATION = "COMPLEX_VALUATION"  # Multi-step DCF, WACC, intrinsic value, financial modeling
    RAG_QUERY = "RAG_QUERY"                  # SEC 10-K filings, annual report risks, segment revenue
    MARKET_LIVE = "MARKET_LIVE"              # Real-time stock prices, 10Y yield, market cap, breaking news
    GENERAL_CHAT = "GENERAL_CHAT"            # Greetings, general financial education, conversational query


class RouteDecision(BaseModel):
    """Structured routing outcome delivered to the ReAct agent engine."""
    route: RouteCategory = Field(description="Primary execution route")
    ticker: Optional[str] = Field(default=None, description="Extracted stock ticker symbol (e.g. AAPL, NVDA, MSFT)")
    confidence: float = Field(default=0.90, description="Classification confidence score between 0.0 and 1.0")
    recommended_tools: List[str] = Field(default_factory=list, description="Recommended tool names for this route")
    reasoning: str = Field(description="Brief explanation of why this route was selected")
    latency_ms: float = Field(default=0.0, description="Routing classifier execution latency in ms")


# Mapping of route categories to optimal tool subsets
TOOL_ROUTING_MAP: Dict[RouteCategory, List[str]] = {
    RouteCategory.COMPLEX_VALUATION: [
        "sec_10k_search",
        "run_financial_math",
        "get_live_stock_quote",
        "get_us_treasury_yield",
    ],
    RouteCategory.RAG_QUERY: [
        "sec_10k_search",
    ],
    RouteCategory.MARKET_LIVE: [
        "get_live_stock_quote",
        "get_us_treasury_yield",
        "get_company_news",
    ],
    RouteCategory.GENERAL_CHAT: [],
}

# Ticker pattern matcher
TICKER_PATTERNS = {
    "AAPL": re.compile(r"\b(AAPL|Apple(?:\s+Inc\.?)?)\b", re.IGNORECASE),
    "NVDA": re.compile(r"\b(NVDA|Nvidia(?:\s+Corporation)?)\b", re.IGNORECASE),
    "MSFT": re.compile(r"\b(MSFT|Microsoft(?:\s+Corporation)?)\b", re.IGNORECASE),
}

# Fast keyword patterns for fallback heuristic classifier
GREETING_KEYWORDS = re.compile(
    r"\b(hello|hi|hey|greetings|who\s+are\s+you|how\s+are\s+you|what\s+can\s+you\s+do|help\s+me)\b",
    re.IGNORECASE,
)
VALUATION_KEYWORDS = re.compile(
    r"\b(dcf|wacc|cagr|intrinsic\s+value|valuation|undervalued|overvalued|fair\s+value|"
    r"discounted\s+cash\s+flow|terminal\s+value|enterprise\s+value|target\s+price)\b",
    re.IGNORECASE,
)
RAG_KEYWORDS = re.compile(
    r"\b(10-k|10k|annual\s+report|sec\s+filing|item\s+1|item\s+1a|risk\s+factors|"
    r"item\s+7|md&a|capex|capital\s+expenditure|supply\s+chain\s+risk|antitrust|doj)\b",
    re.IGNORECASE,
)
MARKET_KEYWORDS = re.compile(
    r"\b(stock\s+price|current\s+price|trading\s+at|market\s+cap|pe\s+ratio|p/e|52-week|"
    r"yield|treasury|news|headline|gain|loss|volume|beta|today\'s\s+(?:price|market|trading|gain))\b",
    re.IGNORECASE,
)


class PromptRouter:
    """
    Handler 2: Sub-150ms Intent Classifier & Tool Router.
    Uses Groq LPU with Llama-3.2-3B for lightning-fast semantic classification,
    with an instant deterministic heuristic fallback.
    """

    def __init__(self):
        self.groq_api_key = settings.GROQ_API_KEY
        self.model_name = settings.GROQ_ROUTER_MODEL

    def extract_ticker(self, text: str) -> Optional[str]:
        """Extracts target company ticker from text."""
        for sym, pattern in TICKER_PATTERNS.items():
            if pattern.search(text):
                return sym
        return None

    def _heuristic_route(self, text: str, ticker: Optional[str]) -> RouteDecision:
        """Instant sub-millisecond pattern-based intent router (Fallback)."""
        clean = text.strip()

        # Rule 1: General greeting takes precedence if no company ticker is mentioned
        if GREETING_KEYWORDS.search(clean) and not ticker and not VALUATION_KEYWORDS.search(clean) and not RAG_KEYWORDS.search(clean):
            route = RouteCategory.GENERAL_CHAT
            reason = "Query is a general greeting or conversational question; zero tools needed."
        # Rule 2: Complex valuation
        elif VALUATION_KEYWORDS.search(clean):
            route = RouteCategory.COMPLEX_VALUATION
            reason = "Query references financial valuation models (DCF/WACC/Intrinsic Value)."
        # Rule 3: SEC 10-K RAG query
        elif RAG_KEYWORDS.search(clean):
            route = RouteCategory.RAG_QUERY
            reason = "Query requests audited SEC 10-K disclosures, filings, or risk factors."
        # Rule 4: Live market quotes or news
        elif MARKET_KEYWORDS.search(clean) or ticker:
            route = RouteCategory.MARKET_LIVE
            reason = "Query requests real-time market quotes, yields, or corporate news."
        # Rule 5: Default conversational fallback
        else:
            route = RouteCategory.GENERAL_CHAT
            reason = "Query is general conversation or conceptual question; zero tools needed."

        return RouteDecision(
            route=route,
            ticker=ticker,
            confidence=0.92,
            recommended_tools=TOOL_ROUTING_MAP[route],
            reasoning=f"Heuristic Match: {reason}",
        )

    def route_query(self, text: str) -> RouteDecision:
        """
        Classifies user prompt into the optimal execution route.

        Args:
            text: Sanitized user prompt from Handler 1 (Input Shield).

        Returns:
            RouteDecision containing target category, ticker, and recommended tools.
        """
        start_time = time.perf_counter()
        clean_text = text.strip()
        ticker = self.extract_ticker(clean_text)

        # Attempt Groq Llama-3.2-3B classification if API key is present
        if self.groq_api_key:
            try:
                from groq import Groq
                client = Groq(api_key=self.groq_api_key)

                system_prompt = (
                    "You are a strict, ultra-fast intent classifier for an AI Financial Analyst Agent. "
                    "Analyze the user query and classify it into EXACTLY ONE category:\n"
                    "- COMPLEX_VALUATION: User asks for DCF, WACC, intrinsic value, or financial modeling.\n"
                    "- RAG_QUERY: User asks about official SEC 10-K reports, annual risks, or Capex history.\n"
                    "- MARKET_LIVE: User asks for live stock quotes, price changes, P/E ratios, or news.\n"
                    "- GENERAL_CHAT: Greetings, conversational queries, or general non-data definitions.\n\n"
                    "Respond with ONLY a valid JSON object matching this schema:\n"
                    '{"category": "COMPLEX_VALUATION|RAG_QUERY|MARKET_LIVE|GENERAL_CHAT", "reasoning": "brief explanation"}'
                )

                response = client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": clean_text},
                    ],
                    temperature=0.0,
                    max_tokens=80,
                    response_format={"type": "json_object"},
                    timeout=2.0,
                )

                raw_content = response.choices[0].message.content.strip()
                parsed = json.loads(raw_content)
                category_str = parsed.get("category", "").upper()

                if category_str in RouteCategory.__members__:
                    category = RouteCategory(category_str)
                    latency = (time.perf_counter() - start_time) * 1000.0
                    return RouteDecision(
                        route=category,
                        ticker=ticker,
                        confidence=0.96,
                        recommended_tools=TOOL_ROUTING_MAP[category],
                        reasoning=parsed.get("reasoning", "Classified by Groq Llama-3.2-3B"),
                        latency_ms=round(latency, 2),
                    )

            except Exception as e:
                logger.debug(f"Groq router fallback to heuristic ({e})")

        # Fallback to instant heuristic router
        decision = self._heuristic_route(clean_text, ticker)
        latency = (time.perf_counter() - start_time) * 1000.0
        decision.latency_ms = round(latency, 2)
        return decision

    # Alias for API uniformity
    route = route_query


# Singleton instance for direct import
prompt_router = PromptRouter()


def route_prompt(text: str) -> RouteDecision:
    """Convenience helper to route a user prompt."""
    return prompt_router.route_query(text)
