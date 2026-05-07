# Parallel Work And LLM-Assisted Authoring

This document explains how Agent Pidgin work can be parallelized and where LLM-assisted authoring fits.

## Parallel Processing

Agent Pidgin has several independent workstreams that can run in parallel because they touch different parts of the system.

Good parallel tracks:

- Catalog work: add or review semantic pointers in JSON catalogs.
- Policy work: tune policy rules and policy tests.
- Schema work: evolve message, catalog, and receipt schemas.
- Docs/examples: improve quickstarts, diagrams, A2A examples, MCP examples, and clinical safety demos.
- Verification: run unit tests, lint, semantic diff checks, and example smoke tests.
- Adapter work: improve A2A/MCP wrappers as long as they call the same resolver boundary.

Avoid parallelizing edits that touch the same trust-critical path unless ownership is clear. The highest-conflict files are:

- `src/agent_pidgin/service.py`
- `src/agent_pidgin/resolver.py`
- `src/agent_pidgin/policy.py`
- `src/agent_pidgin/catalog.py`
- `src/agent_pidgin/schema_validator.py`

The safest pattern is:

```text
Core resolver changes
  -> focused unit tests
  -> docs/examples updated in parallel
  -> full verification
```

## LLM-Assisted Authoring

LLM-assisted authoring can improve the user experience without becoming part of the trust-critical path.

Useful features:

- Draft a Pidgin contract from a plain-language workflow description.
- Explain what an existing contract does in novice-friendly language.
- Suggest missing safety primitives, such as `agent.attach_receipts`.
- Compare two contracts and summarize risk in human language.
- Help catalog authors draft descriptions and type signatures.
- Generate starter tests and examples for a new pointer.

The initial implementation uses the OpenRouter Chat Completions-compatible endpoint through `OPENROUTER_API_KEY` and defaults to `qwen/qwen3.6-flash`.

The LLM must not decide what a pointer means. The source of truth remains:

```text
schema + policy + trusted catalog + catalog hash + receipt
```

Recommended user experience:

1. User describes intent in plain language.
2. LLM drafts a proposed contract.
3. Agent Pidgin validates the contract deterministically.
4. Policy check accepts or rejects it.
5. Resolver returns an implementation plan with receipts.
6. Human can inspect the contract, diff, and receipts before use.

The LLM is a drafting assistant. Agent Pidgin is the deterministic verifier and resolver.

CLI commands:

```bash
agent-pidgin author-contract request.txt \
  --artifact-repo waynesatz/agent-pidgin-data \
  --artifact-revision aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --json

agent-pidgin explain-contract examples/contracts/sample_message.json --json
agent-pidgin review-contract examples/contracts/sample_message.json --json
```

The API key must be provided in the environment and must not be stored in the repository.
