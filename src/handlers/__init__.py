"""
Service Handlers Package for Financial & Market Analyst Agent.
Hosts the 4 core pipeline handlers:
1. Input Shield (Security & PII Guardrail)
2. Prompt Router (Sub-150ms Intent Classifier)
3. ReAct Core Engine (Llama-3.3-70B Reasoning Loop)
4. Output Shield (Llama Guard 3 8B Compliance Auditor)
"""

from src.handlers.input_shield import InputShield, ShieldResult, input_shield, validate_input
from src.handlers.prompt_router import (
    PromptRouter,
    RouteCategory,
    RouteDecision,
    prompt_router,
    route_prompt,
)
from src.handlers.react_core import (
    ReActCoreEngine,
    ReActResult,
    react_core,
    run_analyst_agent,
)

from src.handlers.output_shield import (
    AuditResult,
    OutputShield,
    audit_output,
    output_shield,
)

__all__ = [
    "InputShield",
    "ShieldResult",
    "input_shield",
    "validate_input",
    "PromptRouter",
    "RouteCategory",
    "RouteDecision",
    "prompt_router",
    "route_prompt",
    "ReActCoreEngine",
    "ReActResult",
    "react_core",
    "run_analyst_agent",
    "OutputShield",
    "AuditResult",
    "output_shield",
    "audit_output",
]
