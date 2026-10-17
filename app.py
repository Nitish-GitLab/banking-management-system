"""Banking Customer Analytics Dashboard - entry point.

Run with:  streamlit run app.py
"""
import streamlit as st

import config as cfg
import data_processing as dp
import database
import ui
from views import explorer, financial, overview, risk, segmentation

st.set_page_config(page_title="Banking Customer Analytics", page_icon="🏦", layout="wide")
ui.load_css()

PAGES = {
    "Executive Overview": overview,
    "Customer Segmentation": segmentation,
    "Financial Analysis": financial,
    "Risk & Credit Analysis": risk,
    "Customer Data Explorer": explorer,
}


# --------------------------------------------------------------------------
# Data loading (cached; the Refresh button clears the cache)
# --------------------------------------------------------------------------
@st.cache_data(ttl=cfg.CACHE_TTL_SECONDS, show_spinner="Loading customer data from MySQL...")
def load_and_clean():
    return dp.clean_data(database.load_table(cfg.TABLE_NAME))


try:
    base_df, report = load_and_clean()
except (database.ConfigError, database.DatabaseError, dp.DataValidationError) as exc:
    st.error("The dashboard could not load the data.")
    st.code(str(exc), language="text")
    st.info("Check your .env values, that MySQL is running, and that the table/column names are correct. "
            "Then click 'Rerun' (top right) or press R.")
    st.stop()

if base_df.empty:
    st.warning(f"Table `{cfg.TABLE_NAME}` returned no rows.")
    st.stop()

# --------------------------------------------------------------------------
# Sidebar: navigation, data options, filters
# --------------------------------------------------------------------------
FILTER_KEYS = {col: f"flt::{col}" for col in cfg.FILTER_COLUMNS}


def reset_filters():
    for key in FILTER_KEYS.values():
        st.session_state[key] = []
    st.session_state["thr_low"] = float(cfg.INCOME_LOW_MAX)
    st.session_state["thr_med"] = float(cfg.INCOME_MED_MAX)


st.session_state.setdefault("thr_low", float(cfg.INCOME_LOW_MAX))
st.session_state.setdefault("thr_med", float(cfg.INCOME_MED_MAX))

with st.sidebar:
    st.markdown("### Banking Analytics")
    page_name = st.radio("Navigate", list(PAGES), key="nav")
    if st.button("Refresh data from MySQL"):
        st.cache_data.clear()
        st.rerun()

    with st.expander("Data options"):
        low = st.number_input("Low income below", min_value=0.0, step=10_000.0, key="thr_low")
        med = st.number_input("Medium income below", min_value=0.0, step=10_000.0, key="thr_med",
                              help="Income at or above this value is 'High'.")
        drop_dups = st.checkbox("Drop exact duplicate rows", value=False,
                                help=f"{report.duplicate_rows:,} exact duplicate row(s) found in the table. "
                                     "Off by default because without a verified customer ID, identical rows may be genuine.")

if not low < med:
    st.error("Income thresholds must satisfy: Low limit < Medium limit. Adjust them in 'Data options'.")
    st.stop()

df = dp.drop_exact_duplicates(base_df) if drop_dups else base_df
df = dp.add_income_band(df, low, med)

selections = {}
with st.sidebar:
    st.markdown("#### Filters")
    st.button("Reset filters", on_click=reset_filters)
    for col, key in FILTER_KEYS.items():
        options = dp.filter_options(df, col)
        # drop stale selections (e.g. after a data refresh) before the widget is created
        st.session_state[key] = [v for v in st.session_state.get(key, []) if v in options]
        selections[col] = st.multiselect(col, options, key=key, placeholder="All")

filtered = dp.apply_filters(df, selections)
with st.sidebar:
    st.metric("Filtered records", f"{len(filtered):,} of {len(df):,}")

# --------------------------------------------------------------------------
# Main area
# --------------------------------------------------------------------------
ui.banner("Banking Customer Analytics Dashboard",
          f"Source: MySQL `{cfg.TABLE_NAME}`  |  {len(filtered):,} of {len(df):,} records selected")

if cfg.CUSTOMER_ID_COLUMN and cfg.CUSTOMER_ID_COLUMN in df.columns and df[cfg.CUSTOMER_ID_COLUMN].duplicated().any():
    st.caption(f"Note: `{cfg.CUSTOMER_ID_COLUMN}` has repeated values, so 'Total Customers' counts unique IDs "
               "while sums add every record.")

if filtered.empty:
    st.warning("No records match the current filters. Use 'Reset filters' in the sidebar.")
    st.stop()

context = {
    "id_col": cfg.CUSTOMER_ID_COLUMN or None,
    "filters_text": dp.describe_filters(selections),
    "report": report,
    "demo_mode": cfg.DEMO_MODE,
}
PAGES[page_name].render(filtered, context)
