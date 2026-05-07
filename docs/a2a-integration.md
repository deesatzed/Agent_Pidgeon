# A2A Integration

A2A is transport and collaboration. Agent Pidgin is semantic meaning and provenance.

Recommended shape:

```text
A2A Task
  -> Pidgin semantic contract artifact
      -> local Agent Pidgin resolver
          -> receipts and implementation plan
```

Agent Pidgin should not become an A2A clone. A2A can carry a Pidgin contract as task data or an artifact, but resolution still happens through `PidginReceiverService`.

See `examples/a2a_wrapper/` for a JSON-first example with no SDK dependency.

