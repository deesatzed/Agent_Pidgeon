# Agent Pidgin Showpiece Demo

This demo shows Agent Pidgin as a semantic contract resolver, not an execution engine.

The scenario is a clinical intake note preparation request. A sender asks for safe text preparation before another agent summarizes the note. Agent Pidgin turns the request into a compact semantic contract, validates it, checks policy, resolves pointers against trusted catalogs, and returns an auditable plan with receipts.

## Run Offline

```bash
PYTHONPATH=src python3 examples/showpiece_demo/run_showpiece.py --json
```

The offline path uses a deterministic authoring fixture, so it works without an API key.

## Run With OpenRouter

```bash
export OPENROUTER_API_KEY="..."
export OPENROUTER_MODEL="qwen/qwen3.6-flash"
PYTHONPATH=src python3 examples/showpiece_demo/run_showpiece.py --live-llm --json
```

The LLM helps draft a contract from plain language. It does not define pointer truth. The resolver still accepts only known catalog pointers, validates schema, applies policy, resolves against trusted catalogs, and attaches receipts.

If a live LLM draft contains no known catalog pointers, the demo records that rejection and falls back to the offline fixture so the trust-critical resolver path remains reproducible.

## What It Proves

- Compact semantic contracts can be authored from plain language.
- Unknown or missing semantic pointers do not become trusted behavior.
- Policy can flag unsafe provenance choices such as an unpinned artifact revision.
- A semantic diff can catch a safety-sensitive pointer removal.
- The resolver returns an implementation plan with catalog hashes, artifact revision, implementation hashes, and receipts.

## Novice Expectations

At the end of the demo, the app has not cleaned real patient text and has not executed code. It has produced a trustworthy plan: these are the exact semantic steps requested, these are the catalog entries they came from, this is the pinned artifact target, these are the policy findings, and these are the receipts proving how each step was resolved.
