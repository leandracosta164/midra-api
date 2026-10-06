"""Phase 5.65 — incoming agency review letter -> controlled comment/response workflow."""

COMMENT_STATES={"OPEN","ADDRESSED","REQUIRES_REVIEW"}

def create_review_letter_record(*,review_id,job_number,agency,title,received_date,
                                source_document_id,comments):
    normalized=[]
    for i,c in enumerate(comments,1):
        normalized.append({
            "comment_id":c.get("comment_id") or f"{review_id}-C{i}",
            "number":c.get("number",i),
            "text":c["text"],
            "status":"OPEN",
            "response_draft":None,
            "evidence":[],
            "confirmed_by":None,
        })
    return {"review_id":review_id,"job_number":job_number,"agency":agency,"title":title,
            "received_date":received_date,"source_document_id":source_document_id,
            "comments":normalized,"status":"RESPONSE_WORKFLOW_OPEN"}

def attach_comment_evidence(*,review,comment_id,evidence):
    r=_copy(review); c=_comment(r,comment_id)
    c["evidence"].append(dict(evidence))
    c["status"]="REQUIRES_REVIEW"
    return r

def draft_comment_response(*,review,comment_id,response_text,basis=None):
    r=_copy(review); c=_comment(r,comment_id)
    c["response_draft"]=response_text
    if basis: c["evidence"].append(dict(basis))
    c["status"]="REQUIRES_REVIEW"
    return r

def confirm_comment_status(*,review,comment_id,status,authorized_by):
    if status not in COMMENT_STATES: raise ValueError("unsupported comment state")
    if not authorized_by.strip(): raise ValueError("authorized reviewer required")
    r=_copy(review); c=_comment(r,comment_id)
    if status=="ADDRESSED" and not c.get("response_draft") and not c.get("evidence"):
        raise ValueError("addressed status requires response or evidence")
    c["status"]=status; c["confirmed_by"]=authorized_by
    return r

def response_letter_draft(*,review,template_id):
    comments=[]
    for c in review["comments"]:
        comments.append({"number":c["number"],"original_comment":c["text"],
                         "response":c.get("response_draft"),"status":c["status"]})
    return {"job_number":review["job_number"],"review_id":review["review_id"],
            "agency":review["agency"],"template_id":template_id,
            "comments":comments,"status":"DRAFT_REQUIRES_REVIEW",
            "send_authorized":False}

def review_progress(*,review):
    total=len(review["comments"])
    counts={s:sum(c["status"]==s for c in review["comments"]) for s in COMMENT_STATES}
    return {"total":total,**{k.lower():v for k,v in counts.items()},
            "complete":total>0 and counts["ADDRESSED"]==total}

def _comment(review,comment_id):
    for c in review["comments"]:
        if c["comment_id"]==comment_id: return c
    raise KeyError(comment_id)

def _copy(review):
    r=dict(review); r["comments"]=[]
    for c in review["comments"]:
        x=dict(c); x["evidence"]=[dict(e) for e in c.get("evidence",[])]
        r["comments"].append(x)
    return r

def review_response_policy():
    return {"automatic_comment_extraction_may_create_draft_records":True,
            "automatic_addressed_status":False,
            "human_confirmation_required_for_addressed":True,
            "response_letter_uses_project_template":True,
            "automatic_sending":False}
