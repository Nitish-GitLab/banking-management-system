<<<<<<< HEAD
# Banking Customer Analytics Dashboard

An interactive Streamlit dashboard that turns a MySQL customer table (`india.customerShop`) into KPI cards,
shared sidebar filters, Plotly charts, descriptive risk views and a downloadable customer explorer.

> Status: the data-processing logic is covered by unit tests (`tests/`). The Streamlit/Plotly interface has to be
> run on your machine against your own database; see "Testing checklist" below.

## Features
- **5 pages**: Executive Overview, Customer Segmentation, Financial Analysis, Risk & Credit Analysis, Customer Data Explorer
- **8 KPI cards** that recalculate with the filters (Indian digit grouping, e.g. 12,34,567; compact Lakh/Crore on cards)
- **9 sidebar filters** (multi-select, searchable): Occupation, Nationality, GenderId, Income Band, Loyalty Classification,
  Risk Weighting, Fee Structure, Properties Owned, Amount of Credit Cards, plus Reset Filters and a filtered record count
- **Configurable Income Bands** (Low / Med / High) with explicit *Negative* and *Missing* bands, so no row disappears
- **Plotly charts**: bar, horizontal bar, donut, histogram, box, scatter, 100% stacked bar, grouped bars, correlation heatmap
- **Insights generated from the filtered data** (nothing hard-coded)
- **Customer explorer**: column picker, search, sort, pagination, CSV export, active-filter summary, data-quality report
- **Security**: credentials only via `.env`, read-only `SELECT`, connection always closed, `DEMO_MODE` for public demos
- **Manual refresh** button and cached database reads

## Project structure
```
banking-analytics-dashboard/
├── app.py                 # entry point: page setup, sidebar, filters, navigation
├── config.py              # column names, thresholds, environment settings
├── database.py            # MySQL connection + read-only table load
├── data_processing.py     # validation, cleaning, filters, KPIs, insights (no Streamlit/Plotly)
├── formatting.py          # Indian number/currency formatting
├── visualizations.py      # Plotly figure builders (no Streamlit)
├── ui.py                  # CSS, KPI cards, chart display helpers
├── views/                 # one module per dashboard page
├── assets/style.css       # navy/white theme
├── .streamlit/config.toml # Streamlit theme
├── tests/                 # unit tests
├── docs/                  # resume + interview notes
├── requirements.txt  .env.example  .gitignore
```
The pages folder is named `views/` (not `pages/`) on purpose: Streamlit auto-creates its own navigation from a
`pages/` folder, which would conflict with the shared sidebar filters.

**Data flow:** MySQL → `database.load_table` → `data_processing.clean_data` (cached) → income band + optional duplicate
removal → sidebar filters → `apply_filters` → the selected page's `render()` → KPIs / charts / tables.

## Setup (Windows + VS Code)
1. Install Python 3.10-3.12 from python.org (tick "Add python.exe to PATH") and VS Code with the Python extension.
2. Open the project folder in VS Code, then open a terminal (**Terminal → New Terminal**, PowerShell).
3. Create and activate a virtual environment:
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
   If PowerShell blocks the script, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.
4. Install dependencies:
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
5. Configure credentials (never commit this file):
   ```powershell
   copy .env.example .env
   notepad .env
   ```
   Fill in `DB_USER`, `DB_PASSWORD`, `DB_NAME=india`, `DB_TABLE=customerShop`.
6. Run the dashboard:
   ```powershell
   streamlit run app.py
   ```
   It opens at http://localhost:8501.
7. Run the tests:
   ```powershell
   python -m unittest discover -s tests -v
   ```

### Before you push to GitHub
- Confirm `git status` does **not** list `.env`.
- If your old scripts contained a real password (for example hard-coded in a notebook), change that MySQL password
  and remove it from Git history before making the repository public.

## Configuration (`.env`)
| Variable | Purpose |
|---|---|
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_TABLE` | MySQL connection |
| `CUSTOMER_ID_COLUMN` | A column you have **verified** is a unique customer key. Empty = each row is one "record" |
| `CURRENCY_SYMBOL` | Symbol on KPI cards (default ₹; the source has no currency column) |
| `INCOME_LOW_MAX`, `INCOME_MED_MAX` | Default band limits (also editable in the sidebar) |
| `DEMO_MODE` | `true` hides record-level data and CSV download |

## Data dictionary
Column names are used exactly as in the original analysis. Meanings below are based on the column names only;
confirm them against your data source.

| Column | Treated as | Notes |
|---|---|---|
| Estimated Income | number | Negative = invalid (own band, excluded from average income) |
| Superannuation Savings | number | |
| Credit Card Balance | number | |
| Bank Loans / Bank Deposits | number | |
| Checking Accounts / Saving Accounts | number | |
| Foreign Currency Account / Business Lending | number | |
| Amount of Credit Cards | whole number (code) | Used as a filter and for counts |
| Properties Owned | whole number (code) | |
| Risk Weighting | number if every value is numeric, else label | Average shown only when numeric |
| Nationality, Occupation, Fee Structure, Loyalty Classification | label | |
| BRId, GenderId, IAId | code | Codes are displayed as stored; their meaning is not assumed |
| Income Band | derived | Low `[0, low)`, Med `[low, med)`, High `>= med`, plus Negative and Missing |

## KPI definitions
| KPI | Definition |
|---|---|
| Customer Records / Total Customers | Row count. If `CUSTOMER_ID_COLUMN` is set: number of unique values in that column |
| Total Bank Deposits / Loans | Sum over the filtered rows (all-missing → N/A, not 0) |
| Avg Estimated Income | Mean of non-negative, non-missing incomes |
| Total Superannuation Savings | Sum of `Superannuation Savings` |
| Total Credit Card Balance | Sum of `Credit Card Balance` |
| Checking + Savings Balances | Sum of `Checking Accounts` plus `Saving Accounts` |
| Avg Risk Weighting | Mean, only if the column is numeric and varies; otherwise N/A. If it is an ordinal code, treat the mean as indicative |

**Double counting:** sums add every row. That is correct only if each row is one customer. The data-quality report
shows whether any ID column is unique on every row; set `CUSTOMER_ID_COLUMN` only after you have verified it.

## Insights and limits
- Insights are computed from the filtered data. "Highest average" statements only rank groups with at least 30 records.
- Correlations are Pearson r between financial columns. They do not show causation.
- The table has no default/outcome field, so the dashboard makes **no** default or creditworthiness claims.
- Chart axes use international SI notation (k, M); KPI cards and tables use Indian grouping.
- There is no date filter because no date column has been confirmed.

## Testing checklist
Automated: `python -m unittest discover -s tests -v` (formatting, cleaning, income bands, filters, KPIs, insights).

Manual, against your database:
- [ ] App starts; wrong password / stopped MySQL shows a readable error (no password displayed)
- [ ] Temporarily rename a column in `config.py`: the error lists the missing column and suggests similar names
- [ ] Row count on the Overview equals `SELECT COUNT(*) FROM customerShop`
- [ ] Total deposits and loans match `SELECT SUM(\`Bank Deposits\`), SUM(\`Bank Loans\`) FROM customerShop`
- [ ] Choose one Occupation: KPIs, every page and the explorer all change; "Filtered records" matches a SQL `COUNT`
- [ ] Combine two filters; then **Reset filters** restores everything
- [ ] Income thresholds changed in "Data options" move customers between bands; no rows vanish
- [ ] Filters that match nothing show a warning, not a crash
- [ ] Explorer: search, sort, paging and the CSV (row count equals the filtered count)
- [ ] `DEMO_MODE=true` hides the record table and download
- [ ] Refresh button reloads data after you change a row in MySQL
- [ ] `git status` shows no `.env`

## Suggested GitHub description
> Interactive banking customer analytics dashboard built with Python, MySQL, Pandas, Streamlit and Plotly: dynamic KPIs, shared filters, income-band segmentation, descriptive risk views and CSV export.

See `docs/RESUME_AND_INTERVIEW.md` for resume bullets and interview preparation.
=======
# 🏦 Banking Management & Data Analysis Project

## 📌 Project Overview
This project focuses on analyzing banking customer data using Python and MySQL to generate meaningful insights into customer demographics, financial profiles, and banking activities.

The project uses data cleaning, preprocessing, exploratory data analysis (EDA), and visualization techniques to make banking data easier to understand.

## 🎯 Project Objectives
- Analyze banking customer information.
- Clean and preprocess raw banking data.
- Categorize customers based on estimated income.
- Explore customer demographics and financial attributes.
- Identify patterns and trends using data visualization.
- Support data-driven decision-making through analysis.

## 🛠️ Technologies Used
- **Python** — Data analysis and processing
- **MySQL** — Database management
- **Pandas** — Data cleaning and manipulation
- **Matplotlib** — Data visualization
- **Seaborn** — Statistical visualizations
- **Jupyter Notebook / VS Code** — Development environment

## 📊 Key Features
- Import banking customer data from MySQL.
- Clean column names and handle data inconsistencies.
- Categorize estimated income into Low, Medium, and High bands.
- Analyze customer attributes such as nationality, occupation, and loyalty classification.
- Visualize categorical data using charts.
- Generate insights from customer and financial information.

## 📂 Project Structure

```text
banking-management-system/
│
├── app.py
├── README.md
├── requirements.txt
├── data/
├── notebooks/
└── .gitignore
```

*Note: Update this structure to match your actual project files.*

## ⚙️ Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/banking-management-system.git
cd banking-management-system
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure MySQL
- Install and start MySQL.
- Create or select the required database.
- Import the banking dataset into the appropriate table.
- Configure your database connection using environment variables.

### 4. Run the Project

Run the appropriate Python script or notebook according to your project setup.

## 📈 Expected Outcomes
- Better understanding of banking customer data.
- Identification of customer demographic and income patterns.
- Clear visual representation of banking data.
- Data-driven insights for further analysis.

## 🚀 Future Improvements
- Build an interactive dashboard with KPIs and filters.
- Add advanced customer segmentation.
- Integrate Power BI for interactive reporting.
- Deploy the application online if a web interface is included.

## 👨‍💻 Author
**Nitish Yadav
>>>>>>> e96efcecafab1b9112bc9cd3a602d85b2d4a31d2
