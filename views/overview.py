"""Page 1: Executive Overview."""
import streamlit as st

import config as cfg
import data_processing as dp
import ui
import visualizations as viz


def render(df, ctx):
    st.header("Executive Overview")
    kpis = dp.compute_kpis(df, ctx["id_col"])
    ui.kpi_cards(ui.build_kpi_items(kpis, ctx["id_col"]))
    if not ctx["id_col"]:
        st.caption("No verified customer ID is configured (CUSTOMER_ID_COLUMN), so every row is counted as one "
                   "customer record. Balances are summed across records.")

    st.subheader("Customer distribution")
    left, right = st.columns(2)
    with left:
        ui.show(viz.bar_counts(df, cfg.COL_OCCUPATION, "Records by occupation (top 10)", horizontal=True, top_n=10))
    with right:
        ui.show(viz.donut(df, cfg.COL_INCOME_BAND, "Income band distribution"))

    st.subheader("Deposits versus loans")
    mode = st.radio("Measure", ["Average per record", "Total"], horizontal=True, key="ov_mode")
    agg = "mean" if mode.startswith("Average") else "sum"
    group = st.selectbox("Compare across", [cfg.COL_INCOME_BAND, cfg.COL_OCCUPATION, cfg.COL_LOYALTY, cfg.COL_FEE],
                         key="ov_group")
    ui.show(viz.grouped_values(df, group, [cfg.COL_DEPOSITS, cfg.COL_LOANS],
                               f"{'Average' if agg == 'mean' else 'Total'} deposits vs loans by {group}", agg=agg))

    st.subheader("Savings overview")
    ui.show(viz.totals_bar(df, [cfg.COL_CHECKING, cfg.COL_SAVINGS, cfg.COL_SUPER, cfg.COL_FOREIGN],
                           "Total balances by account type"))

    st.subheader("Key findings")
    st.caption("Calculated from the currently filtered data; they change when you change the filters.")
    ui.insights(dp.generate_insights(df))
