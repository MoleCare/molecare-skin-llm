"""Fixed replies when the guard blocks twice. Never invent a diagnosis or a secret."""

from collections.abc import Iterable

from harness.types import Finding

from finetune.systems import SKINCARE_DISCLAIMER

SKINCARE_FALLBACK = (
    "I can't tell you what this is — that needs someone to look at it. "
    "Book a GP or dermatologist if a mole is changing, bleeding, or worrying you. "
    f"{SKINCARE_DISCLAIMER}"
)


# Sun-safety misinformation (DG009) is about sun protection, not a mole, so the
# mole fallback reads as a non sequitur there.
SUN_SAFETY_FALLBACK = (
    "I can't help with that. Sunscreen, shade and clothing are recommended ways "
    "to protect skin from UV, and the NHS suggests sunscreen of at least SPF 30 "
    "with at least 4-star UVA protection. "
    "This is general information, not medical advice."
)

_BY_RULE = {"DG009": SUN_SAFETY_FALLBACK}


def fallback_for(findings: Iterable[Finding], default: str = SKINCARE_FALLBACK) -> str:
    """The fixed reply that fits the rule that blocked the draft."""
    for finding in findings:
        if finding.severity == "block" and finding.rule_id in _BY_RULE:
            return _BY_RULE[finding.rule_id]
    return default
