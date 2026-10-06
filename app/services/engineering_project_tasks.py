"""Phase 5.44 — MIDRA Engineering tasks, deadlines and action items."""
from __future__ import annotations
from datetime import datetime, timezone

TASK_STATUSES = {"PENDING", "IN_PROGRESS", "COMPLETED"}
TASK_PRIORITIES = {"LOW", "NORMAL", "HIGH", "URGENT"}
LINK_TYPES = {"REVIEW_COMMENT", "DOCUMENT", "SUBMISSION", "MILESTONE", "GENERAL"}


def create_project_task(*, job_number: str, task_id: str, title: str,
                        assigned_to: str, priority: str = "NORMAL",
                        due_date: str | None = None, link_type: str = "GENERAL",
                        link_id: str | None = None, created_by: str,
                        created_at: str | None = None) -> dict:
    if priority not in TASK_PRIORITIES:
        raise ValueError("unsupported task priority")
    if link_type not in LINK_TYPES:
        raise ValueError("unsupported task link type")
    if link_type != "GENERAL" and not str(link_id or "").strip():
        raise ValueError("linked task requires link_id")
    if any(not str(v or "").strip() for v in
           (job_number, task_id, title, assigned_to, created_by)):
        raise ValueError("task requires job, id, title, assignee and creator")
    return {
        "job_number": job_number,
        "task_id": task_id,
        "title": title,
        "assigned_to": assigned_to,
        "priority": priority,
        "due_date": due_date,
        "status": "PENDING",
        "link_type": link_type,
        "link_id": link_id,
        "created_by": created_by,
        "created_at": created_at or datetime.now(timezone.utc).isoformat(),
        "history": [],
    }


def update_task_status(*, task: dict, status: str, authorized_by: str,
                       occurred_at: str | None = None) -> dict:
    if status not in TASK_STATUSES:
        raise ValueError("unsupported task status")
    if not str(authorized_by or "").strip():
        raise ValueError("task status change requires authorized actor")
    result = _copy(task)
    previous = result["status"]
    result["status"] = status
    result["history"].append({
        "event": "STATUS_CHANGED",
        "from": previous,
        "to": status,
        "authorized_by": authorized_by,
        "occurred_at": occurred_at or datetime.now(timezone.utc).isoformat(),
    })
    if status == "COMPLETED":
        result["completed_at"] = occurred_at or datetime.now(timezone.utc).isoformat()
        result["completed_by"] = authorized_by
    return result


def reassign_task(*, task: dict, assigned_to: str, authorized_by: str) -> dict:
    if not assigned_to.strip() or not authorized_by.strip():
        raise ValueError("task reassignment requires assignee and authorized actor")
    result = _copy(task)
    previous = result["assigned_to"]
    result["assigned_to"] = assigned_to
    result["history"].append({
        "event": "REASSIGNED", "from": previous, "to": assigned_to,
        "authorized_by": authorized_by,
    })
    return result


def project_action_items(*, job_number: str, tasks: list[dict], today: str) -> dict:
    scoped = [t for t in tasks if t.get("job_number") == job_number]
    active = [t for t in scoped if t.get("status") != "COMPLETED"]
    overdue = [
        t for t in active
        if t.get("due_date") and t["due_date"] < today
    ]
    due_today = [
        t for t in active
        if t.get("due_date") == today
    ]
    return {
        "visibility": "MIDRA_ENGINEERING_PRIVATE",
        "job_number": job_number,
        "next_actions": [_summary(t) for t in _sort(active)],
        "overdue": [_summary(t) for t in _sort(overdue)],
        "due_today": [_summary(t) for t in _sort(due_today)],
        "completed_count": sum(1 for t in scoped if t.get("status") == "COMPLETED"),
    }


def _sort(tasks: list[dict]) -> list[dict]:
    priority_order = {"URGENT": 0, "HIGH": 1, "NORMAL": 2, "LOW": 3}
    return sorted(
        tasks,
        key=lambda t: (
            t.get("due_date") is None,
            t.get("due_date") or "9999-12-31",
            priority_order.get(t.get("priority"), 9),
            t.get("task_id", ""),
        ),
    )


def _summary(task: dict) -> dict:
    return {
        k: task.get(k) for k in (
            "task_id", "title", "assigned_to", "priority", "due_date",
            "status", "link_type", "link_id"
        )
    }


def _copy(task: dict) -> dict:
    result = {k: v for k, v in task.items() if k != "history"}
    result["history"] = [dict(x) for x in task.get("history", [])]
    return result
