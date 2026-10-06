"""Phase 5.73 — broader MIDRA Engineering workflow integration.

Connects municipal-review workflows to the full engineering project lifecycle without
forcing every project through the same path.
"""

WORKSTREAMS={
    "INTAKE_ESTIMATING",
    "DESIGN_PRODUCTION",
    "CLIENT_COORDINATION",
    "PERMIT_PREPARATION",
    "MUNICIPAL_REVIEW",
    "AGENCY_REVIEW",
    "CONSTRUCTION_SUPPORT",
    "REVISION",
    "RESOLUTION_COMPLIANCE",
    "BILLING",
    "CLOSEOUT",
}

ARTIFACT_TYPES={
    "CIVIL_3D","AUTOCAD","HYDROCAD","RETAINING_WALL_SOFTWARE",
    "CALCULATION","SPREADSHEET","PLAN_PDF","REPORT","OTHER"
}

def create_engineering_job_workflow(*, job_number, project_source, property_address=None,
                                    service_types=None):
    return {
        "job_number":job_number,
        "project_source":project_source,
        "property_address":property_address,
        "service_types":list(service_types or []),
        "active_workstreams":[],
        "design_artifacts":[],
        "milestones":[],
        "alerts":[],
        "status":"ACTIVE",
    }

def activate_workstream(*, job, workstream, authorized_by):
    if workstream not in WORKSTREAMS:
        raise ValueError("unsupported workstream")
    if not (authorized_by or "").strip():
        raise ValueError("authorized user required")
    r=_copy(job)
    if workstream not in r["active_workstreams"]:
        r["active_workstreams"].append(workstream)
    return r

def register_design_artifact(*, job, artifact_id, artifact_type, file_reference,
                             software=None, modified_at=None, purpose="WORKING"):
    if artifact_type not in ARTIFACT_TYPES:
        raise ValueError("unsupported artifact type")
    r=_copy(job)
    r["design_artifacts"].append({
        "artifact_id":artifact_id,
        "artifact_type":artifact_type,
        "file_reference":file_reference,
        "software":software,
        "modified_at":modified_at,
        "purpose":purpose,
        "issued":False,
        "issued_at":None,
        "submission_id":None,
    })
    return r

def record_artifact_change(*, job, artifact_id, modified_at):
    r=_copy(job)
    a=_artifact(r,artifact_id)
    a["modified_at"]=modified_at
    # Saving/editing a working file never means that it was issued.
    return r

def issue_artifact(*, job, artifact_id, issued_at, authorized_by, submission_id=None):
    if not (authorized_by or "").strip():
        raise ValueError("issue authorization required")
    r=_copy(job)
    a=_artifact(r,artifact_id)
    a["issued"]=True
    a["issued_at"]=issued_at
    a["submission_id"]=submission_id
    a["purpose"]="ISSUED"
    return r

def detect_post_issue_design_changes(*, job):
    alerts=[]
    for a in job["design_artifacts"]:
        if a.get("issued_at") and a.get("modified_at") and a["modified_at"] > a["issued_at"]:
            alerts.append({
                "type":"DESIGN_CHANGED_AFTER_ISSUE",
                "artifact_id":a["artifact_id"],
                "file_reference":a["file_reference"],
                "requires_review":True,
            })
    return alerts

def connect_review_cycle(*, job, review_cycle_id):
    r=_copy(job)
    r["milestones"].append({
        "type":"REVIEW_CYCLE",
        "reference_id":review_cycle_id,
    })
    if "MUNICIPAL_REVIEW" not in r["active_workstreams"]:
        r["active_workstreams"].append("MUNICIPAL_REVIEW")
    return r

def command_center_view(*, job):
    alerts=[dict(x) for x in job.get("alerts",[])]
    alerts.extend(detect_post_issue_design_changes(job=job))
    return {
        "job_number":job["job_number"],
        "project_source":job["project_source"],
        "property_address":job.get("property_address"),
        "service_types":list(job.get("service_types",[])),
        "active_workstreams":list(job["active_workstreams"]),
        "design_artifact_count":len(job["design_artifacts"]),
        "alerts":alerts,
        "status":job["status"],
    }

def _artifact(job,artifact_id):
    for a in job["design_artifacts"]:
        if a["artifact_id"]==artifact_id:
            return a
    raise KeyError(artifact_id)

def _copy(job):
    r=dict(job)
    r["service_types"]=list(job.get("service_types",[]))
    r["active_workstreams"]=list(job.get("active_workstreams",[]))
    r["design_artifacts"]=[dict(x) for x in job.get("design_artifacts",[])]
    r["milestones"]=[dict(x) for x in job.get("milestones",[])]
    r["alerts"]=[dict(x) for x in job.get("alerts",[])]
    return r

def broader_workflow_policy():
    return {
        "municipal_review_is_one_workstream_not_the_whole_platform":True,
        "different_jobs_may_use_different_workstreams":True,
        "working_file_save_does_not_equal_issue":True,
        "design_software_is_not_replaced_by_midra":True,
        "authorized_project_workspace_tracking_supported":True,
        "project_source_preserved":True,
    }
