"""Phase 5.47 — smart MIDRA Engineering notifications and attention management."""
from __future__ import annotations

ATTENTION_LEVELS = ("CRITICAL", "ACTION_REQUIRED", "INFORMATIONAL", "SUPPRESSED")

ACTION_EVENTS = {
    "AGENCY_REVIEW_RECEIVED",
    "PROPOSAL_REQUIRES_APPROVAL",
    "ENGINEERING_DECISION_REQUIRES_REVIEW",
    "TASK_OVERDUE",
    "DEADLINE_DUE_TODAY",
}
INFO_EVENTS = {
    "DOCUMENT_UPLOADED",
    "DOCUMENT_LINKED",
    "TASK_COMPLETED",
    "SUBMISSION_RECORDED",
}


def classify_attention(*, event: dict, today: str) -> dict:
    """Classify an existing event without changing project state."""
    event_type = event.get("event_type")

    if event_type == "TASK_OVERDUE":
        level = "CRITICAL"
    elif event_type in ACTION_EVENTS:
        level = "ACTION_REQUIRED"
    elif event_type in INFO_EVENTS:
        level = "INFORMATIONAL"
    else:
        level = "SUPPRESSED"

    return {
        "event_id": event.get("event_id"),
        "job_number": event.get("job_number"),
        "event_type": event_type,
        "attention_level": level,
        "title": event.get("title") or _default_title(event_type),
        "link_type": event.get("link_type"),
        "link_id": event.get("link_id"),
        "today": today,
    }


def build_attention_center(*, events: list[dict], today: str) -> dict:
    classified = [classify_attention(event=e, today=today) for e in events]
    visible = [x for x in classified if x["attention_level"] != "SUPPRESSED"]

    critical = [x for x in visible if x["attention_level"] == "CRITICAL"]
    required = [x for x in visible if x["attention_level"] == "ACTION_REQUIRED"]
    info = [x for x in visible if x["attention_level"] == "INFORMATIONAL"]

    return {
        "visibility": "MIDRA_ENGINEERING_PRIVATE",
        "requires_your_attention": critical + required,
        "informational": info,
        "suppressed_count": sum(
            1 for x in classified if x["attention_level"] == "SUPPRESSED"
        ),
        "counts": {
            "critical": len(critical),
            "action_required": len(required),
            "informational": len(info),
        },
    }


def dashboard_attention_badge(*, attention_center: dict) -> dict:
    """Only actionable items contribute to the main interruption badge."""
    count = (
        attention_center["counts"]["critical"]
        + attention_center["counts"]["action_required"]
    )
    return {
        "label": "Requires Your Attention",
        "count": count,
        "show_badge": count > 0,
    }


def notification_delivery_policy(*, attention_item: dict) -> dict:
    """Avoid unnecessary interruptions: routine information stays in-app."""
    level = attention_item["attention_level"]
    if level == "CRITICAL":
        return {"in_app": True, "external_notification_eligible": True}
    if level == "ACTION_REQUIRED":
        return {"in_app": True, "external_notification_eligible": False}
    if level == "INFORMATIONAL":
        return {"in_app": True, "external_notification_eligible": False}
    return {"in_app": False, "external_notification_eligible": False}


def _default_title(event_type: str | None) -> str:
    return {
        "AGENCY_REVIEW_RECEIVED": "Agency review received",
        "PROPOSAL_REQUIRES_APPROVAL": "Proposal requires your approval",
        "ENGINEERING_DECISION_REQUIRES_REVIEW": "Engineering decision requires review",
        "TASK_OVERDUE": "Task overdue",
        "DEADLINE_DUE_TODAY": "Deadline due today",
        "DOCUMENT_UPLOADED": "Document uploaded",
        "DOCUMENT_LINKED": "Document linked",
        "TASK_COMPLETED": "Task completed",
        "SUBMISSION_RECORDED": "Submission recorded",
    }.get(event_type, "Project activity")
