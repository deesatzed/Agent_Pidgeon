# Supplement Coach Domain Boundary Benchmark

This example measures whether Agent Pidgin can keep a focused supplement education assistant inside its safe lane.

It does not provide medical advice. It tests prompt-boundary classification:

- allowed supplement education
- constrained medication, pregnancy, chronic-condition, and dosing questions
- escalated urgent-symptom prompts
- blocked medication-change or disease-treatment prompts

Run:

```bash
PYTHONPATH=src python3 scripts/check_supplement_guard_benchmark.py
```

Expected result:

```json
{
  "status": "passed",
  "case_count": 10,
  "status_accuracy": 1.0,
  "tier_accuracy": 1.0,
  "unsafe_catch_rate": 1.0
}
```

This benchmark is intentionally small. Its purpose is to prove a measurable boundary-control loop before adding LLM-assisted extraction, response checking, or flight-recorder integration.
