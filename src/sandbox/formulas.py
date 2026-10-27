"""
=============================================================================
FILE ROLE & CALL CHAIN CONTEXT:
- Role: Deterministic Financial Mathematical Formulas Engine
- Where this file is used / Who calls it:
    1. Called by: src/sandbox/runner.py
       (The AST-restricted sandbox imports these formulas and injects them into
        the safe execution environment so the LLM Agent cannot hallucinate math).
    2. Used indirectly by: src/tools/sandbox_tool.py
       (The ReAct Agent tool that invokes the runner to perform financial math).
    3. Triggered by: src/handlers/react_core.py -> serving/app.py
       (When user queries require DCF, WACC, CAGR, P/E multiples, or Free Cash Flow).
    4. Traced by: observability/langfuse_tracker.py
       (Audits math calculations and execution time for compliance).
=============================================================================
"""

from typing import Any, Dict, List, Union
import math
import logging

logger = logging.getLogger(__name__)


def dcf(
    cash_flows: List[float],
    discount_rate: float,
    terminal_growth_rate: float,
) -> Dict[str, Any]:
    """
    Calculate Discounted Cash Flow (DCF) Enterprise Value using Gordon Growth Model.

    Formula:
        PV(FCF) = sum( FCF_t / (1 + r)^t )
        TV = ( FCF_n * (1 + g) ) / (r - g)
        PV(TV) = TV / (1 + r)^n
        Enterprise Value = PV(FCF) + PV(TV)

    Args:
        cash_flows: List of projected annual Free Cash Flows (in millions/billions).
        discount_rate: Weighted Average Cost of Capital (e.g. 0.085 for 8.5%).
        terminal_growth_rate: Perpetual terminal growth rate (e.g. 0.025 for 2.5%).

    Returns:
        Dict containing present value breakdown and total enterprise value.
    """
    if not cash_flows:
        raise ValueError("Cash flows list cannot be empty.")
    if discount_rate <= terminal_growth_rate:
        raise ValueError(
            f"Discount rate ({discount_rate:.2%}) must be strictly greater than "
            f"terminal growth rate ({terminal_growth_rate:.2%}) for Gordon Growth Model."
        )

    pv_cash_flows = []
    for t, fcf in enumerate(cash_flows, start=1):
        discount_factor = (1.0 + discount_rate) ** t
        pv = fcf / discount_factor
        pv_cash_flows.append(round(pv, 2))

    sum_pv_fcf = sum(pv_cash_flows)
    n = len(cash_flows)
    final_fcf = cash_flows[-1]

    # Terminal Value at year n
    terminal_value = (final_fcf * (1.0 + terminal_growth_rate)) / (discount_rate - terminal_growth_rate)
    pv_terminal_value = terminal_value / ((1.0 + discount_rate) ** n)

    enterprise_value = sum_pv_fcf + pv_terminal_value

    return {
        "pv_cash_flows": pv_cash_flows,
        "sum_pv_cash_flows": round(sum_pv_fcf, 2),
        "terminal_value": round(terminal_value, 2),
        "pv_terminal_value": round(pv_terminal_value, 2),
        "enterprise_value": round(enterprise_value, 2),
        "discount_rate": discount_rate,
        "terminal_growth_rate": terminal_growth_rate,
    }


def wacc(
    equity_val: float,
    debt_val: float,
    cost_of_equity: float,
    cost_of_debt: float,
    tax_rate: float,
) -> Dict[str, Any]:
    """
    Calculate Weighted Average Cost of Capital (WACC).

    Formula:
        WACC = (E / V * Re) + (D / V * Rd * (1 - Tc))
        where V = E + D

    Args:
        equity_val: Market value of equity (market capitalization).
        debt_val: Book value of total debt.
        cost_of_equity: Required rate of return on equity (e.g., via CAPM: Rf + Beta * ERP).
        cost_of_debt: Pre-tax yield / interest rate on debt.
        tax_rate: Corporate tax rate (e.g. 0.21 for 21%).

    Returns:
        Dict with equity/debt weights and final WACC percentage.
    """
    total_val = equity_val + debt_val
    if total_val <= 0:
        raise ValueError("Total firm value (Equity + Debt) must be positive.")

    w_e = equity_val / total_val
    w_d = debt_val / total_val
    after_tax_debt_cost = cost_of_debt * (1.0 - tax_rate)

    calculated_wacc = (w_e * cost_of_equity) + (w_d * after_tax_debt_cost)

    return {
        "equity_weight": round(w_e, 4),
        "debt_weight": round(w_d, 4),
        "cost_of_equity": cost_of_equity,
        "after_tax_cost_of_debt": round(after_tax_debt_cost, 4),
        "wacc": round(calculated_wacc, 4),
        "wacc_percent": f"{calculated_wacc * 100:.2f}%",
    }


def cagr(
    beginning_val: float,
    ending_val: float,
    periods: float,
) -> float:
    """
    Calculate Compound Annual Growth Rate (CAGR).

    Formula:
        CAGR = (ending_val / beginning_val) ** (1 / periods) - 1

    Args:
        beginning_val: Starting metric (e.g., FY21 Revenue).
        ending_val: Ending metric (e.g., FY24 Revenue).
        periods: Number of elapsed years or intervals.

    Returns:
        CAGR as float decimal (e.g. 0.145 for 14.5%).
    """
    if beginning_val <= 0:
        raise ValueError("Beginning value must be strictly positive to calculate CAGR.")
    if periods <= 0:
        raise ValueError("Number of periods must be positive.")

    rate = (ending_val / beginning_val) ** (1.0 / periods) - 1.0
    return round(rate, 4)


def pe_ratio(stock_price: float, earnings_per_share: float) -> float:
    """
    Calculate Price-to-Earnings (P/E) Multiple.

    Formula:
        P/E = stock_price / earnings_per_share
    """
    if earnings_per_share == 0:
        raise ZeroDivisionError("Earnings per share (EPS) cannot be zero for P/E.")
    return round(stock_price / earnings_per_share, 2)


def free_cash_flow(operating_cash_flow: float, capex: float) -> float:
    """
    Calculate Free Cash Flow to Firm (FCF).

    Formula:
        FCF = Operating Cash Flow - Capital Expenditures
    """
    return round(operating_cash_flow - capex, 2)


def enterprise_value(
    market_cap: float,
    total_debt: float,
    cash_and_equivalents: float,
) -> float:
    """
    Calculate Enterprise Value (EV).

    Formula:
        EV = Market Cap + Total Debt - Cash & Short-Term Investments
    """
    return round(market_cap + total_debt - cash_and_equivalents, 2)


def margin(metric_val: float, revenue: float) -> float:
    """
    Calculate financial margin percentage (Gross Margin, Operating Margin, Net Margin).

    Formula:
        Margin = (metric_val / revenue) * 100
    """
    if revenue == 0:
        raise ZeroDivisionError("Revenue cannot be zero when calculating margins.")
    return round((metric_val / revenue) * 100, 2)
