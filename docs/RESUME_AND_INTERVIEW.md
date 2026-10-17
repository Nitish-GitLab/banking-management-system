# Resume and interview notes

## Project title
**Banking Customer Analytics Dashboard** (Python, MySQL, Pandas, Streamlit, Plotly)

## Resume bullets
Replace the [brackets] with real numbers from your own database and only keep claims you can defend.

- Built an interactive banking analytics dashboard with Streamlit and Plotly on a MySQL database of [N] customer records, with 5 pages, 8 KPI cards and 9 shared filters that recalculate every chart and table.
- Designed a modular data pipeline (validation, type coercion, duplicate and missing-value reporting, configurable income bands) separated from the UI, and wrote [30] unit tests for cleaning, filtering and KPI logic.
- Defined KPIs carefully (records vs unique customers, handling of negative or missing incomes) and generated insights automatically from the filtered data instead of hard-coding conclusions.
- Secured the app with `.env`-based credentials, read-only SQL, graceful error handling and a demo mode that hides record-level data.
- Added a customer explorer with search, sorting, pagination and CSV export, and descriptive risk views with explicit caveats against causal or default-prediction claims.

## Interview questions and answers

**1. Why Streamlit?**  
It turns Pandas code into an interactive web app quickly, which suits an analytics prototype. The trade-off is that it reruns the script on each interaction, so I cache the database read and keep calculations in plain functions.

**2. How do the filters work across all pages?**  
Selections live in `st.session_state`. `app.py` builds one filtered DataFrame with `apply_filters` and hands it to the active page, so every KPI, chart and table sees the same data.

**3. How did you avoid double counting?**  
No verified customer ID exists in the table, so I count rows as "records" and say so on screen. If you verify a key, you set `CUSTOMER_ID_COLUMN` and the customer count switches to unique IDs. The data-quality report shows whether any ID column is actually unique per row.

**4. How did you handle bad data?**  
Numeric columns are coerced with `errors="coerce"`, and the number of values that failed is reported. Negative and missing incomes get their own income bands, so no rows silently disappear. Negative balances are reported but kept, because overdrawn accounts can be legitimate.

**5. Can the dashboard predict loan defaults?**  
No. The table has no default or outcome column, so I only show descriptive patterns (distributions, loan-to-deposit ratios, correlations) and state that correlation is not causation. A prediction would need a labelled target and a validated model.

**6. How is security handled?**  
Credentials come from environment variables, `.env` is git-ignored, queries are read-only, the table name is validated before use, connections are closed in `finally`, and `DEMO_MODE` hides individual records.

**7. How would you scale this to millions of rows?**  
Push aggregation into SQL (GROUP BY queries per page), cache those results, sample for scatter plots (already capped), and consider a materialised summary table.

**8. What would you improve next?**  
Add a date field to enable trends, confirm what the ID codes mean and add readable labels, add integration tests against a test database, and deploy with aggregated data only.

**9. Why is the `views/` folder not called `pages/`?**  
Streamlit builds its own multipage menu from `pages/`, which would bypass the shared sidebar and filter state I wanted.

**10. What are the limitations?**  
No currency or date columns were confirmed, risk weighting semantics are unverified, and chart axes use SI abbreviations rather than lakh/crore.
