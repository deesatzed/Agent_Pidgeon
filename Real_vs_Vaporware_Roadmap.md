# Agent-Pidgin: Reality vs. Potential & Production Roadmap (2026-03-25)

This document provides a critical assessment of the current state of the **agent-pidgin** project, distinguishing between verified functionality and planned potential, and outlines the strategy for achieving production-grade stability and scale.

---

## 1. Reality Check: What Actually Works (Verified)

These features have been implemented, are under version control, and are verified by the automated test suite (`tests/`).

*   **Hybrid Protocol Engine:** The "brains" of the protocol. It correctly handles the precedence logic between legacy `dataset_*` fields and the new `artifact` model.
*   **MCP Stdio Transport:** The project successfully communicates as an MCP server over `stdio` using `FastMCP`. Handshake and resolution round-trips are fully functional.
*   **Secure Input Validation:** A robust regex-based security layer protects the system from shell injection and path traversal by validating all `repo_id` and `revision` strings before they reach the system shell.
*   **Idempotent Mount Management:** The `HfMountManager` correctly interface with the `hf-mount` binary, handling "already mounted" states gracefully to prevent process conflicts.
*   **Structured Logging & Telemetry:** All key operations (handshake, mount, resolve) emit structured logs to `stderr` with sub-millisecond timing data for performance tracking.
*   **CI/CD Foundation:** A GitHub Actions pipeline automatically enforces code quality (via Ruff) and functional correctness (via Unittest) on every push.

---

## 2. The "Vaporware" Gap (Current Potential)

These are documented goals or architectural directions that are not yet fully realized in the codebase.

*   **Production-Scale Observability:** While logs exist, integrated distributed tracing (OpenTelemetry) and real-time health dashboards are currently theoretical.
*   **Multi-Artifact Bundling:** The protocol defines an `artifact` object, but the receiver currently processes one repository at a time. Resolving a "bundle" of multiple repositories in a single atomic request is planned but not implemented.
*   **Resource & Disk Quotas:** The system assumes sufficient disk space and "friendly" repository sizes. There are currently no automated checks to prevent a repository from exhausting host disk space.
*   **Dynamic Plugin Resolvers:** The `resolver.py` is currently a static implementation. The vision of a "plugin-based" architecture where agents can register new resolution logic at runtime remains a future goal.

---

## 3. Mitigations for Scaling & Production Readiness

To bridge the gap between PoC and Production, the following architectural mitigations are recommended:

### A. Scaling & Concurrency
*   **Mount Reference Counting:** Implement a registry to track active mounts. Only stop a mount when the reference count hits zero to avoid redundant and expensive mount operations.
*   **Async Process Execution:** Transition from blocking `subprocess.run` to `asyncio` for shell calls, allowing a single receiver to handle dozens of concurrent resolution requests without blocking.

### B. Security & Resource Protection
*   **Repository Whitelisting:** Implement a strict `ALLOWED_REPOS` configuration to prevent the system from being used to mount unauthorized or malicious repositories.
*   **Process Guardrails:** Add strict wall-clock timeouts and memory limits to the `hf-mount` child processes to ensure they cannot "hang" the main receiver.
*   **Disk Space Verification:** Implement a pre-mount check to ensure the host has sufficient capacity before attempting a download.

### C. Operational Reliability
*   **Automated Janitor (TTL):** Implement a background task to automatically unmount repositories that haven't been accessed within a defined Time-To-Live (e.g., 30 minutes).
*   **Graceful Shutdown:** Add signal handlers (SIGTERM/SIGINT) to ensure all FUSE mounts are cleanly unmounted if the receiver service is restarted or stopped.
*   **Health Check MCP Tool:** Add a dedicated tool for external monitoring systems to verify the service's "readiness" (binary availability, mount point permissions, HF API connectivity).

---
**Status:** This roadmap serves as the blueprint for the `v0.3.0` release cycle.
