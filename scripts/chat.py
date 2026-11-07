#!/usr/bin/env python3
"""Ask a model through its harness (Ollama generate → guard → fallback)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from finetune.models import SPECS  # noqa: E402
from harness.fallbacks import fallback_for  # noqa: E402
from harness.ollama_generate import OllamaGenerate  # noqa: E402
from harness.run import complete  # noqa: E402
from harness.skincare import SkincareGuard  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Ask one model through its harness. "
            "Pass the model name, then the prompt. Optional --red-flag may repeat."
        )
    )
    parser.add_argument("model", choices=sorted(SPECS))
    parser.add_argument("prompt")
    parser.add_argument("--red-flag", action="append", default=[])
    args = parser.parse_args()
    spec = SPECS[args.model]

    guard: object = SkincareGuard()
    fallback = fallback_for

    generate = OllamaGenerate(spec.ollama_base, spec.system)
    outcome = complete(
        generate,
        guard,  # type: ignore[arg-type]
        fallback,
        args.prompt,
        red_flags=args.red_flag,
    )
    print(outcome.output or "")
    meta = {
        "verdict": outcome.verdict,
        "fallback": outcome.fallback,
        "ruleset": outcome.ruleset_version,
        "findings": [f.rule_id for f in outcome.findings],
    }
    print(json.dumps(meta), file=sys.stderr)


if __name__ == "__main__":
    main()
