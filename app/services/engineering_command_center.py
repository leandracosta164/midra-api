"""MIDRA Engineering Milestone 6.1 — Command Center & Project Operations.

A larger product milestone: one concise operating view over adaptive workflows,
design activity, reviews, client dependencies, deadlines, billing and approvals.
It recommends/organizes; it does not silently make professional decisions.
"""

ATTENTION_LEVELS={"INFO":1,"NORMAL":2,"ATTENTION":3,"URGENT":4}
PROJECT_STATES={"ACTIVE","WAITING","ON_HOLD","READY_FOR_REVIEW","CLOSEOUT","CLOSED"}

def create_project_operations(*, job_number, project_name, project_type,
                              project_state="ACTIVE", active_workstreams=None):
    if project_state not in PROJECT_STATES:
        raise ValueError("unsupported project state")
    return {
        "job_number":job_number,"project_name":project_name,
        "project_type":project_type,"project_state":project_state,
        "active_workstreams":list(active_workstreams or []),
        "signals":[],"approvals":[],"activity":[],
    }

def record_signal(*, project, signal_id, category, message, level="NORMAL",
                  due_at=None, waiting_on=None, reference_id=None,
                  requires_user_action=False):
    if level not in ATTENTION_LEVELS:
        raise ValueError("unsupported attention level")
    r=_copy(project)
    r["signals"]=[x for x in r["signals"] if x["signal_id"]!=signal_id]
    r["signals"].append({
        "signal_id":signal_id,"category":category,"message":message,"level":level,
        "due_at":due_at,"waiting_on":waiting_on,"reference_id":reference_id,
        "requires_user_action":requires_user_action,"resolved":False,
    })
    return r

def resolve_signal(*, project, signal_id, authorized_by):
    if not (authorized_by or "").strip():
        raise ValueError("authorization required")
    r=_copy(project)
    s=_signal(r,signal_id)
    s["resolved"]=True
    s["resolved_by"]=authorized_by
    return r

def request_approval(*, project, approval_id, action, reference_id):
    r=_copy(project)
    r["approvals"].append({
        "approval_id":approval_id,"action":action,"reference_id":reference_id,
        "status":"REQUIRES_APPROVAL","authorized_by":None,
    })
    return r

def authorize_action(*, project, approval_id, authorized_by):
    if not (authorized_by or "").strip():
        raise ValueError("authorization required")
    r=_copy(project)
    a=_approval(r,approval_id)
    a["status"]="AUTHORIZED"; a["authorized_by"]=authorized_by
    return r

def record_activity(*, project, activity_type, summary, reference_id=None):
    r=_copy(project)
    r["activity"].append({"activity_type":activity_type,"summary":summary,
                          "reference_id":reference_id})
    return r

def next_action(*, project):
    open_signals=[x for x in project["signals"] if not x.get("resolved")]
    actionable=[x for x in open_signals if x.get("requires_user_action")]
    pending=[x for x in project["approvals"] if x["status"]=="REQUIRES_APPROVAL"]

    if pending:
        return {"type":"APPROVAL_REQUIRED","message":pending[0]["action"],
                "reference_id":pending[0]["reference_id"]}

    if actionable:
        actionable=sorted(
            actionable,
            key=lambda x:(-ATTENTION_LEVELS[x["level"]], x.get("due_at") or "9999")
        )
        x=actionable[0]
        return {"type":"USER_ACTION","message":x["message"],
                "reference_id":x.get("reference_id")}

    waiting=[x for x in open_signals if x.get("waiting_on")]
    if waiting:
        x=waiting[0]
        return {"type":"WAITING","message":x["message"],
                "waiting_on":x["waiting_on"],"reference_id":x.get("reference_id")}

    return {"type":"NO_IMMEDIATE_ACTION","message":"No immediate action required."}

def command_center_card(*, project):
    open_signals=[x for x in project["signals"] if not x.get("resolved")]
    highest=max((ATTENTION_LEVELS[x["level"]] for x in open_signals),default=1)
    reverse={v:k for k,v in ATTENTION_LEVELS.items()}
    return {
        "job_number":project["job_number"],
        "project_name":project["project_name"],
        "project_type":project["project_type"],
        "project_state":project["project_state"],
        "active_workstreams":list(project["active_workstreams"]),
        "attention":reverse[highest],
        "open_signal_count":len(open_signals),
        "pending_approval_count":sum(
            x["status"]=="REQUIRES_APPROVAL" for x in project["approvals"]),
        "next_action":next_action(project=project),
    }

def command_center_dashboard(*, projects):
    cards=[command_center_card(project=x) for x in projects]
    cards.sort(key=lambda x:(
        -ATTENTION_LEVELS[x["attention"]],
        -x["pending_approval_count"],
        x["job_number"]
    ))
    return {
        "project_count":len(cards),
        "needs_attention":sum(
            x["attention"] in {"ATTENTION","URGENT"} or x["pending_approval_count"]>0
            for x in cards),
        "cards":cards,
    }

def _signal(project,signal_id):
    for x in project["signals"]:
        if x["signal_id"]==signal_id: return x
    raise KeyError(signal_id)

def _approval(project,approval_id):
    for x in project["approvals"]:
        if x["approval_id"]==approval_id: return x
    raise KeyError(approval_id)

def _copy(project):
    r=dict(project)
    r["active_workstreams"]=list(project.get("active_workstreams",[]))
    r["signals"]=[dict(x) for x in project.get("signals",[])]
    r["approvals"]=[dict(x) for x in project.get("approvals",[])]
    r["activity"]=[dict(x) for x in project.get("activity",[])]
    return r

def command_center_policy():
    return {
        "one_concise_operating_view":True,
        "small_projects_are_not_forced_into_extra_steps":True,
        "signals_can_come_from_multiple_subsystems":True,
        "professional_actions_remain_approval_gated":True,
        "waiting_dependencies_are_visible":True,
        "resolved_items_leave_active_attention":True,
    }
