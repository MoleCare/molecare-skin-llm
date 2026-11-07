#!/usr/bin/env python3
"""Tiny HTTP sidecar: Ollama generates, the skincare harness decides.

  PYTHONPATH=src python scripts/serve.py
  curl -s localhost:8080/health
  curl -s localhost:8080/v1/skincare-qa -d '{"prompt":"what is ABCDE?"}' -H 'content-type: application/json'
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from finetune.models import SPECS  # noqa: E402
from harness.fallbacks import fallback_for  # noqa: E402
from harness.ollama_generate import OllamaGenerate  # noqa: E402
from harness.run import complete  # noqa: E402
from harness.skincare import SkincareGuard  # noqa: E402


def _routes():
    skin = SPECS["skincare-qa"]
    return {
        "/v1/skincare-qa": (
            OllamaGenerate(skin.ollama_base, skin.system),
            SkincareGuard(),
            fallback_for,
        ),
    }


# Filled in main() after argparse. Building routes at import constructs
# SkincareGuard, which needs skin-care-harness — CI does not have that,
# and --help must still work.
MAX_BODY_BYTES = 64 * 1024

ROUTES: dict = {}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _json(self, status: int, payload: dict) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/health":
            self._json(404, {"error": "not found"})
            return
        backends = {
            name: generate.healthy()
            for name, (generate, _, _) in (
                ("skincare-qa", ROUTES["/v1/skincare-qa"]),
            )
        }
        self._json(200, {"ok": True, "ollama": backends, "models": {
            name: {
                "ollama": spec.ollama_base,
                "hf": f"https://huggingface.co/{spec.hf_repo}",
                "ram_mb": spec.ram_mb,
            }
            for name, spec in SPECS.items()
        }})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        route = ROUTES.get(path)
        if route is None:
            self._json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length") or "0")
        if length > MAX_BODY_BYTES:
            # Refuse before reading. Content-Length is attacker-controlled, so
            # rfile.read(length) on an unchecked value is an allocation the
            # client chooses the size of.
            self._json(413, {"error": "request body too large"})
            return
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._json(400, {"error": "invalid json"})
            return
        prompt = (body.get("prompt") or "").strip()
        if not prompt:
            self._json(400, {"error": "prompt required"})
            return
        red_flags = list(body.get("red_flags") or [])
        generate, guard, fallback = route
        try:
            outcome = complete(generate, guard, fallback, prompt, red_flags=red_flags)
        except RuntimeError as exc:
            self._json(502, {"error": str(exc)})
            return
        self._json(
            200,
            {
                "text": outcome.output,
                "verdict": outcome.verdict,
                "fallback": outcome.fallback,
                "findings": [
                    {"rule_id": f.rule_id, "severity": f.severity, "excerpt": f.excerpt}
                    for f in outcome.findings
                ],
                "ruleset": outcome.ruleset_version,
            },
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "HTTP sidecar. Binds 127.0.0.1:8080 by default -- this server has "
            "no authentication, so exposing it needs a deliberate --host. "
            "A port number as the first argument still works."
        )
    )
    parser.add_argument(
        "port",
        nargs="?",
        type=int,
        default=8080,
        help="TCP port (default: 8080)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("HARNESS_HOST", "127.0.0.1"),
        help="bind address (default: 127.0.0.1, or $HARNESS_HOST)",
    )
    args = parser.parse_args()
    host, port = args.host, args.port
    ROUTES.clear()
    ROUTES.update(_routes())
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"harness listening on http://{host}:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
