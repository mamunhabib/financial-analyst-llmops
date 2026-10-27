"""
Call Chain & Role:
------------------
Architecture Layer: Phase 7 - Interactive Financial Dashboard (Visualization Component)
Role: Generates high-fidelity Plotly charts and financial sensitivity tables for the analyst UI.
Callers:
    - ui/app.py: Renders stock charts and valuation heatmaps in the Streamlit dashboard.
Dependencies:
    - plotly.graph_objects: Financial chart generation.
    - pandas: Data manipulation.
    - numpy: Matrix calculations for sensitivity analysis.
"""

from typing import List, Optional

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def render_stock_chart(ticker: str, prices: Optional[List[float]] = None, dates: Optional[List[str]] = None) -> go.Figure:
    """
    Renders an institutional-grade dark-themed price trend and volume chart.
    If historical series is not provided, generates realistic synthetic trend data for the ticker.
    """
    if not prices or len(prices) < 5:
        # Default representative 30-day baseline data for supported tickers
        base_price = 225.0 if "AAPL" in ticker.upper() else (430.0 if "MSFT" in ticker.upper() else 140.0)
        import random
        random.seed(42)
        prices = [round(base_price * (1 + (i * 0.004) + (random.uniform(-0.015, 0.015))), 2) for i in range(30)]
        dates = [f"Day {i+1}" for i in range(30)]

    df = pd.DataFrame({"Date": dates, "Price": prices})
    df["SMA_7"] = df["Price"].rolling(window=5, min_periods=1).mean()

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.75, 0.25],
        subplot_titles=(f"{ticker.upper()} — Historical Price Action & Trend", "Relative Trading Activity"),
    )

    # Main Price Line
    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["Price"],
            mode="lines+markers",
            name="Spot Price",
            line=dict(color="#38bdf8", width=2.5),
            marker=dict(size=4, color="#38bdf8"),
            fill="tozeroy",
            fillcolor="rgba(56, 189, 248, 0.08)",
        ),
        row=1,
        col=1,
    )

    # 5-Period Moving Average
    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["SMA_7"],
            mode="lines",
            name="Short-Term SMA",
            line=dict(color="#f59e0b", width=1.5, dash="dash"),
        ),
        row=1,
        col=1,
    )

    # Simulated Volume Indicator
    volume = [abs(int(p * 150000)) for p in prices]
    colors = ["#10b981" if i == 0 or prices[i] >= prices[i - 1] else "#ef4444" for i in range(len(prices))]
    fig.add_trace(
        go.Bar(
            x=df["Date"],
            y=volume,
            name="Volume",
            marker=dict(color=colors, opacity=0.7),
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0f172a",
        plot_bgcolor="#1e293b",
        margin=dict(l=40, r=40, t=50, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(family="Inter, -apple-system, sans-serif", color="#e2e8f0"),
        height=420,
    )

    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="#334155")
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="#334155")

    return fig


def render_dcf_sensitivity_table(
    cash_flows: List[float],
    discount_rates: Optional[List[float]] = None,
    growth_rates: Optional[List[float]] = None,
) -> go.Figure:
    """
    Renders an interactive 2D DCF sensitivity heatmap (Discount Rate vs. Terminal Growth Rate).
    Displays enterprise valuation in Billions ($B).
    """
    if not discount_rates:
        discount_rates = [0.075, 0.080, 0.085, 0.090, 0.095, 0.100]
    if not growth_rates:
        growth_rates = [0.015, 0.020, 0.025, 0.030, 0.035]

    # Calculate Enterprise Value for each grid cell
    matrix = []
    text_matrix = []

    for r in discount_rates:
        row = []
        text_row = []
        for g in growth_rates:
            if r <= g:
                val = 0.0
            else:
                # PV of projected cash flows
                pv_cf = sum(cf / ((1 + r) ** (t + 1)) for t, cf in enumerate(cash_flows))
                # Terminal Value discounted to present
                terminal_val = (cash_flows[-1] * (1 + g)) / (r - g)
                pv_tv = terminal_val / ((1 + r) ** len(cash_flows))
                val = round(pv_cf + pv_tv, 2)
            row.append(val)
            text_row.append(f"${val:,.1f}B")
        matrix.append(row)
        text_matrix.append(text_row)

    x_labels = [f"g = {g * 100:.1f}%" for g in growth_rates]
    y_labels = [f"WACC = {r * 100:.1f}%" for r in discount_rates]

    fig = go.Figure(
        data=go.Heatmap(
            z=matrix,
            x=x_labels,
            y=y_labels,
            text=text_matrix,
            texttemplate="%{text}",
            textfont=dict(size=12, color="#ffffff"),
            colorscale="Viridis",
            showscale=True,
            colorbar=dict(title=dict(text="Enterprise Value ($B)", font=dict(color="#cbd5e1")), tickfont=dict(color="#94a3b8")),
        )
    )

    fig.update_layout(
        title="DCF Enterprise Value Sensitivity Matrix (WACC vs. Terminal Growth Rate)",
        template="plotly_dark",
        paper_bgcolor="#0f172a",
        plot_bgcolor="#1e293b",
        font=dict(family="Inter, sans-serif", color="#e2e8f0"),
        margin=dict(l=60, r=40, t=60, b=50),
        xaxis_title="Terminal Perpetual Growth Rate (g)",
        yaxis_title="Discount Rate (WACC)",
        height=360,
    )

    return fig
