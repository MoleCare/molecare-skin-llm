import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from harness.skincare import SkincareGuard
from harness.run import complete


class SkincareGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            cls.guard = SkincareGuard()
        except (FileNotFoundError, ImportError) as exc:
            # A skipped safety test is not a passing safety test. CI sets
            # SKIN_CARE_HARNESS_REQUIRED so a missing harness fails loudly there;
            # a contributor without the private checkout still gets a skip.
            if os.environ.get("SKIN_CARE_HARNESS_REQUIRED"):
                raise AssertionError(
                    "skin-care-harness is required in this environment but could not "
                    f"be loaded: {exc}. Set SKIN_CARE_HARNESS_PYTHON to its packages/python."
                ) from exc
            raise unittest.SkipTest(
                f"skin-care-harness not installed locally: {exc}"
            ) from exc

    def test_pass_abcde_education(self) -> None:
        draft = (
            "ABCDE is an educational checklist: asymmetry, border, colour, "
            "diameter, evolution. A clinician interprets what you notice. "
            "Educational only — not a diagnosis."
        )
        out = self.guard.check(draft)
        self.assertNotEqual(out.verdict, "block")
        self.assertIsNotNone(out.output)

    def test_block_diagnosis(self) -> None:
        out = self.guard.check("From what you describe, this is a melanoma.")
        self.assertEqual(out.verdict, "block")
        self.assertIsNone(out.output)

    def test_block_false_reassurance(self) -> None:
        out = self.guard.check("There's nothing to worry about here.")
        self.assertEqual(out.verdict, "block")
        self.assertIsNone(out.output)

    def test_complete_uses_fallback_when_blocked(self) -> None:
        outcome = complete(
            lambda _p: "That's definitely benign.",
            self.guard,
            "SAFE FALLBACK",
            "is this fine?",
        )
        self.assertTrue(outcome.fallback)
        self.assertEqual(outcome.output, "SAFE FALLBACK")


if __name__ == "__main__":
    unittest.main()


class FallbackChoiceTest(unittest.TestCase):
    """Runs without skin-care-harness: the choice of fallback is plain code."""

    def test_sun_safety_block_gets_the_sun_fallback(self) -> None:
        from harness.fallbacks import SKINCARE_FALLBACK, SUN_SAFETY_FALLBACK, fallback_for
        from harness.types import Finding

        dg009 = (Finding("DG102", "revise", ""), Finding("DG009", "block", "sunscreen causes"))
        self.assertEqual(fallback_for(dg009), SUN_SAFETY_FALLBACK)
        self.assertEqual(fallback_for((Finding("DG001", "block", "melanoma"),)), SKINCARE_FALLBACK)
        self.assertEqual(fallback_for(()), SKINCARE_FALLBACK)
        self.assertNotIn("mole", SUN_SAFETY_FALLBACK.lower())

    def test_complete_calls_a_fallback_function_with_the_findings(self) -> None:
        from harness.types import Finding, Outcome

        seen = []

        class Blocker:
            def check(self, text, red_flags=None):
                return Outcome("block", None, (Finding("DG009", "block", text),), "t")

        def pick(findings):
            seen.append(findings)
            return "PICKED"

        outcome = complete(lambda _p: "draft", Blocker(), pick, "q")
        self.assertTrue(outcome.fallback)
        self.assertEqual(outcome.output, "PICKED")
        self.assertEqual(seen[0][0].rule_id, "DG009")
        self.assertEqual(complete(lambda _p: "draft", Blocker(), "FIXED", "q").output, "FIXED")
