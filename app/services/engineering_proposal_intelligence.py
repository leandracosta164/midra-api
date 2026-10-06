"""Phase 5.56 — proposal scope intelligence and controlled automatic drafting."""

def build_scope_suggestions(*,request,property_analysis=None,historical_scopes=None):
    """Suggest scope/deliverables from known project information; do not silently commit."""
    requested=list(request.get("requested_services",[]))
    history=list(historical_scopes or [])
    suggestions=[]
    for service in requested:
        suggestions.append({"item":service,"source":"CLIENT_REQUEST","confidence":"DIRECT","selected":True})
    for item in (property_analysis or {}).get("engineering_scope_candidates",[]):
        if item not in [x["item"] for x in suggestions]:
            suggestions.append({"item":item,"source":"MIDRA_PROPERTY","confidence":"SUGGESTED","selected":False})
    for item in history:
        if item not in [x["item"] for x in suggestions]:
            suggestions.append({"item":item,"source":"HISTORICAL_SCOPE","confidence":"SUGGESTED","selected":False})
    return suggestions

def generate_proposal_draft(*,request,client,property_record,scope_suggestions,fee_recommendation,template_id):
    selected=[x["item"] for x in scope_suggestions if x.get("selected")]
    return {
        "request_id":request["request_id"],"client_id":client["client_id"],
        "property_address":property_record["property_address"],
        "project_type":request["project_type"],"scope":selected,
        "deliverables":list(request.get("known_deliverables",[])),
        "suggested_fee":fee_recommendation.get("recommended_fee"),
        "fee_basis_status":fee_recommendation.get("status"),
        "template_id":template_id,"status":"DRAFT_REQUIRES_REVIEW",
        "send_authorized":False,"job_created":False,
    }

def revise_proposal_draft(*,draft,scope=None,deliverables=None,selected_fee=None,authorized_by):
    if not authorized_by.strip(): raise ValueError("authorized reviewer required")
    r=dict(draft)
    if scope is not None: r["scope"]=list(scope)
    if deliverables is not None: r["deliverables"]=list(deliverables)
    if selected_fee is not None: r["selected_fee"]=selected_fee
    r["reviewed_by"]=authorized_by; r["status"]="REVIEWED_DRAFT"; return r

def authorize_proposal_send(*,draft,authorized_by):
    if not authorized_by.strip(): raise ValueError("send authorization required")
    if draft.get("status") not in {"REVIEWED_DRAFT","APPROVED_FOR_SEND"}:
        raise ValueError("proposal must be reviewed before send authorization")
    r=dict(draft); r["status"]="APPROVED_FOR_SEND"; r["send_authorized"]=True; r["send_authorized_by"]=authorized_by; return r

def proposal_acceptance_transition(*,proposal,accepted_by_client):
    """Acceptance may trigger job-setup review, but does not silently create a job."""
    if not accepted_by_client: return {"accepted":False,"job_setup_review_required":False}
    return {"accepted":True,"proposal_request_id":proposal["request_id"],
            "job_setup_review_required":True,"job_created":False}

def proposal_policy():
    return {"automatic_drafting":True,"automatic_scope_commitment":False,
            "automatic_fee_commitment":False,"automatic_sending":False,
            "automatic_job_creation":False}
