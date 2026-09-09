---
license: llama3.2
base_model: meta-llama/Llama-3.2-1B-Instruct
library_name: mlx
tags:
  - mlx
  - lora
  - llama
  - skin-health
  - not-a-medical-device
language:
  - en
---

# skincare-qa-1b

LoRA-fused **Llama-3.2-1B-Instruct** (4-bit MLX) for educational skin-health Q&A.
Owned by [YauhenBichel](https://huggingface.co/YauhenBichel).

**Not a medical device.** It must not diagnose a person's lesion. Serve only
behind MoleCare [skin-care-harness](https://github.com/MoleCare/skin-care-harness).
Training text comes from [molecare-mcp](https://github.com/MoleCare/molecare-mcp)
knowledge, not a parallel medical KB.

## Use

```python
from mlx_lm import load, generate

model, tokenizer = load("YauhenBichel/skincare-qa-1b")
```

Base weights: `meta-llama/Llama-3.2-1B-Instruct` (Llama 3.2 Community License).
You still need Meta's license grant to use Llama weights.

## Training data

Generated, not scraped. `scripts/build_data.py` turns two MoleCare sources into
question–answer pairs with the same system prompt on every example:

- `molecare-mcp/src/resources/medical-kb.ts` — term, definition, details and
  significance for each skin-health concept, rewritten into educational voice
  (for example "benign moles" becomes "typical moles").
- `molecare-webapp` FAQ and chatbot copy.

| Split | Examples |
|---|---|
| train | 52 |
| valid | 8 |
| test | 8 |

Every answer is screened by MoleCare `skin-care-harness` before it is written;
the build aborts if any answer would be blocked. No patient data, no photos,
no user conversations. The set is small and templated: it teaches tone and
boundaries, not knowledge the base model lacks.

## Evaluation

No held-out benchmark has been published yet. `valid` and `test` come from the
same generator as `train`, so a good loss on them says the model learned the
template, not that it is a better skin-health assistant. Safety is not a
property of these weights: it is enforced at serving time by
`skin-care-harness`, which blocks a diagnosis or false reassurance whichever
model produced it. Treat any accuracy claim about this model as unsupported
until an independent evaluation is added.

## What is served

`scripts/fuse_and_export.py` writes the Ollama Modelfile and prints what it
points at:

| Modelfile `FROM` | What answers |
|---|---|
| `llama3.2:1b` (default without `--gguf`) | the **stock** Llama-3.2-1B with this system prompt; the LoRA is not applied |
| `../fused/skincare-qa/skincare-qa-q8_0.gguf` (with `--gguf`) | the fused fine-tuned weights |

The MLX weights on this Hub repo are for `mlx_lm`; Ollama needs the GGUF form.
