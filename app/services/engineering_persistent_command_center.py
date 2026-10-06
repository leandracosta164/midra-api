"""Persistent MIDRA Engineering Command Center projection."""
from app.repositories.engineering_job import SQLAlchemyEngineeringJobRepository

LEVELS={"INFO":1,"NORMAL":2,"ATTENTION":3,"URGENT":4}

def job_to_command_center_card(job):
    sections=job.sections or {}
    events=job.events or []
    signals=(sections.get("command_center") or {}).get("summary",{}).get("signals",[])
    open_signals=[s for s in signals if not s.get("resolved")]
    pending=(sections.get("command_center") or {}).get("summary",{}).get("pending_approvals",[])
    highest=max((LEVELS.get(s.get("level","NORMAL"),2) for s in open_signals),default=1)
    reverse={v:k for k,v in LEVELS.items()}
    actionable=sorted(
        [s for s in open_signals if s.get("requires_user_action")],
        key=lambda s:(-LEVELS.get(s.get("level","NORMAL"),2),s.get("due_at") or "9999")
    )
    waiting=[s for s in open_signals if s.get("waiting_on")]
    if pending:
        nxt={"type":"APPROVAL_REQUIRED","message":pending[0].get("action"),
             "reference_id":pending[0].get("reference_id")}
    elif actionable:
        s=actionable[0]
        nxt={"type":"USER_ACTION","message":s.get("message"),
             "reference_id":s.get("reference_id")}
    elif waiting:
        s=waiting[0]
        nxt={"type":"WAITING","message":s.get("message"),
             "waiting_on":s.get("waiting_on"),"reference_id":s.get("reference_id")}
    else:
        nxt={"type":"NO_IMMEDIATE_ACTION","message":"No immediate action required."}
    return {
        "job_number":job.job_number,"project_name":job.project_name,
        "project_type":job.project_type,"project_state":job.state,
        "attention":reverse[highest],"open_signal_count":len(open_signals),
        "pending_approval_count":len(pending),"next_action":nxt,
        "event_count":len(events),"version":job.version,
    }

def persistent_command_center(db,state=None):
    repo=SQLAlchemyEngineeringJobRepository(db)
    cards=[job_to_command_center_card(j) for j in repo.list_jobs(state=state)]
    cards.sort(key=lambda c:(
        -LEVELS[c["attention"]],-c["pending_approval_count"],c["job_number"]))
    return {
        "project_count":len(cards),
        "needs_attention":sum(
            c["attention"] in {"ATTENTION","URGENT"} or c["pending_approval_count"]>0
            for c in cards),
        "cards":cards,
    }
