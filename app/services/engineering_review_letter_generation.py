"""Phase 5.68 — controlled engineering/completeness review letter generation."""

FINDING_STATES={"OPEN","RESOLVED","NEW_COMMENT","REQUIRES_REVIEW"}

def create_review_finding(*,finding_id,text,status,source=None,evidence=None,
                          prior_comment_id=None):
    if status not in FINDING_STATES:
        raise ValueError("unsupported finding status")
    return {"finding_id":finding_id,"text":text,"status":status,"source":source,
            "evidence":[dict(x) for x in (evidence or [])],
            "prior_comment_id":prior_comment_id,"confirmed":False}

def confirm_review_finding(*,finding,authorized_by):
    if not authorized_by.strip():
        raise ValueError("authorized reviewer required")
    r=dict(finding); r["evidence"]=[dict(x) for x in finding.get("evidence",[])]
    r["confirmed"]=True; r["confirmed_by"]=authorized_by
    return r

def build_engineering_review_letter_draft(*,job,review_type,review_number,
                                          documents_reviewed,findings,template_id,
                                          addressee=None):
    """Assemble review draft; unconfirmed findings remain visibly review-required."""
    sections={"OPEN":[],"RESOLVED":[],"NEW_COMMENT":[],"REQUIRES_REVIEW":[]}
    for f in findings:
        x=dict(f); x["evidence"]=[dict(e) for e in f.get("evidence",[])]
        effective=f["status"] if f.get("confirmed") else "REQUIRES_REVIEW"
        sections[effective].append(x)
    return {
        "job_number":job["job_number"],
        "property_address":job.get("property_address"),
        "municipality":job.get("municipality"),
        "review_type":review_type,"review_number":review_number,
        "addressee":addressee,
        "documents_reviewed":[dict(x) for x in documents_reviewed],
        "sections":sections,"template_id":template_id,
        "status":"DRAFT_REQUIRES_REVIEW","issue_authorized":False,
    }

def revise_review_letter(*,draft,authorized_by,addressee=None):
    if not authorized_by.strip():
        raise ValueError("authorized reviewer required")
    r=dict(draft)
    if addressee is not None: r["addressee"]=addressee
    r["status"]="REVIEWED_DRAFT"; r["reviewed_by"]=authorized_by
    return r

def authorize_review_letter_issue(*,draft,authorized_by):
    if draft.get("status")!="REVIEWED_DRAFT":
        raise ValueError("review letter must be reviewed before issue authorization")
    if not authorized_by.strip():
        raise ValueError("issue authorization required")
    if draft.get("sections",{}).get("REQUIRES_REVIEW"):
        raise ValueError("unconfirmed findings remain")
    r=dict(draft); r["status"]="APPROVED_FOR_ISSUE"
    r["issue_authorized"]=True; r["issue_authorized_by"]=authorized_by
    return r

def review_letter_summary(*,draft):
    s=draft["sections"]
    return {"open":len(s["OPEN"]),"resolved":len(s["RESOLVED"]),
            "new_comments":len(s["NEW_COMMENT"]),
            "requires_review":len(s["REQUIRES_REVIEW"])}

def review_letter_policy():
    return {"uses_verified_project_findings":True,
            "unconfirmed_findings_cannot_be_issued_as_final":True,
            "automatic_professional_issue":False,
            "documents_reviewed_are_preserved":True,
            "project_template_required":True}

