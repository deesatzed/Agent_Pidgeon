from __future__ import annotations

import html
import json
from typing import Any

from agent_pidgin.flight_recorder import validate_trace_integrity
from agent_pidgin.schema_validator import validate_pidgin_trace


def build_trace_html(trace: dict[str, Any], title: str = "Agent Pidgeon Trace Replay") -> str:
    validate_pidgin_trace(trace)
    event_cards = "\n".join(_event_card(event) for event in trace["events"])
    integrity = validate_trace_integrity(trace)
    policy_groups = _policy_groups(trace["events"])
    policy_section = _policy_section(policy_groups)
    receipt_section = _receipt_section(trace["events"])
    diff_section = _semantic_diff_section(trace["events"])
    summary = trace.get("summary", {})
    trace_meta = (
        f"Trace {_escape(trace['trace_id'])} · status {_escape(trace['status'])} · hash {_escape(trace['trace_hash'])}"
    )
    drift_count = summary.get("semantic_drift_event_count", 0)
    integrity_class = "resolved" if integrity["status"] == "valid" else "blocked"
    integrity_label = "valid hash chain" if integrity["status"] == "valid" else "invalid hash chain"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #16202a;
      --muted: #5f6b76;
      --line: #d8dee5;
      --bg: #f7f9fb;
      --panel: #ffffff;
      --blocked: #b42318;
      --resolved: #047857;
      --observed: #315b88;
      --warn: #a15c00;
    }}
    body {{
      margin: 0;
      font: 15px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--bg);
    }}
    main {{
      max-width: 1120px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    h1 {{
      font-size: 30px;
      margin: 0 0 8px;
    }}
    .subhead {{
      color: var(--muted);
      margin: 0 0 24px;
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin-bottom: 24px;
    }}
    .metric, .event, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }}
    .metric strong {{
      display: block;
      font-size: 22px;
    }}
    .event {{
      margin-bottom: 12px;
    }}
    .panel {{
      margin-bottom: 18px;
    }}
    .panel h2 {{
      font-size: 18px;
      margin: 0 0 10px;
    }}
    .event header {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: start;
    }}
    .badge {{
      border-radius: 999px;
      padding: 3px 9px;
      color: white;
      font-size: 12px;
      text-transform: uppercase;
      white-space: nowrap;
    }}
    .blocked, .error {{ background: var(--blocked); }}
    .resolved {{ background: var(--resolved); }}
    .policy_failed, .warning {{ background: var(--warn); }}
    .observed, .drift_detected {{ background: var(--observed); }}
    .integrity-row, .finding-row, .receipt-row {{
      display: grid;
      grid-template-columns: minmax(120px, 0.8fr) minmax(180px, 1fr) minmax(220px, 2fr);
      gap: 10px;
      border-top: 1px solid var(--line);
      padding: 9px 0;
    }}
    .integrity-row:first-of-type, .finding-row:first-of-type, .receipt-row:first-of-type {{
      border-top: 0;
    }}
    .diff-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 12px;
    }}
    .diff-panel {{
      min-width: 0;
    }}
    .muted {{
      color: var(--muted);
    }}
    .chips {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin: 8px 0;
    }}
    .chip {{
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 3px 8px;
      background: #f8fafc;
      font-size: 12px;
    }}
    pre {{
      white-space: pre-wrap;
      word-break: break-word;
      background: #f1f4f7;
      border-radius: 6px;
      padding: 10px;
      overflow: auto;
    }}
    code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 12px;
    }}
  </style>
</head>
<body>
  <main>
    <h1>{html.escape(title)}</h1>
    <p class="subhead">{trace_meta}</p>
    <section class="metrics">
      <div class="metric"><span>Events</span><strong>{summary.get("event_count", 0)}</strong></div>
      <div class="metric"><span>Blocked</span><strong>{summary.get("blocked_event_count", 0)}</strong></div>
      <div class="metric"><span>Semantic drift</span><strong>{drift_count}</strong></div>
      <div class="metric"><span>Receipts</span><strong>{summary.get("receipt_count", 0)}</strong></div>
    </section>
    <section class="panel" aria-labelledby="trace-integrity-heading">
      <h2 id="trace-integrity-heading">Trace integrity</h2>
      <div class="integrity-row">
        <span><span class="badge {integrity_class}">{_escape(integrity["status"])}</span></span>
        <strong>{integrity_label}</strong>
        <span>{_escape(integrity.get("error") or "Event hashes, previous hashes, and trace hash match.")}</span>
      </div>
      <div class="integrity-row">
        <span>summary</span>
        <strong>{_escape(summary.get("integrity", "not reported"))}</strong>
        <span class="muted">Top-level trace hash: <code>{_escape(trace["trace_hash"])}</code></span>
      </div>
    </section>
    {policy_section}
    {receipt_section}
    {diff_section}
    <section>
      {event_cards}
    </section>
  </main>
</body>
</html>
"""


def _event_card(event: dict[str, Any]) -> str:
    decision = str(event["decision"])
    details = {
        key: event[key]
        for key in [
            "event_id",
            "parent_event_id",
            "event_type",
            "actor",
            "payload_hash",
            "contract_hash",
            "previous_contract_hash",
            "skill_manifest_hash",
            "policy_findings",
            "semantic_diff",
            "receipt_ids",
            "receipts",
            "event_hash",
        ]
        if key in event
    }
    badges = _event_badges(event)
    return f"""<article class="event">
  <header>
    <div>
      <strong>{_escape(event["event_id"])} · {_escape(event["event_type"])}</strong>
      <p>{_escape(event["summary"])}</p>
      {badges}
    </div>
    <span class="badge {_escape(decision)}">{_escape(decision)}</span>
  </header>
  <pre><code>{_json(details)}</code></pre>
</article>"""


def _policy_groups(events: list[dict[str, Any]]) -> dict[tuple[str, str], list[tuple[dict[str, Any], dict[str, Any]]]]:
    groups: dict[tuple[str, str], list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    for event in events:
        for finding in event.get("policy_findings", []):
            if not isinstance(finding, dict):
                continue
            key = (str(finding.get("severity", "unknown")), str(finding.get("code", "UNKNOWN")))
            groups.setdefault(key, []).append((event, finding))
    return groups


def _policy_section(
    policy_groups: dict[tuple[str, str], list[tuple[dict[str, Any], dict[str, Any]]]],
) -> str:
    if not policy_groups:
        return ""
    rows = []
    for (severity, code), findings in sorted(policy_groups.items()):
        event_ids = ", ".join(_escape(event["event_id"]) for event, _finding in findings)
        messages = sorted({str(finding.get("message", "")) for _event, finding in findings if finding.get("message")})
        message = messages[0] if messages else "No message supplied."
        rows.append(
            f"""<div class="finding-row">
        <span><span class="badge {_escape(severity)}">{_escape(severity)}</span></span>
        <strong>{_escape(code)} <span class="muted">({len(findings)})</span></strong>
        <span>{_escape(message)} <span class="muted">Events: {event_ids}</span></span>
      </div>"""
        )
    return f"""<section class="panel" aria-labelledby="policy-findings-heading">
      <h2 id="policy-findings-heading">Grouped policy findings</h2>
      {"".join(rows)}
    </section>"""


def _receipt_section(events: list[dict[str, Any]]) -> str:
    rows = []
    for event in events:
        receipt_ids = event.get("receipt_ids", [])
        if not receipt_ids:
            continue
        receipts = event.get("receipts", [])
        receipt_chips = "".join(f'<span class="chip">{_escape(receipt_id)}</span>' for receipt_id in receipt_ids)
        hashes = [
            f"payload <code>{_escape(event['payload_hash'])}</code>",
            f"event <code>{_escape(event['event_hash'])}</code>",
        ]
        if event.get("contract_hash"):
            hashes.insert(1, f"contract <code>{_escape(event['contract_hash'])}</code>")
        if event.get("previous_contract_hash"):
            hashes.insert(1, f"previous contract <code>{_escape(event['previous_contract_hash'])}</code>")
        receipt_detail = _json(receipts) if receipts else _json(receipt_ids)
        rows.append(
            f"""<details class="receipt-row">
        <summary><strong>{_escape(event["event_id"])} · {_escape(event["event_type"])}</strong></summary>
        <span>{len(receipt_ids)} receipt ID{"s" if len(receipt_ids) != 1 else ""}</span>
        <div><div class="chips">{receipt_chips}</div>
        <p class="muted">Bound to {"; ".join(hashes)}.</p>
        <pre><code>{receipt_detail}</code></pre></div>
      </details>"""
        )
    if not rows:
        return ""
    return f"""<section class="panel" aria-labelledby="receipt-drilldown-heading">
      <h2 id="receipt-drilldown-heading">Receipt drilldown</h2>
      {"".join(rows)}
    </section>"""


def _semantic_diff_section(events: list[dict[str, Any]]) -> str:
    panels = [_semantic_diff_panel(event) for event in events if event.get("semantic_diff")]
    panels = [panel for panel in panels if panel]
    if not panels:
        return ""
    return f"""<section class="panel" aria-labelledby="semantic-diff-heading">
      <h2 id="semantic-diff-heading">Semantic diff and before/after</h2>
      {"".join(panels)}
    </section>"""


def _semantic_diff_panel(event: dict[str, Any]) -> str:
    semantic_diff = event.get("semantic_diff", {})
    payload = event.get("payload", {})
    before = payload.get("before") if isinstance(payload, dict) else None
    after = payload.get("after") if isinstance(payload, dict) else None
    before_label = "Before"
    after_label = "After"
    if before is None and event.get("previous_contract") is not None:
        before = event.get("previous_contract")
        before_label = "Previous contract"
    if after is None and event.get("contract") is not None:
        after = event.get("contract")
        after_label = "Proposed contract"
    before_after = ""
    if before is not None or after is not None:
        before_after = f"""<div class="diff-grid">
          <div class="diff-panel"><strong>{_escape(before_label)}</strong><pre><code>{_json(before)}</code></pre></div>
          <div class="diff-panel"><strong>{_escape(after_label)}</strong><pre><code>{_json(after)}</code></pre></div>
        </div>"""
    changes = {
        key: semantic_diff.get(key)
        for key in ["risk_level", "added", "removed", "changed", "risk_notes", "contract_changes"]
        if key in semantic_diff
    }
    return f"""<article class="event">
        <header>
          <div>
            <strong>{_escape(event["event_id"])} · {_escape(event["event_type"])}</strong>
            <p class="muted">Risk level: {_escape(changes.get("risk_level", "unknown"))}</p>
          </div>
          <span class="badge {_escape(event["decision"])}">{_escape(event["decision"])}</span>
        </header>
        {before_after}
        <pre><code>{_json(changes)}</code></pre>
      </article>"""


def _event_badges(event: dict[str, Any]) -> str:
    items = []
    if event.get("semantic_diff"):
        items.append(f'<span class="chip">diff: {_escape(event["semantic_diff"].get("risk_level", "unknown"))}</span>')
    if event.get("policy_findings"):
        items.append(f'<span class="chip">policy: {len(event["policy_findings"])}</span>')
    if event.get("receipt_ids"):
        items.append(f'<span class="chip">receipts: {len(event["receipt_ids"])}</span>')
    if not items:
        return ""
    return f'<div class="chips">{"".join(items)}</div>'


def _json(value: Any) -> str:
    return _escape(json.dumps(value, indent=2, sort_keys=True))


def _escape(value: Any) -> str:
    return html.escape(str(value))
