"""Generate → guard → regenerate once → fixed fallback.

Matches MoleCare example 02: the guard never edits its way out of a block.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from harness.types import Finding, Outcome


class Guard(Protocol):
    def check(self, text: str, red_flags: list[str] | None = None) -> Outcome: ...


def complete(
    generate: Callable[[str], str],
    guard: Guard,
    fallback: str | Callable[[tuple[Finding, ...]], str],
    prompt: str,
    *,
    red_flags: list[str] | None = None,
    attempts: int = 2,
) -> Outcome:
    last: Outcome | None = None
    for _ in range(attempts):
        draft = generate(prompt)
        outcome = guard.check(draft, red_flags)
        if outcome.output is not None:
            return outcome
        last = outcome
    assert last is not None
    text = fallback(last.findings) if callable(fallback) else fallback
    return Outcome(
        verdict="block",
        output=text,
        findings=last.findings,
        ruleset_version=last.ruleset_version,
        fallback=True,
    )
