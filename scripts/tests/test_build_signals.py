"""build.py: insight ordering (lead pinned), the aggregate filter, and emission
of the 'why absent' reason fields."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import build, config, narrative
from lenses.config import Indicator, Lens


def _ind(id_, rule, **kw):
    return Indicator(id=id_, title=id_, short=id_, unit="%", color="#fff",
                     series_id=id_.upper(), limit=10, rule=rule, context="c", **kw)


def _obs(v):
    return [{"date": "2026-01-01", "value": str(v)}]


class OrderingTest(unittest.TestCase):
    def test_pins_authored_lead_then_sorts_rest_by_tier(self):
        # lead = info (would be tier 3) but stays first; the rest sort by tier.
        lead = _ind("lead", narrative.energy_level("Lead"))           # info
        info = _ind("info2", narrative.energy_level("Info"))          # info -> tier 3
        scored = _ind("scored", narrative.rule_inflation)            # severity+fred -> tier 0
        ordered = build.order_indicators([lead, info, scored])
        self.assertEqual([i.id for i in ordered], ["lead", "scored", "info2"])

    def test_ordering_never_changes_any_real_lead(self):
        for cat in config.CATEGORIES:
            for lens in cat["lenses"]:
                ordered = build.order_indicators(lens.indicators)
                self.assertEqual(ordered[0].id, lens.indicators[0].id,
                                 f"{lens.id} lead changed under ordering")

    def test_global_growth_demotes_unpredicted_annuals(self):
        lens = next(l for c in config.CATEGORIES for l in c["lenses"]
                    if l.id == "global-growth")
        ordered = [i.id for i in build.order_indicators(lens.indicators)]
        self.assertEqual(ordered[0], "world-growth")            # lead pinned
        self.assertEqual(ordered[1], "ea-gdp-quarterly")        # tier 0 (scored+predicted)
        self.assertEqual(ordered[-3:], ["china-growth", "euro-growth", "world-inflation"])


class AggregateFilterTest(unittest.TestCase):
    def test_non_aggregating_severity_excluded_from_badge(self):
        lead = _ind("lead", narrative.rule_inflation)                 # will read ok
        echo = _ind("echo", narrative.rule_inflation, aggregate=False)  # will read elevated
        lens = Lens(id="x", title="X", accent="#fff", indicators=[lead, echo])
        fetched = {"LEAD:lin": _obs(1.0), "ECHO:lin": _obs(5.0)}
        result = build.build_lens(lens, fetched)
        self.assertEqual(result["status"], "ok")  # echo's 'elevated' is held out

    def test_aggregating_severity_still_counts(self):
        lead = _ind("lead", narrative.rule_inflation)
        other = _ind("other", narrative.rule_inflation)  # aggregate defaults True
        lens = Lens(id="x", title="X", accent="#fff", indicators=[lead, other])
        fetched = {"LEAD:lin": _obs(1.0), "OTHER:lin": _obs(5.0)}
        self.assertEqual(build.build_lens(lens, fetched)["status"], "elevated")


class ReasonEmissionTest(unittest.TestCase):
    def test_reasons_emitted_only_when_set(self):
        scored = _ind("scored", narrative.rule_inflation)
        noted = _ind("noted", narrative.energy_level("Thing"), source="computed",
                     no_severity_reason="why no score")
        lens = Lens(id="x", title="X", accent="#fff", indicators=[scored, noted])
        fetched = {"SCORED:lin": _obs(1.0), "NOTED:lin": _obs(100.0)}
        by_id = {i["id"]: i for i in build.build_lens(lens, fetched)["indicators"]}
        self.assertNotIn("no_severity_reason", by_id["scored"])
        self.assertEqual(by_id["noted"]["no_severity_reason"], "why no score")

    def test_no_prediction_reason_emitted(self):
        noted = _ind("ann", narrative.rule_inflation, source="imf",
                     no_prediction_reason="annual data")
        lens = Lens(id="x", title="X", accent="#fff", indicators=[noted])
        fetched = {"ANN:lin": _obs(1.0)}
        d = build.build_lens(lens, fetched)["indicators"][0]
        self.assertEqual(d["no_prediction_reason"], "annual data")


class SignalNoteTest(unittest.TestCase):
    def test_both_reasons_combine(self):
        h, b = build.signal_note("no score here.", "no forecast here.")
        self.assertEqual(h, "Why it isn't scored or forecast")
        self.assertEqual(b, "no score here. no forecast here.")

    def test_severity_only(self):
        self.assertEqual(build.signal_note("no score.", ""),
                         ("Why it isn't scored", "no score."))

    def test_prediction_only(self):
        self.assertEqual(build.signal_note("", "no forecast."),
                         ("Why it isn't forecast", "no forecast."))

    def test_neither_is_none(self):
        self.assertIsNone(build.signal_note("", ""))
        self.assertIsNone(build.signal_note(None, None))


if __name__ == "__main__":
    unittest.main()
