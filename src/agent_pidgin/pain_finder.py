from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

RUBRIC_FIELDS = [
    "ambiguity",
    "risk",
    "repeatability",
    "need_for_audit",
    "need_for_exact_steps",
    "local_terminology",
    "current_friction",
    "automation_potential",
]

STRONG_CANDIDATE_THRESHOLD = 10
EXCELLENT_CANDIDATE_THRESHOLD = 14

AMBIGUITY_TERMS = (
    "safe",
    "safely",
    "clean",
    "normalize",
    "handle",
    "review",
    "urgent",
    "appropriate",
    "as needed",
    "don't break",
    "do not break",
    "fix",
    "make sure",
)
RISK_TERMS = (
    "phi",
    "patient",
    "clinical",
    "clinical",
    "med",
    "medication",
    "diagnosis",
    "credential",
    "secret",
    "production",
    "payment",
    "delete",
    "truncate",
    "deploy",
    "external",
    "compliance",
    "policy",
    "shell",
)
REPEATABILITY_TERMS = ("always", "every", "daily", "batch", "pipeline", "workflow", "step", "runbook")
AUDIT_TERMS = ("audit", "receipt", "evidence", "log", "approval", "approved", "policy", "compliance", "review")
EXACT_STEP_TERMS = (
    "then",
    "before",
    "after",
    "first",
    "step",
    "run",
    "truncate",
    "deploy",
    "schema",
    "json",
    "rollback",
    "order",
)
LOCAL_TERMS = (
    "phi",
    "mrn",
    "ehr",
    "avs",
    "dc",
    "bid",
    "ssis",
    "ed",
    "etl",
    "staging",
    "encounter",
    "anticoagulant",
)
FRICTION_TERMS = (
    "conflict",
    "conflicting",
    "confusing",
    "unclear",
    "failed",
    "rework",
    "clarify",
    "drift",
    "mismatch",
    "but",
    "still",
)
AUTOMATION_TERMS = (
    "agent",
    "automate",
    "pipeline",
    "script",
    "tool",
    "workflow",
    "model",
    "run",
    "route",
    "send",
    "deploy",
)


@dataclass(frozen=True)
class PainFinderInput:
    item_id: str
    source_type: str
    raw_instruction: str


def load_pain_finder_csv(path: str | Path) -> list[PainFinderInput]:
    with Path(path).open(encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        missing = {"id", "source_type", "raw_instruction"} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Pain Finder CSV missing required columns: {', '.join(sorted(missing))}")
        return [
            PainFinderInput(
                item_id=str(row["id"]),
                source_type=str(row["source_type"]),
                raw_instruction=str(row["raw_instruction"]),
            )
            for row in reader
            if str(row.get("raw_instruction", "")).strip()
        ]


def score_instruction(item: PainFinderInput) -> dict[str, Any]:
    text = _normalize(item.raw_instruction)
    source_type = _normalize(item.source_type)
    rubric = {
        "ambiguity": _score_ambiguity(text),
        "risk": _score_risk(text),
        "repeatability": _score_repeatability(text, source_type),
        "need_for_audit": _score_audit_need(text),
        "need_for_exact_steps": _score_exact_steps(text),
        "local_terminology": _score_local_terminology(text),
        "current_friction": _score_terms(text, FRICTION_TERMS, strong_when=2),
        "automation_potential": _score_terms(text, AUTOMATION_TERMS, strong_when=2),
    }
    score = sum(rubric.values())
    return {
        "id": item.item_id,
        "source_type": item.source_type,
        "raw_instruction": item.raw_instruction,
        "pidgin_pain_score": score,
        "candidate_strength": _candidate_strength(score),
        "rubric": rubric,
        "pain_reasons": _pain_reasons(rubric),
        "candidate_contract_type": _candidate_contract_type(text, source_type),
        "hidden_requirements": _hidden_requirements(text, rubric),
        "recommended_next_step": _recommended_next_step(score),
    }


def analyze_pain_finder_inputs(items: list[PainFinderInput]) -> dict[str, Any]:
    results = [score_instruction(item) for item in items]
    strong_candidates = [result for result in results if result["pidgin_pain_score"] >= STRONG_CANDIDATE_THRESHOLD]
    excellent_candidates = [
        result for result in results if result["pidgin_pain_score"] >= EXCELLENT_CANDIDATE_THRESHOLD
    ]
    catalog_gap_signals = _ordered_unique(
        requirement
        for result in strong_candidates
        for requirement in result["hidden_requirements"]
        if requirement.endswith("policy version")
        or requirement.endswith("schema")
        or requirement.endswith("approval gate")
    )
    return {
        "status": "analyzed",
        "item_count": len(results),
        "strong_candidate_count": len(strong_candidates),
        "excellent_candidate_count": len(excellent_candidates),
        "strong_candidate_rate": _ratio(len(strong_candidates), len(results)),
        "catalog_gap_signals": catalog_gap_signals,
        "results": results,
    }


def analyze_pain_finder_csv(path: str | Path) -> dict[str, Any]:
    return analyze_pain_finder_inputs(load_pain_finder_csv(path))


def _score_terms(text: str, terms: tuple[str, ...], strong_when: int) -> int:
    hits = _term_hits(text, terms)
    if hits >= strong_when:
        return 2
    if hits > 0:
        return 1
    return 0


def _score_ambiguity(text: str) -> int:
    hits = _term_hits(text, AMBIGUITY_TERMS)
    transform_count = _term_hits(text, ("clean", "remove", "preserve", "return", "route", "send", "refactor"))
    if hits >= 2 or transform_count >= 3:
        return 2
    if hits > 0 or transform_count >= 2:
        return 1
    return 0


def _score_risk(text: str) -> int:
    hits = _term_hits(text, RISK_TERMS)
    if any(term in text for term in ("phi", "patient", "clinical", "medication")) and hits >= 2:
        return 2
    if any(term in text for term in ("truncate", "delete", "deploy", "production", "external", "payment")):
        return 2
    if hits > 0:
        return 1
    return 0


def _score_repeatability(text: str, source_type: str) -> int:
    score = _score_terms(text, REPEATABILITY_TERMS, strong_when=2)
    if any(term in source_type for term in ("runbook", "pipeline", "workflow")):
        score = max(score, 2)
    if any(term in source_type for term in ("ticket", "issue", "workflow", "prompt", "request", "runbook")):
        score = max(score, 1)
    return score


def _score_audit_need(text: str) -> int:
    if any(term in text for term in ("receipt", "logged", "approval", "approved", "verified", "compliance")):
        return 2
    if "phi" in text:
        return 2
    if any(term in text for term in ("phi", "patient", "external", "explain", "policy", "review")):
        return 1
    return _score_terms(text, AUDIT_TERMS, strong_when=2)


def _score_exact_steps(text: str) -> int:
    hits = _term_hits(text, EXACT_STEP_TERMS)
    transform_count = _term_hits(text, ("clean", "remove", "preserve", "return", "route", "send", "run"))
    if hits >= 2 or transform_count >= 3:
        return 2
    if hits > 0 or transform_count >= 2:
        return 1
    return 0


def _score_local_terminology(text: str) -> int:
    hits = _term_hits(text, LOCAL_TERMS)
    if hits >= 2:
        return 2
    if hits > 0:
        return 1
    return 0


def _candidate_strength(score: int) -> str:
    if score >= EXCELLENT_CANDIDATE_THRESHOLD:
        return "excellent_candidate"
    if score >= STRONG_CANDIDATE_THRESHOLD:
        return "good_candidate"
    if score >= 6:
        return "weak_candidate"
    return "not_a_pidgin_problem"


def _pain_reasons(rubric: dict[str, int]) -> list[str]:
    labels = {
        "ambiguity": "ambiguous instruction",
        "risk": "safety or operational risk",
        "repeatability": "repeated workflow pattern",
        "need_for_audit": "audit or evidence need",
        "need_for_exact_steps": "exact step ordering needed",
        "local_terminology": "local terminology present",
        "current_friction": "current friction or contradiction",
        "automation_potential": "automation candidate",
    }
    return [labels[name] for name in RUBRIC_FIELDS if rubric[name] > 0]


def _candidate_contract_type(text: str, source_type: str) -> str:
    if any(term in text for term in ("phi", "clinical", "patient", "medication", "ehr", "avs")):
        if any(term in text for term in ("clean", "scrub", "json", "note", "summarize")):
            return "clinical_text_transformation"
        return "clinical_workflow_safety_review"
    if any(term in text for term in ("truncate", "ssis", "staging", "etl", "pipeline")):
        return "data_pipeline_operation"
    if any(term in text for term in ("send", "email", "external", "customer")):
        return "external_communication_review"
    if any(term in text for term in ("refactor", "repo", "tests", "agent")) or "prompt" in source_type:
        return "agent_task_contract"
    if any(term in text for term in ("policy", "exception", "approval")):
        return "policy_exception_review"
    return "generic_workflow_contract"


def _hidden_requirements(text: str, rubric: dict[str, int]) -> list[str]:
    requirements = []
    if any(term in text for term in ("phi", "patient", "clinical", "ehr", "medication")):
        requirements.extend(["safety policy version", "evidence spans", "human review rule"])
    if any(term in text for term in ("clean", "normalize", "json", "schema")):
        requirements.extend(["output schema", "transformation receipts"])
    if any(term in text for term in ("send", "external", "email", "customer")):
        requirements.extend(["recipient verification", "approval gate", "send-mode boundary"])
    if any(term in text for term in ("truncate", "delete", "deploy", "production", "rollback")):
        requirements.extend(["execution order", "rollback rule", "row-count or deployment receipt"])
    if any(term in text for term in ("refactor", "repo", "tests", "don't break", "do not break")):
        requirements.extend(["test evidence", "forbidden behavior", "change summary receipt"])
    if rubric["need_for_audit"] > 0:
        requirements.append("audit receipt")
    if rubric["current_friction"] > 0:
        requirements.append("clarifying assumption")
    return _ordered_unique(requirements)


def _recommended_next_step(score: int) -> str:
    if score >= STRONG_CANDIDATE_THRESHOLD:
        return "convert_to_candidate_pidgin_contract"
    if score >= 6:
        return "clarify_before_contract_authoring"
    return "leave_as_plain_instruction"


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _term_hits(text: str, terms: tuple[str, ...]) -> int:
    return sum(1 for term in terms if term in text)


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def _ordered_unique(values: list[str] | Any) -> list[str]:
    seen = set()
    unique = []
    for value in values:
        if value not in seen:
            seen.add(value)
            unique.append(value)
    return unique
