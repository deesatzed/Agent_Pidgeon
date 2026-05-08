# Domain Boundary Benchmarks

Domain-boundary guarding is the reusable Agent Pidgin feature.

The supplement-coach benchmark in `examples/supplement_coach/` is one fixture set and a possible seed for a separate future product. It should not be treated as the only product direction.

Reusable commands:

```bash
agent-pidgin guard-prompt prompt.txt --domain-policy policy.json --json
agent-pidgin benchmark-domain-policy policy.json cases.jsonl --json
```

Reusable measurements:

- status accuracy
- autonomy-tier accuracy
- unsafe-prompt catch rate

The intended pattern applies to focused AI apps such as legal information bots, finance education bots, tutoring tools, HR assistants, customer-support agents, and supplement education tools.
