"""
Call Chain & Role:
------------------
Architecture Layer: Phase 5 - Core Agent & Handlers (Defense-in-Depth Output Layer)
Role: Handler 4 — Output Compliance, Secret Leak Prevention & Factual Grounding Shield.
Callers:
    - src/agent/engine.py: Evaluates raw synthesized text from ReActCoreEngine before returning to client.
Dependencies:
    - config/settings.py: settings.GROQ_API_KEY, settings.GROQ_GUARD_MODEL
    - re: Regular expressions for credentials, tokens, and compliance violations.
    - pydantic: AuditResult schema.
"""

import logging
import re
import time
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger("OutputShield")

# Mandatory Institutional Disclaimer appended to all research outputs
MANDATORY_SEC_FINRA_DISCLAIMER = """
---
### ⚖️ Regulatory & Compliance Disclaimer
*This research report is generated autonomously by an AI financial research assistant for analytical and educational purposes only. It does not constitute investment advice, financial endorsement, or a solicitation to buy or sell securities. Past performance is no guarantee of future results. Estimates, intrinsic valuations, and DCF projections are subject to inherent market volatility and model assumptions. Always consult a licensed financial advisor before executing investment decisions.*
""".strip()

# Patterns of prohibited financial promises (SEC Rule 156 / FINRA Rule 2210)
PROHIBITED_FINANCIAL_PATTERNS = [
    (r"\bguaranteed\s+(?:return|profit|gain|yield|interest)\b", "GUARANTEED_RETURNS_PROHIBITION"),
    (r"\brisk[- ]free\s+(?:investment|profit|gain|return|money)\b", "RISK_FREE_PROMISE_PROHIBITION"),
    (r"\bcan'?t\s+lose\s+(?:money|capital|funds)\b", "NO_LOSS_GUARANTEE_PROHIBITION"),
    (r"\b100%\s+(?:safe|guaranteed|certain|profit)\b", "ABSOLUTE_CERTAINTY_PROHIBITION"),
    (r"\binsider\s+(?:tip|information|trade|leak)\b", "INSIDER_TRADING_REFERENCE_PROHIBITION"),
    (r"\bguarantee\s+\d+%\b", "SPECIFIC_RETURN_GUARANTEE_PROHIBITION"),
    (r"\bpump\s+and\s+dump\b", "MARKET_MANIPULATION_REFERENCE"),
]

# Patterns for sensitive internal credentials / secrets
CREDENTIAL_LEAK_PATTERNS = [
    (r"\bgsk_[A-Za-z0-9_]{20,}\b", "GROQ_API_KEY"),
    (r"\bhf_[A-Za-z0-9]{25,}\b", "HUGGINGFACE_TOKEN"),
    (r"\b(?:pk|sk)-lf-[a-z0-9-]{30,}\b", "LANGFUSE_KEY"),
    (r"https://[a-z0-9-]+\.upstash\.io", "UPSTASH_REST_URL"),
    (r"\b[A-Za-z0-9+/]{40,}={0,2}\b", "BASE64_TOKEN"),
]

# Layer 5 Statutory Policy Ingress Boundary Rules (SEC Rule 10b-5 & Exchange Act § 9(a)(2))
STATUTORY_POLICY_RULES = [
    (
        "INSIDER_TRADING_PROHIBITION",
        re.compile(
            r"(?:confidential|non-public|unannounced|board\s+member|internal\s+memo|leak(?:ed)?)\s+.*?(?:earnings|revenue|numbers|merger|acquisition|takeover)"
            r"|(?:insider\s+trading|trade\s+on\s+insider|execute\s+buy\s+orders?\s+before\s+.*market\s+open)",
            re.IGNORECASE,
        ),
        (
            "### ⚖️ Regulatory Policy Violation: SEC Rule 10b-5 (Prohibition of Insider Trading)\n\n"
            "This autonomous financial agent strictly refuses to provide investment advice, order execution recommendations, "
            "or trading strategies based on Material Non-Public Information (MNPI) or confidential corporate disclosures.\n\n"
            "• **Statutory Authority:** Securities Exchange Act of 1934 § 10(b) and SEC Rule 10b-5.\n"
            "• **Violation Identified:** Solicitation of trading recommendations based on non-public, confidential corporate disclosures.\n"
            "• **Action Taken:** Immediate statutory policy block by **Layer 5: Policy & Compliance Shield** (0 Groq LLM tokens consumed).\n\n"
            "Trading securities on the basis of material non-public information carries severe civil liability, "
            "substantial financial penalties, and federal criminal sanctions."
        ),
    ),
    (
        "MARKET_MANIPULATION_PROHIBITION",
        re.compile(
            r"(?:pump\s+and\s+dump|artificially\s+pump|short\s+squeeze|viral\s+social\s+media\s+campaign|penny\s+stock\s+.*pump)",
            re.IGNORECASE,
        ),
        (
            "### ⚖️ Regulatory Policy Violation: Market Manipulation & Securities Exchange Act § 9(a)(2)\n\n"
            "This autonomous financial agent strictly refuses requests to coordinate viral social media campaigns, "
            "artificially inflate trading volumes, or orchestrate short squeezes.\n\n"
            "• **Statutory Authority:** Securities Exchange Act of 1934 § 9(a)(2) and FINRA Rule 2010 (Standards of Commercial Honor).\n"
            "• **Violation Identified:** Coordinated volume distortion and artificial price manipulation campaign.\n"
            "• **Action Taken:** Immediate statutory policy block by **Layer 5: Policy & Compliance Shield** (0 Groq LLM tokens consumed).\n\n"
            "Orchestrating deceptive promotional schemes to manipulate securities prices is illegal and subject to SEC enforcement action."
        ),
    ),
]


class AuditResult(BaseModel):
    """Structured audit validation result from Output Shield."""
    passed: bool = Field(default=True, description="Whether the response passed all safety & compliance gates")
    violations: List[str] = Field(default_factory=list, description="List of detected regulatory or safety violations")
    sanitized_content: str = Field(..., description="Post-processed, compliance-cleared report content")
    grounding_score: float = Field(default=1.0, description="Confidence score for factual grounding (0.0 to 1.0)")
    credentials_scrubbed: bool = Field(default=False, description="Whether internal API credentials were redacted")
    disclaimer_appended: bool = Field(default=False, description="Whether mandatory SEC/FINRA disclaimer was added")
    latency_ms: float = Field(default=0.0, description="Audit execution duration in milliseconds")


class OutputShield:
    """
    Handler 4: Output Compliance & Safety Shield.
    Enforces SEC/FINRA financial compliance, redacts accidental credential leaks,
    and attaches standard regulatory disclosures.
    """

    def __init__(self):
        self.prohibited_patterns = [
            (re.compile(pat, re.IGNORECASE), name) for pat, name in PROHIBITED_FINANCIAL_PATTERNS
        ]
        self.credential_patterns = [
            (re.compile(pat), name) for pat, name in CREDENTIAL_LEAK_PATTERNS
        ]

    def check_ingress_policy(self, text: str) -> Optional[Tuple[str, str]]:
        """
        Layer 5 Ingress Policy Gate:
        Detects statutory SEC Rule 10b-5 and Market Manipulation solicitations in ingress prompts
        and rejects them immediately without consuming LLM tokens.

        Returns:
            Tuple of (violation_name, refusal_text) if violated, else None.
        """
        for violation_name, pattern, refusal_text in STATUTORY_POLICY_RULES:
            if pattern.search(text):
                return violation_name, refusal_text
        return None

    def _scrub_credentials(self, text: str) -> Tuple[str, bool]:
        """Redacts accidental credential leaks from synthesized text."""
        scrubbed = False
        cleaned = text
        for pattern, cred_type in self.credential_patterns:
            if pattern.search(cleaned):
                scrubbed = True
                cleaned = pattern.sub(f"[REDACTED_{cred_type}]", cleaned)
        return cleaned, scrubbed

    def _check_compliance_violations(self, text: str) -> List[str]:
        """Detects regulatory violations (guaranteed returns, risk-free claims)."""
        violations = []
        for pattern, violation_name in self.prohibited_patterns:
            if pattern.search(text):
                violations.append(violation_name)
        return violations

    def _calculate_grounding(self, text: str, tool_context: Optional[str] = None) -> float:
        """
        Heuristic factual grounding confidence score.
        Rewards explicit SEC Form 10-K citations, market quotes, and math tool references.
        """
        score = 0.85  # Baseline confidence
        lower = text.lower()

        # Bonus for citing audited SEC filings or specific Items
        if "10-k" in lower or "item 1a" in lower or "item 1" in lower or "sec" in lower:
            score += 0.05
        # Bonus for market quote / source attribution
        if "quote" in lower or "price" in lower or "yield" in lower or "source:" in lower:
            score += 0.05
        # Penalty if text has suspicious unsourced valuation claims without math
        if "intrinsic value" in lower and "dcf" not in lower and "wacc" not in lower:
            score -= 0.10

        return min(1.0, max(0.5, round(score, 2)))

    def audit(
        self,
        content: str,
        tool_context: Optional[str] = None,
        force_pass_with_caveats: bool = True,
    ) -> AuditResult:
        """
        Audits raw synthesized content against compliance rules, credential leaks,
        and missing legal disclosures.

        Args:
            content: Raw report text from ReActCoreEngine.
            tool_context: Optional context/data collected from tool executions.
            force_pass_with_caveats: If True, redacts prohibited claims rather than rejecting outright.

        Returns:
            AuditResult with sanitized text, violation report, and metadata.
        """
        start_time = time.perf_counter()

        # Step 1: Credential Leak Scrubbing
        sanitized_text, creds_scrubbed = self._scrub_credentials(content)

        # Step 2: SEC / FINRA Compliance Audit
        violations = self._check_compliance_violations(sanitized_text)

        passed = True
        if violations:
            logger.warning(f"OutputShield detected compliance violations: {violations}")
            if force_pass_with_caveats:
                # Replace prohibited guarantees with compliant caveats
                for pattern, _ in self.prohibited_patterns:
                    sanitized_text = pattern.sub(
                        "[COMPLIANCE NOTE: Financial projections carry market risk and are not guaranteed]",
                        sanitized_text,
                    )
            else:
                passed = False

        # Step 3: Factual Grounding Confidence
        grounding = self._calculate_grounding(sanitized_text, tool_context)

        # Step 4: Mandatory SEC/FINRA Legal Disclaimer Attachment
        disclaimer_appended = False
        lower_content = sanitized_text.lower()
        if "regulatory & compliance disclaimer" not in lower_content and "not constitute investment advice" not in lower_content:
            sanitized_text = sanitized_text.rstrip() + "\n\n" + MANDATORY_SEC_FINRA_DISCLAIMER
            disclaimer_appended = True

        latency = (time.perf_counter() - start_time) * 1000.0

        return AuditResult(
            passed=passed,
            violations=violations,
            sanitized_content=sanitized_text,
            grounding_score=grounding,
            credentials_scrubbed=creds_scrubbed,
            disclaimer_appended=disclaimer_appended,
            latency_ms=round(latency, 2),
        )


# Global singleton instance for high-throughput reuse
output_shield = OutputShield()


def audit_output(
    content: str,
    tool_context: Optional[str] = None,
) -> AuditResult:
    """Convenience functional wrapper for OutputShield.audit()."""
    return output_shield.audit(content, tool_context=tool_context)
