"""Phase 5.60 — deadlines, submissions, waiting periods and follow-up intelligence."""
from datetime import datetime, timedelta

EVENT_TYPES={"SUBMISSION_DEADLINE","CLIENT_COMMITMENT","AGENCY_FOLLOWUP","REVIEW_WAIT","OTHER"}
EVENT_STATES={"OPEN","WAITING","COMPLETED","CANCELLED"}

def create_time_event(*,event_id,job_number,title,event_type,due_at=None,status="OPEN",
                      related_task_id=None,follow_up_after_days=None,source=None):
    if event_type not in EVENT_TYPES: raise ValueError("unsupported event type")
    if status not in EVENT_STATES: raise ValueError("unsupported event state")
    return {"event_id":event_id,"job_number":job_number,"title":title,"event_type":event_type,
            "due_at":due_at,"status":status,"related_task_id":related_task_id,
            "follow_up_after_days":follow_up_after_days,"source":source}

def derive_followup_due_at(*,submitted_at,follow_up_after_days):
    dt=datetime.fromisoformat(submitted_at)
    return (dt+timedelta(days=int(follow_up_after_days))).isoformat()

def time_attention(*,event,now):
    if event.get("status") in {"COMPLETED","CANCELLED"}:
        return {"event_id":event["event_id"],"attention":"NONE","days_remaining":None}
    due=event.get("due_at")
    if not due:
        return {"event_id":event["event_id"],"attention":"NO_DATE","days_remaining":None}
    current=datetime.fromisoformat(now); target=datetime.fromisoformat(due)
    seconds=(target-current).total_seconds()
    days=int(seconds//86400) if seconds>=0 else -int(abs(seconds)//86400 or 1)
    if seconds < 0: level="OVERDUE"
    elif seconds <= 3*86400: level="DUE_SOON"
    else: level="UPCOMING"
    return {"event_id":event["event_id"],"attention":level,"days_remaining":days}

def complete_time_event(*,event,authorized_by):
    if not authorized_by.strip(): raise ValueError("completion requires authorized human")
    r=dict(event); r["status"]="COMPLETED"; r["completed_by"]=authorized_by; return r

def project_time_command_view(*,job_number,events,now):
    relevant=[e for e in events if e["job_number"]==job_number]
    items=[{**dict(e),**time_attention(event=e,now=now)} for e in relevant]
    rank={"OVERDUE":0,"DUE_SOON":1,"UPCOMING":2,"NO_DATE":3,"NONE":4}
    items.sort(key=lambda x:(rank[x["attention"]],x.get("due_at") or "9999"))
    return {"job_number":job_number,
            "attention_items":[x for x in items if x["attention"]!="NONE"],
            "overdue_count":sum(x["attention"]=="OVERDUE" for x in items),
            "due_soon_count":sum(x["attention"]=="DUE_SOON" for x in items)}

def smart_time_next_action(*,job_number,events,now):
    view=project_time_command_view(job_number=job_number,events=events,now=now)
    if not view["attention_items"]:
        return {"status":"NO_TIME_SENSITIVE_ACTION"}
    x=view["attention_items"][0]
    if x["attention"]=="OVERDUE" and x["event_type"]=="AGENCY_FOLLOWUP":
        action=f'Follow up: {x["title"]}'
    elif x["attention"] in {"OVERDUE","DUE_SOON"}:
        action=x["title"]
    else:
        action=f'Monitor: {x["title"]}'
    return {"status":"TIME_SENSITIVE_ACTION","event_id":x["event_id"],
            "action":action,"attention":x["attention"]}

def deadline_policy():
    return {"automatic_deadline_invention":False,
            "source_dates_must_be_preserved":True,
            "professional_completion_requires_human_confirmation":True,
            "manual_calendar_maintenance_required":False}
