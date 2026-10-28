"""
=============================================================================
FILE ROLE & CALL CHAIN CONTEXT:
- Role: Handler 1 — Input Security Shield & PII Redaction Guardrail
- Where this file is used / Who calls it:
    1. Called by: src/agent/engine.py
       (First stage executed when a user submits a query to the agent).
    2. Invoked during Ingress: serving/app.py
       (Validates and scrubs incoming payload before routing to prompt_router or react_core).
    3. Tested by: tests/security_robot/
       (The Automated Security Robot fires 15+ adversarial prompt attacks against
        this shield during CI/CD to audit bypass rates and defense integrity).
    4. Traced in: observability/langfuse_tracker.py
       (Records whether the prompt passed or was blocked, along with threat scores).
=============================================================================
"""

import logging
import re
import time
from typing import Dict, List, Optional, Tuple

import httpx
from pydantic import BaseModel, Field

from config.settings import settings

logger = logging.getLogger(__name__)

# PII Regex Patterns for automatic data scrubbing
PII_PATTERNS: Dict[str, re.Pattern] = {
    "CREDIT_CARD": re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b"),
    "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "EMAIL": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "PHONE": re.compile(r"\b(?:\+?1[-.]?)?\(?[2-9]\d{2}\)?[-.]?\d{3}[-.]?\d{4}\b"),
}

# Prompt Injection & Jailbreak Attack Patterns
INJECTION_SIGNATURES: List[Tuple[str, re.Pattern, float]] = [
    ("IGNORE_INSTRUCTIONS", re.compile(r"(?:ignore|disregard|forget|stop\s+following)\s+(?:all\s+)?(?:previous|prior|above|system)\s+(?:instructions|prompts|rules|commands)", re.IGNORECASE), 0.95),
    ("SYSTEM_PROMPT_LEAK", re.compile(r"(?:reveal|print|show|output|leak|display)\s+(?:your\s+)?(?:system\s+prompt|initial\s+prompt|hidden\s+instructions|system\s+instructions)", re.IGNORECASE), 0.90),
    ("ROLEPLAY_JAILBREAK", re.compile(r"(?:you\s+are\s+now|pretend\s+to\s+be|act\s+as|roleplay\s+(?:as|a\s+fictional\s+world)|stop\s+being\s+a\s+[a-z\s]+|in\s+a\s+fictional\s+world)\s*.*?(?:DAN|developer\s+mode|unrestricted|an\s+ai\s+without\s+rules|unfiltered|rogue|repealed|insider)", re.IGNORECASE), 0.95),
    ("GUARDRAIL_OVERRIDE", re.compile(r"(?:disable|bypass|override|turn\s+off|repeal(?:ed)?)\s+(?:all\s+)?(?:security|guardrails?|filters?|safety\s+checks?|rules?)", re.IGNORECASE), 0.90),
    ("DELIMITER_HIJACK", re.compile(r"(?:<\|im_start\|>|<\|im_end\|>|###\s*system|###\s*instruction|\[SYSTEM_PROMPT\]|===\s*(?:END|START|SYSTEM|CONTEXT)[^=\n]*===|---\s*(?:END|START|SYSTEM)[^-\n]*---)", re.IGNORECASE), 0.90),
    ("BASE64_OBFUSCATION", re.compile(r"(?:decode|execute|run)\s+(?:this\s+)?base64", re.IGNORECASE), 0.70),
    ("SIMULATED_ADMIN", re.compile(r"(?:sudo|chmod|rm\s+-rf|format\s+drive|cat\s+/etc/passwd|api[_-]key\s*leak|root\s+password)", re.IGNORECASE), 0.85),
    ("CREDENTIAL_PROBE", re.compile(r"(?:api[_-]?key|secret|password|token|redis_rest_url|groq_api_key|backend_url).*?(?:echo|print|show|reveal|what\s+is|tell\s+me)|(?:what\s+is\s+your\s+backend\s+[a-z0-9_-]+)", re.IGNORECASE), 0.90),
]


class ShieldResult(BaseModel):
    """Structured response from the Input Shield guardrail."""
    passed: bool = Field(description="Whether the prompt passed all safety checks")
    sanitized_text: str = Field(description="Text with PII redacted and cleaned")
    threat_type: Optional[str] = Field(default=None, description="Type of threat detected if blocked")
    risk_score: float = Field(default=0.0, description="Risk score between 0.0 (safe) and 1.0 (dangerous)")
    flagged_patterns: List[str] = Field(default_factory=list, description="List of attack patterns identified")
    pii_detected: bool = Field(default=False, description="Whether personal identifying info was scrubbed")
    pii_types: List[str] = Field(default_factory=list, description="Categories of PII redacted")
    rejection_reason: Optional[str] = Field(default=None, description="User-facing rejection explanation")
    latency_ms: float = Field(default=0.0, description="Shield inspection duration in milliseconds")


class InputShield:
    """
    Handler 1: Input Security Shield Guardrail.
    Inspects user prompt before LLM invocation, scrubs PII, and blocks prompt injections.
    """

    def __init__(self, risk_threshold: float = 0.60):
        self.risk_threshold = risk_threshold
        self.hf_token = settings.HF_TOKEN
        self.shield_model = settings.HF_SHIELD_MODEL

    def scrub_pii(self, text: str) -> Tuple[str, List[str]]:
        """
        Detects and masks sensitive personal data (Credit cards, SSNs, emails, phone numbers).
        """
        scrubbed = text
        detected_types = []

        for pii_name, pattern in PII_PATTERNS.items():
            if pattern.search(scrubbed):
                detected_types.append(pii_name)
                scrubbed = pattern.sub(f"[REDACTED_{pii_name}]", scrubbed)

        return scrubbed, detected_types

    def evaluate_injection_patterns(self, text: str) -> Tuple[float, List[str], Optional[str]]:
        """
        Inspects text against known prompt injection and jailbreak signatures.
        """
        max_score = 0.0
        flagged = []
        primary_threat = None

        for name, pattern, score in INJECTION_SIGNATURES:
            if pattern.search(text):
                flagged.append(name)
                if score > max_score:
                    max_score = score
                    primary_threat = name

        return max_score, flagged, primary_threat

    def query_prompt_guard_model(self, text: str) -> Optional[float]:
        """
        Queries Meta's Prompt-Guard-86M via Hugging Face Inference API if configured.
        Falls back seamlessly if remote API is unavailable.
        """
        if not self.hf_token:
            return None

        # Short-circuit check: HF model evaluation
        api_url = f"https://api-inference.huggingface.co/models/{self.shield_model}"
        headers = {"Authorization": f"Bearer {self.hf_token}"}
        payload = {"inputs": text}

        try:
            with httpx.Client(timeout=2.0) as client:
                resp = client.post(api_url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    # Prompt Guard returns label probabilities: 'BENIGN', 'INJECTION', 'JAILBREAK'
                    if isinstance(data, list) and len(data) > 0:
                        predictions = data[0] if isinstance(data[0], list) else data
                        for item in predictions:
                            label = item.get("label", "").upper()
                            score = float(item.get("score", 0.0))
                            if label in ("INJECTION", "JAILBREAK"):
                                return score
        except Exception as e:
            logger.debug(f"Prompt Guard remote API skipped ({e}); using heuristic shield.")

        return None

    def inspect(self, prompt: str) -> ShieldResult:
        """
        Full pre-flight inspection of a user prompt.

        Args:
            prompt: Raw user input string.

        Returns:
            ShieldResult with passed status, sanitized text, and risk assessment.
        """
        start_time = time.perf_counter()
        clean_input = prompt.strip()

        # Step 1: Reject empty inputs
        if not clean_input:
            latency = (time.perf_counter() - start_time) * 1000.0
            return ShieldResult(
                passed=False,
                sanitized_text="",
                threat_type="EMPTY_INPUT",
                risk_score=1.0,
                rejection_reason="Query cannot be empty.",
                latency_ms=round(latency, 2),
            )

        # Step 2: Scrub sensitive PII
        sanitized_text, detected_pii = self.scrub_pii(clean_input)

        # Step 3: Fast heuristic injection signature scan
        risk_score, flagged_patterns, threat_name = self.evaluate_injection_patterns(sanitized_text)

        # Step 4: Optional Prompt Guard 86M verification if threshold borderline
        if 0.3 <= risk_score < self.risk_threshold:
            model_score = self.query_prompt_guard_model(sanitized_text)
            if model_score is not None:
                risk_score = max(risk_score, model_score)

        latency = (time.perf_counter() - start_time) * 1000.0

        # Step 5: Enforce security verdict
        is_blocked = risk_score >= self.risk_threshold
        threat_type = threat_name if is_blocked else None
        reason = None

        if is_blocked:
            reason = (
                f"Security Guardrail Block: Prompt rejected due to detected {threat_type} "
                f"(Risk Score: {risk_score:.2f})."
            )
            logger.warning(f"Blocked malicious prompt: threat={threat_type}, score={risk_score}")

        return ShieldResult(
            passed=not is_blocked,
            sanitized_text=sanitized_text,
            threat_type=threat_type,
            risk_score=round(risk_score, 2),
            flagged_patterns=flagged_patterns,
            pii_detected=len(detected_pii) > 0,
            pii_types=detected_pii,
            rejection_reason=reason,
            latency_ms=round(latency, 2),
        )

    # Alias for API uniformity
    validate = inspect


# Singleton instance for direct import
input_shield = InputShield()


def validate_input(prompt: str) -> ShieldResult:
    """Convenience helper to inspect a user prompt."""
    return input_shield.inspect(prompt)
