# Clinical Safety Demo

This is not clinical decision support.

This demo shows how Agent Pidgin can represent a semantic safety contract for text handling. It demonstrates schema validation, policy enforcement, catalog resolution, and receipts for safety-oriented primitives.

The contract does not diagnose, treat, triage, or recommend care.

Demo flow:

1. A sample note exists as ordinary text.
2. A Pidgin contract requests safety and annotation primitives.
3. Agent Pidgin resolves the contract into an auditable implementation plan.
4. Receipts show what each pointer meant at resolution time.

The resolved implementation strings are plan data. They are not executed by default.

Run:

```bash
PYTHONPATH=src python examples/clinical_safety_demo/resolve_demo.py
```
