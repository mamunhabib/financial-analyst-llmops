"""
Agent Package for Financial & Market Analyst LLMOps.
Provides:
    - FinancialAnalystEngine: End-to-end pipeline linking all 4 handlers.
    - AgentResponse: Unified response schema with audit traces.
    - RedisMemoryClient: Upstash Serverless Redis session checkpointer.
"""

from src.agent.engine import AgentResponse, FinancialAnalystEngine, financial_agent
from src.agent.memory import RedisMemoryClient, memory_client

__all__ = [
    "FinancialAnalystEngine",
    "AgentResponse",
    "financial_agent",
    "RedisMemoryClient",
    "memory_client",
]
