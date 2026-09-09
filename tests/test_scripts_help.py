"""--help on train, serve, and chat (issue #8). No model, no network."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _help(script: str) -> str:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise AssertionError(proc.stderr or proc.stdout)
    return proc.stdout


class ScriptsHelpTest(unittest.TestCase):
    def test_serve_help_names_host_and_port(self) -> None:
        text = _help("serve.py")
        self.assertIn("8080", text)
        # The default bind must stay loopback. This server has no
        # authentication, so a 0.0.0.0 default would expose it to the network
        # for anyone following the README on a cloud VM.
        self.assertIn("127.0.0.1", text)
        self.assertNotIn("default: 0.0.0.0", text)

    def test_train_help(self) -> None:
        text = _help("train.py")
        self.assertIn("--iters", text)
        self.assertIn("--resume", text)

    def test_fuse_help_offers_gguf(self) -> None:
        text = _help("fuse_and_export.py")
        self.assertIn("--gguf", text)
        self.assertIn("--convert-script", text)
        self.assertIn("NOT applied", text)

    def test_chat_help(self) -> None:
        text = _help("chat.py")
        self.assertIn("prompt", text)
        self.assertIn("--red-flag", text)

    def test_serve_help_without_a_home_harness(self) -> None:
        """CI has no skin-care-harness under $HOME. --help must still print."""
        env = os.environ.copy()
        env["HOME"] = "/tmp/no-home-for-ci"
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "serve.py"), "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("8080", proc.stdout)


if __name__ == "__main__":
    unittest.main()
