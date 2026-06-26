"""Drift lock: probe every LIVE severity rule against its declared band_spec.

For each declared edge we feed synthetic observations straddling it and assert the
rule returns the descriptor's segment on each side. Editing a threshold in a rule
body without editing its band_spec (or vice versa) turns this red — the whole point
of generating the methodology page + scale strip from the spec.

Also: coverage (every severity indicator has a well-formed spec + curated 'why') and
no-orphan (every BAND_WHY key is a tag actually in use).
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import bands, config, narrative, reasons, util  # noqa: E402

SEVERITY = {"ok", "watch", "elevated", "alert"}


def _all_rules():
    """(label, rule) for every indicator across CATEGORIES + the injected crypto lens."""
    out = []
    for cat in config.CATEGORIES:
        for lens in cat["lenses"]:
            for ind in lens.indicators:
                out.append((f"{lens.id}::{ind.id}", ind.rule))
    for rule in (narrative.rule_btc_dominance, narrative.rule_crypto_rotation,
                 narrative.rule_btc_eth_relative):
        out.append((f"crypto-structure::{rule.__name__}", rule))
    return out


def _cap(status, cap):
    if cap and util.STATUS_ORDER.get(status, 0) > util.STATUS_ORDER[cap]:
        return cap
    return status


class TestCoverage(unittest.TestCase):
    def test_every_severity_indicator_has_a_wellformed_spec(self):
        for label, rule in _all_rules():
            if narrative.rule_kind(rule) != "severity":
                continue
            spec = getattr(rule, "band_spec", None)
            self.assertIsNotNone(spec, f"{label}: severity rule missing band_spec")
            self.assertEqual(len(spec.segments), len(spec.edges) + 1,
                             f"{label}: segments must be one longer than edges")
            self.assertTrue(all(spec.edges[i] < spec.edges[i + 1]
                                for i in range(len(spec.edges) - 1)),
                            f"{label}: edges must be strictly ascending")
            self.assertTrue(all(s in SEVERITY for s in spec.segments),
                            f"{label}: bad segment token in {spec.segments}")
            self.assertIn(getattr(rule, "band_tag", None), reasons.BAND_WHY,
                          f"{label}: no BAND_WHY entry for tag {getattr(rule,'band_tag',None)}")


class TestDriftLock(unittest.TestCase):
    def test_every_edge_flips_where_the_descriptor_says(self):
        probed = 0
        for label, rule in _all_rules():
            spec = getattr(rule, "band_spec", None)
            if not spec or not spec.probe:
                continue
            for i, e in enumerate(spec.edges):
                eps = max(abs(e), 1.0) * 1e-4
                below = rule(bands.synth_obs(spec.kind, e - eps))[1]
                above = rule(bands.synth_obs(spec.kind, e + eps))[1]
                self.assertEqual(below, _cap(spec.segments[i], spec.cap),
                                 f"{label}: just below edge {e} expected "
                                 f"{spec.segments[i]}, rule returned {below}")
                self.assertEqual(above, _cap(spec.segments[i + 1], spec.cap),
                                 f"{label}: just above edge {e} expected "
                                 f"{spec.segments[i + 1]}, rule returned {above}")
                probed += 1
        self.assertGreater(probed, 50, "expected to probe the whole severity roster")


class TestNoOrphanProse(unittest.TestCase):
    def test_band_why_keys_match_tags_in_use(self):
        tags = {getattr(rule, "band_tag", None)
                for _, rule in _all_rules() if getattr(rule, "band_spec", None)}
        tags.discard(None)
        self.assertEqual(set(reasons.BAND_WHY), tags,
                         "BAND_WHY keys must exactly match the band_tags in use")


if __name__ == "__main__":
    unittest.main()
