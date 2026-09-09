#!/usr/bin/env python3
"""Fuse LoRA adapters, optionally convert to GGUF, and write an Ollama Modelfile.

What Ollama ends up serving depends on the Modelfile's FROM line:

  FROM llama3.2:1b                -> stock base + system prompt (LoRA NOT applied)
  FROM ../fused/<name>/<x>.gguf   -> the fused, fine-tuned weights

Without --gguf this script writes the first form (or reuses a GGUF it finds in
the fused directory) and says so on stderr. With --gguf it fuses de-quantized,
converts with llama.cpp's convert_hf_to_gguf.py, and writes the second form.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from finetune.modelfile import find_gguf, render_modelfile, serving_note, source_for  # noqa: E402
from finetune.models import SPECS  # noqa: E402

MODELFILES = ROOT / "modelfiles"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("model", choices=sorted(SPECS))
    parser.add_argument(
        "--gguf",
        action="store_true",
        help="fuse de-quantized and convert to GGUF so Ollama serves the fine-tune, not the base",
    )
    parser.add_argument(
        "--convert-script",
        default=os.environ.get("LLAMA_CPP_CONVERT") or shutil.which("convert_hf_to_gguf.py"),
        help="path to llama.cpp's convert_hf_to_gguf.py (default: $LLAMA_CPP_CONVERT or PATH)",
    )
    parser.add_argument("--outtype", default="q8_0", help="GGUF quantisation passed to the converter (default q8_0)")
    parser.add_argument("--skip-fuse", action="store_true", help="reuse the existing fused directory")
    parser.add_argument(
        "--ollama",
        action="store_true",
        help="ollama create <name> from the Modelfile",
    )
    parser.add_argument("--hf", action="store_true", help="upload fused weights to Hugging Face (YauhenBichel/…)")
    parser.add_argument("--public", action="store_true", help="with --hf, make the Hugging Face repo public")
    return parser.parse_args(argv)


def fuse(spec, dequantize: bool) -> None:
    fuse_bin = shutil.which("mlx_lm.fuse")
    if not fuse_bin:
        sys.exit("mlx_lm.fuse not on PATH")
    spec.fused_path.mkdir(parents=True, exist_ok=True)
    cmd = [
        fuse_bin,
        "--model",
        spec.mlx_base,
        "--adapter-path",
        str(spec.adapter_path),
        "--save-path",
        str(spec.fused_path),
    ]
    if dequantize:
        # GGUF conversion wants full-precision HF tensors, not MLX 4-bit blocks.
        cmd.append("--de-quantize")
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd, cwd=ROOT)


def convert_to_gguf(spec, convert_script: str | None, outtype: str) -> Path:
    if not convert_script or not Path(convert_script).is_file():
        sys.exit(
            "convert_hf_to_gguf.py not found. Clone https://github.com/ggml-org/llama.cpp and pass "
            "--convert-script /path/to/llama.cpp/convert_hf_to_gguf.py (or set LLAMA_CPP_CONVERT)."
        )
    out = spec.fused_path / f"{spec.name}-{outtype}.gguf"
    cmd = [sys.executable, str(convert_script), str(spec.fused_path), "--outfile", str(out), "--outtype", outtype]
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd, cwd=ROOT)
    return out


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    spec = SPECS[args.model]

    if not args.skip_fuse:
        fuse(spec, dequantize=args.gguf)

    gguf = convert_to_gguf(spec, args.convert_script, args.outtype) if args.gguf else find_gguf(spec.fused_path)

    MODELFILES.mkdir(parents=True, exist_ok=True)
    modelfile = MODELFILES / args.model
    source = source_for(spec.ollama_base, gguf, MODELFILES)
    modelfile.write_text(render_modelfile(source, spec.system), encoding="utf-8")
    print("wrote", modelfile)
    print(serving_note(source, args.model), file=sys.stderr)

    if args.ollama:
        ollama = shutil.which("ollama")
        if not ollama:
            sys.exit("ollama not on PATH")
        subprocess.check_call([ollama, "create", args.model, "-f", str(modelfile)])

    if args.hf:
        from finetune.huggingface_store import push_folder, require_token

        url = push_folder(spec, spec.fused_path, private=not args.public, token=require_token())
        print(url)


if __name__ == "__main__":
    main()
