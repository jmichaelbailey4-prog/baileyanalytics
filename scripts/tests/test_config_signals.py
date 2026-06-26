"""The score-explain-order config contract: every gray chip explains itself,
every non-aggregating chip is actually scored, and the audited outcomes hold."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import config, narrative


def _all_indicators():
    for cat in config.CATEGORIES:
        for lens in cat["lenses"]:
            for ind in lens.indicators:
                yield cat, lens, ind


def _find(lens_id, ind_id):
    for _, lens, ind in _all_indicators():
        if lens.id == lens_id and ind.id == ind_id:
            return ind
    raise AssertionError(f"{lens_id}/{ind_id} not found")


class FieldDefaultsTest(unittest.TestCase):
    def test_indicator_has_new_fields(self):
        ind = _find("recession-watch", "yield-curve")
        self.assertTrue(ind.aggregate)
        self.assertEqual(ind.no_severity_reason, "")
        self.assertEqual(ind.no_prediction_reason, "")


class MatrixInvariantsTest(unittest.TestCase):
    def test_every_unscored_signal_explains_itself(self):
        # info/momentum indicators carry no severity chip -> must say why.
        for _, lens, ind in _all_indicators():
            if narrative.rule_kind(ind.rule) in ("info", "momentum"):
                self.assertTrue(ind.no_severity_reason,
                                f"{lens.id}/{ind.id} is unscored but has no reason")

    def test_scored_signals_have_no_severity_note(self):
        for _, lens, ind in _all_indicators():
            if narrative.rule_kind(ind.rule) == "severity":
                self.assertEqual(ind.no_severity_reason, "",
                                 f"{lens.id}/{ind.id} is scored but carries a why-no-score note")

    def test_unpredictable_signal_explains_itself(self):
        for _, lens, ind in _all_indicators():
            if not config.is_predictable(ind):
                self.assertTrue(ind.no_prediction_reason,
                                f"{lens.id}/{ind.id} isn't predictable but has no reason")

    def test_predictable_signal_has_no_prediction_note(self):
        for _, lens, ind in _all_indicators():
            if config.is_predictable(ind):
                self.assertEqual(ind.no_prediction_reason, "",
                                 f"{lens.id}/{ind.id} is predictable but carries a why-no-forecast note")

    def test_non_aggregating_only_on_scored(self):
        for _, lens, ind in _all_indicators():
            if not ind.aggregate:
                self.assertEqual(narrative.rule_kind(ind.rule), "severity",
                                 f"{lens.id}/{ind.id} is non-aggregating but not scored")


class AuditedOutcomesTest(unittest.TestCase):
    def test_treasuries_scored_and_aggregating(self):  # D1
        for tid in ("treasury-10y", "treasury-2y"):
            ind = _find("cost-of-money", tid)
            self.assertEqual(narrative.rule_kind(ind.rule), "severity", tid)
            self.assertTrue(ind.aggregate, tid)

    def test_wage_growth_scored(self):  # D2
        self.assertEqual(narrative.rule_kind(_find("job-market", "wage-growth").rule), "severity")

    def test_participation_info_with_reason(self):  # D2
        ind = _find("job-market", "participation")
        self.assertEqual(narrative.rule_kind(ind.rule), "info")
        self.assertTrue(ind.no_severity_reason)

    def test_receipts_promoted(self):  # 1a
        self.assertEqual(narrative.rule_kind(_find("fiscal-health", "receipts").rule), "severity")

    def test_interest_cost_info_interest_burden_scored(self):  # D3
        self.assertEqual(narrative.rule_kind(_find("fiscal-health", "interest-cost").rule), "info")
        burden = _find("fiscal-health", "interest-burden")
        self.assertEqual(burden.source, "computed")
        self.assertEqual(narrative.rule_kind(burden.rule), "severity")
        self.assertTrue(burden.aggregate)

    def test_auto_sales_promoted(self):  # 1a
        self.assertEqual(narrative.rule_kind(_find("consumer-spending", "auto-sales").rule), "severity")

    def test_mdsp_promoted(self):  # 1a
        self.assertEqual(narrative.rule_kind(_find("housing-affordability", "debt-service").rule), "severity")

    def test_non_aggregating_echo_set(self):  # D5
        for lens_id, ind_id in (("housing-home-prices", "median-price"),
                                ("housing-rent-shelter", "owners-equivalent-rent"),
                                ("business-profitability", "nonfinancial-profits"),
                                ("business-formation", "high-propensity"),
                                ("consumer-income-savings", "net-worth"),
                                ("global-growth", "ea-gdp-quarterly")):
            ind = _find(lens_id, ind_id)
            self.assertEqual(narrative.rule_kind(ind.rule), "severity", ind_id)
            self.assertFalse(ind.aggregate, ind_id)

    def test_active_listings_kept_info(self):  # D5 guardrail
        ind = _find("housing-supply-construction", "active-listings")
        self.assertEqual(narrative.rule_kind(ind.rule), "info")
        self.assertTrue(ind.no_severity_reason)

    def test_world_growth_severity_but_no_forecast(self):
        ind = _find("global-growth", "world-growth")
        self.assertEqual(narrative.rule_kind(ind.rule), "severity")
        self.assertTrue(ind.no_prediction_reason)
        self.assertEqual(ind.no_severity_reason, "")


if __name__ == "__main__":
    unittest.main()
