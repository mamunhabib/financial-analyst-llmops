"""
Call Chain & Role:
------------------
Architecture Layer: Phase 5 - Agent Serving Microservice
Role: Ingress HTTP REST & SSE Streaming API on Port 8000 (External 8091).
Callers:
    - ui/app.py: Streamlit frontend sends analyst queries and consumes SSE stream.
    - Kubernetes Service: agent-serving LoadBalancer / ClusterIP routes port 8091 -> 8000.
Dependencies:
    - fastapi: Web framework.
    - src.agent.engine: FinancialAnalystEngine.
    - config.settings: Application settings.
"""

import asyncio
import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from config.settings import settings
from src.agent.engine import AgentResponse, financial_agent
from src.agent.memory import memory_client

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("AgentServingAPI")

app = FastAPI(
    title="Autonomous Financial & Market Analyst Agent API",
    description="Defense-in-depth LLMOps Agent serving SEC 10-K RAG, live market quotes, and DCF math.",
    version="1.0.0",
)

# Enable CORS for local Streamlit UI (Port 8090 / 8501) and ingress
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    query: str = Field(..., description="Financial analyst question or valuation prompt")
    session_id: Optional[str] = Field(default=None, description="Optional conversation session UUID")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None
    stream: bool = False
    session_id: Optional[str] = None


@app.get("/health", tags=["System"])
async def health_check():
    """Kubernetes liveness and readiness probe endpoint."""
    return {
        "status": "healthy",
        "service": "financial-analyst-agent",
        "environment": settings.ENVIRONMENT,
        "ports": {
            "internal": settings.AGENT_PORT,
            "market_gateway": settings.MARKET_GATEWAY_PORT,
        },
        "reasoning_model": settings.GROQ_REASONING_MODEL,
        "timestamp": time.time(),
    }


@app.post("/v1/analyze", response_model=AgentResponse, tags=["Agent"])
async def analyze_query(req: AnalyzeRequest):
    """
    Primary financial analysis endpoint.
    Executes the 4-handler pipeline: Input Shield -> Router -> ReAct Engine -> Output Shield.
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        response = financial_agent.process_query(
            query=req.query,
            session_id=req.session_id,
        )
        return response
    except Exception as e:
        logger.error(f"Error during agent execution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal agent error: {str(e)}")


@app.post("/v1/chat/completions", tags=["OpenAI Compatibility"])
async def chat_completions(req: ChatCompletionRequest):
    """OpenAI-compatible chat completion endpoint for standard integrations."""
    if not req.messages:
        raise HTTPException(status_code=400, detail="Messages array cannot be empty.")

    # Extract last user message
    user_query = req.messages[-1].content

    response = financial_agent.process_query(
        query=user_query,
        session_id=req.session_id,
    )

    return {
        "id": f"chatcmpl-{response.session_id}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": settings.GROQ_REASONING_MODEL,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response.response,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": len(user_query.split()),
            "completion_tokens": len(response.response.split()),
            "total_tokens": len(user_query.split()) + len(response.response.split()),
        },
    }


async def sse_event_generator(query: str, session_id: Optional[str]) -> AsyncGenerator[str, None]:
    """Generates Server-Sent Events (SSE) streaming thought progression and final response."""
    yield f"data: {json.dumps({'type': 'status', 'message': '🛡️ Input Shield: Sanitizing query and checking guardrails...'})}\n\n"
    await asyncio.sleep(0.05)

    # Execute agent pipeline in threadpool to avoid blocking async event loop
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: financial_agent.process_query(query=query, session_id=session_id)
    )

    # Stream route event
    yield f"data: {json.dumps({'type': 'route', 'route': response.route, 'ticker': response.ticker})}\n\n"
    await asyncio.sleep(0.05)

    # Stream tool execution events
    for t in response.tool_calls:
        yield f"data: {json.dumps({'type': 'tool_call', 'tool': t.get('tool'), 'preview': t.get('output_preview', '')[:100]})}\n\n"
        await asyncio.sleep(0.05)

    # Stream final response in chunks for typing effect in UI
    yield f"data: {json.dumps({'type': 'status', 'message': '⚖️ Output Shield: SEC/FINRA compliance verified.'})}\n\n"
    
    words = response.response.split(" ")
    chunk_size = 8
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size]) + " "
        yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
        await asyncio.sleep(0.02)

    # Final complete response event
    yield f"data: {json.dumps({'type': 'done', 'session_id': response.session_id, 'total_latency_ms': response.total_latency_ms})}\n\n"


@app.get("/v1/stream", tags=["Agent"])
async def stream_analysis(
    query: str = Query(..., description="Financial query to stream"),
    session_id: Optional[str] = Query(None, description="Optional session UUID"),
):
    """
    Server-Sent Events (SSE) endpoint for real-time thought & token streaming in Streamlit UI.
    """
    return StreamingResponse(
        sse_event_generator(query, session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/v1/session/{session_id}/history", tags=["Session"])
async def get_session_history(session_id: str):
    """Retrieves conversation history for a given session from Upstash Redis."""
    history = memory_client.get_history(session_id)
    return {"session_id": session_id, "turns": history}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.AGENT_PORT)
