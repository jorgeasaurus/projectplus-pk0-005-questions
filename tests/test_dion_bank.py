"""Validation for the Dion bank import and review exclusions.

These checks keep loadable questions, counts, and provenance aligned.
They do not store removed question text.
"""

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REMOVED_AT_REVIEW = {
    "dion-f218d8cee0fb",
    "dion-27cbbb7d1a13",
    "dion-4d98e61005fb",
    "dion-69c8955c9ed8",
    "dion-72bf52dacb69",
    "dion-6b42ddf650a9",
    "dion-292c31a36a32",
    "dion-a699e5f05737",
    "dion-5576e5cad8b3",
    "dion-1283024cdd86",
    "dion-6c3661524ce1",
    "dion-6e2707175d12",
    "dion-f90b832ad519",
}

# Phrases that would teach a wrong rule if a coach loaded the item.
BLOCKED_EXPLANATION_PHRASES = (
    "Contingency reserves are separate from the project cost baseline",
    "expected value minus the planned value",
    "Voice and fingerprints are both things you have",
    "identifying information is included",
)


class DionBankTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dion = json.loads((ROOT / "dion.json").read_text())
        cls.questions = json.loads((ROOT / "questions.json").read_text())
        cls.rizwan = json.loads((ROOT / "rizwan.json").read_text())

    def test_existing_banks_unchanged_in_count(self):
        self.assertEqual(len(self.questions), 120)
        self.assertEqual(len(self.rizwan["questions"]), 189)

    def test_active_counts_match_questions_and_coverage(self):
        active = self.dion["questions"]
        self.assertEqual(len(active), 160)
        self.assertEqual(self.dion["importedQuestionCount"], 160)
        self.assertEqual(self.dion["activeQuestionCount"], 160)
        self.assertEqual(self.dion["load"]["activeAdditions"], 160)
        self.assertEqual(sum(self.dion["coverage"].values()), 160)
        self.assertEqual(self.dion["coverage"]["1.6"], 8)
        self.assertEqual(self.dion["coverage"]["1.7"], 4)
        self.assertEqual(self.dion["coverage"]["4.2"], 8)
        self.assertEqual(self.dion["coverage"]["1.8"], 0)

    def test_combined_load_count(self):
        combined = 120 + 189 + len(self.dion["questions"])
        self.assertEqual(combined, 469)
        self.assertEqual(self.dion["load"]["combinedWithExisting"], 469)
        readme = (ROOT / "README.md").read_text()
        notice = (ROOT / "NOTICE-dion.txt").read_text()
        self.assertIn("160 active", readme)
        self.assertIn("469", readme)
        self.assertIn("Thirteen reviewed", readme)
        self.assertIn("Thirteen reviewed", notice)

    def test_provenance_totals_still_account_for_supplied_rows(self):
        quarantined = self.dion["quarantined"]["count"]
        self.assertEqual(
            len(self.dion["questions"]) + len(self.dion["excluded"]) + quarantined,
            self.dion["supplierUniqueCount"],
        )
        self.assertEqual(self.dion["supplierUniqueCount"], 174)
        self.assertEqual(self.dion["excludedQuestionCount"], 13)
        self.assertIsNone(self.dion["license"])

    def test_reviewed_ids_are_excluded_and_not_loadable(self):
        active_ids = {item["id"] for item in self.dion["questions"]}
        excluded_ids = [item["id"] for item in self.dion["excluded"]]
        self.assertEqual(set(excluded_ids), REMOVED_AT_REVIEW)
        self.assertEqual(len(excluded_ids), len(set(excluded_ids)))
        self.assertTrue(REMOVED_AT_REVIEW.isdisjoint(active_ids))
        for item in self.dion["excluded"]:
            self.assertEqual(set(item), {"id", "upstreamId", "code", "reason"})
            self.assertTrue(item["reason"].startswith("Removed at review."))
            self.assertNotIn("question", item)
            self.assertNotIn("options", item)
            self.assertNotIn("explanation", item)
            self.assertNotIn("answer", item)
            self.assertEqual(item["id"], "dion-" + item["upstreamId"])

    def test_missing_chart_item_stays_out_of_questions(self):
        active_ids = {item["id"] for item in self.dion["questions"]}
        self.assertNotIn("dion-5057d10a0fa3", active_ids)
        held = self.dion["quarantined"]["items"]
        self.assertEqual([item["id"] for item in held], ["dion-5057d10a0fa3"])
        self.assertFalse(held[0]["enabled"])
        self.assertEqual(self.dion["load"]["read"], "questions")
        self.assertEqual(self.dion["load"]["doNotRead"], ["excluded", "quarantined"])

    def test_active_records_are_well_formed(self):
        seen = set()
        for item in self.dion["questions"]:
            self.assertNotIn(item["id"], seen)
            seen.add(item["id"])
            self.assertTrue(item["id"].startswith("dion-"))
            self.assertEqual(len(item["options"]), 4)
            self.assertIsInstance(item["answer"], int)
            self.assertGreaterEqual(item["answer"], 0)
            self.assertLess(item["answer"], 4)
            self.assertEqual(item["source"]["upstreamId"], item["id"].removeprefix("dion-"))
            self.assertNotIn(item["id"], REMOVED_AT_REVIEW)

    def test_blocked_explanations_are_not_loadable(self):
        for item in self.dion["questions"]:
            explanation = item["explanation"]
            for phrase in BLOCKED_EXPLANATION_PHRASES:
                self.assertNotIn(phrase, explanation, item["id"])
        self.assertNotIn(
            "dion-1283024cdd86",
            {item["id"] for item in self.dion["questions"]},
        )


if __name__ == "__main__":
    unittest.main()
