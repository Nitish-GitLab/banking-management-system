"""Page 4: Risk and Credit Analysis (descriptive patterns only)."""
import streamlit as st

import config as cfg
import data_processing as dp
import formatting as fmt
import ui
import visualizations as viz


def render(df, ctx):
    st.header("Risk and Credit Analysis")
    st.warning(
        "These views describe patterns in the data. They do not measure default risk or creditworthiness, "
        "and correlation does not imply causation. The table has no default/outcome field, so no prediction is made."
    )

    a, b = st.columns(2)
    with a:
        ui.show(viz.bar_counts(df, cfg.COL_RISK, "Risk weighting distribution", sort="label"))
    with b:
        ui.show(viz.stacked_share(df, cfg.COL_INCOME_BAND, cfg.COL_RISK, "Risk weighting mix within each income band (%)"))

    c, d = st.columns(2)
    with c:
        ui.show(viz.bar_counts(df, cfg.COL_CARDS, "Customers by number of credit cards", sort="label"))
    with d:
        segment = st.selectbox("Segment for credit card balance",
                               [cfg.COL_OCCUPATION, cfg.COL_INCOME_BAND, cfg.COL_RISK, cfg.COL_LOYALTY, cfg.COL_CARDS],
                               key="risk_cc_segment")
        ui.show(viz.box_by_category(df, segment, cfg.COL_CC_BALANCE, f"Credit card balance by {segment}"))

    st.subheader("Loans across occupations")
    e, f = st.columns(2)
    with e:
        ui.show(viz.grouped_values(df, cfg.COL_OCCUPATION, [cfg.COL_LOANS], "Average bank loans by occupation", top_n=12))
    with f:
        ratios = dp.loan_deposit_ratio_by_group(df, cfg.COL_OCCUPATION)
        ui.show(viz.ratio_bar(ratios, "Loan-to-deposit ratio by occupation (descriptive)"))
    st.caption(f"Only groups with at least {cfg.MIN_GROUP_SIZE} records are ranked. A higher ratio means more lending "
               "relative to deposits in that group; it is not a measure of default.")

    st.subheader("Financial indicator correlations")
    ui.show(viz.correlation_heatmap(df, cfg.FINANCIAL_COLUMNS, "Correlation matrix (Pearson r)"))
    pairs = dp.correlation_pairs(df, cfg.FINANCIAL_COLUMNS)
    if not pairs.empty:
        left, right = st.columns(2)
        left.markdown("**Strongest positive pairs**")
        left.dataframe(pairs.head(5), hide_index=True, column_config={"Correlation": st.column_config.NumberColumn(format="%.2f")})
        right.markdown("**Strongest negative pairs**")
        right.dataframe(pairs.tail(5).iloc[::-1], hide_index=True, column_config={"Correlation": st.column_config.NumberColumn(format="%.2f")})

    st.subheader("Relationship explorer")
    numeric = cfg.FINANCIAL_COLUMNS
    x, y = st.columns(2)
    x_col = x.selectbox("X axis", numeric, index=numeric.index(cfg.COL_INCOME), key="risk_x")
    y_col = y.selectbox("Y axis", numeric, index=numeric.index(cfg.COL_LOANS), key="risk_y")
    color = st.selectbox("Colour by (optional)", ["None", cfg.COL_RISK, cfg.COL_INCOME_BAND, cfg.COL_LOYALTY], key="risk_color")
    sample = dp.sample_for_plot(df)
    if len(sample) < len(df):
        st.caption(f"Showing a random sample of {len(sample):,} of {len(df):,} filtered records.")
    ui.show(viz.scatter(sample, x_col, y_col, f"{y_col} vs {x_col}", color=None if color == "None" else color))

    st.subheader("Possible patterns to investigate")
    risk_text = dp.risk_by_band_text(df)
    lines = [risk_text] if risk_text else []
    if not ratios.empty:
        top = ratios.iloc[0]
        lines.append(f"**{top['Group']}** has the highest loan-to-deposit ratio among occupations "
                     f"({top['Loan-to-deposit ratio']:.2f}; {fmt.number(top['Records'])} records).")
    ui.insights(lines)
