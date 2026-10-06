"""Phase 5.59 — milestones, dependencies, blockers and smart next action."""

TASK_STATES={"NOT_STARTED","READY","IN_PROGRESS","WAITING","COMPLETED","NOT_REQUIRED"}

def create_project_task(*,task_id,title,category,dependencies=None,status="NOT_STARTED",
                        requires_human_completion=False,priority=100):
    if status not in TASK_STATES: raise ValueError("unsupported task state")
    return {"task_id":task_id,"title":title,"category":category,
            "dependencies":list(dependencies or []),"status":status,
            "requires_human_completion":bool(requires_human_completion),
            "priority":int(priority)}

def evaluate_task_readiness(*,tasks):
    """Derive readiness from dependencies without pretending work is complete."""
    by_id={t["task_id"]:dict(t) for t in tasks}
    out=[]
    for original in tasks:
        t=dict(original)
        if t["status"] in {"COMPLETED","NOT_REQUIRED","IN_PROGRESS","WAITING"}:
            out.append(t); continue
        blockers=[]
        for dep in t.get("dependencies",[]):
            d=by_id.get(dep)
            if d is None:
                blockers.append({"dependency_id":dep,"reason":"UNKNOWN_DEPENDENCY"})
            elif d.get("status") not in {"COMPLETED","NOT_REQUIRED"}:
                blockers.append({"dependency_id":dep,"reason":"DEPENDENCY_NOT_COMPLETE"})
        t["blockers"]=blockers
        t["status"]="READY" if not blockers else "NOT_STARTED"
        out.append(t)
    return out

def smart_next_action(*,tasks):
    evaluated=evaluate_task_readiness(tasks=tasks)
    ready=[t for t in evaluated if t["status"]=="READY"]
    if ready:
        ready.sort(key=lambda x:(x.get("priority",100),x["task_id"]))
        chosen=ready[0]
        return {"status":"NEXT_ACTION_AVAILABLE","task_id":chosen["task_id"],
                "title":chosen["title"],"requires_human_completion":chosen["requires_human_completion"],
                "reason":"Dependencies are satisfied."}
    blockers=[]
    for t in evaluated:
        for b in t.get("blockers",[]):
            blockers.append({"blocked_task_id":t["task_id"],**b})
    return {"status":"BLOCKED_OR_NO_ACTION","task_id":None,"blockers":blockers}

def complete_task(*,task,authorized_by):
    if task.get("requires_human_completion") and not authorized_by.strip():
        raise ValueError("human-controlled task requires authorization")
    r=dict(task); r["status"]="COMPLETED"
    if authorized_by: r["completed_by"]=authorized_by
    return r

def mark_waiting(*,task,waiting_for,note=None):
    r=dict(task); r["status"]="WAITING"; r["waiting_for"]=waiting_for; r["waiting_note"]=note; return r

def project_command_view(*,job_number,tasks):
    evaluated=evaluate_task_readiness(tasks=tasks)
    return {"job_number":job_number,"next_action":smart_next_action(tasks=evaluated),
            "waiting":[dict(t) for t in evaluated if t["status"]=="WAITING"],
            "blocked":[dict(t) for t in evaluated if t.get("blockers")],
            "completed_count":sum(t["status"]=="COMPLETED" for t in evaluated),
            "total_actionable_count":sum(t["status"]!="NOT_REQUIRED" for t in evaluated)}

def dependency_policy():
    return {"automatic_completion_of_professional_tasks":False,
            "dependency_order_enforced":True,
            "unknown_dependencies_are_blockers":True,
            "manual_schedule_maintenance_required":False}
