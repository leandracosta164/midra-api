"""Phase 5.76 — adaptive project workflow intelligence.

MIDRA exposes only the minimum useful workflow for the actual project while retaining
the larger engineering capability set underneath.
"""

WORKFLOW_MODULES = {
    "ESTIMATING","DESIGN","CLIENT_COORDINATION","SUBMISSION","REVISION",
    "STORMWATER","UTILITY_DESIGN","RETAINING_WALL_DESIGN","COMPLETENESS_REVIEW",
    "ENGINEERING_REVIEW","AGENCY_REVIEW","RESOLUTION_COMPLIANCE",
    "CONSTRUCTION_SUPPORT","BILLING","CLOSEOUT"
}

BASE_MODULES = ["ESTIMATING","DESIGN","CLIENT_COORDINATION","BILLING","CLOSEOUT"]

def create_project_profile(*, job_number, service_types, project_scale="SMALL",
                           requires_submission=False, anticipated_revision=False,
                           stormwater=False, utilities=False, retaining_wall=False,
                           municipal_review=False, agency_review=False,
                           resolution_compliance=False, construction_support=False):
    return {
        "job_number":job_number,
        "service_types":list(service_types),
        "project_scale":project_scale,
        "requires_submission":requires_submission,
        "anticipated_revision":anticipated_revision,
        "stormwater":stormwater,
        "utilities":utilities,
        "retaining_wall":retaining_wall,
        "municipal_review":municipal_review,
        "agency_review":agency_review,
        "resolution_compliance":resolution_compliance,
        "construction_support":construction_support,
    }

def recommend_workflow(*, profile):
    modules=list(BASE_MODULES)

    def add(name):
        if name not in modules:
            modules.append(name)

    if profile["requires_submission"]:
        add("SUBMISSION")
    if profile["anticipated_revision"]:
        add("REVISION")
    if profile["stormwater"]:
        add("STORMWATER")
    if profile["utilities"]:
        add("UTILITY_DESIGN")
    if profile["retaining_wall"]:
        add("RETAINING_WALL_DESIGN")
    if profile["municipal_review"]:
        add("ENGINEERING_REVIEW")
    if profile["agency_review"]:
        add("AGENCY_REVIEW")
    if profile["resolution_compliance"]:
        add("RESOLUTION_COMPLIANCE")
    if profile["construction_support"]:
        add("CONSTRUCTION_SUPPORT")

    return {
        "job_number":profile["job_number"],
        "recommended_modules":modules,
        "hidden_modules":sorted(WORKFLOW_MODULES-set(modules)),
        "status":"RECOMMENDATION_REQUIRES_CONFIRMATION",
        "confirmed":False,
    }

def confirm_workflow(*, workflow, authorized_by):
    if not (authorized_by or "").strip():
        raise ValueError("workflow confirmation required")
    r=_copy(workflow)
    r["confirmed"]=True
    r["confirmed_by"]=authorized_by
    r["status"]="ACTIVE"
    return r

def add_optional_module(*, workflow, module, authorized_by):
    if module not in WORKFLOW_MODULES:
        raise ValueError("unsupported workflow module")
    if not (authorized_by or "").strip():
        raise ValueError("authorization required")
    r=_copy(workflow)
    if module not in r["recommended_modules"]:
        r["recommended_modules"].append(module)
    r["hidden_modules"]=sorted(WORKFLOW_MODULES-set(r["recommended_modules"]))
    return r

def visible_project_steps(*, workflow):
    if not workflow.get("confirmed"):
        raise ValueError("workflow must be confirmed before activation")
    # The UI can render these as compact stages; hidden capabilities remain available.
    return list(workflow["recommended_modules"])

def adapt_to_project_change(*, workflow, change, authorized_by):
    """Add capability when project scope changes; never silently remove existing work."""
    mapping={
        "STORMWATER_REQUIRED":"STORMWATER",
        "UTILITY_DESIGN_REQUIRED":"UTILITY_DESIGN",
        "RETAINING_WALL_ADDED":"RETAINING_WALL_DESIGN",
        "MUNICIPAL_REVIEW_REQUIRED":"ENGINEERING_REVIEW",
        "AGENCY_REVIEW_REQUIRED":"AGENCY_REVIEW",
        "RESOLUTION_COMPLIANCE_REQUIRED":"RESOLUTION_COMPLIANCE",
        "CONSTRUCTION_SUPPORT_ADDED":"CONSTRUCTION_SUPPORT",
        "REVISION_REQUIRED":"REVISION",
    }
    if change not in mapping:
        raise ValueError("unsupported project change")
    return add_optional_module(workflow=workflow,module=mapping[change],
                               authorized_by=authorized_by)

def workflow_complexity(*, workflow):
    specialized=[x for x in workflow["recommended_modules"] if x not in BASE_MODULES]
    if len(specialized)<=2:
        return "LEAN"
    if len(specialized)<=5:
        return "STANDARD"
    return "EXPANDED"

def _copy(workflow):
    r=dict(workflow)
    r["recommended_modules"]=list(workflow.get("recommended_modules",[]))
    r["hidden_modules"]=list(workflow.get("hidden_modules",[]))
    return r

def adaptive_workflow_policy():
    return {
        "complexity_scales_with_project":True,
        "unused_modules_hidden_not_deleted":True,
        "recommendation_requires_confirmation":True,
        "scope_change_can_expand_workflow":True,
        "scope_change_does_not_silently_remove_work":True,
        "small_projects_remain_lean":True,
    }
