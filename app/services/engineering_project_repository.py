"""Phase 5.49 — persistent Job Database and managed project repository foundation."""
from __future__ import annotations
from datetime import datetime, timezone

REPOSITORY_AREAS = {
    "PROPERTY", "PROPOSAL", "DESIGN", "SUBMISSIONS",
    "AGENCY_REVIEWS", "RESPONSES", "FINAL", "OTHER",
}


def create_job_repository(*, job_number: str, property_address: str,
                          created_by: str, created_at: str | None = None) -> dict:
    if any(not str(v or "").strip() for v in (job_number, property_address, created_by)):
        raise ValueError("repository requires job number, property and creator")
    return {
        "job_number": job_number,
        "property_address": property_address,
        "repository_id": f"REPO:{job_number}",
        "storage_scope": "MIDRA_MANAGED_PROJECT_STORAGE",
        "created_by": created_by,
        "created_at": created_at or datetime.now(timezone.utc).isoformat(),
        "documents": [],
    }


def register_project_document(*, repository: dict, document_id: str,
                              artifact_id: str, filename: str, sha256: str,
                              area: str, uploaded_by: str,
                              classification_source: str = "USER_CONFIRMED") -> dict:
    if area not in REPOSITORY_AREAS:
        raise ValueError("unsupported repository area")
    if any(not str(v or "").strip() for v in
           (document_id, artifact_id, filename, sha256, uploaded_by)):
        raise ValueError("document registration requires artifact identity")
    result = _copy(repository)
    result["documents"].append({
        "document_id": document_id,
        "artifact_id": artifact_id,
        "filename": filename,
        "sha256": sha256,
        "area": area,
        "classification_source": classification_source,
        "uploaded_by": uploaded_by,
        "job_number": repository["job_number"],
    })
    return result


def suggest_document_classification(*, filename: str, extracted_text: str = "") -> dict:
    """Low-risk filing suggestion only; user can confirm/correct before registration."""
    text = f"{filename} {extracted_text}".lower()
    if "review" in text or "comment" in text:
        area, label = "AGENCY_REVIEWS", "Agency Review"
    elif "response" in text:
        area, label = "RESPONSES", "Response"
    elif "proposal" in text or "estimate" in text:
        area, label = "PROPOSAL", "Proposal"
    elif "tax map" in text or "zoning map" in text:
        area, label = "PROPERTY", "Property Document"
    elif "final" in text or "approved" in text:
        area, label = "FINAL", "Final Deliverable"
    elif "plan" in text or "calculation" in text or "report" in text:
        area, label = "DESIGN", "Design Document"
    else:
        area, label = "OTHER", "Unclassified Document"
    return {"suggested_area": area, "suggested_label": label, "requires_confirmation": True}


def job_database_record(*, job: dict, repository: dict) -> dict:
    if job["job_number"] != repository["job_number"]:
        raise ValueError("repository does not belong to job")
    return {
        "job_number": job["job_number"],
        "client": job.get("client"),
        "property_address": job.get("property_address"),
        "project_goal": job.get("project_goal"),
        "source": job.get("source"),
        "job_status": job.get("job_status"),
        "current_stage": job.get("current_stage"),
        "repository_id": repository["repository_id"],
        "document_count": len(repository["documents"]),
    }


def repository_projection(*, repository: dict) -> dict:
    grouped = {area: [] for area in REPOSITORY_AREAS}
    for document in repository["documents"]:
        grouped[document["area"]].append(dict(document))
    return {
        "visibility": "MIDRA_ENGINEERING_PRIVATE",
        "job_number": repository["job_number"],
        "repository_id": repository["repository_id"],
        "storage_scope": repository["storage_scope"],
        "areas": grouped,
    }


def local_computer_access_policy() -> dict:
    """MIDRA web storage must not imply unrestricted access to the user's computer."""
    return {
        "unrestricted_local_file_access": False,
        "supported_ingest": ["USER_UPLOAD", "DRAG_AND_DROP", "AUTHORIZED_INTEGRATION"],
        "integration_requires_explicit_authorization": True,
    }


def _copy(repository: dict) -> dict:
    result = {k: v for k, v in repository.items() if k != "documents"}
    result["documents"] = [dict(x) for x in repository.get("documents", [])]
    return result
