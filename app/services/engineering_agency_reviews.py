"""Phase 5.43 — agency submissions, review cycles and comment tracking."""
from __future__ import annotations
from datetime import datetime, timezone

COMMENT_STATUSES = {"OPEN", "ADDRESSED", "CLOSED"}


def create_review_cycle(*, job_number: str, cycle_id: str, agency: str,
                        submission_reference: dict, created_by: str,
                        submitted_at: str | None = None) -> dict:
    if any(not str(v or "").strip() for v in (job_number, cycle_id, agency, created_by)):
        raise ValueError("review cycle requires job, cycle, agency and creator")
    if not submission_reference.get("artifact_id"):
        raise ValueError("review cycle requires exact submission artifact")
    return {
        "job_number": job_number,
        "cycle_id": cycle_id,
        "agency": agency,
        "submission_reference": dict(submission_reference),
        "submitted_at": submitted_at,
        "review_letters": [],
        "comments": [],
        "created_by": created_by,
    }


def attach_review_letter(*, cycle: dict, artifact_id: str, filename: str,
                         sha256: str, received_at: str, recorded_by: str) -> dict:
    result = _copy_cycle(cycle)
    result["review_letters"].append({
        "artifact_id": artifact_id, "filename": filename, "sha256": sha256,
        "received_at": received_at, "recorded_by": recorded_by,
    })
    return result


def add_review_comment(*, cycle: dict, comment_id: str, text: str,
                       review_letter_artifact_id: str, recorded_by: str) -> dict:
    if not text.strip():
        raise ValueError("review comment text required")
    if not any(x["artifact_id"] == review_letter_artifact_id for x in cycle["review_letters"]):
        raise ValueError("comment must reference a review letter in this cycle")
    result = _copy_cycle(cycle)
    result["comments"].append({
        "comment_id": comment_id,
        "text": text,
        "review_letter_artifact_id": review_letter_artifact_id,
        "status": "OPEN",
        "responses": [],
        "recorded_by": recorded_by,
    })
    return result


def address_review_comment(*, cycle: dict, comment_id: str, response_text: str,
                           response_artifact_id: str, revised_artifact_ids: list[str],
                           authorized_by: str, occurred_at: str | None = None) -> dict:
    result = _copy_cycle(cycle)
    comment = _comment(result, comment_id)
    if comment["status"] == "CLOSED":
        raise ValueError("closed comment cannot be re-addressed")
    comment["responses"].append({
        "response_text": response_text,
        "response_artifact_id": response_artifact_id,
        "revised_artifact_ids": list(revised_artifact_ids),
        "authorized_by": authorized_by,
        "occurred_at": occurred_at or datetime.now(timezone.utc).isoformat(),
    })
    comment["status"] = "ADDRESSED"
    return result


def close_review_comment(*, cycle: dict, comment_id: str, closed_by: str,
                         closed_at: str | None = None) -> dict:
    result = _copy_cycle(cycle)
    comment = _comment(result, comment_id)
    if comment["status"] != "ADDRESSED":
        raise ValueError("comment must be addressed before closure")
    comment["status"] = "CLOSED"
    comment["closed_by"] = closed_by
    comment["closed_at"] = closed_at or datetime.now(timezone.utc).isoformat()
    return result


def review_workspace_projection(*, cycles: list[dict]) -> dict:
    all_comments = [c for cycle in cycles for c in cycle.get("comments", [])]
    return {
        "visibility": "MIDRA_ENGINEERING_PRIVATE",
        "cycles": [_copy_cycle(c) for c in cycles],
        "comment_counts": {
            status: sum(1 for c in all_comments if c.get("status") == status)
            for status in ("OPEN", "ADDRESSED", "CLOSED")
        },
    }


def _comment(cycle: dict, comment_id: str) -> dict:
    for comment in cycle["comments"]:
        if comment["comment_id"] == comment_id:
            return comment
    raise ValueError("review comment not found")


def _copy_cycle(cycle: dict) -> dict:
    result = {k: v for k, v in cycle.items() if k not in {"review_letters", "comments"}}
    result["submission_reference"] = dict(cycle.get("submission_reference", {}))
    result["review_letters"] = [dict(x) for x in cycle.get("review_letters", [])]
    result["comments"] = []
    for c in cycle.get("comments", []):
        nc = {k: v for k, v in c.items() if k != "responses"}
        nc["responses"] = [
            {**r, "revised_artifact_ids": list(r.get("revised_artifact_ids", []))}
            for r in c.get("responses", [])
        ]
        result["comments"].append(nc)
    return result
