"""Phase 5.45 — efficient MIDRA Engineering dashboard with human-control gates."""
from __future__ import annotations

CONSEQUENTIAL_ACTIONS = {
    "CONFIRM_COMMENT_ADDRESSED",
    "CLOSE_REVIEW_COMMENT",
    "MARK_READY_FOR_SUBMISSION",
    "SEND_PROPOSAL",
    "AUTHORIZE_JOB_CREATION",
    "MARK_PROJECT_APPROVED",
    "MARK_PROJECT_COMPLETED",
}

SAFE_AUTOMATIONS = {
    "RECORD_UPLOAD",
    "LINK_DOCUMENT_TO_JOB",
    "LINK_PROPOSAL_TO_REQUEST",
    "CALCULATE_DASHBOARD_COUNTS",
    "SUGGEST_TASK",
    "SUGGEST_COMMENT_STATUS",
}


def automation_policy(*, action: str) -> dict:
    if action in CONSEQUENTIAL_ACTIONS:
        return {"action": action, "human_authorization_required": True}
    if action in SAFE_AUTOMATIONS:
        return {"action": action, "human_authorization_required": False}
    return {"action": action, "human_authorization_required": True}


def create_review_item(*, job_number: str, item_id: str, item_type: str,
                       title: str, suggested_action: str, basis: list[dict]) -> dict:
    """MIDRA may suggest; official state remains unchanged until authorized."""
    return {
        "job_number": job_number,
        "item_id": item_id,
        "item_type": item_type,
        "title": title,
        "suggested_action": suggested_action,
        "basis": [dict(x) for x in basis],
        "review_status": "REQUIRES_REVIEW",
        "authorized_action": None,
        "authorized_by": None,
    }


def authorize_review_item(*, item: dict, action: str, authorized_by: str) -> dict:
    if not str(authorized_by or "").strip():
        raise ValueError("review decision requires authorized actor")
    result = _copy_item(item)
    result["review_status"] = "REVIEWED"
    result["authorized_action"] = action
    result["authorized_by"] = authorized_by
    return result


def build_engineering_dashboard(*, jobs: list[dict], tasks: list[dict],
                                review_items: list[dict]) -> dict:
    """Surface only actionable operational information; avoid duplicate data entry."""
    rows = []
    for job in jobs:
        number = job["job_number"]
        active_tasks = [
            t for t in tasks
            if t.get("job_number") == number and t.get("status") != "COMPLETED"
        ]
        pending_reviews = [
            r for r in review_items
            if r.get("job_number") == number and r.get("review_status") == "REQUIRES_REVIEW"
        ]
        rows.append({
            "job_number": number,
            "client": job.get("client"),
            "property_address": job.get("property_address"),
            "project_goal": job.get("project_goal"),
            "source": job.get("source"),
            "stage": job.get("current_stage"),
            "next_action": _next_action(active_tasks, pending_reviews),
            "open_task_count": len(active_tasks),
            "requires_review_count": len(pending_reviews),
        })

    pending = [r for r in review_items if r.get("review_status") == "REQUIRES_REVIEW"]
    return {
        "visibility": "MIDRA_ENGINEERING_PRIVATE",
        "jobs": rows,
        "requires_your_review": [_copy_item(r) for r in pending],
        "summary": {
            "active_jobs": len([j for j in jobs if j.get("job_status") == "ACTIVE"]),
            "requires_review": len(pending),
            "open_tasks": len([t for t in tasks if t.get("status") != "COMPLETED"]),
        },
    }


def _next_action(tasks: list[dict], reviews: list[dict]) -> dict | None:
    if reviews:
        r = reviews[0]
        return {"type": "REVIEW", "id": r["item_id"], "title": r["title"]}
    if tasks:
        ordered = sorted(tasks, key=lambda t: (t.get("due_date") is None, t.get("due_date") or "9999-12-31"))
        t = ordered[0]
        return {"type": "TASK", "id": t["task_id"], "title": t["title"]}
    return None


def _copy_item(item: dict) -> dict:
    result = dict(item)
    result["basis"] = [dict(x) for x in item.get("basis", [])]
    return result
