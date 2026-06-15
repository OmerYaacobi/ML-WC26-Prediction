"""Tests for fixture status normalization."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fixture_status import extract_scores, is_finished, normalize_fixture


class FixtureStatusTests(unittest.TestCase):
    def test_pending_no_scores(self):
        norm = normalize_fixture("pending", "2099-06-20T16:00:00Z", None)
        self.assertEqual(norm["status"], "pending")
        self.assertIsNone(norm["homeScore"])
        self.assertTrue(norm["bettable"])

    def test_pending_placeholder_zero_zero_not_finished(self):
        norm = normalize_fixture(
            "pending",
            "2099-06-20T16:00:00Z",
            {"home": 0, "away": 0},
        )
        self.assertEqual(norm["status"], "pending")
        self.assertIsNone(norm["homeScore"])
        self.assertIsNone(norm["awayScore"])
        self.assertTrue(norm["bettable"])

    def test_settled_with_ft_period(self):
        norm = normalize_fixture(
            "settled",
            "2026-06-14T17:00:00Z",
            {
                "home": 2,
                "away": 1,
                "periods": {"ft": {"home": 2, "away": 1}},
            },
        )
        self.assertEqual(norm["status"], "settled")
        self.assertEqual(norm["homeScore"], 2)
        self.assertEqual(norm["awayScore"], 1)
        self.assertFalse(norm["bettable"])

    def test_settled_zero_zero_is_valid(self):
        norm = normalize_fixture(
            "settled",
            "2026-06-14T17:00:00Z",
            {
                "home": 0,
                "away": 0,
                "periods": {"ft": {"home": 0, "away": 0}},
            },
        )
        self.assertEqual(norm["status"], "settled")
        self.assertEqual(norm["homeScore"], 0)
        self.assertEqual(norm["awayScore"], 0)

    def test_live_with_current_score(self):
        norm = normalize_fixture(
            "live",
            "2026-06-15T16:00:00Z",
            {"home": 1, "away": 0},
        )
        self.assertEqual(norm["status"], "live")
        self.assertEqual(norm["homeScore"], 1)
        self.assertFalse(norm["bettable"])

    def test_kickoff_passed_becomes_live_not_settled(self):
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        norm = normalize_fixture("pending", past, {"home": 0, "away": 0})
        self.assertEqual(norm["status"], "live")
        self.assertEqual(norm["homeScore"], 0)
        self.assertFalse(norm["bettable"])

    def test_extract_scores_distinguishes_live_from_ft(self):
        home, away, has_ft = extract_scores({"home": 0, "away": 0})
        self.assertEqual((home, away, has_ft), (0, 0, False))

        home, away, has_ft = extract_scores(
            {"home": 2, "away": 1, "periods": {"ft": {"home": 2, "away": 1}}}
        )
        self.assertEqual((home, away, has_ft), (2, 1, True))

    def test_is_finished(self):
        self.assertTrue(is_finished({"status": "settled", "homeScore": 1, "awayScore": 0}))
        self.assertFalse(is_finished({"status": "pending", "homeScore": 0, "awayScore": 0}))
        self.assertFalse(is_finished({"status": "live", "homeScore": 1, "awayScore": 0}))


if __name__ == "__main__":
    unittest.main()
