"""
=============================================================================
FILE ROLE & CALL CHAIN CONTEXT:
- Role: Deterministic Financial Math Execution ReAct Tool
- Where this file is used / Who calls it:
    1. Registered in: src/tools/__init__.py
       (Bundled into ALL_FINANCIAL_TOOLS list for the ReAct Agent).
    2. Bound to LLM in: src/handlers/react_core.py
       (Groq Llama-3.3-70B invokes this tool when computing valuations,
        growth rates, or multiples without hallucinating).
    3. Invokes: src/sandbox/runner.py -> src/sandbox/formulas.py
       (Executes in-process with AST security verification in < 1ms).
    4. Traced in: observability/langfuse_tracker.py
       (Captures code executed, output values, and latency).
=============================================================================
"""

import json
import logging

from langchain_core.tools import tool

from src.sandbox.runner import SandboxRunner

logger = logging.getLogger(__name__)


def execute_financial_math(code: str) -> str:
    """
    Executes Python financial math calculations inside a restricted AST sandbox.
    
    Pre-injected safe formulas:
    - dcf(cash_flows, discount_rate, terminal_growth_rate)
    - wacc(equity_val, debt_val, cost_of_equity, cost_of_debt, tax_rate)
    - cagr(beginning_val, ending_val, periods)
    - pe_ratio(stock_price, earnings_per_share)
    - free_cash_flow(operating_cash_flow, capex)
    - enterprise_value(market_cap, total_debt, cash)
    - margin(metric_val, revenue)
    - standard 'math' module (sqrt, log, exp, etc.)

    Args:
        code: Python snippet that assigns final answer to 'result' or computes an expression.

    Returns:
        Formatted string containing calculation result, stdout, and execution latency.
    """
    runner = SandboxRunner(timeout_seconds=5.0)
    exec_res = runner.execute(code)

    if not exec_res["success"]:
        return (
            f"❌ Math Calculation Failed:\n"
            f"Error: {exec_res['error']}\n"
            f"Time: {exec_res['execution_time_ms']}ms"
        )

    res_val = exec_res["result"]
    stdout = exec_res.get("stdout", "").strip()

    output_lines = [f"✅ Calculation Successful (Execution Time: {exec_res['execution_time_ms']}ms)"]
    if stdout:
        output_lines.append(f"Output Print:\n{stdout}")
    if res_val is not None:
        if isinstance(res_val, dict):
            output_lines.append(f"Result Breakdown:\n{json.dumps(res_val, indent=2)}")
        else:
            output_lines.append(f"Result: {res_val}")

    return "\n".join(output_lines)


@tool("run_financial_math")
def run_financial_math(code: str) -> str:
    """
    Execute deterministic financial calculations in a secure Python sandbox.
    Use this tool whenever you need exact numerical accuracy for financial valuation,
    such as Discounted Cash Flow (DCF), Weighted Average Cost of Capital (WACC),
    Compound Annual Growth Rate (CAGR), P/E valuation multiples, or Free Cash Flow.
    
    Assign your final calculated answer to a variable named `result`.
    
    Examples:
    - DCF:
      result = dcf(cash_flows=[100, 115, 130, 145, 160], discount_rate=0.085, terminal_growth_rate=0.025)
    - WACC:
      result = wacc(equity_val=3000, debt_val=100, cost_of_equity=0.09, cost_of_debt=0.045, tax_rate=0.21)
    - CAGR:
      result = cagr(beginning_val=274.5, ending_val=383.3, periods=3)
    """
    return execute_financial_math(code=code)
