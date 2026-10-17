"""Central configuration: column names, thresholds and environment settings.

Column names are written exactly as they appear in the MySQL table. If your
table uses different names, change them HERE - the app never renames columns
for you and will tell you which names it could not find.
"""
from __future__ import annotations

import os
from pathlib import Path

try:  # python-dotenv is in requirements.txt; it is optional only so unit tests run without it
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

PROJECT_ROOT = Path(__file__).resolve().parent
DOTENV_AVAILABLE = load_dotenv is not None
if load_dotenv is not None:
    load_dotenv(PROJECT_ROOT / ".env")


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    return default if raw is None else raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_number(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be a number, got {raw!r}.") from exc


# ----------------------------------------------------------------------------
# Database (credentials are read from environment variables / .env only)
# ----------------------------------------------------------------------------
TABLE_NAME = os.getenv("DB_TABLE", "customerShop")

# ----------------------------------------------------------------------------
# Columns
# ----------------------------------------------------------------------------
COL_INCOME = "Estimated Income"
COL_SUPER = "Superannuation Savings"
COL_CC_BALANCE = "Credit Card Balance"
COL_LOANS = "Bank Loans"
COL_DEPOSITS = "Bank Deposits"
COL_CHECKING = "Checking Accounts"
COL_SAVINGS = "Saving Accounts"
COL_FOREIGN = "Foreign Currency Account"
COL_BUSINESS = "Business Lending"

COL_CARDS = "Amount of Credit Cards"
COL_PROPERTIES = "Properties Owned"
COL_RISK = "Risk Weighting"

COL_NATIONALITY = "Nationality"
COL_OCCUPATION = "Occupation"
COL_FEE = "Fee Structure"
COL_LOYALTY = "Loyalty Classification"
COL_BRANCH = "BRId"
COL_GENDER = "GenderId"
COL_INDUSTRY = "IAId"

COL_INCOME_BAND = "Income Band"  # derived by the app (not in the database)

# Money-like columns: forced to numbers; unparseable text becomes missing (and is reported).
FINANCIAL_COLUMNS = [
    COL_INCOME, COL_SUPER, COL_CC_BALANCE, COL_LOANS, COL_DEPOSITS,
    COL_CHECKING, COL_SAVINGS, COL_FOREIGN, COL_BUSINESS,
]
# Small whole-number codes/counts: converted to numbers only if EVERY value parses.
DISCRETE_COLUMNS = [COL_CARDS, COL_PROPERTIES, COL_RISK]
# Treated as labels/codes. Their meaning (e.g. what GenderId 1 stands for) is NOT assumed.
CATEGORICAL_COLUMNS = [
    COL_NATIONALITY, COL_OCCUPATION, COL_FEE, COL_LOYALTY, COL_BRANCH, COL_GENDER, COL_INDUSTRY,
]

# Sidebar filters, in display order
FILTER_COLUMNS = [
    COL_OCCUPATION, COL_NATIONALITY, COL_GENDER, COL_INCOME_BAND, COL_LOYALTY,
    COL_RISK, COL_FEE, COL_PROPERTIES, COL_CARDS,
]

# ----------------------------------------------------------------------------
# Business rules / display settings
# ----------------------------------------------------------------------------
# A column you have verified as a unique customer key. Empty = none verified.
CUSTOMER_ID_COLUMN = os.getenv("CUSTOMER_ID_COLUMN", "").strip()

INCOME_LOW_MAX = _env_number("INCOME_LOW_MAX", 100_000)    # Low  : 0 <= income < LOW_MAX
INCOME_MED_MAX = _env_number("INCOME_MED_MAX", 300_000)    # Med  : LOW_MAX <= income < MED_MAX
INCOME_BAND_ORDER = ["Low", "Med", "High", "Negative", "Missing"]  # High: income >= MED_MAX

CURRENCY_SYMBOL = os.getenv("CURRENCY_SYMBOL", "₹")
DEMO_MODE = _env_bool("DEMO_MODE", False)

MIN_GROUP_SIZE = 30        # smallest group allowed in "highest average" style insights
SCATTER_SAMPLE = 5000      # max points drawn in scatter plots
CACHE_TTL_SECONDS = 3600   # cached database read lifetime
