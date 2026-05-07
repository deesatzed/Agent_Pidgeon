# Autonomous Agent Flight Recorder Demo

This demo explores Agent Pidgeon as an Autonomous Agent Flight Recorder, or AAFR.

AAFR is not an execution engine. It is a replayable semantic audit layer around agent behavior. It records goals, memory/context changes, proposed tool calls, policy findings, semantic diffs, and receipt IDs so operators can inspect what changed before an autonomous agent acts.

## Run

```bash
PYTHONPATH=src python3 examples/agent_flight_recorder_demo/run_flight_recorder.py
```

Full JSON:

```bash
PYTHONPATH=src python3 examples/agent_flight_recorder_demo/run_flight_recorder.py --json
```

## Demo Story

1. A support agent receives a safe goal: create an internal ticket and do not email the customer without review.
2. The agent proposes a safe internal tool call wrapped in a Pidgeon semantic contract.
3. Pidgeon validates schema, checks policy, resolves trusted pointers, and records receipt IDs.
4. A subtle memory/context update changes the operating boundary.
5. Pidgeon detects that memory guardrails were weakened without approval.
6. The agent proposes an external email action.
7. Pidgeon compares the new contract with the safe contract, sees guardrails removed, sees an unpinned artifact revision, and records a blocked event.

The "wow" moment is the replay: the model's proposed action can sound harmless while the flight recorder shows exactly where semantic intent drifted.

## Hardening Checks

This showpiece now exercises failure cases directly:

- event hash chaining with a top-level trace hash
- memory guardrail weakening detection
- high-risk semantic drift blocking
- control guardrail removal detection
- policy failure for unpinned revisions

## Boundary

This is not hardware-level tamper-proof logging. It is the deterministic semantic layer that can make runtime logs meaningful: contract hashes, policy decisions, semantic diffs, catalog-backed resolution, and receipts.
