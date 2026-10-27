"""
Observability Package for Financial & Market Analyst LLMOps.
Provides:
    - langfuse_tracer: Telemetry tracer streaming waterfall traces to Port 8092.
"""

from observability.langfuse_tracer import LangfuseTracer, langfuse_tracer

__all__ = [
    "LangfuseTracer",
    "langfuse_tracer",
]
