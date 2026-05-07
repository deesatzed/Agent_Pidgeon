# LLM-Assisted Authoring

LLM-assisted authoring helps draft, explain, and review Pidgin contracts.

The LLM is not the source of truth. Agent Pidgin still validates schema, checks policy, resolves against trusted catalogs, and attaches receipts.

Set credentials outside the repo:

```bash
export OPENROUTER_API_KEY="..."
export OPENROUTER_MODEL="qwen/qwen3.6-flash"
```

Draft a contract:

```bash
agent-pidgin author-contract examples/llm_authoring/plain_language_request.txt \
  --artifact-repo waynesatz/agent-pidgin-data \
  --artifact-revision aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --json
```

Explain a contract:

```bash
agent-pidgin explain-contract examples/contracts/sample_message.json --json
```

Review a contract:

```bash
agent-pidgin review-contract examples/contracts/sample_message.json --json
```

Do not commit API keys, generated secrets, or live LLM outputs that contain private data.

