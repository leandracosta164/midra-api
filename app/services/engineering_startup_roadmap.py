"""Phase 5.58 — automatic project startup and requirements roadmap."""
VERIFICATION_STATES={"VERIFIED","SUGGESTED","REQUIRES_REVIEW"}

def create_requirement(*,requirement_id,title,category,source,verification_state,
                       source_reference=None,required_action=None):
    if verification_state not in VERIFICATION_STATES:
        raise ValueError("unsupported verification state")
    return {"requirement_id":requirement_id,"title":title,"category":category,
            "source":source,"verification_state":verification_state,
            "source_reference":source_reference,"required_action":required_action,
            "completed":False}

def build_startup_roadmap(*,job,property_analysis,accepted_scope,requirements):
    """Assemble known startup work without converting suggestions into facts."""
    return {
        "job_number":job["job_number"],
        "project_type":job.get("project_type"),
        "municipality":property_analysis.get("municipality"),
        "accepted_scope":list(accepted_scope),
        "requirements":[dict(r) for r in requirements],
        "summary":{
            "verified":sum(r["verification_state"]=="VERIFIED" for r in requirements),
            "suggested":sum(r["verification_state"]=="SUGGESTED" for r in requirements),
            "requires_review":sum(r["verification_state"]=="REQUIRES_REVIEW" for r in requirements),
        },
        "status":"STARTUP_REVIEW_REQUIRED",
    }

def startup_action_groups(*,roadmap):
    groups={"APPLICATIONS_CHECKLISTS":[],"DESIGN_TASKS":[],"SUBMISSIONS_APPROVALS":[],"OTHER":[]}
    for r in roadmap["requirements"]:
        cat=r.get("category")
        if cat in {"APPLICATION","CHECKLIST"}: key="APPLICATIONS_CHECKLISTS"
        elif cat in {"DESIGN","CALCULATION","REPORT"}: key="DESIGN_TASKS"
        elif cat in {"SUBMISSION","APPROVAL","AGENCY"}: key="SUBMISSIONS_APPROVALS"
        else: key="OTHER"
        groups[key].append(dict(r))
    return groups

def checklist_discovery_candidates(*,roadmap):
    """Only verified/suggested checklist needs become discovery requests."""
    return [{"job_number":roadmap["job_number"],"municipality":roadmap["municipality"],
             "requirement_id":r["requirement_id"],"title":r["title"],
             "source_requirement":"OFFICIAL_MUNICIPAL_OR_AGENCY_SOURCE"}
            for r in roadmap["requirements"] if r["category"]=="CHECKLIST"]

def confirm_startup_requirement(*,requirement,authorized_by,confirmed_required):
    if not authorized_by.strip(): raise ValueError("authorized reviewer required")
    r=dict(requirement)
    r["verification_state"]="VERIFIED" if confirmed_required else "REVIEWED_NOT_REQUIRED"
    r["confirmed_by"]=authorized_by
    return r

def startup_policy():
    return {"verified_requirements_may_be_presented_as_requirements":True,
            "suggestions_must_remain_labeled":True,
            "unknown_requirements_must_not_be_invented":True,
            "official_checklist_sources_required":True,
            "human_startup_review_required":True}
