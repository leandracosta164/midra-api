"""Phase 5.39 — controlled accepted-proposal to Engineering-project transition."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json


def create_engineering_project_candidate(
    *,
    response_record: dict,
    proposal: dict,
    engineering_intake: dict,
    authorized_by: str,
    created_at: str | None = None,
) -> dict:
    """Create an Engineering project only from the exact accepted proposal lineage."""
    if response_record.get("response") != "ACCEPTED":
        raise ValueError("engineering project requires an accepted proposal")
    if not str(authorized_by or "").strip():
        raise ValueError("engineering project creation requires authorized actor")

    proposal_id = proposal.get("proposal_id")
    if response_record.get("proposal_id") != proposal_id:
        raise ValueError("accepted response does not match proposal")

    for key in ("release_id", "artifact_id", "pdf_sha256"):
        proposal_value = proposal.get(key)
        response_value = response_record.get(key)
        if not proposal_value or proposal_value != response_value:
            raise ValueError(f"accepted proposal lineage mismatch: {key}")

    intake_proposal = engineering_intake.get("proposal_id")
    if intake_proposal and intake_proposal != proposal_id:
        raise ValueError("engineering intake does not match accepted proposal")

    project = {
        "project_status": "ACTIVE",
        "proposal_id": proposal_id,
        "release_id": response_record["release_id"],
        "accepted_artifact_id": response_record["artifact_id"],
        "accepted_pdf_sha256": response_record["pdf_sha256"],
        "accepted_at": response_record.get("responded_at"),
        "created_at": created_at or datetime.now(timezone.utc).isoformat(),
        "created_by": authorized_by,
        "client": engineering_intake.get("client"),
        "property_record_id": engineering_intake.get("property_record_id"),
        "analysis_id": engineering_intake.get("analysis_id"),
        "analysis_snapshot_id": engineering_intake.get("analysis_snapshot_id"),
        "project_goal": engineering_intake.get("project_goal"),
        "scope_snapshot": _copy_scope(proposal.get("scope_of_services", [])),
        "proposal_total": proposal.get("total"),
        "evidence_access": "LINKED_SHARED_MIDRA_PLATFORM",
        "research_reuse": True,
    }
    project["project_fingerprint"] = _fingerprint(project)
    return project


def _copy_scope(scope: list[dict]) -> list[dict]:
    return [dict(item) for item in scope]


def _fingerprint(project: dict) -> str:
    stable = {k: v for k, v in project.items() if k != "project_fingerprint"}
    raw = json.dumps(stable, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(raw).hexdigest()


def validate_engineering_project_lineage(*, project: dict, response_record: dict) -> bool:
    """Verify the active project still points to the exact accepted proposal artifact."""
    return all([
        project.get("proposal_id") == response_record.get("proposal_id"),
        project.get("release_id") == response_record.get("release_id"),
        project.get("accepted_artifact_id") == response_record.get("artifact_id"),
        project.get("accepted_pdf_sha256") == response_record.get("pdf_sha256"),
        response_record.get("response") == "ACCEPTED",
    ])


def project_workspace_projection(*, project: dict) -> dict:
    """Private Engineering workspace view; shared intelligence stays linked, not duplicated."""
    return {
        "visibility": "MIDRA_ENGINEERING_PRIVATE",
        "project_status": project.get("project_status"),
        "client": project.get("client"),
        "property_record_id": project.get("property_record_id"),
        "analysis_id": project.get("analysis_id"),
        "analysis_snapshot_id": project.get("analysis_snapshot_id"),
        "project_goal": project.get("project_goal"),
        "scope_snapshot": _copy_scope(project.get("scope_snapshot", [])),
        "proposal_total": project.get("proposal_total"),
        "accepted_proposal": {
            "proposal_id": project.get("proposal_id"),
            "release_id": project.get("release_id"),
            "artifact_id": project.get("accepted_artifact_id"),
            "pdf_sha256": project.get("accepted_pdf_sha256"),
        },
        "evidence_access": project.get("evidence_access"),
        "research_reuse": project.get("research_reuse"),
    }
