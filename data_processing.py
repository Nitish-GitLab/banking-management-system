"""Validation, cleaning, filtering, KPI and insight calculations.

Pure pandas/numpy (no Streamlit, no Plotly) so every function can be unit-tested.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass

import numpy as np
import pandas as pd

import config as cfg
import formatting as fmt


class DataValidationError(Exception):
    """The loaded table does not contain what the dashboard expects."""


@dataclass
class DataQualityReport:
    rows: int
    duplicate_rows: int
    missing: pd.DataFrame            # Column, Missing, Missing %
    invalid_numeric: dict            # column -> values that could not be read as numbers
    negative_values: dict            # numeric column -> count of negative values
    id_candidates: pd.DataFrame      # columns ending in "id" and how unique they are


# ----------------------------------------------------------------------------
# Validation and cleaning
# ----------------------------------------------------------------------------
def normalise_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Strip BOM characters and surrounding spaces from headers. Nothing else is renamed."""
    cleaned = [str(c).replace("\ufeff", "").strip() for c in df.columns]
    duplicates = pd.Index(cleaned)[pd.Index(cleaned).duplicated()].unique().tolist()
    if duplicates:
        raise DataValidationError(
            "Column names are duplicated after removing BOM characters and surrounding spaces: "
            + ", ".join(repr(name) for name in duplicates)
        )
    return df.set_axis(cleaned, axis=1)


def required_columns() -> list[str]:
    cols = cfg.FINANCIAL_COLUMNS + cfg.DISCRETE_COLUMNS + cfg.CATEGORICAL_COLUMNS
    if cfg.CUSTOMER_ID_COLUMN:
        cols = cols + [cfg.CUSTOMER_ID_COLUMN]
    return list(dict.fromkeys(cols))


def check_columns(df: pd.DataFrame) -> None:
    missing = [c for c in required_columns() if c not in df.columns]
    if not missing:
        return
    lines = ["The table is missing column(s) the dashboard expects: " + ", ".join(missing) + "."]
    for name in missing:
        close = difflib.get_close_matches(name, list(df.columns), n=3, cutoff=0.6)
        if close:
            lines.append(f"  - '{name}' not found. Similar column(s) in the table: {close}")
    lines.append("Columns actually found: " + ", ".join(map(str, df.columns)))
    lines.append("Fix the spelling in config.py (column constants) or in the table. Nothing was renamed automatically.")
    raise DataValidationError("\n".join(lines))


def clean_data(raw: pd.DataFrame) -> tuple[pd.DataFrame, DataQualityReport]:
    """Normalise headers, validate columns, coerce numeric types and build a quality report."""
    df = normalise_column_names(raw).copy()
    check_columns(df)

    invalid: dict = {}
    for col in cfg.FINANCIAL_COLUMNS:
        original = df[col]
        converted = pd.to_numeric(original, errors="coerce")
        invalid[col] = int((original.notna() & converted.isna()).sum())
        df[col] = converted.astype("float64")

    for col in cfg.DISCRETE_COLUMNS:
        original = df[col]
        converted = pd.to_numeric(original, errors="coerce")
        if int(converted.notna().sum()) == int(original.notna().sum()):
            df[col] = converted          # every value was numeric
        # otherwise the column holds text labels and is left untouched
        invalid[col] = 0

    negatives = {c: int((df[c] < 0).sum()) for c in cfg.FINANCIAL_COLUMNS}

    n = len(df)
    missing = pd.DataFrame({"Missing": df.isna().sum(), "Missing %": (df.isna().mean() * 100).round(2)})
    missing = missing.reset_index(names="Column")

    id_rows = []
    for col in df.columns:
        if str(col).lower().endswith("id"):
            distinct = int(df[col].nunique(dropna=True))
            id_rows.append({
                "Column": col,
                "Distinct values": distinct,
                "Rows": n,
                "Unique ratio": round(distinct / n, 4) if n else 0.0,
                "Unique on every row": bool(n and distinct == n and df[col].notna().all()),
            })
    id_candidates = pd.DataFrame(
        id_rows, columns=["Column", "Distinct values", "Rows", "Unique ratio", "Unique on every row"]
    )

    report = DataQualityReport(
        rows=n,
        duplicate_rows=int(df.duplicated().sum()),
        missing=missing,
        invalid_numeric=invalid,
        negative_values=negatives,
        id_candidates=id_candidates,
    )
    return df, report


def drop_exact_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop_duplicates().reset_index(drop=True)


def add_income_band(df: pd.DataFrame, low_max: float, med_max: float) -> pd.DataFrame:
    """Add 'Income Band': Low [0, low_max), Med [low_max, med_max), High >= med_max,
    plus explicit 'Negative' and 'Missing' bands (never silently dropped)."""
    if not (0 <= low_max < med_max):
        raise ValueError("Income thresholds must satisfy 0 <= low < medium.")
    income = df[cfg.COL_INCOME]
    band = np.select(
        [income.isna(), income < 0, income < low_max, income < med_max],
        ["Missing", "Negative", "Low", "Med"],
        default="High",
    )
    out = df.copy()
    out[cfg.COL_INCOME_BAND] = band
    return out


# ----------------------------------------------------------------------------
# Labels, ordering and counting
# ----------------------------------------------------------------------------
def to_label(series: pd.Series) -> pd.Series:
    """Text labels for grouping/filtering. 2.0 -> '2', NaN -> 'Missing'."""
    s = series
    if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
        non_null = s.dropna()
        if len(non_null) and bool((non_null % 1 == 0).all()):
            s = s.astype("Int64")
    return s.astype("string").fillna("Missing")


def order_labels(labels, col: str | None = None) -> list[str]:
    """Income bands in business order; numbers numerically; text alphabetically; 'Missing' last."""
    present = list(dict.fromkeys(str(x) for x in labels))
    if col == cfg.COL_INCOME_BAND:
        return [b for b in cfg.INCOME_BAND_ORDER if b in present]
    has_missing = "Missing" in present
    rest = [x for x in present if x != "Missing"]
    try:
        rest = sorted(rest, key=float)
    except ValueError:
        rest = sorted(rest)
    return rest + (["Missing"] if has_missing else [])


def count_by(df: pd.DataFrame, col: str, top_n: int | None = None,
             sort: str = "count", group_other: bool = False) -> pd.DataFrame:
    """Records per category. Columns: [col, 'Records', 'Share %']."""
    labels = to_label(df[col]).astype(str)
    out = labels.value_counts().rename_axis(col).reset_index(name="Records")
    if sort == "label":
        out = out.set_index(col).loc[order_labels(out[col], col)].reset_index()
    if top_n is not None and len(out) > top_n:
        head, tail = out.iloc[:top_n], out.iloc[top_n:]
        out = head
        if group_other:
            other = pd.DataFrame({col: ["Other"], "Records": [int(tail["Records"].sum())]})
            out = pd.concat([head, other], ignore_index=True)
    total = int(labels.shape[0])
    out["Share %"] = (out["Records"] / total * 100) if total else 0.0
    return out.reset_index(drop=True)


def sample_for_plot(df: pd.DataFrame, n: int | None = None, seed: int = 42) -> pd.DataFrame:
    n = n or cfg.SCATTER_SAMPLE
    return df if len(df) <= n else df.sample(n=n, random_state=seed)


# ----------------------------------------------------------------------------
# Filters
# ----------------------------------------------------------------------------
def filter_options(df: pd.DataFrame, col: str) -> list[str]:
    return order_labels(to_label(df[col]), col)


def apply_filters(df: pd.DataFrame, selections: dict) -> pd.DataFrame:
    """Keep rows matching every non-empty selection. Empty selection = no restriction."""
    mask = pd.Series(True, index=df.index)
    for col, chosen in selections.items():
        if chosen:
            mask &= to_label(df[col]).isin([str(v) for v in chosen])
    return df[mask]


def describe_filters(selections: dict) -> str:
    parts = [f"{col}: {', '.join(map(str, vals))}" for col, vals in selections.items() if vals]
    return " | ".join(parts) if parts else "No filters applied (all records)"


# ----------------------------------------------------------------------------
# KPIs
# ----------------------------------------------------------------------------
def _sum(series: pd.Series):
    return float(series.sum()) if series.notna().any() else None


def _mean(series: pd.Series):
    return float(series.mean()) if series.notna().any() else None


def compute_kpis(df: pd.DataFrame, id_col: str | None = None) -> dict:
    """All KPI values for the (already filtered) frame. None means 'not computable'."""
    income = df[cfg.COL_INCOME]
    risk = df[cfg.COL_RISK]
    checking, savings = _sum(df[cfg.COL_CHECKING]), _sum(df[cfg.COL_SAVINGS])
    deposits, loans = _sum(df[cfg.COL_DEPOSITS]), _sum(df[cfg.COL_LOANS])
    risk_numeric = pd.api.types.is_numeric_dtype(risk) and risk.nunique(dropna=True) > 1
    return {
        "records": int(len(df)),
        "customers": int(df[id_col].nunique()) if id_col else None,
        "total_deposits": deposits,
        "total_loans": loans,
        "deposit_loan_ratio": (deposits / loans) if deposits is not None and loans else None,
        "avg_income": _mean(income[income >= 0]),   # negative incomes are treated as invalid
        "total_super": _sum(df[cfg.COL_SUPER]),
        "total_cc_balance": _sum(df[cfg.COL_CC_BALANCE]),
        "checking_plus_savings": None if checking is None and savings is None else (checking or 0.0) + (savings or 0.0),
        "avg_risk": float(risk.mean()) if risk_numeric else None,
    }


def loan_deposit_ratio_by_group(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    """Total loans / total deposits per group (descriptive only), for groups with enough records."""
    work = pd.DataFrame({
        "Group": to_label(df[group_col]).astype(str),
        "Deposits": df[cfg.COL_DEPOSITS],
        "Loans": df[cfg.COL_LOANS],
    })
    g = work.groupby("Group").agg(Records=("Group", "size"), Deposits=("Deposits", "sum"), Loans=("Loans", "sum"))
    g = g[(g["Records"] >= cfg.MIN_GROUP_SIZE) & (g["Deposits"] > 0)]
    g["Loan-to-deposit ratio"] = g["Loans"] / g["Deposits"]
    return g.reset_index().sort_values("Loan-to-deposit ratio", ascending=False).reset_index(drop=True)


def correlation_pairs(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Unique variable pairs with Pearson r, sorted from most positive to most negative."""
    usable = [c for c in cols if c in df.columns and df[c].nunique(dropna=True) > 1]
    empty = pd.DataFrame(columns=["Variable A", "Variable B", "Correlation"])
    if len(usable) < 2:
        return empty
    corr = df[usable].corr()
    rows = [
        (a, b, float(corr.loc[a, b]))
        for i, a in enumerate(usable) for b in usable[i + 1:]
        if pd.notna(corr.loc[a, b])
    ]
    if not rows:
        return empty
    return pd.DataFrame(rows, columns=empty.columns).sort_values("Correlation", ascending=False).reset_index(drop=True)


# ----------------------------------------------------------------------------
# Insights (every sentence is computed from the filtered data)
# ----------------------------------------------------------------------------
def _strength(r: float) -> str:
    a = abs(r)
    return "weak" if a < 0.3 else "moderate" if a < 0.6 else "strong"


def _extreme_group(df: pd.DataFrame, group_col: str, value_col: str, highest: bool = True):
    work = pd.DataFrame({"g": to_label(df[group_col]).astype(str), "v": df[value_col]}).dropna(subset=["v"])
    stats = work.groupby("g")["v"].agg(["mean", "size"])
    stats = stats[stats["size"] >= cfg.MIN_GROUP_SIZE]
    if len(stats) < 2:
        return None
    label = stats["mean"].idxmax() if highest else stats["mean"].idxmin()
    return label, float(stats.loc[label, "mean"]), int(stats.loc[label, "size"])


def risk_by_band_text(df: pd.DataFrame):
    labels = to_label(df[cfg.COL_RISK]).astype(str)
    if labels.nunique() < 2:
        return None
    overall = labels.value_counts(normalize=True)
    parts = []
    for band in order_labels(df[cfg.COL_INCOME_BAND], cfg.COL_INCOME_BAND):
        sub = labels[df[cfg.COL_INCOME_BAND] == band]
        if len(sub) >= cfg.MIN_GROUP_SIZE:
            vc = sub.value_counts(normalize=True)
            parts.append(f"{band}: {vc.index[0]} ({vc.iloc[0] * 100:.0f}%)")
    text = (f"The most common {cfg.COL_RISK} value overall is **{overall.index[0]}** "
            f"({overall.iloc[0] * 100:.1f}% of records).")
    if parts:
        text += " Most common value within each income band: " + "; ".join(parts) + "."
    return text


def generate_insights(df: pd.DataFrame) -> list[str]:
    """Plain-English findings for the filtered data. Returns [] when there is nothing to say."""
    if df.empty:
        return []
    out: list[str] = []

    occ = count_by(df, cfg.COL_OCCUPATION).iloc[0]
    out.append(f"**{occ[cfg.COL_OCCUPATION]}** is the largest occupation group: {fmt.number(occ['Records'])} records "
               f"({occ['Share %']:.1f}% of the filtered data).")

    band = count_by(df, cfg.COL_INCOME_BAND).iloc[0]
    out.append(f"The **{band[cfg.COL_INCOME_BAND]}** income band holds the most records "
               f"({fmt.number(band['Records'])}, {band['Share %']:.1f}%).")

    for group_col in (cfg.COL_OCCUPATION, cfg.COL_LOYALTY):
        res = _extreme_group(df, group_col, cfg.COL_DEPOSITS, highest=True)
        if res:
            out.append(f"Among {group_col} groups with at least {cfg.MIN_GROUP_SIZE} records, **{res[0]}** has the "
                       f"highest average bank deposits ({fmt.currency_compact(res[1])}, n={fmt.number(res[2])}).")

    deposits, loans = df[cfg.COL_DEPOSITS].sum(min_count=1), df[cfg.COL_LOANS].sum(min_count=1)
    if pd.notna(deposits) and pd.notna(loans):
        if loans > 0:
            out.append(f"Total deposits ({fmt.currency_compact(deposits)}) are **{deposits / loans:.2f}x** total loans "
                       f"({fmt.currency_compact(loans)}) in this selection.")
        else:
            out.append(f"Total deposits are {fmt.currency_compact(deposits)}; total loans are zero in this selection.")

    hi = _extreme_group(df, cfg.COL_OCCUPATION, cfg.COL_CC_BALANCE, highest=True)
    lo = _extreme_group(df, cfg.COL_OCCUPATION, cfg.COL_CC_BALANCE, highest=False)
    if hi and lo:
        out.append(f"Average credit card balance is highest for **{hi[0]}** ({fmt.currency_compact(hi[1])}) and "
                   f"lowest for **{lo[0]}** ({fmt.currency_compact(lo[1])}), among occupations with at least "
                   f"{cfg.MIN_GROUP_SIZE} records.")

    pairs = correlation_pairs(df, cfg.FINANCIAL_COLUMNS)
    if not pairs.empty:
        top, bottom = pairs.iloc[0], pairs.iloc[-1]
        if top["Correlation"] > 0:
            out.append(f"Strongest positive correlation: **{top['Variable A']}** and **{top['Variable B']}** "
                       f"(r = {top['Correlation']:.2f}, {_strength(top['Correlation'])}).")
        if bottom["Correlation"] < 0:
            out.append(f"Strongest negative correlation: **{bottom['Variable A']}** and **{bottom['Variable B']}** "
                       f"(r = {bottom['Correlation']:.2f}, {_strength(bottom['Correlation'])}).")
        out.append("Correlation describes how two measures move together; it does not show that one causes the other.")

    risk_text = risk_by_band_text(df)
    if risk_text:
        out.append(risk_text)
    return out
