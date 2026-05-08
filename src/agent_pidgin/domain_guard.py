from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from agent_pidgin.constants import PIDGIN_PROTOCOL_VERSION
from agent_pidgin.hash_utils import sha256_digest

STATUS_PRIORITY = {
    "blocked": 0,
    "escalate": 1,
    "constrained": 2,
    "clarify": 3,
    "allowed": 4,
}

TIER_PRIORITY = {
    "T0_BLOCK_OR_ESCALATE": 0,
    "T1_COLLECT_INFO_ONLY": 1,
    "T2_SAFE_GENERAL_EDUCATION": 2,
    "T3_CONSTRAINED_RESPONSE": 3,
    "T4_ALLOWED_DOMAIN_RESPONSE": 4,
}


@dataclass(frozen=True)
class DomainBoundaryRule:
    rule_id: str
    topic: str
    pattern: str
    status: str
    autonomy_tier: str
    severity: str
    assumption: str
    reason: str
    controls: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DomainBoundaryFinding:
    rule_id: str
    topic: str
    status: str
    autonomy_tier: str
    severity: str
    evidence: str
    reason: str
    controls: list[str]


@dataclass(frozen=True)
class AssumptionStatus:
    name: str
    status: str
    reason: str


def load_domain_policy(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as policy_file:
        policy = json.load(policy_file)
    validate_domain_policy(policy)
    return policy


def validate_domain_policy(policy: dict[str, Any]) -> None:
    if not isinstance(policy, dict):
        raise ValueError("domain policy must be a JSON object")
    if not str(policy.get("domain", "")).strip():
        raise ValueError("domain policy requires a domain")
    if not isinstance(policy.get("rules"), list):
        raise ValueError("domain policy requires a rules list")
    for raw_rule in policy["rules"]:
        if not isinstance(raw_rule, dict):
            raise ValueError("domain policy rules must be JSON objects")
        _rule_from_dict(raw_rule)


def evaluate_prompt_boundary(
    prompt: str,
    domain_policy: dict[str, Any],
    conversation_signals: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    validate_domain_policy(domain_policy)
    normalized_prompt = _normalize_text(prompt)
    findings = _findings_for_prompt(normalized_prompt, domain_policy)
    findings.extend(_findings_for_conversation_signals(conversation_signals or [], domain_policy))

    if findings:
        status = _most_restrictive_status(finding.status for finding in findings)
        autonomy_tier = _most_restrictive_tier(finding.autonomy_tier for finding in findings)
        topic = findings[0].topic
    else:
        status = str(domain_policy.get("default_status", "allowed"))
        autonomy_tier = str(domain_policy.get("default_autonomy_tier", "T4_ALLOWED_DOMAIN_RESPONSE"))
        topic = str(domain_policy.get("default_topic", f"{domain_policy['domain']}.general"))

    controls = _ordered_unique(control for finding in findings for control in finding.controls)
    assumptions = _assumptions_for_findings(findings, status=status)
    report = {
        "status": status,
        "autonomy_tier": autonomy_tier,
        "domain": str(domain_policy["domain"]),
        "topic": topic,
        "prompt_hash": sha256_digest(prompt),
        "policy_hash": sha256_digest(domain_policy),
        "assumptions": [asdict(assumption) for assumption in assumptions],
        "findings": [asdict(finding) for finding in findings],
        "required_response_controls": controls,
        "receipt": {
            "policy_hash": sha256_digest(domain_policy),
            "rule_ids": [finding.rule_id for finding in findings],
            "resolver_version": PIDGIN_PROTOCOL_VERSION,
        },
    }
    return report


def benchmark_prompt_boundaries(cases: list[dict[str, Any]], domain_policy: dict[str, Any]) -> dict[str, Any]:
    validate_domain_policy(domain_policy)
    results = []
    unsafe_total = 0
    unsafe_caught = 0
    status_matches = 0
    tier_matches = 0

    for case in cases:
        report = evaluate_prompt_boundary(
            str(case["prompt"]),
            domain_policy,
            conversation_signals=list(case.get("conversation_signals", [])),
        )
        expected_status = str(case["expected_status"])
        expected_tier = str(case["expected_autonomy_tier"])
        status_match = report["status"] == expected_status
        tier_match = report["autonomy_tier"] == expected_tier
        is_unsafe = bool(case.get("unsafe", expected_status in {"blocked", "escalate"}))
        caught = report["status"] in {"blocked", "escalate"} if is_unsafe else True

        unsafe_total += 1 if is_unsafe else 0
        unsafe_caught += 1 if is_unsafe and caught else 0
        status_matches += 1 if status_match else 0
        tier_matches += 1 if tier_match else 0
        results.append(
            {
                "case_id": str(case.get("case_id", "")),
                "expected_status": expected_status,
                "actual_status": report["status"],
                "expected_autonomy_tier": expected_tier,
                "actual_autonomy_tier": report["autonomy_tier"],
                "status_match": status_match,
                "tier_match": tier_match,
                "unsafe": is_unsafe,
                "unsafe_caught": caught,
                "rule_ids": report["receipt"]["rule_ids"],
            }
        )

    total = len(cases)
    passed = status_matches == total and tier_matches == total and unsafe_caught == unsafe_total
    return {
        "status": "passed" if passed else "failed",
        "case_count": total,
        "status_accuracy": _ratio(status_matches, total),
        "tier_accuracy": _ratio(tier_matches, total),
        "unsafe_case_count": unsafe_total,
        "unsafe_catch_rate": _ratio(unsafe_caught, unsafe_total),
        "results": results,
    }


def load_benchmark_cases(path: str | Path) -> list[dict[str, Any]]:
    cases = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        case = json.loads(line)
        if not isinstance(case, dict):
            raise ValueError(f"benchmark case line {line_number} must be a JSON object")
        for required in ["case_id", "prompt", "expected_status", "expected_autonomy_tier"]:
            if required not in case:
                raise ValueError(f"benchmark case line {line_number} missing {required}")
        cases.append(case)
    return cases


def _findings_for_prompt(prompt: str, policy: dict[str, Any]) -> list[DomainBoundaryFinding]:
    findings = []
    for raw_rule in policy["rules"]:
        rule = _rule_from_dict(raw_rule)
        match = re.search(rule.pattern, prompt, flags=re.IGNORECASE)
        if not match:
            continue
        findings.append(
            DomainBoundaryFinding(
                rule_id=rule.rule_id,
                topic=rule.topic,
                status=rule.status,
                autonomy_tier=rule.autonomy_tier,
                severity=rule.severity,
                evidence=match.group(0),
                reason=rule.reason,
                controls=list(rule.controls),
            )
        )
    return sorted(findings, key=lambda finding: (STATUS_PRIORITY[finding.status], TIER_PRIORITY[finding.autonomy_tier]))


def _findings_for_conversation_signals(
    conversation_signals: list[dict[str, Any]],
    policy: dict[str, Any],
) -> list[DomainBoundaryFinding]:
    findings = []
    signal_rules = policy.get("conversation_signal_rules", {})
    if not isinstance(signal_rules, dict):
        return findings
    for signal in conversation_signals:
        signal_id = str(signal.get("signal_id", ""))
        raw_rule = signal_rules.get(signal_id)
        if not isinstance(raw_rule, dict):
            continue
        rule = _rule_from_dict({"rule_id": signal_id, **raw_rule})
        evidence = str(signal.get("evidence", signal_id))
        findings.append(
            DomainBoundaryFinding(
                rule_id=rule.rule_id,
                topic=rule.topic,
                status=rule.status,
                autonomy_tier=rule.autonomy_tier,
                severity=rule.severity,
                evidence=evidence,
                reason=rule.reason,
                controls=list(rule.controls),
            )
        )
    return findings


def _assumptions_for_findings(findings: list[DomainBoundaryFinding], status: str) -> list[AssumptionStatus]:
    if not findings:
        return [
            AssumptionStatus(
                name="Prompt remains inside domain",
                status="ok",
                reason="No boundary rule matched.",
            )
        ]
    assumption_status = "breached" if status in {"blocked", "escalate"} else "weak"
    return [
        AssumptionStatus(
            name=finding.topic,
            status=assumption_status,
            reason=finding.reason,
        )
        for finding in findings
    ]


def _rule_from_dict(raw_rule: dict[str, Any]) -> DomainBoundaryRule:
    required = ["rule_id", "topic", "pattern", "status", "autonomy_tier", "severity", "assumption", "reason"]
    missing = [key for key in required if key not in raw_rule]
    if missing:
        raise ValueError(f"domain boundary rule missing required fields: {', '.join(missing)}")
    status = str(raw_rule["status"])
    autonomy_tier = str(raw_rule["autonomy_tier"])
    if status not in STATUS_PRIORITY:
        raise ValueError(f"unknown domain boundary status: {status}")
    if autonomy_tier not in TIER_PRIORITY:
        raise ValueError(f"unknown autonomy tier: {autonomy_tier}")
    re.compile(str(raw_rule["pattern"]))
    controls = raw_rule.get("controls", [])
    if not isinstance(controls, list):
        raise ValueError("domain boundary rule controls must be a list")
    return DomainBoundaryRule(
        rule_id=str(raw_rule["rule_id"]),
        topic=str(raw_rule["topic"]),
        pattern=str(raw_rule["pattern"]),
        status=status,
        autonomy_tier=autonomy_tier,
        severity=str(raw_rule["severity"]),
        assumption=str(raw_rule["assumption"]),
        reason=str(raw_rule["reason"]),
        controls=[str(control) for control in controls],
    )


def _most_restrictive_status(statuses: Any) -> str:
    return min(statuses, key=lambda status: STATUS_PRIORITY[str(status)])


def _most_restrictive_tier(tiers: Any) -> str:
    return min(tiers, key=lambda tier: TIER_PRIORITY[str(tier)])


def _normalize_text(value: str) -> str:
    return " ".join(str(value).strip().split())


def _ordered_unique(values: Any) -> list[str]:
    out = []
    seen = set()
    for value in values:
        if value in seen:
            continue
        out.append(str(value))
        seen.add(value)
    return out


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 1.0
    return round(numerator / denominator, 4)
