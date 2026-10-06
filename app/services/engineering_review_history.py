"""Phase 5.69 — review-cycle and comment-history intelligence."""

EVENT_TYPES={
    "COMMENT_CREATED","APPLICANT_RESPONSE","DOCUMENT_CHANGE",
    "REVIEWER_DETERMINATION","COMMENT_REOPENED"
}

def create_comment_history(*, history_id, job_number, comment_id, origin_review_id,
                           original_comment):
    return {
        "history_id":history_id,
        "job_number":job_number,
        "comment_id":comment_id,
        "origin_review_id":origin_review_id,
        "original_comment":original_comment,
        "current_status":"OPEN",
        "events":[{
            "event_type":"COMMENT_CREATED",
            "review_id":origin_review_id,
            "text":original_comment,
            "confirmed":True,
        }],
    }

def add_history_event(*, history, event_type, review_id, text=None,
                      document_set_id=None, evidence=None, authorized_by=None):
    if event_type not in EVENT_TYPES:
        raise ValueError("unsupported history event type")
    if event_type in {"REVIEWER_DETERMINATION","COMMENT_REOPENED"} and not (authorized_by or "").strip():
        raise ValueError("reviewer-controlled history event requires authorization")
    r=_copy(history)
    event={
        "event_type":event_type,"review_id":review_id,"text":text,
        "document_set_id":document_set_id,
        "evidence":[dict(x) for x in (evidence or [])],
        "confirmed":event_type in {"REVIEWER_DETERMINATION","COMMENT_REOPENED"},
    }
    if authorized_by:
        event["authorized_by"]=authorized_by
    r["events"].append(event)
    if event_type=="COMMENT_REOPENED":
        r["current_status"]="OPEN"
    return r

def record_reviewer_determination(*, history, review_id, determination,
                                  authorized_by, note=None):
    if determination not in {"OPEN","ADDRESSED"}:
        raise ValueError("unsupported reviewer determination")
    r=add_history_event(
        history=history,event_type="REVIEWER_DETERMINATION",
        review_id=review_id,text=note or determination,authorized_by=authorized_by)
    r["events"][-1]["determination"]=determination
    r["current_status"]=determination
    return r

def reopen_comment(*, history, review_id, authorized_by, reason):
    if not reason:
        raise ValueError("reopen reason required")
    return add_history_event(
        history=history,event_type="COMMENT_REOPENED",review_id=review_id,
        text=reason,authorized_by=authorized_by)

def comment_cycle_summary(*, history):
    responses=[e for e in history["events"] if e["event_type"]=="APPLICANT_RESPONSE"]
    changes=[e for e in history["events"] if e["event_type"]=="DOCUMENT_CHANGE"]
    determinations=[e for e in history["events"] if e["event_type"]=="REVIEWER_DETERMINATION"]
    reopens=[e for e in history["events"] if e["event_type"]=="COMMENT_REOPENED"]
    reviews=[]
    for e in history["events"]:
        rid=e.get("review_id")
        if rid and rid not in reviews:
            reviews.append(rid)
    return {
        "comment_id":history["comment_id"],
        "origin_review_id":history["origin_review_id"],
        "current_status":history["current_status"],
        "review_ids":reviews,
        "applicant_response_count":len(responses),
        "document_change_count":len(changes),
        "determination_count":len(determinations),
        "reopened_count":len(reopens),
    }

def review_cycle_view(*, job_number, histories):
    rows=[]
    for h in histories:
        if h["job_number"]!=job_number:
            continue
        s=comment_cycle_summary(history=h)
        rows.append({
            "comment_id":h["comment_id"],
            "original_comment":h["original_comment"],
            **s,
        })
    return {
        "job_number":job_number,
        "comments":rows,
        "open_count":sum(x["current_status"]=="OPEN" for x in rows),
        "addressed_count":sum(x["current_status"]=="ADDRESSED" for x in rows),
    }

def _copy(history):
    r=dict(history)
    r["events"]=[]
    for e in history.get("events",[]):
        x=dict(e)
        x["evidence"]=[dict(v) for v in e.get("evidence",[])]
        r["events"].append(x)
    return r

def history_policy():
    return {
        "preserve_original_comment":True,
        "preserve_prior_applicant_responses":True,
        "preserve_revision_history":True,
        "automatic_addressed_determination":False,
        "automatic_reopen":False,
        "reviewer_authorization_required_for_status_changes":True,
    }
