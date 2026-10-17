"""Page 5: Customer Data Explorer."""
import pandas as pd
import streamlit as st

import config as cfg
import data_processing as dp
import formatting as fmt


def _quality_section(report):
    with st.expander("Data quality report (full table, before filters)"):
        st.write(f"**Rows loaded:** {fmt.number(report.rows)}  |  **Exact duplicate rows:** {fmt.number(report.duplicate_rows)}")
        cols_missing = report.missing[report.missing["Missing"] > 0]
        st.markdown("**Missing values**")
        if cols_missing.empty:
            st.success("No missing values found.")
        else:
            st.dataframe(cols_missing, hide_index=True)
        bad = {k: v for k, v in report.invalid_numeric.items() if v}
        if bad:
            st.markdown("**Values that could not be read as numbers (treated as missing)**")
            st.dataframe(pd.DataFrame({"Column": list(bad), "Invalid values": list(bad.values())}), hide_index=True)
        neg = {k: v for k, v in report.negative_values.items() if v}
        if neg:
            st.markdown("**Negative values in financial columns (kept as-is)**")
            st.dataframe(pd.DataFrame({"Column": list(neg), "Negative values": list(neg.values())}), hide_index=True)
        st.markdown("**Is any ID column a unique customer key?**")
        if report.id_candidates.empty:
            st.write("No columns ending in 'id' were found.")
        else:
            st.dataframe(report.id_candidates, hide_index=True)
            st.caption("A column is only a customer key if it is unique on every row AND you have confirmed what it "
                       "identifies. Branch, gender and industry codes repeat by design. Set CUSTOMER_ID_COLUMN in .env "
                       "after verifying one.")


def render(df, ctx):
    st.header("Customer Data Explorer")
    st.caption("Active filters: " + ctx["filters_text"])

    if ctx["demo_mode"]:
        st.info("DEMO_MODE is on: record-level data and CSV download are hidden. Use the other pages for "
                "aggregated analysis.")
        _quality_section(ctx["report"])
        return

    st.warning("This table shows individual customer records. Do not screenshot or publish it.")

    all_cols = list(df.columns)
    chosen = st.multiselect("Columns to show", all_cols, default=all_cols, key="ex_cols")
    if not chosen:
        st.info("Select at least one column.")
        return

    view = df[chosen]

    s1, s2 = st.columns([1, 2])
    default_search = ctx["id_col"] if ctx["id_col"] in chosen else chosen[0]
    search_col = s1.selectbox("Search in column", chosen, index=chosen.index(default_search), key="ex_search_col")
    term = s2.text_input("Contains (case-insensitive)", key="ex_search_term",
                         help="Searches the selected column. With a verified customer ID configured it defaults to that column.")
    if term:
        view = view[view[search_col].astype(str).str.contains(term, case=False, regex=False, na=False)]

    o1, o2, o3 = st.columns(3)
    sort_col = o1.selectbox("Sort by", ["(none)"] + chosen, key="ex_sort_col")
    ascending = o2.radio("Order", ["Ascending", "Descending"], horizontal=True, key="ex_sort_dir") == "Ascending"
    page_size = o3.selectbox("Rows per page", [25, 50, 100, 500], index=1, key="ex_page_size")
    if sort_col != "(none)":
        view = view.sort_values(sort_col, ascending=ascending, na_position="last", kind="stable")

    total = len(view)
    pages = max(1, -(-total // page_size))
    page = st.number_input("Page", min_value=1, max_value=pages, value=1, step=1, key="ex_page")
    start = (int(page) - 1) * page_size
    st.caption(f"Showing rows {fmt.number(start + 1 if total else 0)}-{fmt.number(min(start + page_size, total))} "
               f"of {fmt.number(total)} (page {int(page)} of {pages})")
    st.dataframe(view.iloc[start:start + page_size], hide_index=True)

    st.download_button(
        "Download filtered results as CSV",
        data=view.to_csv(index=False).encode("utf-8-sig"),
        file_name="filtered_customers.csv",
        mime="text/csv",
        help="Includes all rows that match the filters and search, not only the current page.",
    )
    _quality_section(ctx["report"])
