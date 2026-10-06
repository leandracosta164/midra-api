"""Phase 5.53 — revenue opportunity and additional-service detection."""
DECISIONS={"INCLUDED_IN_EXISTING_SCOPE","ADDITIONAL_SERVICE","NEED_MORE_INFORMATION"}

def detect_scope_opportunity(*,job_number,request_id,requested_work,accepted_scope,source,evidence=None):
    """Flag a comparison for review; never decide that work is billable."""
    scope=[x.strip().casefold() for x in accepted_scope if str(x).strip()]
    requested=requested_work.strip()
    exact_in_scope=requested.casefold() in scope
    return {
        "job_number":job_number,"request_id":request_id,"source":source,
        "requested_work":requested_work,"accepted_scope":list(accepted_scope),
        "evidence":[dict(x) for x in (evidence or [])],
        "status":"NO_REVENUE_REVIEW_NEEDED" if exact_in_scope else "POTENTIAL_ADDITIONAL_SERVICE",
        "reason":"Requested work exactly matches accepted scope." if exact_in_scope
                 else "Requested work is not an exact accepted-scope item and requires human review.",
        "decision":None,"requires_human_review":not exact_in_scope,
    }

def decide_scope_opportunity(*,opportunity,decision,authorized_by,note=None):
    if decision not in DECISIONS: raise ValueError("unsupported scope decision")
    if not authorized_by.strip(): raise ValueError("authorized reviewer required")
    r=_copy(opportunity); r["decision"]=decision; r["decided_by"]=authorized_by; r["decision_note"]=note
    r["status"]="REVIEWED"; return r

def additional_service_proposal_draft(*,opportunity,service_id,description,proposed_fee=None):
    if opportunity.get("decision")!="ADDITIONAL_SERVICE":
        raise ValueError("additional-service proposal requires authorized additional-service decision")
    return {
        "job_number":opportunity["job_number"],"source_request_id":opportunity["request_id"],
        "service_id":service_id,"description":description,"proposed_fee":proposed_fee,
        "status":"DRAFT_REQUIRES_REVIEW","send_authorized":False,
    }

def authorize_additional_service_proposal_send(*,draft,authorized_by):
    if not authorized_by.strip(): raise ValueError("send authorization required")
    r=dict(draft); r["send_authorized"]=True; r["authorized_by"]=authorized_by; return r

def revenue_opportunity_queue(*,opportunities):
    pending=[_copy(x) for x in opportunities if x.get("status")=="POTENTIAL_ADDITIONAL_SERVICE"]
    return {"visibility":"MIDRA_ENGINEERING_PRIVATE","potential_additional_services":pending,"count":len(pending)}

def _copy(x):
    r=dict(x); r["accepted_scope"]=list(x.get("accepted_scope",[])); r["evidence"]=[dict(e) for e in x.get("evidence",[])]
    return r
