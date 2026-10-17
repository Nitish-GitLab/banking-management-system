"""Page 3: Financial Analysis."""
import streamlit as st

import config as cfg
import data_processing as dp
import ui
import visualizations as viz


def _hist(df, col, key):
    log = st.checkbox("Log scale (positive values only)", key=key)
    ui.show(viz.histogram(df, col, f"Distribution of {col}", log_x=log))


def render(df, ctx):
    st.header("Financial Analysis")
    st.caption("Financial amounts are usually right-skewed; use the log-scale option to see the full range.")

    tabs = st.tabs(["Income", "Deposits", "Loans", "Credit card balance", "Superannuation",
                    "Checking vs Savings", "Foreign currency & Business lending"])

    with tabs[0]:
        _hist(df, cfg.COL_INCOME, "fin_log_income")
        ui.show(viz.box_by_category(df, cfg.COL_OCCUPATION, cfg.COL_INCOME, "Estimated income by occupation (top 10)"))
    with tabs[1]:
        _hist(df, cfg.COL_DEPOSITS, "fin_log_dep")
        ui.show(viz.box_by_category(df, cfg.COL_INCOME_BAND, cfg.COL_DEPOSITS, "Bank deposits by income band"))
    with tabs[2]:
        _hist(df, cfg.COL_LOANS, "fin_log_loans")
        ui.show(viz.box_by_category(df, cfg.COL_INCOME_BAND, cfg.COL_LOANS, "Bank loans by income band"))
    with tabs[3]:
        _hist(df, cfg.COL_CC_BALANCE, "fin_log_cc")
        ui.show(viz.box_by_category(df, cfg.COL_OCCUPATION, cfg.COL_CC_BALANCE,
                                    "Credit card balance by occupation (top 10)"))
    with tabs[4]:
        _hist(df, cfg.COL_SUPER, "fin_log_super")
        ui.show(viz.grouped_values(df, cfg.COL_INCOME_BAND, [cfg.COL_SUPER, cfg.COL_INCOME],
                                   "Average superannuation savings and income by income band"))
    with tabs[5]:
        group = st.selectbox("Compare across", [cfg.COL_INCOME_BAND, cfg.COL_OCCUPATION, cfg.COL_LOYALTY],
                             key="fin_chk_group")
        ui.show(viz.grouped_values(df, group, [cfg.COL_CHECKING, cfg.COL_SAVINGS],
                                   f"Average checking vs saving balances by {group}"))
        sample = _sample(df)
        ui.show(viz.scatter(sample, cfg.COL_CHECKING, cfg.COL_SAVINGS, "Checking vs saving accounts (per record)"))
    with tabs[6]:
        group = st.selectbox("Compare across", [cfg.COL_INCOME_BAND, cfg.COL_OCCUPATION, cfg.COL_NATIONALITY],
                             key="fin_fx_group")
        ui.show(viz.grouped_values(df, group, [cfg.COL_FOREIGN, cfg.COL_BUSINESS],
                                   f"Average foreign currency account and business lending by {group}"))
        sample = _sample(df)
        ui.show(viz.scatter(sample, cfg.COL_FOREIGN, cfg.COL_BUSINESS, "Foreign currency account vs business lending"))


def _sample(df):
    sample = dp.sample_for_plot(df)
    if len(sample) < len(df):
        st.caption(f"Scatter plots show a random sample of {len(sample):,} of {len(df):,} filtered records.")
    return sample
