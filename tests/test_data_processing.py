"""Unit tests for formatting and data processing. Run from the project root:

    python -m unittest discover -s tests -v

The DataFrames below are tiny hand-made fixtures used ONLY to test the logic.
The dashboard itself never uses fabricated data.
"""
import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config as cfg  # noqa: E402
import data_processing as dp  # noqa: E402
import formatting as fmt  # noqa: E402
import ui  # noqa: E402
import visualizations as viz  # noqa: E402


def make_frame(n=6):
    """Minimal valid frame containing every required column."""
    data = {c: np.arange(1, n + 1, dtype=float) * 1000 for c in cfg.FINANCIAL_COLUMNS}
    data.update({c: [1, 2, 3, 1, 2, 3][:n] for c in cfg.DISCRETE_COLUMNS})
    data.update({c: ["A", "B", "A", "B", "A", "B"][:n] for c in cfg.CATEGORICAL_COLUMNS})
    return pd.DataFrame(data)


class FormattingTests(unittest.TestCase):
    def test_indian_grouping(self):
        self.assertEqual(fmt.indian_grouping(0), "0")
        self.assertEqual(fmt.indian_grouping(999), "999")
        self.assertEqual(fmt.indian_grouping(1000), "1,000")
        self.assertEqual(fmt.indian_grouping(123456), "1,23,456")
        self.assertEqual(fmt.indian_grouping(1234567), "12,34,567")
        self.assertEqual(fmt.indian_grouping(123456789), "12,34,56,789")
        self.assertEqual(fmt.indian_grouping(-1234567), "-12,34,567")
        self.assertEqual(fmt.indian_grouping(1234.5, 2), "1,234.50")

    def test_missing_values(self):
        self.assertEqual(fmt.indian_grouping(None), "N/A")
        self.assertEqual(fmt.currency_compact(float("nan")), "N/A")

    def test_compact_currency(self):
        sym = cfg.CURRENCY_SYMBOL
        self.assertEqual(fmt.currency_compact(45_000), f"{sym}45,000")
        self.assertEqual(fmt.currency_compact(780_000), f"{sym}7.80 L")
        self.assertEqual(fmt.currency_compact(45_600_000), f"{sym}4.56 Cr")
        self.assertEqual(fmt.currency_compact(-780_000), f"-{sym}7.80 L")


class CleaningTests(unittest.TestCase):
    def test_header_cleanup_only_strips(self):
        df = make_frame()
        df.columns = ["\ufeff" + df.columns[0]] + [f" {c} " for c in df.columns[1:]]
        cleaned, _ = dp.clean_data(df)
        self.assertEqual(sorted(cleaned.columns), sorted(dp.required_columns()))

    def test_missing_column_raises_with_suggestion(self):
        df = make_frame().rename(columns={cfg.COL_SUPER: "Superannution Savings"})
        with self.assertRaises(dp.DataValidationError) as ctx:
            dp.clean_data(df)
        self.assertIn(cfg.COL_SUPER, str(ctx.exception))
        self.assertIn("Superannution Savings", str(ctx.exception))

    def test_header_cleanup_rejects_colliding_names(self):
        df = make_frame()
        df.columns = [f" {df.columns[0]} "] + list(df.columns[1:])
        df.insert(1, cfg.FINANCIAL_COLUMNS[0], df.iloc[:, 0])
        with self.assertRaises(dp.DataValidationError) as ctx:
            dp.clean_data(df)
        self.assertIn(cfg.FINANCIAL_COLUMNS[0], str(ctx.exception))

    def test_invalid_numbers_become_missing_and_are_counted(self):
        df = make_frame()
        df[cfg.COL_LOANS] = df[cfg.COL_LOANS].astype(object)
        df.loc[0, cfg.COL_LOANS] = "n/a"
        df.loc[1, cfg.COL_LOANS] = None
        cleaned, report = dp.clean_data(df)
        self.assertEqual(report.invalid_numeric[cfg.COL_LOANS], 1)   # only the text value
        self.assertEqual(int(cleaned[cfg.COL_LOANS].isna().sum()), 2)

    def test_duplicates_and_negatives_reported(self):
        df = pd.concat([make_frame(), make_frame().iloc[[0]]], ignore_index=True)
        df.loc[2, cfg.COL_DEPOSITS] = -5
        cleaned, report = dp.clean_data(df)
        self.assertEqual(report.duplicate_rows, 1)
        self.assertEqual(report.negative_values[cfg.COL_DEPOSITS], 1)
        self.assertEqual(len(dp.drop_exact_duplicates(cleaned)), len(df) - 1)

    def test_discrete_text_labels_left_alone(self):
        df = make_frame()
        df[cfg.COL_RISK] = ["Low", "High", "Low", "High", "Low", "High"]
        cleaned, _ = dp.clean_data(df)
        self.assertFalse(pd.api.types.is_numeric_dtype(cleaned[cfg.COL_RISK]))

    def test_id_candidates_flags_unique_column(self):
        df = make_frame()
        df[cfg.COL_BRANCH] = range(len(df))      # unique
        _, report = dp.clean_data(df)
        row = report.id_candidates.set_index("Column").loc[cfg.COL_BRANCH]
        self.assertTrue(row["Unique on every row"])
        self.assertFalse(report.id_candidates.set_index("Column").loc[cfg.COL_GENDER, "Unique on every row"])


class IncomeBandTests(unittest.TestCase):
    def band_for(self, value):
        df = pd.DataFrame({cfg.COL_INCOME: [value]})
        return dp.add_income_band(df, 100_000, 300_000)[cfg.COL_INCOME_BAND].iloc[0]

    def test_boundaries(self):
        self.assertEqual(self.band_for(0), "Low")
        self.assertEqual(self.band_for(99_999.99), "Low")
        self.assertEqual(self.band_for(100_000), "Med")
        self.assertEqual(self.band_for(299_999), "Med")
        self.assertEqual(self.band_for(300_000), "High")

    def test_negative_and_missing_are_explicit(self):
        self.assertEqual(self.band_for(-1), "Negative")
        self.assertEqual(self.band_for(np.nan), "Missing")

    def test_no_row_is_dropped(self):
        df = pd.DataFrame({cfg.COL_INCOME: [-5, np.nan, 10, 150_000, 900_000]})
        out = dp.add_income_band(df, 100_000, 300_000)
        self.assertEqual(len(out), 5)
        self.assertEqual(int(out[cfg.COL_INCOME_BAND].isna().sum()), 0)

    def test_bad_thresholds_rejected(self):
        with self.assertRaises(ValueError):
            dp.add_income_band(pd.DataFrame({cfg.COL_INCOME: [1.0]}), 300_000, 100_000)


class FilterTests(unittest.TestCase):
    def setUp(self):
        self.df = dp.add_income_band(dp.clean_data(make_frame())[0], 2_000, 4_000)

    def test_empty_selection_keeps_everything(self):
        self.assertEqual(len(dp.apply_filters(self.df, {cfg.COL_OCCUPATION: []})), 6)

    def test_single_filter(self):
        out = dp.apply_filters(self.df, {cfg.COL_OCCUPATION: ["A"]})
        self.assertEqual(len(out), 3)
        self.assertTrue((out[cfg.COL_OCCUPATION] == "A").all())

    def test_filters_combine_with_and(self):
        out = dp.apply_filters(self.df, {cfg.COL_OCCUPATION: ["A"], cfg.COL_RISK: ["1"]})
        self.assertEqual(len(out), 1)

    def test_numeric_column_matches_text_selection(self):
        out = dp.apply_filters(self.df, {cfg.COL_CARDS: ["1", "2"]})
        self.assertEqual(len(out), 4)

    def test_options_and_order(self):
        self.assertEqual(dp.filter_options(self.df, cfg.COL_RISK), ["1", "2", "3"])
        bands = dp.filter_options(self.df, cfg.COL_INCOME_BAND)
        self.assertEqual(bands, [b for b in cfg.INCOME_BAND_ORDER if b in bands])

    def test_describe_filters(self):
        self.assertIn("No filters", dp.describe_filters({cfg.COL_OCCUPATION: []}))
        self.assertIn("Occupation: A", dp.describe_filters({cfg.COL_OCCUPATION: ["A"]}))


class KpiTests(unittest.TestCase):
    def test_values(self):
        df = dp.clean_data(make_frame())[0]
        k = dp.compute_kpis(df)
        self.assertEqual(k["records"], 6)
        self.assertIsNone(k["customers"])                       # no verified ID configured
        self.assertEqual(k["total_deposits"], 21_000)
        self.assertEqual(k["total_loans"], 21_000)
        self.assertEqual(k["checking_plus_savings"], 42_000)
        self.assertAlmostEqual(k["avg_income"], 3_500)
        self.assertAlmostEqual(k["avg_risk"], 2.0)

    def test_unique_customers_uses_verified_id(self):
        df = make_frame()
        df[cfg.COL_BRANCH] = [1, 1, 2, 2, 3, 3]
        k = dp.compute_kpis(dp.clean_data(df)[0], id_col=cfg.COL_BRANCH)
        self.assertEqual(k["records"], 6)
        self.assertEqual(k["customers"], 3)

    def test_negative_income_excluded_from_average(self):
        df = make_frame()
        df.loc[0, cfg.COL_INCOME] = -999_999
        k = dp.compute_kpis(dp.clean_data(df)[0])
        self.assertAlmostEqual(k["avg_income"], np.mean([2000, 3000, 4000, 5000, 6000]))

    def test_all_missing_gives_none_not_zero(self):
        df = make_frame()
        df[cfg.COL_LOANS] = np.nan
        k = dp.compute_kpis(dp.clean_data(df)[0])
        self.assertIsNone(k["total_loans"])
        self.assertIsNone(k["deposit_loan_ratio"])

    def test_zero_deposit_loan_ratio_is_displayed(self):
        items = ui.build_kpi_items({
            "customers": None,
            "records": 1,
            "deposit_loan_ratio": 0.0,
            "total_deposits": 0.0,
            "total_loans": 1.0,
            "avg_income": None,
            "total_super": None,
            "total_cc_balance": None,
            "checking_plus_savings": None,
            "avg_risk": None,
        }, None)
        deposits = next(item for item in items if item["label"] == "Total Bank Deposits")
        self.assertEqual(deposits["sub"], "Deposits / loans: 0.00x")

    def test_risk_average_only_when_numeric(self):
        df = make_frame()
        df[cfg.COL_RISK] = ["Low", "High", "Low", "High", "Low", "High"]
        self.assertIsNone(dp.compute_kpis(dp.clean_data(df)[0])["avg_risk"])

    def test_empty_frame_does_not_crash(self):
        df = dp.clean_data(make_frame())[0].iloc[0:0]
        k = dp.compute_kpis(df)
        self.assertEqual(k["records"], 0)
        self.assertIsNone(k["total_deposits"])


class AnalysisTests(unittest.TestCase):
    def test_count_by_shares_sum_to_100(self):
        df = dp.clean_data(make_frame())[0]
        counts = dp.count_by(df, cfg.COL_OCCUPATION)
        self.assertAlmostEqual(counts["Share %"].sum(), 100.0)
        self.assertEqual(int(counts["Records"].sum()), 6)

    def test_count_by_missing_label(self):
        df = make_frame()
        df.loc[0, cfg.COL_OCCUPATION] = None
        counts = dp.count_by(dp.clean_data(df)[0], cfg.COL_OCCUPATION)
        self.assertIn("Missing", counts[cfg.COL_OCCUPATION].tolist())

    def test_correlation_pairs_sorted(self):
        df = pd.DataFrame({"a": [1, 2, 3, 4], "b": [2, 4, 6, 8], "c": [4, 3, 2, 1]})
        pairs = dp.correlation_pairs(df, ["a", "b", "c"])
        self.assertAlmostEqual(pairs.iloc[0]["Correlation"], 1.0)
        self.assertAlmostEqual(pairs.iloc[-1]["Correlation"], -1.0)

    def test_constant_column_ignored_in_correlation(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": [5, 5, 5], "c": [3, 2, 1]})
        pairs = dp.correlation_pairs(df, ["a", "b", "c"])
        self.assertEqual(len(pairs), 1)

    def test_grouped_totals_keep_all_missing_as_missing(self):
        df = pd.DataFrame({
            cfg.COL_OCCUPATION: ["A", "A", "B"],
            cfg.COL_DEPOSITS: [np.nan, np.nan, 4.0],
            cfg.COL_LOANS: [np.nan, np.nan, 2.0],
        })
        fig = viz.grouped_values(
            df, cfg.COL_OCCUPATION, [cfg.COL_DEPOSITS, cfg.COL_LOANS], "Totals", agg="sum"
        )
        deposits = next(trace for trace in fig.data if trace.name == cfg.COL_DEPOSITS)
        values = dict(zip(deposits.x, deposits.y))
        self.assertTrue(pd.isna(values["A"]))
        self.assertEqual(values["B"], 4.0)

    def test_insights_come_from_data(self):
        df = dp.add_income_band(dp.clean_data(make_frame())[0], 2_000, 4_000)
        text = " ".join(dp.generate_insights(df))
        self.assertIn("largest occupation group", text)
        self.assertIn("does not show that one causes the other", text)
        self.assertEqual(dp.generate_insights(df.iloc[0:0]), [])


if __name__ == "__main__":
    unittest.main()
