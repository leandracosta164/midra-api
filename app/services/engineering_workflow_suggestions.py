"""Phase 5.46 — smart Engineering workflow suggestions with human-control gates."""
from __future__ import annotations

SUPPORTED_EVENTS = {
    "REVIEW_LETTER_RECEIVED",
    "REVIEW_COMMENTS_EXTRACTED",
    "PROPOSAL_ACCEPTED",
    "DOCUMENT_REVISION_CREATED",
    "SUBMISSION_RECORDED",
}

CONSEQUENTIAL_SUGGESTIONS = {
    "CONFIRM_COMMENT_ADDRESSED",
    "MARK_READY_FOR_SUBMISSION",
    "CLOSE_REVIEW_COMMENT",
    "MARK_PROJECT_COMPLETED",
}


def suggest_actions_from_event(*, job_number: str, event: dict) -> list[dict]:
    """Suggest useful next work from existing project events; never execute it."""
    event_type = event.get("event_type")
    if event_type not in SUPPORTED_EVENTS:
        return []

    suggestions = []

    if event_type == "REVIEW_LETTER_RECEIVED":
        suggestions.append(_suggest(
            job_number, event, "EXTRACT_REVIEW_COMMENTS",
            "Review agency letter and extract individual comments", False,
        ))

    elif event_type == "REVIEW_COMMENTS_EXTRACTED":
        for comment in event.get("comments", []):
            suggestions.append(_suggest(
                job_number, event, "CREATE_COMMENT_ACTION_ITEM",
                f"Address {comment.get('comment_id')}: {comment.get('summary', 'Review comment')}",
                False,
                link_type="REVIEW_COMMENT", link_id=comment.get("comment_id"),
            ))
        suggestions.extend([
            _suggest(job_number, event, "PREPARE_REVISED_DOCUMENTS",
                     "Prepare revisions addressing review comments", False),
            _suggest(job_number, event, "PREPARE_RESPONSE_LETTER",
                     "Prepare response letter for review comments", False),
        ])

    elif event_type == "PROPOSAL_ACCEPTED":
        suggestions.append(_suggest(
            job_number, event, "AUTHORIZE_JOB_SETUP",
            "Review accepted proposal and authorize Engineering job setup", True,
        ))

    elif event_type == "DOCUMENT_REVISION_CREATED":
        suggestions.append(_suggest(
            job_number, event, "REVIEW_DOCUMENT_REVISION",
            "Review revised document before changing any official project state", True,
            link_type="DOCUMENT", link_id=event.get("document_id"),
        ))

    elif event_type == "SUBMISSION_RECORDED":
        suggestions.append(_suggest(
            job_number, event, "AWAIT_AGENCY_REVIEW",
            "Track agency review for the recorded submission", False,
            link_type="SUBMISSION", link_id=event.get("submission_id"),
        ))

    return suggestions


def accept_suggestion_as_task(*, suggestion: dict, task_id: str,
                              assigned_to: str, due_date: str | None,
                              authorized_by: str) -> dict:
    """Human accepts a suggestion before it becomes a real task."""
    if not authorized_by.strip() or not assigned_to.strip():
        raise ValueError("suggestion acceptance requires authorized actor and assignee")
    return {
        "job_number": suggestion["job_number"],
        "task_id": task_id,
        "title": suggestion["title"],
        "assigned_to": assigned_to,
        "priority": "NORMAL",
        "due_date": due_date,
        "status": "PENDING",
        "link_type": suggestion.get("link_type", "GENERAL"),
        "link_id": suggestion.get("link_id"),
        "origin": "MIDRA_SUGGESTION",
        "suggestion_id": suggestion["suggestion_id"],
        "accepted_by": authorized_by,
    }


def suggestion_review_queue(*, suggestions: list[dict]) -> dict:
    """Only consequential suggestions enter the mandatory human-review queue."""
    required = [dict(s) for s in suggestions if s.get("human_authorization_required")]
    optional = [dict(s) for s in suggestions if not s.get("human_authorization_required")]
    return {
        "visibility": "MIDRA_ENGINEERING_PRIVATE",
        "requires_your_review": required,
        "suggested_actions": optional,
    }


def _suggest(job_number, event, action, title, human_required,
             link_type="GENERAL", link_id=None):
    event_id = str(event.get("event_id") or event.get("event_type"))
    return {
        "suggestion_id": f"{event_id}:{action}:{link_id or 'GENERAL'}",
        "job_number": job_number,
        "source_event_id": event_id,
        "action": action,
        "title": title,
        "link_type": link_type,
        "link_id": link_id,
        "human_authorization_required": human_required or action in CONSEQUENTIAL_SUGGESTIONS,
        "status": "SUGGESTED",
    }
