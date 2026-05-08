# Contract Discovery Experiments

This directory contains the first deterministic proof suite for Agent Pidgin contract discovery.

It tests whether messy workflow instructions contain hidden semantic obligations that should become explicit contracts before an agent or workflow system acts.

## Pain Finder

```bash
PYTHONPATH=src python3 scripts/run_pain_finder.py examples/contract_discovery/messy_workflow_examples.csv
```

The output scores each row from 0-16 and recommends whether it should become a candidate Pidgin contract.

## Full Proof Suite

```bash
PYTHONPATH=src python3 scripts/run_contract_discovery_experiments.py
```

The full suite checks:

- corpus pain: do messy instructions contain enough high-scoring contract candidates?
- contract lift: did conversion expose assumptions, validation points, safety constraints, receipts, reproducibility, or catalog gaps?
- raw-agent vs. contract-guided behavior: did contracts reduce missed requirements and unsafe omissions while increasing audit artifacts?
- catalog gaps: did strong examples reveal reusable semantic pointers the catalog should support?
- human reaction: did reviewers find the contract clarifying more often than bureaucratic?
- tiny local model readiness: are domains repetitive and schema-stable enough for a future Nanowhale-style intake compiler trial?

This is deliberately deterministic. Nanowhale or another tiny local model may later propose candidate contracts, but only after this proof-of-pain and proof-of-lift path shows that contract discovery is useful.
