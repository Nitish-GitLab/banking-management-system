"""Small Streamlit UI helpers: CSS, KPI cards, chart display."""
from __future__ import annotations

import html

import streamlit as st

import config as cfg
import formatting as fmt


def load_css() -> None:
    css = (cfg.PROJECT_ROOT / "assets" / "style.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def banner(title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="app-banner"><h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div>',
        unsafe_allow_html=True,
    )


def show(fig) -> None:
    """Render a Plotly figure at container width (the default in Streamlit >= 1.50)."""
    title = fig.layout.title.text if fig.layout.title and fig.layout.title.text else "chart"
    st.plotly_chart(fig, key=f"chart-{abs(hash(title))}")


def _card(label: str, value: str, sub: str = "", tooltip: str = "") -> str:
    return (
        f'<div class="kpi" title="{html.escape(tooltip)}">'
        f'<div class="kpi-label">{html.escape(label)}</div>'
        f'<div class="kpi-value">{html.escape(value)}</div>'
        f'<div class="kpi-sub">{html.escape(sub)}</div></div>'
    )


def build_kpi_items(kpis: dict, id_col: str | None) -> list[dict]:
    if kpis["customers"] is not None:
        first = dict(label="Total Customers", value=fmt.number(kpis["customers"]),
                     sub=f"unique {id_col} values ({fmt.number(kpis['records'])} records)")
    else:
        first = dict(label="Customer Records", value=fmt.number(kpis["records"]),
                     sub="1 row = 1 record (no verified customer ID)")
    ratio = kpis["deposit_loan_ratio"]
    return [
        first,
        dict(label="Total Bank Deposits", value=fmt.currency_compact(kpis["total_deposits"]),
               sub=f"Deposits / loans: {ratio:.2f}x" if ratio is not None else "",
               tooltip=fmt.currency(kpis["total_deposits"])),
        dict(label="Total Bank Loans", value=fmt.currency_compact(kpis["total_loans"]),
             tooltip=fmt.currency(kpis["total_loans"])),
        dict(label="Avg Estimated Income", value=fmt.currency_compact(kpis["avg_income"]),
             sub="excludes negative / missing", tooltip=fmt.currency(kpis["avg_income"])),
        dict(label="Total Superannuation Savings", value=fmt.currency_compact(kpis["total_super"]),
             tooltip=fmt.currency(kpis["total_super"])),
        dict(label="Total Credit Card Balance", value=fmt.currency_compact(kpis["total_cc_balance"]),
             tooltip=fmt.currency(kpis["total_cc_balance"])),
        dict(label="Checking + Savings Balances", value=fmt.currency_compact(kpis["checking_plus_savings"]),
             sub="sum of both account columns", tooltip=fmt.currency(kpis["checking_plus_savings"])),
        dict(label="Avg Risk Weighting",
             value="N/A" if kpis["avg_risk"] is None else f"{kpis['avg_risk']:.2f}",
             sub="numeric field" if kpis["avg_risk"] is not None else "field is not numeric"),
    ]


def kpi_cards(items: list[dict], per_row: int = 4) -> None:
    for start in range(0, len(items), per_row):
        row = items[start:start + per_row]
        for col, item in zip(st.columns(per_row), row):
            col.markdown(_card(item["label"], item["value"], item.get("sub", ""), item.get("tooltip", "")),
                         unsafe_allow_html=True)


def insights(lines: list[str]) -> None:
    if not lines:
        st.info("Not enough data in the current selection to calculate findings.")
        return
    # "$" would start LaTeX in Streamlit markdown, so escape it
    st.markdown("\n".join(f"- {line.replace('$', chr(92) + '$')}" for line in lines))
