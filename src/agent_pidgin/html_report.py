from __future__ import annotations

import html
import json
from typing import Any

from agent_pidgin.schema_validator import validate_pidgin_trace


def build_trace_html(trace: dict[str, Any], title: str = "Agent Pidgeon Trace Replay") -> str:
    validate_pidgin_trace(trace)
    event_cards = "\n".join(_event_card(event) for event in trace["events"])
    summary = trace.get("summary", {})
    trace_meta = (
        f"Trace {html.escape(trace['trace_id'])} · "
        f"status {html.escape(trace['status'])} · "
        f"hash {html.escape(trace['trace_hash'])}"
    )
    drift_count = summary.get("semantic_drift_event_count", 0)
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
    .metric, .event {{
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
    .blocked {{ background: var(--blocked); }}
    .resolved {{ background: var(--resolved); }}
    .observed, .drift_detected {{ background: var(--observed); }}
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
            "skill_manifest_hash",
            "policy_findings",
            "semantic_diff",
            "receipt_ids",
            "event_hash",
        ]
        if key in event
    }
    return f"""<article class="event">
  <header>
    <div>
      <strong>{html.escape(event["event_id"])} · {html.escape(event["event_type"])}</strong>
      <p>{html.escape(event["summary"])}</p>
    </div>
    <span class="badge {html.escape(decision)}">{html.escape(decision)}</span>
  </header>
  <pre><code>{html.escape(json.dumps(details, indent=2))}</code></pre>
</article>"""
