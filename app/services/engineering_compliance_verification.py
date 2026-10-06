"""Phase 5.66 — evidence-based plan/document compliance verification."""

VERDICTS={"SUPPORTED","NOT_FOUND","CONFLICTING","INSUFFICIENT_EVIDENCE","REQUIRES_REVIEW"}

def create_compliance_check(*,check_id,job_number,comment_id,requirement_text,
                            document_set_id):
    return {
        "check_id":check_id,"job_number":job_number,"comment_id":comment_id,
        "requirement_text":requirement_text,"document_set_id":document_set_id,
        "evidence":[],"system_assessment":"REQUIRES_REVIEW",
        "human_verdict":None,"confirmed_by":None,
    }

def add_document_evidence(*,check,document_id,location,excerpt=None,
                          evidence_type="SUPPORTING",note=None):
    r=_copy(check)
    r["evidence"].append({
        "document_id":document_id,"location":location,"excerpt":excerpt,
        "evidence_type":evidence_type,"note":note,
    })
    r["system_assessment"]="REQUIRES_REVIEW"
    return r

def assess_evidence(*,check):
    """Conservative evidence assessment; never converts itself into final compliance."""
    types={e.get("evidence_type") for e in check.get("evidence",[])}
    if not check.get("evidence"):
        assessment="NOT_FOUND"
    elif "CONFLICTING" in types:
        assessment="CONFLICTING"
    elif "SUPPORTING" in types:
        assessment="SUPPORTED"
    else:
        assessment="INSUFFICIENT_EVIDENCE"
    r=_copy(check)
    r["system_assessment"]=assessment
    return r

def confirm_compliance_verdict(*,check,verdict,authorized_by,note=None):
    if verdict not in VERDICTS:
        raise ValueError("unsupported compliance verdict")
    if not authorized_by.strip():
        raise ValueError("authorized reviewer required")
    if verdict=="SUPPORTED" and not check.get("evidence"):
        raise ValueError("supported verdict requires document evidence")
    r=_copy(check)
    r["human_verdict"]=verdict
    r["confirmed_by"]=authorized_by
    r["confirmation_note"]=note
    return r

def response_support_record(*,check):
    """Only a human-confirmed supported check may support an 'addressed' response."""
    if check.get("human_verdict")!="SUPPORTED":
        raise ValueError("confirmed supporting evidence required")
    return {
        "job_number":check["job_number"],
        "comment_id":check["comment_id"],
        "check_id":check["check_id"],
        "evidence":[dict(e) for e in check["evidence"]],
        "eligible_to_support_addressed_status":True,
    }

def compare_document_sets(*,previous_set_id,current_set_id,changes):
    return {
        "previous_document_set_id":previous_set_id,
        "current_document_set_id":current_set_id,
        "changes":[dict(x) for x in changes],
        "status":"COMPARISON_REQUIRES_REVIEW",
    }

def _copy(check):
    r=dict(check)
    r["evidence"]=[dict(e) for e in check.get("evidence",[])]
    return r

def compliance_policy():
    return {
        "trust_applicant_response_without_verification":False,
        "document_evidence_required_for_supported_finding":True,
        "automatic_final_compliance_decision":False,
        "human_confirmation_required":True,
        "document_set_comparison_supported":True,
    }
