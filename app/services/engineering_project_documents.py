"""Phase 5.42 — Engineering project documents, versions, submissions and deliverables."""
from __future__ import annotations
from datetime import datetime, timezone

DOCUMENT_TYPES = {
    "PLAN", "CALCULATION", "REPORT", "APPLICATION",
    "SUBMISSION_PACKAGE", "AGENCY_COMMENT", "RESPONSE",
    "FINAL_DELIVERABLE", "OTHER",
}


def create_document_record(*, job_number: str, document_id: str, document_type: str,
                           title: str, created_by: str) -> dict:
    if document_type not in DOCUMENT_TYPES:
        raise ValueError("unsupported Engineering document type")
    if any(not str(v or "").strip() for v in (job_number, document_id, title, created_by)):
        raise ValueError("document record requires job, id, title and creator")
    return {
        "job_number": job_number,
        "document_id": document_id,
        "document_type": document_type,
        "title": title,
        "versions": [],
        "current_version": None,
        "created_by": created_by,
    }


def add_document_version(*, document: dict, artifact_id: str, filename: str,
                         sha256: str, created_by: str, created_at: str | None = None) -> dict:
    if any(not str(v or "").strip() for v in (artifact_id, filename, sha256, created_by)):
        raise ValueError("document version requires artifact identity")
    result = _copy(document)
    number = len(result["versions"]) + 1
    for version in result["versions"]:
        version["is_current"] = False
        if version["status"] == "CURRENT":
            version["status"] = "SUPERSEDED"
    version = {
        "version": number,
        "artifact_id": artifact_id,
        "filename": filename,
        "sha256": sha256,
        "created_by": created_by,
        "created_at": created_at or datetime.now(timezone.utc).isoformat(),
        "status": "CURRENT",
        "is_current": True,
        "submissions": [],
    }
    result["versions"].append(version)
    result["current_version"] = number
    return result


def record_submission(*, document: dict, version: int, recipient: str,
                      submission_type: str, submitted_by: str,
                      submitted_at: str | None = None) -> dict:
    result = _copy(document)
    target = _version(result, version)
    if not recipient.strip() or not submitted_by.strip():
        raise ValueError("submission requires recipient and authorized actor")
    target["submissions"].append({
        "recipient": recipient,
        "submission_type": submission_type,
        "submitted_by": submitted_by,
        "submitted_at": submitted_at or datetime.now(timezone.utc).isoformat(),
        "artifact_id": target["artifact_id"],
        "sha256": target["sha256"],
        "version": version,
    })
    return result


def mark_final_deliverable(*, document: dict, version: int, authorized_by: str) -> dict:
    if not authorized_by.strip():
        raise ValueError("final deliverable designation requires authorized actor")
    result = _copy(document)
    target = _version(result, version)
    target["final_deliverable"] = True
    target["finalized_by"] = authorized_by
    return result


def document_workspace_projection(*, documents: list[dict]) -> dict:
    return {
        "visibility": "MIDRA_ENGINEERING_PRIVATE",
        "documents": [_copy(d) for d in documents],
        "current_artifacts": [
            {
                "document_id": d["document_id"],
                "version": d["current_version"],
                "artifact_id": next(
                    (v["artifact_id"] for v in d["versions"] if v["is_current"]), None
                ),
            }
            for d in documents
        ],
    }


def _version(document: dict, number: int) -> dict:
    for version in document["versions"]:
        if version["version"] == number:
            return version
    raise ValueError("document version not found")


def _copy(document: dict) -> dict:
    result = {k: v for k, v in document.items() if k != "versions"}
    result["versions"] = []
    for v in document.get("versions", []):
        nv = {k: val for k, val in v.items() if k != "submissions"}
        nv["submissions"] = [dict(s) for s in v.get("submissions", [])]
        result["versions"].append(nv)
    return result
