---
name: memory-log
description: Format and rules for saving a decision to the sizing run's memory. Use it every time an agent records its reasoning, a prediction or a result.
---

# Memory log

Your task gives a memory folder and an entry prefix, for example `runs/run1/` and `refiner_r2`.
Save each entry as a NEW file named `<prefix>_<k>.md`, with k = 1, 2, 3, ... Never overwrite a file.

Each entry contains:

- `agent`: your `name` from your agent file, exactly, not a job description
- `simulator_calls`: the last `get_status` value plus your `simulate` calls since then (0 if you have no MCP tools)
- `outcome`: what was measured, compared with the exact ranges you wrote in your previous prediction, and whether each was correct ("none" for your first entry). Never restate a prediction differently afterwards
- Keep each entry under about 150 words, and write `design` on one line. Every entry is resent to the model, so long entries cost tokens
- `reasoning`: why you act, using circuit theory and measured numbers, at most 3 sentences
- `action`: what you do next
- `prediction`: the measurable result you expect, with direction and rough size
- `design`: the full parameters you are about to simulate

## Order
Write the entry BEFORE the action it describes, and never include that action's result in it.
The result goes in the `outcome` of your NEXT entry, together with the measured specs and reward.
After your last simulation, write one closing entry with that `outcome`, and `action: stop`.

`simulate` results are not stored in any CSV, so every simulated design and its result must appear in an entry.

Label numbers as `measured` or `estimate`. If a write fails, say so in your reply.
