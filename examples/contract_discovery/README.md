# Contract Discovery Example

This fixture is the first Pidgin Pain Finder dataset.

It tests whether messy workflow instructions contain hidden semantic obligations that should become explicit contracts before an agent or workflow system acts.

Run:

```bash
PYTHONPATH=src python3 scripts/run_pain_finder.py examples/contract_discovery/messy_workflow_examples.csv
```

The output scores each row from 0-16 and recommends whether it should become a candidate Pidgin contract.

This is deliberately deterministic. Nanowhale or another tiny local model may later propose candidate contracts, but only after this proof-of-pain step shows that contract discovery is useful.
