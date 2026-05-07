# Future Idea: CAD / Manufacturing Review Contracts

This is a future exploration idea, not part of the current showpiece.

Agent Pidgin could be useful for CAD and manufacturing review workflows where agents need to exchange precise, auditable instructions without silently changing files.

Example request:

```text
Prepare a CAD model for manufacturing review: validate units, normalize metadata, check material annotations, flag missing tolerances, require evidence, attach receipts, and request human review before export.
```

Possible future pointers:

```text
cad.units.validate
cad.metadata.normalize
cad.tolerance.flag_missing
cad.material.require_annotation
cad.export.require_review
agent.attach_receipts
agent.require_evidence
```

Why it might matter:

- CAD workflows often need strict versioning and review gates.
- Agents should not silently alter design files.
- A semantic contract could make design-review expectations explicit.
- Receipts could document what checks were requested and resolved.

This would require a new `catalogs/cad_ops.json` and should start as non-executing semantic contract resolution only.

