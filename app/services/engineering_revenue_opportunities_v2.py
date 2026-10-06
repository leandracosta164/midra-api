"""Phase 5.53A — explicit complimentary additional-service handling."""
DECISIONS={
    "INCLUDED_IN_EXISTING_SCOPE",
    "ADDITIONAL_SERVICE_BILL_CLIENT",
    "ADDITIONAL_SERVICE_NO_CHARGE",
    "NEED_MORE_INFORMATION",
}

def decide_scope_opportunity(*,opportunity,decision,authorized_by,note=None,estimated_value=None):
    if decision not in DECISIONS: raise ValueError("unsupported scope decision")
    if not authorized_by.strip(): raise ValueError("authorized reviewer required")
    r=dict(opportunity)
    r["accepted_scope"]=list(opportunity.get("accepted_scope",[]))
    r["evidence"]=[dict(e) for e in opportunity.get("evidence",[])]
    r.update({"decision":decision,"decided_by":authorized_by,"decision_note":note,"status":"REVIEWED"})
    if decision=="ADDITIONAL_SERVICE_NO_CHARGE":
        r["billing_status"]="INTENTIONALLY_NO_CHARGE"
        r["estimated_complimentary_value"]=estimated_value
        r["revenue_attention_required"]=False
    elif decision=="ADDITIONAL_SERVICE_BILL_CLIENT":
        r["billing_status"]="BILLABLE_PENDING_PROPOSAL"
        r["estimated_complimentary_value"]=None
        r["revenue_attention_required"]=True
    elif decision=="INCLUDED_IN_EXISTING_SCOPE":
        r["billing_status"]="IN_SCOPE"
        r["estimated_complimentary_value"]=None
        r["revenue_attention_required"]=False
    else:
        r["billing_status"]="UNDECIDED"
        r["estimated_complimentary_value"]=None
        r["revenue_attention_required"]=False
    return r

def additional_service_proposal_draft(*,opportunity,service_id,description,proposed_fee=None):
    if opportunity.get("decision")!="ADDITIONAL_SERVICE_BILL_CLIENT":
        raise ValueError("billable additional-service decision required")
    return {"job_number":opportunity["job_number"],"source_request_id":opportunity["request_id"],
            "service_id":service_id,"description":description,"proposed_fee":proposed_fee,
            "status":"DRAFT_REQUIRES_REVIEW","send_authorized":False}

def complimentary_service_summary(*,opportunities):
    items=[x for x in opportunities if x.get("decision")=="ADDITIONAL_SERVICE_NO_CHARGE"]
    return {"visibility":"MIDRA_ENGINEERING_PRIVATE","complimentary_services":[dict(x) for x in items],
            "count":len(items),"creates_invoice":False,"creates_negative_attention":False}
