# MCP Integration

MCP is the tool/resource layer. Agent Pidgin can expose resolver behavior through MCP tools.

Recommended mapping:

- `resolve_pidgin_message` as an MCP tool
- `list_pidgin_catalog` and `show_pidgin_pointer` as read-only catalog metadata tools
- catalogs as MCP resources in a future adapter
- receipts as structured tool output
- policies as server-side guardrails

Server-mode policy can be enabled with:

```bash
export AGENT_PIDGIN_ENFORCE_POLICY=1
export AGENT_PIDGIN_POLICY_PATH=policies/default_policy.json
```

Custom catalogs can be selected with:

```bash
export AGENT_PIDGIN_CATALOGS="catalogs/core.json:catalogs/agent_ops.json"
```

MCP tools must return structured output:

```json
{
  "status": "resolved",
  "resolution": {
    "target_language": "python",
    "resolved_steps": [],
    "receipts": []
  },
  "policy_findings": []
}
```

Errors should also be structured and must not expose raw tracebacks to clients.
