import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from harness.run import complete
from harness.skincare import SkincareGuard

# Sun-safety myths spread online (AAD 2025 survey). The harness rule DG009
# blocks answers that endorse one. These tests hold the model's guard and its
# training data to that rule.
EVAL_SET = [json.loads(line) for line in (ROOT / "data/evals/sun-myths.jsonl").read_text().splitlines() if line]
SPLITS = ("train", "valid", "test")


def fires(outcome, rule_id: str) -> bool:
    return any(f.rule_id == rule_id for f in outcome.findings)


class SunMythsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            cls.guard = SkincareGuard()
        except (FileNotFoundError, ImportError) as exc:
            # Same contract as test_skincare_guard: CI fails, a contributor skips.
            if os.environ.get("SKIN_CARE_HARNESS_REQUIRED"):
                raise AssertionError(f"skin-care-harness could not be loaded: {exc}") from exc
            raise unittest.SkipTest(f"skin-care-harness not installed locally: {exc}") from exc

    def test_the_eval_set_has_every_field(self) -> None:
        self.assertGreaterEqual(len(EVAL_SET), 6)
        for case in EVAL_SET:
            self.assertEqual(set(case), {"myth", "question", "endorses", "corrects"})

    def test_an_answer_that_endorses_a_myth_is_blocked(self) -> None:
        for case in EVAL_SET:
            with self.subTest(myth=case["myth"]):
                outcome = self.guard.check(case["endorses"])
                self.assertTrue(fires(outcome, "DG009"), case["endorses"])
                self.assertEqual(outcome.verdict, "block")
                self.assertIsNone(outcome.output)

    def test_an_answer_that_corrects_a_myth_is_not_flagged(self) -> None:
        for case in EVAL_SET:
            with self.subTest(myth=case["myth"]):
                self.assertFalse(fires(self.guard.check(case["corrects"]), "DG009"), case["corrects"])

    def test_the_user_gets_the_fallback_instead_of_the_myth(self) -> None:
        case = EVAL_SET[0]
        outcome = complete(lambda _p: case["endorses"], self.guard, "SAFE FALLBACK", case["question"])
        self.assertTrue(outcome.fallback)
        self.assertEqual(outcome.output, "SAFE FALLBACK")

    def test_the_training_data_teaches_no_sun_myth(self) -> None:
        for split in SPLITS:
            for number, line in enumerate((ROOT / f"data/skincare-qa/{split}.jsonl").read_text().splitlines(), 1):
                for message in json.loads(line)["messages"]:
                    if message["role"] == "assistant":
                        with self.subTest(split=split, line=number):
                            self.assertFalse(fires(self.guard.check(message["content"]), "DG009"))


if __name__ == "__main__":
    unittest.main()
