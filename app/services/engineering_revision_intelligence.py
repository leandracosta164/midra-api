"""Phase 5.67 — revision comparison and change intelligence."""

CHANGE_TYPES={"ADDED","REMOVED","MODIFIED","UNCHANGED","POTENTIAL_CONFLICT"}

def create_revision_comparison(*,comparison_id,job_number,previous_set_id,current_set_id):
    if previous_set_id==current_set_id:
        raise ValueError("revision comparison requires different document sets")
    return {"comparison_id":comparison_id,"job_number":job_number,
            "previous_set_id":previous_set_id,"current_set_id":current_set_id,
            "changes":[],"status":"COMPARISON_IN_PROGRESS"}

def add_revision_change(*,comparison,document_key,location,change_type,
                        description,previous_value=None,current_value=None,
                        related_comment_ids=None,evidence=None):
    if change_type not in CHANGE_TYPES:
        raise ValueError("unsupported change type")
    r=_copy(comparison)
    r["changes"].append({
        "document_key":document_key,"location":location,"change_type":change_type,
        "description":description,"previous_value":previous_value,
        "current_value":current_value,
        "related_comment_ids":list(related_comment_ids or []),
        "evidence":[dict(x) for x in (evidence or [])],
        "confirmed":False,
    })
    r["status"]="COMPARISON_REQUIRES_REVIEW"
    return r

def confirm_revision_change(*,comparison,index,authorized_by):
    if not authorized_by.strip():
        raise ValueError("authorized reviewer required")
    r=_copy(comparison)
    r["changes"][index]["confirmed"]=True
    r["changes"][index]["confirmed_by"]=authorized_by
    return r

def comment_change_view(*,comparison,comment_id):
    matches=[dict(c) for c in comparison["changes"]
             if comment_id in c.get("related_comment_ids",[])]
    changed=[c for c in matches if c["change_type"]!="UNCHANGED"]
    return {"comment_id":comment_id,"related_changes":matches,
            "change_found":bool(changed),
            "status":"CHANGE_FOUND" if changed else "NO_RELEVANT_CHANGE_FOUND"}

def revision_summary(*,comparison):
    counts={k:sum(c["change_type"]==k for c in comparison["changes"])
            for k in CHANGE_TYPES}
    unconfirmed=sum(not c.get("confirmed") for c in comparison["changes"])
    return {"comparison_id":comparison["comparison_id"],"counts":counts,
            "unconfirmed_changes":unconfirmed,
            "review_complete":bool(comparison["changes"]) and unconfirmed==0}

def focused_review_queue(*,comparison):
    rank={"POTENTIAL_CONFLICT":0,"MODIFIED":10,"ADDED":20,"REMOVED":20,"UNCHANGED":50}
    items=[dict(c) for c in comparison["changes"] if not c.get("confirmed")]
    items.sort(key=lambda x:(rank[x["change_type"]],x["document_key"],x["location"]))
    return items

def _copy(comparison):
    r=dict(comparison); r["changes"]=[]
    for c in comparison.get("changes",[]):
        x=dict(c); x["related_comment_ids"]=list(c.get("related_comment_ids",[]))
        x["evidence"]=[dict(e) for e in c.get("evidence",[])]
        r["changes"].append(x)
    return r

def revision_policy():
    return {"automatic_final_change_confirmation":False,
            "unchanged_items_may_be_reported":True,
            "open_comment_linkage_supported":True,
            "evidence_locations_preserved":True,
            "full_rereview_required_when_focused_review_is_sufficient":False}
