# Agent Pidgin Non-Technical Assessment

**1. Purpose — What is this thing for?**

Agent Pidgin is like a safety inspector standing beside an AI assistant before it presses a real-world button. It checks what the AI is trying to do, whether the meaning changed, whether safety steps disappeared, and whether there is a clear paper trail.

In plain terms: it helps make autonomous agents less mysterious and easier to audit.

**2. How It Works — Step-by-step in plain English**

1. Someone gives Agent Pidgin a small instruction contract. Like handing a restaurant a short recipe card instead of saying, "Just make dinner somehow."
2. Pidgin checks whether the contract is shaped correctly. Like checking that a form has a name, address, and signature before accepting it.
3. Pidgin looks up each instruction in trusted catalogs. A catalog is like a store shelf label. It says what `comm.require_human_approval` or `shell.require_sandbox` actually means.
4. Pidgin applies rules. For example, it can reject risky things like "use the latest main branch" or "run raw code directly."
5. Pidgin creates receipts. These are like grocery receipts. They show what was checked, which catalog defined it, and what exact version was used.
6. If the agent changes its mind, Pidgin compares the old plan to the new plan. Like noticing that a recipe quietly removed "wash hands" and "check allergies."
7. If the change is dangerous, Pidgin blocks it. For example, it blocks an email plan that drops human approval and receipt steps.
8. Pidgin records everything in a flight recorder trace. Like an airplane black box, but for agent decisions.
9. Pidgin can turn that trace into a readable report or HTML page. A human can replay what happened without reading code.

**3. All Features — Everything it can actually do right now**

- Validate message files. The user gets a clear yes/no answer about whether a contract is shaped correctly. Example: "This email-sending contract has all required fields."
- Validate catalog files. It checks whether a list of trusted meanings is properly written. Example: "This catalog entry for `str.trim` is valid."
- Load built-in trusted catalogs. It includes catalogs for strings, clinical safety, agent operations, communications, files, shell commands, skills, memory, and finance. Example: "The system knows what `shell.require_sandbox` means."
- List catalog contents. The user can see what semantic pointers are available. Example: "Show me all Python-ready actions."
- Show one pointer without exposing raw implementation code. It shows safe metadata instead of dumping executable strings. Example: "Tell me what `clinical.phi.scrub` means."
- Resolve a contract into a plan. It turns short semantic steps into a structured result with receipts. Example: "Resolve this safe email plan and tell me what each step means."
- Enforce policy rules. It can block unsafe patterns. Example: "Do not accept a contract that uses an unpinned `main` branch."
- Create resolution receipts. Each resolved step gets a proof record. Example: "This approval step came from this catalog version and this catalog hash."
- Hash catalogs. It creates a stable fingerprint for a catalog. Example: "If one catalog entry changes, the hash changes."
- Sign catalogs with HMAC-SHA256. This is a shared-secret signature method. Example: "Only catalogs signed with our local secret are accepted."
- Verify catalog trust roots. It checks trusted catalog IDs, trusted keys, revoked keys, pinned hashes, and HMAC signatures. Example: "Reject this catalog because the key was revoked."
- Enforce trusted catalog loading in CLI commands. If a user supplies a catalog and a trust root, Pidgin verifies the catalog before using it. Example: "Do not resolve a contract using a tampered catalog."
- Compare two contracts. It finds added, removed, or changed semantic steps. Example: "The new version removed `agent.request_human_review`."
- Flag risky semantic drift. It treats removed safety steps as serious. Example: "This plan used to require approval, but now it does not."
- Run policy checks from the command line. The user can check a contract without fully resolving it. Example: "Tell me if this contract violates policy."
- Provide LLM-assisted authoring. It can use an LLM to draft a contract from plain language, while deterministic checks still decide what is valid. Example: "Turn 'send a customer email with approval' into semantic steps."
- Provide LLM-assisted explanation. It can explain a contract in plain language. Example: "Tell me what this contract does."
- Provide LLM-assisted review. It can review a contract and point out risks. Example: "This draft may be missing a human approval step."
- Fall back safely when LLM output is bad. If the live LLM suggests no known pointers, the demo falls back to a known safe fixture. Example: "The model gave unusable output, so the demo uses the tested version."
- Record basic flight-recorder events. It can record goals and observed events. Example: "The agent received a support escalation."
- Record proposed memory updates. It can detect when memory changes weaken guardrails. Example: "The memory changed from 'human review required' to 'not required.'"
- Record proposed tool calls. It can preflight a proposed action before execution. Example: "The agent wants to send an external email."
- Record proposed skill installs. It can block risky skills. Example: "This community skill wants shell access and credential access."
- Detect tampering in trace history. The trace is hash-chained, so changes are detectable. Example: "Someone edited event 1 after the fact."
- Render a text flight-recorder report. The user gets a readable replay. Example: "Event 5 was blocked because guardrails disappeared."
- Render an HTML replay. The user gets a visual report with integrity status, findings, receipts, and before/after panels. Example: "Open the replay and see exactly what changed."
- Export trace data in an OpenTelemetry-style shape. This lets normal observability tools receive a compatible trace-like export. Example: "Send Pidgin events into a telemetry pipeline."
- Run a dependency-free HTTP sidecar. Other tools can call Pidgin over local HTTP before acting. Example: "Ask Pidgin before installing a skill."
- Preflight skill, memory, and contract requests through the sidecar. It can answer allow/block-style decisions. Example: "Block this unsafe memory update."
- Provide an OpenClaw-class demo. The demo shows a local agent gateway asking Pidgin before skills, memory writes, email, and shell commands. Example: "A support agent tries unsafe actions; Pidgin blocks the dangerous ones."
- Provide an OpenClaw gateway adapter example. It shows how a gateway could call Pidgin instead of acting directly. Example: "Before shell execution, call the sidecar."
- Provide an A2A wrapper example. It shows how Pidgin contracts could travel inside an agent-to-agent style message. Example: "Send the semantic contract as an artifact."
- Provide MCP-style receiver tools. It exposes structured tools for handshake, resolve, and catalog metadata. Example: "An MCP client asks Pidgin what pointers it supports."
- Provide a clinical safety demo. It shows non-diagnostic safety steps and receipts. Example: "Scrub private health information and flag uncertainty, without diagnosing anyone."
- Provide a static landing page. It explains the product visually and links to the replay. Example: "A non-technical visitor can understand the flight recorder idea."

**4. Features That Were Tested**

- Message validation was tested. Example: valid messages pass, malformed messages fail.
- Catalog validation and loading were tested. Example: duplicate pointers are caught.
- Catalog hashing was tested. Example: the same catalog content gives a stable hash.
- Pointer lookup was tested. Example: `str.trim` can be found and summarized.
- Resolution was tested. Example: a valid contract resolves into ordered steps and receipts.
- Receipt creation was tested. Example: each resolved step gets a receipt.
- Policy enforcement was tested. Example: unpinned `main` branch revisions are rejected.
- Semantic diffing was tested. Example: removing `clinical.phi.scrub` is detected.
- High-risk guardrail removal was tested. Example: removing human review blocks the proposed action.
- CLI commands were tested. Example: validate, resolve, diff, render trace, verify skill, and catalog trust commands all have tests.
- HMAC catalog signing and verification were tested. Example: a tampered signed catalog is rejected.
- Trusted catalog loading was tested. Example: `resolve` blocks an untrusted explicit catalog before using it.
- Skill preflight was tested. Example: an unsigned shell-capable skill is blocked.
- Skill trust roots were tested. Example: trusted publishers pass, untrusted publishers fail.
- Flight recorder trace creation was tested. Example: events build a valid trace.
- Trace tampering detection was tested. Example: changing an event summary breaks the hash check.
- Memory drift detection was tested. Example: weakening review rules is blocked.
- Contract event recording was tested. Example: contract events store full receipts.
- HTML replay rendering was tested. Example: the page includes integrity, findings, receipts, and before/after panels.
- HTTP sidecar routing was tested. Example: skill, memory, contract, and render-trace requests work.
- OpenClaw gateway adapter was tested. Example: four proposed effects are preflighted without executing them.
- OpenClaw showpiece was tested. Example: the regression check confirms 6 events, 3 blocked events, and 11 receipts.
- LLM authoring helper behavior was tested with controlled fake responses. Example: bad suggested pointers are rejected.
- Telemetry export was tested. Example: Pidgin trace events can be mapped to span-like records.
- Fresh clone installation was tested manually. Example: the repo was cloned from GitHub, dependencies installed, and the test suite passed.

The current test result was 130 tests passing, with 2 skipped opt-in stdio integration tests.

**5. Claims Made in the Code or Comments**

- "Deterministic semantic contracts, receipts, and flight-recorder traces for autonomous agents." Plain English: this project says it helps prove what an agent meant to do.
- "Agent Pidgin is not an execution engine, A2A clone, MCP clone, or generic observability product." Plain English: it is not trying to be the robot hand, the chat pipe, or the normal logging system.
- "It sits beside those layers as the meaning and provenance layer." Plain English: it is meant to explain and prove meaning, not replace everything else.
- "The trust-critical path is deterministic." Plain English: the important safety decisions should not depend on a model guessing.
- "LLMs may help author, explain, or review contracts. They do not define pointer truth." Plain English: AI can help write the form, but it does not decide what the official terms mean.
- "Telemetry is still useful." Plain English: the project is not saying normal logs and traces are bad.
- "A prompted auditor agent gives a model opinion. Agent Pidgin gives a reproducible verdict with provenance." Plain English: Pidgin is meant to give repeatable proof, not just another AI review.
- "Use Agent Pidgin when an agent is about to do something important and a log line is not enough." Plain English: this is for moments where you need more than "the agent called email.send."
- "The demo preflights proposed actions; it does not install skills, send email, or run shell commands." Plain English: the demo checks dangerous actions, but does not actually perform them.
- "The current asymmetric-signature boundary is explicit." Plain English: public-key signature checking is not built yet, and the docs admit that.
- "Pidgeon can provide deterministic semantic preflight, drift detection, receipts, and replay." Plain English: it can inspect proposed agent actions and leave an audit trail.
- "Agent Pidgeon should not claim to secure OpenClaw itself or any particular OpenClaw deployment." Plain English: this is not a magic shield for all agent systems.

**6. Vaporware Claims (Promised but Not Delivered)**

- "Public-key catalog signature verification is still a future boundary." Plain English: it can do HMAC shared-secret signatures now, but not true public-key catalog signature checking yet.
- "Add public-key catalog signatures and key rotation." Plain English: stronger real-world signing is planned, but not built.
- "Prototype a Rust or Zig verifier/proxy." Plain English: there is no fast Rust or Zig version yet. The current project is Python.
- "Add packaged install instructions for local desktop agents and enterprise support bots." Plain English: there is a Python package setup, but not a polished install guide for normal operators.
- "Add signed trace roots or external append-only storage integration." Plain English: traces are hash-chained locally, but there is no outside vault or permanent ledger proving nobody replaced the whole trace.
- "Add event types for tool result observation and approved memory writes." Plain English: it records proposed actions well, but it does not yet fully record what happened after a tool actually ran.
- "Add catalog version pinning in contracts." Plain English: receipts include catalog versions, but contracts themselves do not yet force an exact catalog version.
- "Add external catalog artifact verification." Plain English: it does not yet fetch and verify remote catalog artifacts as a full supply-chain system.
- "Add optional signed catalog and signed receipt checks." Plain English: catalog HMAC signing exists, but signed receipts are not built.
- "A2A SDK adapter only after the JSON wrapper proves useful." Plain English: there is an A2A-style example, but not a full official SDK adapter.
- "MCP resource exposure for catalogs only after structured tool output is stable." Plain English: it has MCP-style tools, but not full catalog resource exposure.
- "Real HTTP or stdio sidecar server endpoint for the gateway adapter." Plain English: the HTTP sidecar exists now, so this older roadmap item is partly stale. The stdio side is still mostly demo/integration-test territory.
- "Live OpenRouter/Qwen LLM-assisted authoring." Plain English: the code supports it, but the normal test suite does not prove real OpenRouter service quality. It mostly tests the safety behavior with controlled fake responses and offline fallback.
- "Secure OpenClaw itself." Plain English: the docs correctly say not to claim this. Pidgin can preflight and record meaning, but it cannot guarantee the outside gateway obeys the decision.

**Bottom Line**

Agent Pidgin is a real working prototype with tests, demos, CLI tools, a sidecar, receipts, and replay reports. It is ready for demos and early technical evaluation, but it is not yet a complete production trust system until public-key signing, external trace anchoring, packaging, and post-execution observation are finished.
