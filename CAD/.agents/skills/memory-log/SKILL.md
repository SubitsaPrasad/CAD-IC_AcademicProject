---
name: memory-log
description: Format and rules for saving a decision to the sizing run's memory. Use it every time an agent records its reasoning, a prediction or a result.
---

# Memory log

Your task gives a memory folder and an entry prefix, for example `runs/run1/` and `refiner_r2`.
Save each entry as a NEW file named `<prefix>_<k>.md`, with k = 1, 2, 3, ... Never overwrite a file.

Never report a result unless a tool returned it, and quote `simulator_calls` from `get_status` in your reply. Do not end your turn before your closing entry is saved: a text reply is read as your final report.

Call cad tools with call_mcp_tool: ServerName `cad`, ToolName, and Arguments such as `simulate` {"parameters": {...}}, `get_status` {"k": 1}, `warmup` {"n_steps": 100}, `train` {"n_steps": 100}.

Each entry contains:

- `agent`: your `name` from your agent file, exactly, not a job description
- `simulator_calls`: the last `get_status` value plus your `simulate` calls since then (0 if you have no MCP tools)
- `outcome`: what was measured, compared with the exact ranges you wrote in your previous prediction: give the count correct and list only the wrong ones ("none" for your first entry). Never restate a prediction differently afterwards
- Keep each entry under about 100 words, and write `design` on one line. Every entry is resent to the model, so long entries cost tokens
- `reasoning`: why you act, using circuit theory and measured numbers, at most 3 sentences
- `action`: what you do next
- `prediction`: the measurable result you expect, with direction and rough size
- `design`: the ID and full parameters of the design you are about to simulate

## Design IDs
Each simulated design gets the ID `D<n>`, where n is `simulator_calls` after that simulation. A rejected design gets no ID. Use IDs whenever you refer to a design, and start each `outcome` with the ID it belongs to, for example `D7: measured ...`. Never name a design after an entry file.

## Order
Write the entry BEFORE the action it describes, and never include that action's result in it. Send the entry and `simulate` in the same step, entry first, to save a turn.
The result goes in the `outcome` of your NEXT entry, together with the measured specs and reward.
After your last simulation, write one closing entry with that `outcome`, and `action: stop`.

`simulate` results are not stored in any CSV, so every simulated design and its result must appear in an entry.

Label numbers as `measured` or `estimate`. If a write fails, say so in your reply.
