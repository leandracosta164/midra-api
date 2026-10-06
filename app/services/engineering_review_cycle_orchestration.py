"""Phase 5.72 — submission/review cycle orchestration."""

STAGES={
    "INTAKE",
    "COMPLETENESS_REVIEW",
    "AWAITING_COMPLETENESS_RESUBMISSION",
    "ENGINEERING_REVIEW",
    "AWAITING_ENGINEERING_RESUBMISSION",
    "RESOLUTION_COMPLIANCE",
    "AWAITING_RESOLUTION_COMPLIANCE_RESUBMISSION",
    "APPROVAL_CLOSEOUT",
    "CLOSED",
}

def create_review_cycle(*, cycle_id, job_number, project_source,
                        initial_package_id=None):
    return {
        "cycle_id":cycle_id,
        "job_number":job_number,
        "project_source":project_source,
        "current_stage":"INTAKE",
        "current_package_id":initial_package_id,
        "submission_number":1 if initial_package_id else 0,
        "history":[],
        "pending_action":"REVIEW_INTAKE",
        "closed":False,
    }

def advance_cycle(*, cycle, event, authorized_by, reference_id=None, note=None):
    """Advance only on explicit, authorized project events."""
    if not (authorized_by or "").strip():
        raise ValueError("authorized user required")
    r=_copy(cycle)
    stage=r["current_stage"]

    transitions={
        ("INTAKE","START_COMPLETENESS_REVIEW"):
            ("COMPLETENESS_REVIEW","COMPLETE_CHECKLIST_REVIEW"),
        ("COMPLETENESS_REVIEW","DETERMINED_INCOMPLETE"):
            ("AWAITING_COMPLETENESS_RESUBMISSION","WAIT_FOR_RESUBMISSION"),
        ("COMPLETENESS_REVIEW","DETERMINED_COMPLETE"):
            ("ENGINEERING_REVIEW","PERFORM_ENGINEERING_REVIEW"),
        ("AWAITING_COMPLETENESS_RESUBMISSION","RESUBMISSION_RECEIVED"):
            ("COMPLETENESS_REVIEW","COMPLETE_CHECKLIST_REVIEW"),
        ("ENGINEERING_REVIEW","ENGINEERING_COMMENTS_ISSUED"):
            ("AWAITING_ENGINEERING_RESUBMISSION","WAIT_FOR_RESUBMISSION"),
        ("ENGINEERING_REVIEW","ENGINEERING_REVIEW_SATISFIED"):
            ("APPROVAL_CLOSEOUT","REVIEW_APPROVAL_CLOSEOUT"),
        ("AWAITING_ENGINEERING_RESUBMISSION","RESUBMISSION_RECEIVED"):
            ("ENGINEERING_REVIEW","PERFORM_ENGINEERING_REVIEW"),
        ("RESOLUTION_COMPLIANCE","COMPLIANCE_COMMENTS_ISSUED"):
            ("AWAITING_RESOLUTION_COMPLIANCE_RESUBMISSION","WAIT_FOR_RESUBMISSION"),
        ("RESOLUTION_COMPLIANCE","COMPLIANCE_SATISFIED"):
            ("APPROVAL_CLOSEOUT","REVIEW_APPROVAL_CLOSEOUT"),
        ("AWAITING_RESOLUTION_COMPLIANCE_RESUBMISSION","RESUBMISSION_RECEIVED"):
            ("RESOLUTION_COMPLIANCE","PERFORM_RESOLUTION_COMPLIANCE_REVIEW"),
        ("APPROVAL_CLOSEOUT","CLOSE_PROJECT_REVIEW_CYCLE"):
            ("CLOSED",None),
    }
    key=(stage,event)
    if key not in transitions:
        raise ValueError(f"invalid transition: {stage} -> {event}")

    next_stage,next_action=transitions[key]
    r["history"].append({
        "from_stage":stage,"event":event,"to_stage":next_stage,
        "reference_id":reference_id,"note":note,"authorized_by":authorized_by,
    })
    r["current_stage"]=next_stage
    r["pending_action"]=next_action
    r["closed"]=next_stage=="CLOSED"

    if event=="RESUBMISSION_RECEIVED":
        r["submission_number"]+=1
        r["current_package_id"]=reference_id

    return r

def enter_resolution_compliance(*, cycle, authorized_by, resolution_id):
    """Resolution compliance is a project path, not assumed for every job."""
    if not (authorized_by or "").strip():
        raise ValueError("authorized user required")
    if cycle["current_stage"] not in {
        "ENGINEERING_REVIEW","APPROVAL_CLOSEOUT",
        "AWAITING_ENGINEERING_RESUBMISSION"
    }:
        raise ValueError("resolution compliance cannot begin from current stage")
    r=_copy(cycle)
    previous=r["current_stage"]
    r["history"].append({
        "from_stage":previous,"event":"ENTER_RESOLUTION_COMPLIANCE",
        "to_stage":"RESOLUTION_COMPLIANCE","reference_id":resolution_id,
        "authorized_by":authorized_by,
    })
    r["current_stage"]="RESOLUTION_COMPLIANCE"
    r["pending_action"]="PERFORM_RESOLUTION_COMPLIANCE_REVIEW"
    return r

def cycle_command_view(*, cycle):
    return {
        "job_number":cycle["job_number"],
        "project_source":cycle["project_source"],
        "current_stage":cycle["current_stage"],
        "submission_number":cycle["submission_number"],
        "current_package_id":cycle["current_package_id"],
        "next_action":cycle["pending_action"],
        "closed":cycle["closed"],
        "cycle_event_count":len(cycle["history"]),
    }

def _copy(cycle):
    r=dict(cycle)
    r["history"]=[dict(x) for x in cycle.get("history",[])]
    return r

def orchestration_policy():
    return {
        "one_job_record_across_review_cycles":True,
        "resubmissions_create_new_packages_not_new_jobs":True,
        "professional_stage_transitions_require_authorization":True,
        "resolution_compliance_is_optional_project_path":True,
        "project_source_preserved":True,
        "automatic_project_closeout":False,
    }
