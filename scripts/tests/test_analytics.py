"""Tests for the Cloudflare Web Analytics beacon snippet (single source of truth)."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import analytics


class BeaconTagTests(unittest.TestCase):
    def test_includes_the_configured_token(self):
        self.assertIn(analytics.CF_BEACON_TOKEN, analytics.beacon_tag())

    def test_a_token_is_configured(self):
        self.assertTrue(analytics.CF_BEACON_TOKEN.strip())

    def test_is_deferred_so_it_never_blocks_render(self):
        self.assertIn("defer", analytics.beacon_tag())

    def test_points_at_the_cloudflare_beacon_cdn(self):
        self.assertIn("static.cloudflareinsights.com/beacon.min.js", analytics.beacon_tag())

    def test_is_marker_wrapped_for_idempotent_injection(self):
        tag = analytics.beacon_tag()
        self.assertTrue(tag.startswith(analytics.BEACON_START))
        self.assertTrue(tag.rstrip().endswith(analytics.BEACON_END))

    def test_token_param_overrides_the_default(self):
        self.assertIn("ZZZ", analytics.beacon_tag(token="ZZZ"))
        self.assertNotIn(analytics.CF_BEACON_TOKEN, analytics.beacon_tag(token="ZZZ"))
