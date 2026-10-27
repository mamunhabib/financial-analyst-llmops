"""
Call Chain & Role:
------------------
Architecture Layer: Phase 5 - Core Agent Controller
Role: Central Financial Analyst Agent Pipeline Orchestrator.
Callers:
    - serving/app.py: FastAPI ingress invokes engine.process_query() for chat completions and SSE streaming.
Dependencies:
    - src.handlers.input_shield: Handler 1 (Input sanitization & prompt injection guard).
    - src.handlers.prompt_router: Handler 2 (Sub-150ms intent router).
    - src.handlers.react_core: Handler 3 (Autonomous ReAct multi-step reasoning).
    - src.handlers.output_shield: Handler 4 (Output compliance & legal disclaimer auditor).
    - src.agent.memory: Upstash Redis session checkpointing.
"""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from observability.langfuse_tracer import langfuse_tracer
from src.agent.memory import RedisMemoryClient, memory_client
from src.handlers.input_shield import InputShield, ShieldResult, input_shield
from src.handlers.output_shield import AuditResult, OutputShield, output_shield
from src.handlers.prompt_router import PromptRouter, RouteDecision, prompt_router
from src.handlers.react_core import ReActCoreEngine, ReActResult, react_core

logger = logging.getLogger("FinancialAnalystEngine")


class AgentResponse(BaseModel):
    """Unified response schema for the Financial Analyst Agent."""
    session_id: str = Field(..., description="Unique conversation session UUID")
    query: str = Field(..., description="Original user prompt")
    sanitized_query: str = Field(..., description="Sanitized query after PII scrubbing")
    response: str = Field(..., description="Final compliance-audited financial report")
    route: str = Field(..., description="Classified intent route")
    ticker: Optional[str] = Field(default=None, description="Analyzed equity ticker")
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list, description="Audit trace of tools executed")
    iterations: int = Field(default=1, description="Number of ReAct reasoning cycles")
    input_shield: Dict[str, Any] = Field(default_factory=dict, description="Input Shield audit metadata")
    output_shield: Dict[str, Any] = Field(default_factory=dict, description="Output Shield compliance metadata")
    total_latency_ms: float = Field(default=0.0, description="End-to-end pipeline latency in ms")


class FinancialAnalystEngine:
    """
    Core Controller: Ties together the 4 service handlers with serverless Redis session state:
    1. Input Shield (Prompt injection / jailbreak / PII detection)
    2. Prompt Router (Sub-150ms intent classification & tool recommendation)
    3. ReAct Core Engine (Autonomous tool execution on Groq LPU)
    4. Output Shield (SEC/FINRA compliance & credential leak firewall)
    5. Redis Checkpoint (Upstash session persistence)
    """

    def __init__(
        self,
        shield: Optional[InputShield] = None,
        router: Optional[PromptRouter] = None,
        react: Optional[ReActCoreEngine] = None,
        auditor: Optional[OutputShield] = None,
        memory: Optional[RedisMemoryClient] = None,
    ):
        self.input_shield = shield or input_shield
        self.router = router or prompt_router
        self.react_engine = react or react_core
        self.output_shield = auditor or output_shield
        self.memory = memory or memory_client

    def process_query(
        self,
        query: str,
        session_id: Optional[str] = None,
    ) -> AgentResponse:
        """
        Executes the full defense-in-depth financial analyst pipeline.

        Args:
            query: Raw user query from client or API.
            session_id: Optional conversation session UUID. If omitted, generates new UUID.

        Returns:
            AgentResponse containing the synthesized report and complete audit trail.
        """
        start_time = time.perf_counter()
        session_id = session_id or str(uuid.uuid4())

        logger.info(f"Processing query for session {session_id[:8]}...: {query[:60]}")

        # ----------------------------------------------------------------------
        # Step 1: Input Shield (PII Scrubbing & Prompt Injection Defense)
        # ----------------------------------------------------------------------
        shield_result: ShieldResult = self.input_shield.inspect(query)
        input_meta = {
            "passed": shield_result.passed,
            "threat_type": shield_result.threat_type,
            "risk_score": shield_result.risk_score,
            "pii_detected": shield_result.pii_detected,
            "pii_types": shield_result.pii_types,
            "latency_ms": shield_result.latency_ms,
        }

        # If malicious prompt injection or jailbreak detected, halt immediately
        if not shield_result.passed:
            latency = (time.perf_counter() - start_time) * 1000.0
            rejection_text = (
                f"### 🛑 Security Guardrail Block\n\n"
                f"Your request was rejected by the **Input Security Shield**.\n\n"
                f"• **Threat Detected:** `{shield_result.threat_type}`\n"
                f"• **Risk Confidence Score:** `{shield_result.risk_score}`\n\n"
                f"Our security policy strictly forbids adversarial jailbreaks, system prompt overrides, "
                f"or non-financial instruction injection."
            )

            # Record security incident in Redis audit trail
            self.memory.save_turn(
                session_id=session_id,
                user_query=query,
                agent_response=rejection_text,
                metadata={"security_violation": True, "input_shield": input_meta},
            )

            # Stream security interception trace to Langfuse (:8092)
            langfuse_tracer.trace_execution(
                session_id=session_id,
                query=query,
                response_data={
                    "route": "SECURITY_REJECTED",
                    "response": rejection_text,
                    "input_shield": input_meta,
                    "total_latency_ms": round(latency, 2),
                },
            )

            return AgentResponse(
                session_id=session_id,
                query=query,
                sanitized_query=shield_result.sanitized_text,
                response=rejection_text,
                route="SECURITY_REJECTED",
                ticker=None,
                tool_calls=[],
                iterations=0,
                input_shield=input_meta,
                output_shield={"passed": False, "violations": ["INPUT_SECURITY_BLOCK"]},
                total_latency_ms=round(latency, 2),
            )

        sanitized_query = shield_result.sanitized_text

        # ----------------------------------------------------------------------
        # Step 2: Prompt Router (Sub-150ms Intent Classifier)
        # ----------------------------------------------------------------------
        route_decision: RouteDecision = self.router.route(sanitized_query)
        logger.info(
            f"Routing decision: {route_decision.route.value} (Ticker: {route_decision.ticker}) "
            f"in {route_decision.latency_ms}ms"
        )

        # ----------------------------------------------------------------------
        # Step 3: ReAct Core Engine (Autonomous Tool Loops on Groq LPU)
        # ----------------------------------------------------------------------
        react_result: ReActResult = self.react_engine.analyze(
            query=sanitized_query,
            route_decision=route_decision,
        )

        # ----------------------------------------------------------------------
        # Step 4: Output Shield (Compliance, Credential Leaks, Disclaimer)
        # ----------------------------------------------------------------------
        audit_result: AuditResult = self.output_shield.audit(
            content=react_result.content,
            tool_context=str(react_result.tool_calls_executed),
        )
        output_meta = {
            "passed": audit_result.passed,
            "violations": audit_result.violations,
            "grounding_score": audit_result.grounding_score,
            "credentials_scrubbed": audit_result.credentials_scrubbed,
            "disclaimer_appended": audit_result.disclaimer_appended,
            "latency_ms": audit_result.latency_ms,
        }

        total_latency = (time.perf_counter() - start_time) * 1000.0

        # ----------------------------------------------------------------------
        # Step 5: Upstash Redis Session Checkpointing
        # ----------------------------------------------------------------------
        self.memory.save_turn(
            session_id=session_id,
            user_query=query,
            agent_response=audit_result.sanitized_content,
            metadata={
                "route": route_decision.route.value,
                "ticker": react_result.ticker,
                "tool_calls": react_result.tool_calls_executed,
                "input_shield": input_meta,
                "output_shield": output_meta,
                "latency_ms": round(total_latency, 2),
            },
        )

        # Stream complete execution trace to Langfuse (:8092)
        langfuse_tracer.trace_execution(
            session_id=session_id,
            query=query,
            response_data={
                "route": route_decision.route.value,
                "ticker": react_result.ticker,
                "response": audit_result.sanitized_content,
                "sanitized_query": sanitized_query,
                "tool_calls": react_result.tool_calls_executed,
                "iterations": react_result.iterations,
                "input_shield": input_meta,
                "output_shield": output_meta,
                "total_latency_ms": round(total_latency, 2),
            },
        )

        return AgentResponse(
            session_id=session_id,
            query=query,
            sanitized_query=sanitized_query,
            response=audit_result.sanitized_content,
            route=route_decision.route.value,
            ticker=react_result.ticker,
            tool_calls=react_result.tool_calls_executed,
            iterations=react_result.iterations,
            input_shield=input_meta,
            output_shield=output_meta,
            total_latency_ms=round(total_latency, 2),
        )


# Global singleton agent engine
financial_agent = FinancialAnalystEngine()
