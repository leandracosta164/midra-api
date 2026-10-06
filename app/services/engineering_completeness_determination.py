"""Phase 5.71 — completeness determination and deficiency-letter intelligence."""

FINAL_STATES={"COMPLETE","INCOMPLETE","COMPLETE_WITH_WAIVERS"}

def create_completeness_determination(*, determination_id, job_number, package,
                                      reviewer_id):
    summary = package["summary"]
    if not summary.get("ready_for_final_determination"):
        raise ValueError("all checklist items must be confirmed before final determination")
    return {
        "determination_id":determination_id,
        "job_number":job_number,
        "package_id":package["package_id"],
        "submission_number":package["submission_number"],
        "reviewer_id":reviewer_id,
        "documents_reviewed":[dict(x) for x in package.get("documents_received",[])],
        "checklist_items":[dict(x) for x in package.get("checklist_items",[])],
        "preliminary_state":_preliminary(package["checklist_items"]),
        "final_state":None,
        "status":"FINAL_DETERMINATION_REQUIRED",
        "confirmed_by":None,
    }

def _preliminary(items):
    states={x["state"] for x in items}
    if "MISSING" in states or "REQUIRES_REVIEW" in states:
        return "INCOMPLETE"
    if "POTENTIAL_WAIVER" in states:
        return "COMPLETE_WITH_WAIVERS"
    return "COMPLETE"

def confirm_final_determination(*, determination, final_state, authorized_by,
                                note=None):
    if final_state not in FINAL_STATES:
        raise ValueError("unsupported completeness determination")
    if not authorized_by.strip():
        raise ValueError("authorized reviewer required")
    r=_copy(determination)
    r["final_state"]=final_state
    r["status"]="DETERMINATION_CONFIRMED"
    r["confirmed_by"]=authorized_by
    r["determination_note"]=note
    return r

def build_completeness_letter_draft(*, determination, template_id, addressee=None):
    if determination.get("status")!="DETERMINATION_CONFIRMED":
        raise ValueError("final completeness determination must be confirmed")
    missing=[dict(x) for x in determination["checklist_items"] if x["state"]=="MISSING"]
    waivers=[dict(x) for x in determination["checklist_items"]
             if x["state"]=="POTENTIAL_WAIVER"]
    review_items=[dict(x) for x in determination["checklist_items"]
                  if x["state"]=="REQUIRES_REVIEW"]
    return {
        "job_number":determination["job_number"],
        "package_id":determination["package_id"],
        "submission_number":determination["submission_number"],
        "determination":determination["final_state"],
        "documents_reviewed":[dict(x) for x in determination["documents_reviewed"]],
        "missing_items":missing,
        "waiver_items":waivers,
        "review_items":review_items,
        "template_id":template_id,
        "addressee":addressee,
        "status":"DRAFT_REQUIRES_REVIEW",
        "issue_authorized":False,
    }

def review_completeness_letter(*, draft, authorized_by, addressee=None):
    if not authorized_by.strip():
        raise ValueError("authorized reviewer required")
    r=dict(draft)
    if addressee is not None:
        r["addressee"]=addressee
    r["status"]="REVIEWED_DRAFT"
    r["reviewed_by"]=authorized_by
    return r

def authorize_completeness_letter_issue(*, draft, authorized_by):
    if draft.get("status")!="REVIEWED_DRAFT":
        raise ValueError("letter must be reviewed before issue authorization")
    if not authorized_by.strip():
        raise ValueError("issue authorization required")
    r=dict(draft)
    r["status"]="APPROVED_FOR_ISSUE"
    r["issue_authorized"]=True
    r["issue_authorized_by"]=authorized_by
    return r

def _copy(d):
    r=dict(d)
    r["documents_reviewed"]=[dict(x) for x in d.get("documents_reviewed",[])]
    r["checklist_items"]=[dict(x) for x in d.get("checklist_items",[])]
    return r

def completeness_determination_policy():
    return {
        "preliminary_state_is_not_final_determination":True,
        "final_professional_determination_requires_authorization":True,
        "missing_items_preserved_in_letter":True,
        "waiver_requests_preserved_in_letter":True,
        "documents_reviewed_preserved":True,
        "automatic_issue":False,
    }
