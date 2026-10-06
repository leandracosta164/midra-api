"""Phase 5.70 — submission package and completeness intelligence."""

ITEM_STATES={"RECEIVED","MISSING","POTENTIAL_WAIVER","REQUIRES_REVIEW","NOT_APPLICABLE"}

def create_submission_package(*,package_id,job_number,submission_number,received_date,
                              transmittal_document_id=None):
    return {
        "package_id":package_id,"job_number":job_number,
        "submission_number":submission_number,"received_date":received_date,
        "transmittal_document_id":transmittal_document_id,
        "documents":[],"checklist_items":[],"status":"PACKAGE_INTAKE",
    }

def add_received_document(*,package,document_id,title,document_date=None,
                          revision=None,document_type=None):
    r=_copy(package)
    r["documents"].append({
        "document_id":document_id,"title":title,"document_date":document_date,
        "revision":revision,"document_type":document_type,
    })
    return r

def add_checklist_item(*,package,item_id,requirement,official_source,
                       matched_document_ids=None,state=None,waiver_basis=None):
    matches=list(matched_document_ids or [])
    if state is None:
        state="RECEIVED" if matches else "MISSING"
    if state not in ITEM_STATES:
        raise ValueError("unsupported checklist state")
    if state=="RECEIVED" and not matches:
        raise ValueError("received checklist item requires matched document")
    if state=="POTENTIAL_WAIVER" and not waiver_basis:
        raise ValueError("potential waiver requires basis")
    r=_copy(package)
    r["checklist_items"].append({
        "item_id":item_id,"requirement":requirement,
        "official_source":official_source,
        "matched_document_ids":matches,"state":state,
        "waiver_basis":waiver_basis,"confirmed":False,
    })
    r["status"]="COMPLETENESS_REVIEW_REQUIRED"
    return r

def confirm_checklist_item(*,package,item_id,state,authorized_by,note=None):
    if state not in ITEM_STATES:
        raise ValueError("unsupported checklist state")
    if not authorized_by.strip():
        raise ValueError("authorized reviewer required")
    r=_copy(package)
    item=_item(r,item_id)
    if state=="RECEIVED" and not item["matched_document_ids"]:
        raise ValueError("cannot confirm received without matched document")
    item["state"]=state
    item["confirmed"]=True
    item["confirmed_by"]=authorized_by
    item["confirmation_note"]=note
    return r

def completeness_summary(*,package):
    items=package["checklist_items"]
    counts={s:sum(x["state"]==s for x in items) for s in ITEM_STATES}
    unconfirmed=sum(not x.get("confirmed") for x in items)
    return {
        "total_items":len(items),
        "received":counts["RECEIVED"],
        "missing":counts["MISSING"],
        "potential_waiver":counts["POTENTIAL_WAIVER"],
        "requires_review":counts["REQUIRES_REVIEW"],
        "not_applicable":counts["NOT_APPLICABLE"],
        "unconfirmed":unconfirmed,
        "ready_for_final_determination":bool(items) and unconfirmed==0,
    }

def applicant_transmittal_claim(*,package,item_id,claim):
    """Applicant/transmittal statements are evidence, not final completeness findings."""
    r=_copy(package)
    item=_item(r,item_id)
    item.setdefault("applicant_claims",[]).append(claim)
    if not item.get("confirmed"):
        item["state"]="REQUIRES_REVIEW"
    return r

def build_completeness_review_input(*,package):
    return {
        "job_number":package["job_number"],
        "package_id":package["package_id"],
        "submission_number":package["submission_number"],
        "documents_received":[dict(x) for x in package["documents"]],
        "checklist_items":[dict(x) for x in package["checklist_items"]],
        "summary":completeness_summary(package=package),
        "status":"DRAFT_REQUIRES_REVIEW",
    }

def _item(package,item_id):
    for x in package["checklist_items"]:
        if x["item_id"]==item_id:
            return x
    raise KeyError(item_id)

def _copy(package):
    r=dict(package)
    r["documents"]=[dict(x) for x in package.get("documents",[])]
    r["checklist_items"]=[]
    for x in package.get("checklist_items",[]):
        y=dict(x)
        y["matched_document_ids"]=list(x.get("matched_document_ids",[]))
        y["applicant_claims"]=list(x.get("applicant_claims",[]))
        r["checklist_items"].append(y)
    return r

def completeness_policy():
    return {
        "official_checklist_source_required":True,
        "trust_transmittal_claim_without_verification":False,
        "automatic_final_completeness_determination":False,
        "waiver_requires_review":True,
        "document_revision_metadata_preserved":True,
        "human_confirmation_required":True,
    }
