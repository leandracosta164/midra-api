"""Phase 5.62 — cross-project work queue and daily engineering dashboard."""

PRIORITY={"OVERDUE":0,"DUE_SOON":10,"APPROVAL":20,"REVIEW":20,
          "NEXT_ACTION":30,"BLOCKED":40,"WAITING":50}

def build_cross_project_queue(*, project_views):
    """Aggregate existing command-center data; do not create duplicate task records."""
    items=[]
    for view in project_views:
        job=view["job_number"]
        address=view.get("property_address")
        for a in view.get("attention",[]):
            items.append({
                "job_number":job,"property_address":address,
                "type":a.get("type"),"title":a.get("title"),
                "reference":a.get("reference"),
                "attention":a.get("attention"),
                "priority":a.get("priority",PRIORITY.get(a.get("type"),100)),
            })
        for b in view.get("blockers",[]):
            items.append({
                "job_number":job,"property_address":address,
                "type":"BLOCKED",
                "title":b.get("title") or b.get("task_id") or "Blocked project item",
                "reference":b.get("task_id"),
                "priority":PRIORITY["BLOCKED"],
            })
        for w in view.get("waiting",[]):
            items.append({
                "job_number":job,"property_address":address,
                "type":"WAITING",
                "title":w.get("title") or "Waiting item",
                "reference":w.get("task_id"),
                "waiting_for":w.get("waiting_for"),
                "priority":PRIORITY["WAITING"],
            })
    items.sort(key=lambda x:(x["priority"],x["job_number"],x.get("title") or ""))
    return {"visibility":"MIDRA_ENGINEERING_PRIVATE","items":items,"count":len(items)}

def daily_engineering_dashboard(*, project_views):
    queue=build_cross_project_queue(project_views=project_views)
    projects=len(project_views)
    overdue=sum(1 for x in queue["items"] if x.get("attention")=="OVERDUE")
    due_soon=sum(1 for x in queue["items"] if x.get("attention")=="DUE_SOON")
    reviews=sum(1 for x in queue["items"] if x["type"]=="REVIEW")
    approvals=sum(1 for x in queue["items"] if x["type"]=="APPROVAL")
    blocked_jobs=len({x["job_number"] for x in queue["items"] if x["type"]=="BLOCKED"})
    return {
        "visibility":"MIDRA_ENGINEERING_PRIVATE",
        "active_project_count":projects,
        "needs_attention_count":queue["count"],
        "overdue_count":overdue,
        "due_soon_count":due_soon,
        "review_count":reviews,
        "approval_count":approvals,
        "blocked_project_count":blocked_jobs,
        "work_queue":queue["items"],
    }

def top_daily_actions(*, dashboard, limit=5):
    """Keep the dashboard focused instead of overwhelming the engineer."""
    if limit < 1: raise ValueError("limit must be positive")
    return dashboard.get("work_queue",[])[:limit]

def dashboard_policy():
    return {
        "attention_first":True,
        "requires_opening_every_job":False,
        "duplicates_project_tasks":False,
        "automatic_professional_decisions":False,
        "default_top_action_limit":5,
        "manual_daily_dashboard_maintenance":False,
    }
