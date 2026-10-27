"""
=============================================================================
FILE ROLE & CALL CHAIN CONTEXT:
- Role: Market Gateway FastAPI Microservice Server (Port 8004)
- Where this file is used / Who calls it:
    1. Executed by: Uvicorn ASGI server
       (Runs locally via: uvicorn market_gateway.app:app --port 8004
        or in K8s pod: market-gateway-deployment on ClusterIP :8004).
    2. Called by: src/tools/market_tool.py
       (The ReAct Agent tool sends HTTP requests to http://localhost:8004
        or http://market-gateway:8004 in Kubernetes).
    3. Monitored by: Kubernetes Liveness/Readiness probes at /health.
=============================================================================
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from market_gateway import feeds

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("market_gateway")

app = FastAPI(
    title="Financial Market Gateway Microservice",
    description="Internal market data feed microservice providing real-time quotes, 10Y yields, and company news.",
    version="1.0.0",
)

# Enable CORS for local Streamlit UI and inter-service mesh calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["System"])
def health_check() -> Dict[str, str]:
    """Kubernetes liveness and readiness probe endpoint."""
    return {
        "status": "healthy",
        "service": "market-gateway",
        "port": "8004",
        "version": "1.0.0",
    }


@app.get("/", tags=["System"])
def root_info() -> Dict[str, Any]:
    """Root info endpoint describing available market endpoints."""
    return {
        "service": "Financial Market Gateway",
        "status": "running",
        "endpoints": {
            "quote": "/api/v1/market/quote/{ticker}",
            "risk_free_rate": "/api/v1/market/risk-free-rate",
            "news": "/api/v1/market/news/{ticker}",
            "health": "/health",
        },
    }


@app.get("/api/v1/market/quote/{ticker}", tags=["Market Data"])
def get_quote(ticker: str) -> Dict[str, Any]:
    """
    Fetch normalized real-time quote for a given equity ticker.
    Returns current price, day change, market cap, P/E ratio, and 52-week range.
    """
    clean_ticker = ticker.strip().upper()
    if not clean_ticker:
        raise HTTPException(status_code=400, detail="Ticker symbol cannot be empty.")

    logger.info(f"Received quote request for ticker: {clean_ticker}")
    quote = feeds.get_stock_quote(clean_ticker)

    if "error" in quote:
        raise HTTPException(status_code=502, detail=quote["error"])

    return quote


@app.get("/api/v1/market/risk-free-rate", tags=["Market Data"])
def get_risk_free_benchmark() -> Dict[str, Any]:
    """
    Fetch benchmark US 10-Year Treasury Yield (^TNX).
    Required input for Discounted Cash Flow (DCF) and WACC valuation models.
    """
    logger.info("Received request for benchmark risk-free rate (^TNX)")
    return feeds.get_risk_free_rate()


@app.get("/api/v1/market/news/{ticker}", tags=["Market Data"])
def get_news(ticker: str, limit: int = Query(default=5, ge=1, le=15)) -> List[Dict[str, Any]]:
    """
    Fetch recent financial headlines and press releases for a company ticker.
    """
    clean_ticker = ticker.strip().upper()
    if not clean_ticker:
        raise HTTPException(status_code=400, detail="Ticker symbol cannot be empty.")

    logger.info(f"Received news request for ticker: {clean_ticker} (limit={limit})")
    return feeds.get_company_news(clean_ticker, limit=limit)


if __name__ == "__main__":
    import uvicorn
    # Local direct runner on internal port 8004
    uvicorn.run("market_gateway.app:app", host="0.0.0.0", port=8004, reload=True)
