# Contributing

This tree trains two small LoRA models and wraps each in a deterministic
harness. It is **Apache-2.0**, easy to run locally, and meant for first-time
contributors — if you keep the safety rules below.

## The rule that is not negotiable (skincare-qa)

**This project must never produce, imply, or imitate a medical diagnosis.**

`skincare-qa` is educational skin-health Q&A. It is not a medical device.
Any change that moves an answer closer to "this lesion is / isn't melanoma"
will be declined, however good the code or the loss curve is.

Same table as [molecare-mcp](https://github.com/MoleCare/molecare-mcp):

| Fine | Not fine |
|---|---|
| "The ABCDE criteria describe asymmetry, border, colour, diameter, evolution." | "This mole scores 4/5 on ABCDE, likely melanoma." |
| "Irregular borders are one feature clinicians assess." | "Irregular border detected — seek urgent care." |
| A confidence on a **photo-quality** check ("too dark, retake") | A confidence used as a verdict on the person's mole |

New skincare training rows must pass MoleCare `skin-care-harness`
(`PYTHONPATH=src python scripts/build_data.py` fails on a `block`).

`skin-care-harness` is currently **private**, so if you are outside MoleCare you
cannot run that check yourself. Open the pull request anyway — a maintainer will
run it for you and paste the result. Please say in the PR that you could not run
it, so nobody assumes it passed.

## Getting set up (no cloud, no secrets)

The tests run on any operating system with **Python 3.10 or newer** and need
no packages, no GPU, no Ollama and no tokens:

```bash
git clone https://github.com/MoleCare/molecare-skin-llm.git
cd molecare-skin-llm
python3 -m unittest discover -s tests -q      # on Windows: py -m unittest discover -s tests -q
```

Two tests are skipped: they need the private skincare harness (see below).

Only **training** needs more: an Apple Silicon Mac, Python 3.13 (MLX does not
install on 3.14 yet) and `pip install -r requirements.txt` in a virtual
environment. Training downloads public 4-bit bases from `mlx-community/*`.

You do **not** need a Hugging Face token, Ollama, AWS, or a MoleCare API key
to run the tests.

### About the skincare harness tests

`skin-care-harness` is a **private** MoleCare repository. Cloning it will 404 for
external contributors, and the docs previously told you to clone it anyway — sorry.
Tracked in [#19](https://github.com/MoleCare/skincare-qa/issues/19).

Those tests **skip** when the checkout is missing, so `python -m unittest discover`
goes green without them. That is worth knowing before you trust a green run: the
`SkinGuard` tests are the ones covering the claim that the model cannot ship a
diagnosis, and they are exactly the ones that skip. See
[#10](https://github.com/MoleCare/skincare-qa/issues/10).

What you *can* run without it: the data loaders and training. That is most of
the repository.

If you are inside MoleCare, clone the harness next to this repository or set
`MOLECARE_ROOT` / `SKIN_CARE_HARNESS_PYTHON`. See `.env.example`.

## What you may add

- More **educational** Q&A pairs sourced from [molecare-mcp](https://github.com/MoleCare/molecare-mcp) knowledge, not from lesion photos
- Harness rules with **fixtures** (a fail string and a near-miss pass)
- Docs, CI, and eval prompts that never include a real skin photo

## What you must not add

- Patient photos, even as "fake" fixtures that are real pictures
- Hugging Face / cloud tokens, private keys, or production hostnames
- A keyword router on the **user** prompt that skips the harness
- Diagnostic labels from [google/derm-foundation](https://huggingface.co/google/derm-foundation) or molecare-ml into training text
- `curl … \| sh` examples that the python harness would block

## Before you open a pull request

- [ ] `python -m unittest discover -s tests -q` passes
- [ ] `PYTHONPATH=src python scripts/build_data.py` passes if you touched skincare pairs
- [ ] New medical answers include the educational disclaimer
- [ ] No secrets, real hostnames, or personal data
- [ ] No patient images

## Pull requests

One concern per PR. Say what a user can do now that they could not before.
Large refactors: open an issue first.

## Reporting security issues

Do **not** open a public issue. See [SECURITY.md](./SECURITY.md).

## Licence

By contributing you agree that your contributions are licensed under the
[Apache-2.0 licence](./LICENSE) that covers this project.
