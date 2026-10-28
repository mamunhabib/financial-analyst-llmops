"""
Call Chain & Role:
------------------
Architecture Layer: Phase 7 - Interactive Financial Dashboard (UI Badges & Citations)
Role: Renders the 5 standardized Header Badges, Threat Deep-Dive Expanders, and SEC Citations.
Callers:
    - ui/app.py: Renders compliance chips, latency pills, and SEC citations in the analyst feed.
Dependencies:
    - streamlit: UI presentation components.
"""

from typing import Any, Dict, List, Optional

import streamlit as st


def render_guardrail_badges(
    threat_name: str,
    status: str,
    layer_name: str,
    total_latency_ms: float,
    iterations: int,
):
    """
    Renders exactly 5 standardized executive badges:
    1. Threat Scenario
    2. Status (PASSED, BLOCKED, MASKED, REMEDIATED)
    3. Layer (Layer 1 to Layer 5)
    4. Latency
    5. ReAct Steps
    """
    # Status Color Palette
    status_colors = {
        "PASSED": "#059669",      # Green
        "BLOCKED": "#dc2626",     # Red
        "MASKED": "#d97706",      # Yellow / Amber
        "REMEDIATED": "#ea580c",  # Orange
    }
    s_color = status_colors.get(status.upper(), "#64748b")

    # Layer Color Palette
    layer_colors = {
        "Layer 1: Perimeter Shield": "#dc2626",
        "Layer 2: PII Gateway": "#d97706",
        "Layer 3: Core Reasoning Engine": "#2563eb",
        "Layer 4: Code Execution Sandbox": "#7c3aed",
        "Layer 5: Policy & Compliance Shield": "#0891b2",
    }
    l_color = layer_colors.get(layer_name, "#475569")

    latency_rounded = round(total_latency_ms, 1)
    steps_label = f"{iterations} ReAct Step{'s' if iterations != 1 else ''}"
    badge_prefix = "🎯 Evaluation" if status.upper() == "PASSED" else "🎯 Threat"

    badge_html = f"""
    <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 12px;">
        <span style="background-color: #1e293b; color: #f8fafc; padding: 4px 10px; border-radius: 9999px; font-weight: 600; border: 1px solid #334155;">
            {badge_prefix}: {threat_name}
        </span>
        <span style="background-color: {s_color}; color: #ffffff; padding: 4px 10px; border-radius: 9999px; font-weight: 700;">
            🛡️ Status: {status}
        </span>
        <span style="background-color: {l_color}; color: #ffffff; padding: 4px 10px; border-radius: 9999px; font-weight: 600;">
            🏛️ Layer: {layer_name}
        </span>
        <span style="background-color: #1e293b; color: #cbd5e1; padding: 4px 10px; border-radius: 9999px; border: 1px solid #334155;">
            ⚡ Latency: {latency_rounded}ms
        </span>
        <span style="background-color: #1e293b; color: #cbd5e1; padding: 4px 10px; border-radius: 9999px; border: 1px solid #334155;">
            🔄 {steps_label}
        </span>
    </div>
    """
    st.markdown(badge_html, unsafe_allow_html=True)


def render_defense_layer_analysis(
    what_it_is: str,
    what_it_harms: str,
    benefit: str,
    how_defended: str,
    status: str = "BLOCKED",
    expanded: bool = False,
    threat_detected: Optional[str] = None,
    detection_engine: Optional[str] = None,
    detection_method: Optional[str] = None,
    action_taken: Optional[str] = None,
    execution_path: Optional[str] = None,
):
    """
    Renders an expandable/hideable block with deep technical telemetry.
    Differentiates between legitimate inquiries (Evaluation Briefing)
    and security attacks (Threat Analysis & Defense Execution).
    """
    is_benign = status.upper() == "PASSED"
    title = (
        "📋 Evaluation & Verification Briefing (Click to Expand)"
        if is_benign
        else "📋 Threat Analysis & Defense Execution (Click to Expand)"
    )

    with st.expander(title, expanded=expanded):
        if is_benign:
            exec_p = execution_path or how_defended
            st.markdown(
                f"""
• **📖 Evaluation Scope:** {what_it_is}

• **🛡️ Security Assessment:** {what_it_harms}

• **💡 Key Insight:** {benefit}

• **⚡ Execution Path:**  
`{exec_p}`
                """
            )
        else:
            threat_tag = threat_detected or "FLAGGED_SECURITY_VIOLATION"
            det_engine = detection_engine or "Layer Defense Guardrail"
            det_method = detection_method or "Heuristic pattern & token classifier"
            act_taken = action_taken or how_defended
            exec_p = execution_path or how_defended

            st.markdown(
                f"""
• **📖 Threat Definition:** {what_it_is}

• **⚠️ What It Harms:** {what_it_harms}

• **💡 Key Insight:** {benefit}

• **🛡️ Technical Defense Telemetry:**
  - **🎯 Threat Detected:** `{threat_tag}`
  - **🧠 Detection Engine:** {det_engine}
  - **🔬 Detection Method:** {det_method}
  - **⚡ Action Taken:** {act_taken}

• **⚡ Execution Path:**  
`{exec_p}`
                """
            )


def render_sec_citations(tool_calls: List[Dict[str, Any]]):
    """
    Scans executed tools for SEC 10-K RAG retrieval results and renders clickable citation accordions.
    """
    rag_calls = [t for t in tool_calls if "rag" in t.get("tool", "").lower() or "sec" in t.get("tool", "").lower()]

    if not rag_calls:
        return

    with st.expander("📚 Verified SEC Form 10-K Document Citations (FastEmbed ONNX 384d)", expanded=False):
        for idx, call in enumerate(rag_calls, 1):
            tool_name = call.get("tool")
            tool_input = call.get("input", {})
            tool_preview = call.get("output_preview", "")

            st.markdown(f"**Source Document Reference #{idx}** (`{tool_name}`)")
            st.caption(f"Query Parameter: `{tool_input}`")
            st.info(f"Filing Extract:\n\n{tool_preview}")


def render_regulatory_disclaimer():
    """
    Renders standardized FINRA Rule 2210 / SEC Rule 156 statutory disclaimer footer.
    """
    st.markdown(
        """
        <div style="background-color: #1e293b; border-left: 4px solid #f59e0b; padding: 12px 16px; border-radius: 4px; margin-top: 24px; font-size: 11px; color: #94a3b8; line-height: 1.5;">
            <strong>Regulatory & Legal Notice (FINRA Rule 2210 & SEC Rule 156):</strong><br/>
            This autonomous financial report is generated by an artificial intelligence system utilizing algorithmic retrieval 
            and deterministic computational sandboxing. Content is strictly for educational and research informational 
            purposes and does NOT constitute personalized investment, legal, tax, or financial advisory recommendations. Past financial 
            performance is no guarantee of future returns. Verify all financial data directly with official SEC EDGAR disclosures.
        </div>
        """,
        unsafe_allow_html=True,
    )
