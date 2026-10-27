"""
Call Chain & Role:
------------------
Architecture Layer: Phase 6 - LLMOps Observability & Tracing Tier
Role: Live OpenTelemetry & Langfuse Telemetry Tracer on Port 8092.
Callers:
    - src/agent/engine.py: Instruments end-to-end query processing with traces, spans, and scores.
    - tests/security_robot/run_attacks.py: Emits red-team attack traces, threat scores, and security audit badges.
Dependencies:
    - langfuse: Langfuse Python SDK.
    - config/settings.py: settings.LANGFUSE_PUBLIC_KEY, settings.LANGFUSE_SECRET_KEY, settings.LANGFUSE_HOST.
"""

import logging
from typing import Any, Dict, Optional

from langfuse import Langfuse

from config.settings import settings

logger = logging.getLogger("LangfuseTracer")


class LangfuseTracer:
    """
    Manages telemetry streaming to the live Langfuse Web UI on http://localhost:8092.
    Records waterfall spans for Input Shield, Router, ReAct Core, and Output Shield.
    """

    def __init__(self):
        self.public_key = settings.LANGFUSE_PUBLIC_KEY
        self.secret_key = settings.LANGFUSE_SECRET_KEY
        self.host = settings.LANGFUSE_HOST
        self._client: Optional[Langfuse] = None

        self._init_client()

    def _init_client(self):
        """Initializes Langfuse client with resilient fallback if offline."""
        if self.public_key and self.secret_key and self.host:
            try:
                self._client = Langfuse(
                    public_key=self.public_key,
                    secret_key=self.secret_key,
                    host=self.host,
                )
                logger.info(f"Langfuse tracer connected to {self.host}")
            except Exception as e:
                logger.warning(f"Could not connect to Langfuse ({e}); telemetry will run in no-op mode.")
                self._client = None
        else:
            logger.info("Langfuse credentials not set. Tracing operating in passive local mode.")

    def trace_execution(
        self,
        session_id: str,
        query: str,
        response_data: Dict[str, Any],
        is_attack: bool = False,
        attack_scenario: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Emits a comprehensive waterfall trace to Langfuse.

        Args:
            session_id: Unique conversation session UUID.
            query: Raw user query or adversarial payload.
            response_data: Dictionary containing route, response, tool_calls, input_shield, output_shield.
            is_attack: Whether this trace originated from the adversarial security robot.
            attack_scenario: Optional attack metadata (id, category, name).

        Returns:
            Trace ID if successfully emitted, or None.
        """
        if not self._client:
            return None

        try:
            # Determine if this trace is an adversarial attack or security incident
            is_security_threat = is_attack or (response_data.get("route") == "SECURITY_REJECTED") or not response_data.get("input_shield", {}).get("passed", True)

            if is_security_threat:
                # Unify trace name so the Langfuse "Traces" box remains clean and separated
                trace_name = "🚨 Adversarial Security Attacks"

                category = "PERIMETER"
                test_id = "ATTACK"
                test_name = "Adversarial Probe"
                if attack_scenario:
                    category = attack_scenario.get("category", "UNKNOWN")
                    test_id = attack_scenario.get("id", "ATTACK")
                    test_name = attack_scenario.get("name", "Adversarial Probe")
                elif response_data.get("input_shield", {}).get("threat_type"):
                    category = "PERIMETER"
                    test_id = response_data.get("input_shield", {}).get("threat_type")
                    test_name = "Ingress Threat Interception"

                passed_defense = response_data.get("input_shield", {}).get("passed") is False or \
                                 response_data.get("route") == "SECURITY_REJECTED" or \
                                 "COMPLIANCE NOTE" in response_data.get("response", "") or \
                                 "[REDACTED_" in response_data.get("response", "") or \
                                 response_data.get("route") == "SANDBOX_INTERCEPTED"

                status_tag = "status:DEFENDED" if passed_defense else "status:BREACHED"
                tags = [
                    "🚨 ADVERSARIAL_ATTACK",
                    f"layer:{category}",
                    f"id:{test_id}",
                    status_tag,
                ]
            else:
                trace_name = "FinancialAnalystPipeline"
                tags = [
                    "production-query",
                    f"route:{response_data.get('route', 'UNKNOWN')}",
                    f"ticker:{response_data.get('ticker') or 'NONE'}",
                ]

            # 1. Root Trace Creation
            trace = self._client.trace(
                name=trace_name,
                session_id=session_id,
                input={"query": query},
                output={"response": response_data.get("response", "")},
                tags=tags,
                metadata={
                    "is_attack": is_security_threat,
                    "attack_id": test_id if is_security_threat else None,
                    "attack_name": test_name if is_security_threat else None,
                    "target_layer": category if is_security_threat else None,
                    "route": response_data.get("route"),
                    "ticker": response_data.get("ticker"),
                    "total_latency_ms": response_data.get("total_latency_ms"),
                },
            )

            # If security threat, emit a prominent event with level="ERROR" to turn the trace RED in Langfuse!
            if is_security_threat:
                trace.event(
                    name=f"🚨 Threat: {test_id} ({category})",
                    level="ERROR",
                    status_message=f"Adversarial security attack intercepted: {test_name}",
                    input={"payload": query},
                    output={"verdict": "DEFENDED" if passed_defense else "BREACHED"},
                    metadata={"category": category, "test_id": test_id, "threat_name": test_name},
                )

            # 2. Span 1: Input Shield
            input_shield_meta = response_data.get("input_shield", {})
            span_input = trace.span(
                name="Handler 1: Input Shield (Prompt Guard 86M & PII)",
                input={"raw_prompt": query},
                output=input_shield_meta,
                level="ERROR" if (is_security_threat and not input_shield_meta.get("passed", True)) else "DEFAULT",
                status_message=f"Threat: {input_shield_meta.get('threat_type')}" if not input_shield_meta.get("passed", True) else "Passed",
                metadata={
                    "threat_type": input_shield_meta.get("threat_type"),
                    "risk_score": input_shield_meta.get("risk_score"),
                    "pii_detected": input_shield_meta.get("pii_detected"),
                },
            )
            span_input.end()

            # If rejected by Input Shield, close trace early with security score
            if not input_shield_meta.get("passed", True) or response_data.get("route") == "SECURITY_REJECTED":
                trace.score(
                    name="security_defense_success",
                    value=1.0 if is_security_threat else 0.0,
                    comment="Attack neutralized at perimeter by Input Shield; 0 Groq tokens consumed.",
                )
                trace.score(
                    name="security_attacks_defended",
                    value=1.0 if passed_defense else 0.0,
                    comment="Dedicated defense metric for security scorecard widget.",
                )
                self._client.flush()
                return trace.id

            # 3. Span 2: Prompt Router
            span_router = trace.span(
                name="Handler 2: Prompt Router (Sub-150ms Classifier)",
                input={"sanitized_query": response_data.get("sanitized_query", query)},
                output={
                    "route": response_data.get("route"),
                    "ticker": response_data.get("ticker"),
                },
            )
            span_router.end()

            # Add dynamic path tags for every tool executed
            tools = response_data.get("tool_calls", [])
            for t in tools:
                tool_name = str(t.get("tool", "")).lower()
                if "sandbox" in tool_name or "math" in tool_name:
                    tags.append("path:sandbox-math")
                elif "10k" in tool_name or "sec" in tool_name:
                    tags.append("path:sec-10k-rag")
                elif "quote" in tool_name:
                    tags.append("path:live-quote")
                elif "yield" in tool_name:
                    tags.append("path:treasury-yield")
                elif "news" in tool_name:
                    tags.append("path:market-news")

            # 4. Span 3: ReAct Core Reasoning & Tool Loops
            span_react = trace.span(
                name="Handler 3: ReAct Core Engine (Qwen 27B on Groq LPU)",
                input={"tools_count": len(tools)},
                output={
                    "iterations": response_data.get("iterations", 1),
                    "tools_executed": [t.get("tool") for t in tools],
                },
            )

            # Emit a dedicated, clickable child span for EACH tool in the path
            for t in tools:
                tool_name = t.get("tool", "tool")
                preview = t.get("output_preview", "")
                args = t.get("args", {})
                span_tool = span_react.span(
                    name=f"Tool Execution: {tool_name}",
                    input={"tool": tool_name, "parameters": args},
                    output={"result_preview": preview},
                    metadata={"tool_name": tool_name},
                )
                span_tool.end()

            span_react.end()

            # 5. Span 4: Output Shield
            output_shield_meta = response_data.get("output_shield", {})
            span_output = trace.span(
                name="Handler 4: Output Shield (SEC/FINRA Compliance & Disclaimer)",
                input={"raw_draft_preview": response_data.get("response", "")[:200]},
                output=output_shield_meta,
                metadata={
                    "violations": output_shield_meta.get("violations", []),
                    "grounding_score": output_shield_meta.get("grounding_score", 1.0),
                },
            )
            span_output.end()

            # Record Scores in Langfuse Dashboard
            grounding = output_shield_meta.get("grounding_score", 1.0)
            trace.score(
                name="factual_grounding",
                value=float(grounding),
                comment="Factual grounding confidence based on SEC 10-K and market feeds.",
            )

            if is_security_threat:
                trace.score(
                    name="security_defense_success",
                    value=1.0 if status_tag == "status:DEFENDED" else 0.0,
                    comment="Adversarial attack evaluation verdict.",
                )
                trace.score(
                    name="security_attacks_defended",
                    value=1.0 if status_tag == "status:DEFENDED" else 0.0,
                    comment="Dedicated security audit defense metric for dashboard scorecard.",
                )

            # Ensure traces are flushed to the local server
            self._client.flush()
            return trace.id

        except Exception as e:
            logger.error(f"Error emitting Langfuse trace: {e}")
            return None


# Global singleton tracer
langfuse_tracer = LangfuseTracer()
