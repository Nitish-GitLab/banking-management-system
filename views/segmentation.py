"""Page 2: Customer Segmentation."""
import streamlit as st

import config as cfg
import data_processing as dp
import ui
import visualizations as viz


def render(df, ctx):
    st.header("Customer Segmentation")
    st.caption("Counts are customer records. GenderId and other ID columns are shown as the codes stored in the "
               "database; their meaning is not assumed.")

    a, b = st.columns(2)
    with a:
        ui.show(viz.bar_counts(df, cfg.COL_OCCUPATION, "Records by occupation", horizontal=True, top_n=15))
    with b:
        ui.show(viz.bar_counts(df, cfg.COL_NATIONALITY, "Records by nationality", horizontal=True, top_n=15))

    c, d, e = st.columns(3)
    with c:
        ui.show(viz.donut(df, cfg.COL_GENDER, "GenderId distribution"))
    with d:
        ui.show(viz.donut(df, cfg.COL_LOYALTY, "Loyalty classification"))
    with e:
        ui.show(viz.bar_counts(df, cfg.COL_INCOME_BAND, "Income band distribution", sort="label"))

    st.subheader("Properties owned")
    f, g = st.columns(2)
    with f:
        ui.show(viz.bar_counts(df, cfg.COL_PROPERTIES, "Records by properties owned", sort="label"))
    with g:
        ui.show(viz.stacked_share(df, cfg.COL_PROPERTIES, cfg.COL_INCOME_BAND,
                                  "Income band mix by properties owned (%)"))

    st.subheader("Segment explorer")
    segment = st.selectbox("Segment", [cfg.COL_OCCUPATION, cfg.COL_NATIONALITY, cfg.COL_LOYALTY, cfg.COL_FEE,
                                       cfg.COL_GENDER, cfg.COL_PROPERTIES, cfg.COL_INCOME_BAND], key="seg_pick")
    ui.show(viz.grouped_values(df, segment, [cfg.COL_DEPOSITS, cfg.COL_LOANS],
                               f"Average deposits and loans by {segment}"))
    summary = dp.count_by(df, segment)
    st.dataframe(summary.rename(columns={"Share %": "Share (%)"}), hide_index=True,
                 column_config={"Share (%)": st.column_config.NumberColumn(format="%.1f")})
