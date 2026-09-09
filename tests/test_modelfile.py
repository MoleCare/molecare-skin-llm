"""The Modelfile must say what it serves: base + prompt, or the fine-tune."""

from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from finetune.modelfile import (  # noqa: E402
    ModelfileSource,
    find_gguf,
    render_modelfile,
    serving_note,
    source_for,
)


class ModelfileTest(unittest.TestCase):
    def test_base_tag_is_labelled_as_not_the_fine_tune(self) -> None:
        source = source_for("llama3.2:1b", None, Path("/repo/modelfiles"))
        self.assertEqual(source, ModelfileSource(kind="base", ref="llama3.2:1b"))
        self.assertFalse(source.fine_tune_applied)
        note = serving_note(source, "skincare-qa")
        self.assertIn("STOCK base model", note)
        self.assertIn("NOT applied", note)
        self.assertIn("--gguf", note)

    def test_gguf_is_referenced_relative_to_the_modelfile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gguf = root / "fused" / "skincare-qa" / "skincare-qa-q8_0.gguf"
            gguf.parent.mkdir(parents=True)
            gguf.write_bytes(b"GGUF")
            source = source_for("llama3.2:1b", gguf, root / "modelfiles")
        self.assertEqual(source.kind, "gguf")
        self.assertTrue(source.fine_tune_applied)
        self.assertEqual(source.ref, os.path.join("..", "fused", "skincare-qa", "skincare-qa-q8_0.gguf"))
        self.assertIn("fused fine-tuned weights", serving_note(source, "skincare-qa"))

    def test_render_is_a_valid_modelfile(self) -> None:
        text = render_modelfile(ModelfileSource("base", "llama3.2:1b"), "  Be kind.\n")
        self.assertTrue(text.startswith("FROM llama3.2:1b\n"))
        self.assertIn('SYSTEM """\nBe kind.\n"""\n', text)
        text = render_modelfile(ModelfileSource("gguf", "../fused/x/x.gguf"), "Be kind.")
        self.assertTrue(text.startswith("FROM ../fused/x/x.gguf\n"))

    def test_find_gguf_returns_the_newest_or_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fused = Path(tmp)
            self.assertIsNone(find_gguf(fused / "missing"))
            self.assertIsNone(find_gguf(fused))
            old = fused / "a.gguf"
            old.write_bytes(b"1")
            os.utime(old, (time.time() - 60, time.time() - 60))
            (fused / "weights.safetensors").write_bytes(b"x")
            new = fused / "b.gguf"
            new.write_bytes(b"2")
            self.assertEqual(find_gguf(fused), new)


if __name__ == "__main__":
    unittest.main()
