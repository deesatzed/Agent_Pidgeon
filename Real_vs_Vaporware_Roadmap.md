# Agent Pidgin: Reality vs. Potential & Production Roadmap

This document distinguishes verified functionality from planned potential. The project has moved beyond the original HF-mount/A2A proof of concept into a deterministic semantic resolver and Autonomous Agent Flight Recorder prototype.

---

## 1. Reality Check: What Actually Works (Verified)

These features have been implemented locally and are verified by the automated test suite (`tests/`).

*   **Semantic Contract Resolver:** Validates resolve messages, enforces policy, resolves trusted catalog pointers, and returns implementation plans with receipts.
*   **Trusted Catalogs:** Loads JSON catalogs for core, clinical-safety, and agent-operation pointers, with duplicate pointer detection and deterministic catalog hashes.
*   **Policy Enforcement:** Rejects unpinned revisions and unsupported artifact kinds, warns on raw execution, and requires receipts for sensitive pointers.
*   **Semantic Diffing:** Detects removed safety-sensitive pointers, removed control guardrails, artifact drift, target-language drift, and implementation changes.
*   **Resolution Receipts:** Records pointer, type signature, implementation hash, catalog ID/version/hash, artifact repo/revision, resolver version, timestamp, and receipt ID.
*   **Autonomous Agent Flight Recorder:** Records goals, memory updates, proposed tool calls, semantic diffs, policy findings, receipt IDs, and hash-chained trace events.
*   **Memory Guardrail Detection:** Blocks unapproved changes such as `external_email_allowed: false -> true` or `human_review_required: true -> false`.
*   **Trace Integrity:** Adds `previous_event_hash`, `event_hash`, and `trace_hash`, with validation that catches tampering after trace generation.
*   **Transport Surfaces:** Provides CLI commands, MCP-style wrappers, stdio sender coverage, and A2A JSON examples around the same resolver boundary.
*   **LLM-Assisted Authoring:** Supports OpenRouter/Qwen-assisted contract authoring, explanation, and review while keeping the deterministic resolver as the authority.

---

## 2. The "Vaporware" Gap (Current Potential)

These are documented goals or architectural directions that are not yet fully realized in the codebase.

*   **Production Trace Storage:** Trace hashes are tamper-evident in local JSON, but there is no append-only external store or signed trace root yet.
*   **OpenTelemetry Export:** Pidgin is not telemetry, but AAFR traces should be exportable into telemetry systems. That adapter is not implemented yet.
*   **Tool Result Observation:** The flight recorder currently records proposed calls, not downstream tool results.
*   **Approval Model:** Approved memory writes use a simple `approved_by` string; production workflows need signed approvals and richer authority modeling.
*   **Catalog/Receipt Signatures:** Catalog hashes and receipt hashes exist, but signed catalogs and signed receipts are not implemented yet.
*   **Production Resource Limits:** The HF mount path still needs disk, process, timeout, and quota hardening before production use.

---

## 3. Mitigations for Scaling & Production Readiness

To bridge the gap between PoC and Production, the following architectural mitigations are recommended:

### A. Scaling & Concurrency
*   **Trace Export:** Add OpenTelemetry-compatible span export while keeping Pidgin as the semantic authority.
*   **Append-Only Trace Sink:** Store trace roots in an append-only log or signed audit sink.
*   **HTML Replay UI:** Build a human-readable timeline for goals, memory changes, proposed calls, diffs, policy findings, and receipt IDs.

### B. Security & Resource Protection
*   **Signed Catalogs and Receipts:** Sign catalog roots and receipt bundles.
*   **Repository Whitelisting:** Keep strict `allowed_repos` policy configuration for production deployments.
*   **Process Guardrails:** Add strict wall-clock timeouts and memory limits to any real mount or resolver subprocess path.
*   **Disk Space Verification:** Implement pre-mount checks before artifact downloads.

### C. Operational Reliability
*   **Golden Trace Fixtures:** Preserve stable AAFR traces for regression testing and demos.
*   **Tool Result Events:** Add event types for observed tool results, failures, and rollbacks.
*   **Health Check MCP Tool:** Add a dedicated tool for external monitoring systems to verify resolver readiness and catalog/policy load state.

---
**Status:** The current repo is a working proof of concept for semantic resolution and flight-recorder traces. It is not yet a production observability or audit platform.
