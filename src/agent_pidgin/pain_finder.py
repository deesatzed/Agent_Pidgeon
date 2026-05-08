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


@dataclass(frozen=True)
class ContractLiftInput:
    item_id: str
    hidden_assumptions_exposed: bool
    ambiguity_reduced: bool
    validation_possible: bool
    safety_constraints_clarified: bool
    receipts_defined: bool
    reproducibility_improved: bool
    catalog_gap_revealed: bool


@dataclass(frozen=True)
class AgentComparisonInput:
    item_id: str
    raw_missed_requirements: int
    contract_missed_requirements: int
    raw_unsafe_omissions: int
    contract_unsafe_omissions: int
    raw_audit_artifacts: int
    contract_audit_artifacts: int


@dataclass(frozen=True)
class HumanReactionInput:
    item_id: str
    revealed_unstated_assumption: bool
    felt_clarifying: bool
    felt_bureaucratic: bool


@dataclass(frozen=True)
class NanowhaleReadinessInput:
    domain: str
    sensitive: bool
    high_volume: bool
    latency_sensitive: bool
    repetitive_language: bool
    stable_schema: bool
    human_review_present: bool


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


def load_contract_lift_csv(path: str | Path) -> list[ContractLiftInput]:
    with Path(path).open(encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        required = {
            "id",
            "hidden_assumptions_exposed",
            "ambiguity_reduced",
            "validation_possible",
            "safety_constraints_clarified",
            "receipts_defined",
            "reproducibility_improved",
            "catalog_gap_revealed",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Contract lift CSV missing required columns: {', '.join(sorted(missing))}")
        return [
            ContractLiftInput(
                item_id=str(row["id"]),
                hidden_assumptions_exposed=_as_bool(row["hidden_assumptions_exposed"]),
                ambiguity_reduced=_as_bool(row["ambiguity_reduced"]),
                validation_possible=_as_bool(row["validation_possible"]),
                safety_constraints_clarified=_as_bool(row["safety_constraints_clarified"]),
                receipts_defined=_as_bool(row["receipts_defined"]),
                reproducibility_improved=_as_bool(row["reproducibility_improved"]),
                catalog_gap_revealed=_as_bool(row["catalog_gap_revealed"]),
            )
            for row in reader
        ]


def analyze_contract_lift(items: list[ContractLiftInput]) -> dict[str, Any]:
    results = []
    meaningful_count = 0
    for item in items:
        signals = {
            "hidden_assumptions_exposed": item.hidden_assumptions_exposed,
            "ambiguity_reduced": item.ambiguity_reduced,
            "validation_possible": item.validation_possible,
            "safety_constraints_clarified": item.safety_constraints_clarified,
            "receipts_defined": item.receipts_defined,
            "reproducibility_improved": item.reproducibility_improved,
            "catalog_gap_revealed": item.catalog_gap_revealed,
        }
        lift_score = sum(1 for value in signals.values() if value)
        meaningful = lift_score >= 4
        meaningful_count += 1 if meaningful else 0
        results.append(
            {
                "id": item.item_id,
                "contract_lift_score": lift_score,
                "meaningful_lift": meaningful,
                "signals": signals,
            }
        )
    rate = _ratio(meaningful_count, len(items))
    return {
        "status": "passed" if rate >= 0.5 else "needs_more_evidence",
        "item_count": len(items),
        "meaningful_lift_count": meaningful_count,
        "meaningful_lift_rate": rate,
        "results": results,
    }


def analyze_contract_lift_csv(path: str | Path) -> dict[str, Any]:
    return analyze_contract_lift(load_contract_lift_csv(path))


def load_agent_comparison_csv(path: str | Path) -> list[AgentComparisonInput]:
    with Path(path).open(encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        required = {
            "id",
            "raw_missed_requirements",
            "contract_missed_requirements",
            "raw_unsafe_omissions",
            "contract_unsafe_omissions",
            "raw_audit_artifacts",
            "contract_audit_artifacts",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Agent comparison CSV missing required columns: {', '.join(sorted(missing))}")
        return [
            AgentComparisonInput(
                item_id=str(row["id"]),
                raw_missed_requirements=int(row["raw_missed_requirements"]),
                contract_missed_requirements=int(row["contract_missed_requirements"]),
                raw_unsafe_omissions=int(row["raw_unsafe_omissions"]),
                contract_unsafe_omissions=int(row["contract_unsafe_omissions"]),
                raw_audit_artifacts=int(row["raw_audit_artifacts"]),
                contract_audit_artifacts=int(row["contract_audit_artifacts"]),
            )
            for row in reader
        ]


def analyze_agent_comparison(items: list[AgentComparisonInput]) -> dict[str, Any]:
    results = []
    improved_count = 0
    safer_count = 0
    more_auditable_count = 0
    for item in items:
        improved = item.contract_missed_requirements < item.raw_missed_requirements
        safer = item.contract_unsafe_omissions <= item.raw_unsafe_omissions
        more_auditable = item.contract_audit_artifacts > item.raw_audit_artifacts
        improved_count += 1 if improved else 0
        safer_count += 1 if safer else 0
        more_auditable_count += 1 if more_auditable else 0
        results.append(
            {
                "id": item.item_id,
                "missed_requirements_delta": item.contract_missed_requirements - item.raw_missed_requirements,
                "unsafe_omissions_delta": item.contract_unsafe_omissions - item.raw_unsafe_omissions,
                "audit_artifacts_delta": item.contract_audit_artifacts - item.raw_audit_artifacts,
                "improved_requirements": improved,
                "no_new_unsafe_omissions": safer,
                "more_auditable": more_auditable,
            }
        )
    raw_missed = sum(item.raw_missed_requirements for item in items)
    contract_missed = sum(item.contract_missed_requirements for item in items)
    raw_unsafe = sum(item.raw_unsafe_omissions for item in items)
    contract_unsafe = sum(item.contract_unsafe_omissions for item in items)
    raw_audit = sum(item.raw_audit_artifacts for item in items)
    contract_audit = sum(item.contract_audit_artifacts for item in items)
    missed_reduction = _ratio(raw_missed - contract_missed, raw_missed)
    unsafe_reduction = _ratio(raw_unsafe - contract_unsafe, raw_unsafe)
    audit_lift = _ratio(contract_audit - raw_audit, max(contract_audit, 1))
    return {
        "status": "passed" if missed_reduction > 0 and unsafe_reduction >= 0 and audit_lift > 0 else "failed",
        "item_count": len(items),
        "raw_missed_requirements": raw_missed,
        "contract_missed_requirements": contract_missed,
        "missed_requirement_reduction": missed_reduction,
        "raw_unsafe_omissions": raw_unsafe,
        "contract_unsafe_omissions": contract_unsafe,
        "unsafe_omission_reduction": unsafe_reduction,
        "raw_audit_artifacts": raw_audit,
        "contract_audit_artifacts": contract_audit,
        "audit_artifact_lift": audit_lift,
        "improved_requirement_rate": _ratio(improved_count, len(items)),
        "no_new_unsafe_omission_rate": _ratio(safer_count, len(items)),
        "more_auditable_rate": _ratio(more_auditable_count, len(items)),
        "results": results,
    }


def analyze_agent_comparison_csv(path: str | Path) -> dict[str, Any]:
    return analyze_agent_comparison(load_agent_comparison_csv(path))


def load_human_reaction_csv(path: str | Path) -> list[HumanReactionInput]:
    with Path(path).open(encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        required = {"id", "revealed_unstated_assumption", "felt_clarifying", "felt_bureaucratic"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Human reaction CSV missing required columns: {', '.join(sorted(missing))}")
        return [
            HumanReactionInput(
                item_id=str(row["id"]),
                revealed_unstated_assumption=_as_bool(row["revealed_unstated_assumption"]),
                felt_clarifying=_as_bool(row["felt_clarifying"]),
                felt_bureaucratic=_as_bool(row["felt_bureaucratic"]),
            )
            for row in reader
        ]


def analyze_human_reactions(items: list[HumanReactionInput]) -> dict[str, Any]:
    assumption_count = sum(1 for item in items if item.revealed_unstated_assumption)
    clarifying_count = sum(1 for item in items if item.felt_clarifying)
    bureaucratic_count = sum(1 for item in items if item.felt_bureaucratic)
    return {
        "status": "passed"
        if _ratio(clarifying_count, len(items)) > _ratio(bureaucratic_count, len(items))
        else "needs_more_evidence",
        "item_count": len(items),
        "revealed_assumption_rate": _ratio(assumption_count, len(items)),
        "clarifying_rate": _ratio(clarifying_count, len(items)),
        "bureaucratic_rate": _ratio(bureaucratic_count, len(items)),
    }


def analyze_human_reactions_csv(path: str | Path) -> dict[str, Any]:
    return analyze_human_reactions(load_human_reaction_csv(path))


def load_nanowhale_readiness_csv(path: str | Path) -> list[NanowhaleReadinessInput]:
    with Path(path).open(encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        required = {
            "domain",
            "sensitive",
            "high_volume",
            "latency_sensitive",
            "repetitive_language",
            "stable_schema",
            "human_review_present",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Nanowhale readiness CSV missing required columns: {', '.join(sorted(missing))}")
        return [
            NanowhaleReadinessInput(
                domain=str(row["domain"]),
                sensitive=_as_bool(row["sensitive"]),
                high_volume=_as_bool(row["high_volume"]),
                latency_sensitive=_as_bool(row["latency_sensitive"]),
                repetitive_language=_as_bool(row["repetitive_language"]),
                stable_schema=_as_bool(row["stable_schema"]),
                human_review_present=_as_bool(row["human_review_present"]),
            )
            for row in reader
        ]


def analyze_nanowhale_readiness(items: list[NanowhaleReadinessInput]) -> dict[str, Any]:
    results = []
    ready_count = 0
    for item in items:
        signals = {
            "sensitive": item.sensitive,
            "high_volume": item.high_volume,
            "latency_sensitive": item.latency_sensitive,
            "repetitive_language": item.repetitive_language,
            "stable_schema": item.stable_schema,
            "human_review_present": item.human_review_present,
        }
        readiness_score = sum(1 for value in signals.values() if value)
        ready = readiness_score >= 4 and item.stable_schema and item.human_review_present
        ready_count += 1 if ready else 0
        results.append(
            {
                "domain": item.domain,
                "readiness_score": readiness_score,
                "ready_for_tiny_model_trial": ready,
                "signals": signals,
            }
        )
    return {
        "status": "ready_for_trial" if ready_count else "defer_tiny_model",
        "domain_count": len(items),
        "ready_domain_count": ready_count,
        "ready_domain_rate": _ratio(ready_count, len(items)),
        "results": results,
    }


def analyze_nanowhale_readiness_csv(path: str | Path) -> dict[str, Any]:
    return analyze_nanowhale_readiness(load_nanowhale_readiness_csv(path))


def run_contract_discovery_experiment(
    pain_csv: str | Path,
    lift_csv: str | Path,
    comparison_csv: str | Path,
    human_csv: str | Path,
    readiness_csv: str | Path,
) -> dict[str, Any]:
    corpus = analyze_pain_finder_csv(pain_csv)
    lift = analyze_contract_lift_csv(lift_csv)
    comparison = analyze_agent_comparison_csv(comparison_csv)
    human = analyze_human_reactions_csv(human_csv)
    readiness = analyze_nanowhale_readiness_csv(readiness_csv)
    catalog_gap = analyze_catalog_gap_evidence(corpus)
    passed = (
        corpus["strong_candidate_rate"] >= 0.3
        and lift["meaningful_lift_rate"] >= 0.5
        and comparison["missed_requirement_reduction"] > 0
        and catalog_gap["catalog_gap_count"] >= 2
        and human["clarifying_rate"] > human["bureaucratic_rate"]
    )
    return {
        "status": "passed" if passed else "needs_more_evidence",
        "corpus": corpus,
        "contract_lift": lift,
        "agent_comparison": comparison,
        "catalog_gap_evidence": catalog_gap,
        "human_reaction": human,
        "nanowhale_readiness": readiness,
        "next_decision": "collect_larger_real_corpus" if passed else "revise_or_narrow_domain",
    }


def analyze_catalog_gap_evidence(corpus: dict[str, Any]) -> dict[str, Any]:
    signals = list(corpus.get("catalog_gap_signals", []))
    by_contract_type: dict[str, int] = {}
    for result in corpus.get("results", []):
        if result.get("candidate_strength") in {"good_candidate", "excellent_candidate"}:
            contract_type = str(result.get("candidate_contract_type", "unknown"))
            by_contract_type[contract_type] = by_contract_type.get(contract_type, 0) + 1
    return {
        "status": "passed" if len(signals) >= 2 else "needs_more_evidence",
        "catalog_gap_count": len(signals),
        "catalog_gap_signals": signals,
        "strong_candidate_contract_types": by_contract_type,
    }


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


def _as_bool(value: Any) -> bool:
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y"}:
        return True
    if normalized in {"0", "false", "no", "n", ""}:
        return False
    raise ValueError(f"Expected boolean-ish CSV value, got {value!r}")


def _ordered_unique(values: list[str] | Any) -> list[str]:
    seen = set()
    unique = []
    for value in values:
        if value not in seen:
            seen.add(value)
            unique.append(value)
    return unique
