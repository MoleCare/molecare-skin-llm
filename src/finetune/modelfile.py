"""What Ollama actually serves, made explicit.

An Ollama Modelfile starts with `FROM`. Two forms matter here:

- `FROM llama3.2:1b` (an Ollama tag): the **stock base model** with this
  project's system prompt. The LoRA is not applied. Useful as a baseline,
  misleading if presented as the fine-tune.
- `FROM ../fused/skincare-qa/skincare-qa-q8_0.gguf`: the **fused, fine-tuned
  weights** converted to GGUF. This is the model the training produced.

These helpers decide which form to write and say so in plain words, so a
Modelfile can never quietly serve the wrong thing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

GGUF_SUFFIX = ".gguf"


@dataclass(frozen=True)
class ModelfileSource:
    """`kind` is "gguf" (fine-tune applied) or "base" (stock model + prompt)."""

    kind: str
    ref: str

    @property
    def fine_tune_applied(self) -> bool:
        return self.kind == "gguf"


def find_gguf(fused_path: Path) -> Path | None:
    """Newest GGUF file in the fused directory, or None."""
    if not fused_path.is_dir():
        return None
    candidates = sorted(
        (p for p in fused_path.iterdir() if p.suffix == GGUF_SUFFIX and p.is_file()),
        key=lambda p: p.stat().st_mtime,
    )
    return candidates[-1] if candidates else None


def source_for(ollama_base: str, gguf: Path | None, modelfile_dir: Path) -> ModelfileSource:
    """Pick the FROM value. A GGUF path is written relative to the Modelfile,
    which is how Ollama resolves it."""
    if gguf is None:
        return ModelfileSource(kind="base", ref=ollama_base)
    rel = os.path.relpath(gguf.resolve(), modelfile_dir.resolve())
    if not rel.startswith("."):
        rel = f"./{rel}"
    return ModelfileSource(kind="gguf", ref=rel)


def render_modelfile(source: ModelfileSource, system: str) -> str:
    return f'FROM {source.ref}\n\nSYSTEM """\n{system.strip()}\n"""\n'


def serving_note(source: ModelfileSource, model_name: str) -> str:
    """One sentence for the terminal and the README about what `ollama run
    <model_name>` will answer with."""
    if source.fine_tune_applied:
        return (
            f"{model_name}: Ollama will serve the fused fine-tuned weights from "
            f"{source.ref}."
        )
    return (
        f"{model_name}: Ollama will serve the STOCK base model {source.ref} with the "
        "system prompt only. The LoRA is NOT applied. Run fuse_and_export.py "
        "--gguf to serve the fine-tune."
    )
