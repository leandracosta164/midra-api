"""Phase 5.63 — communication and correspondence intelligence."""

CHANNELS={"EMAIL","PHONE_NOTE","WEBSITE","AGENCY_LETTER","MEETING_NOTE","OTHER"}

def create_correspondence(*, correspondence_id, channel, subject, body,
                          sender=None, recipient=None, received_at=None,
                          attachments=None):
    if channel not in CHANNELS:
        raise ValueError("unsupported communication channel")
    return {
        "correspondence_id":correspondence_id,"channel":channel,
        "subject":subject,"body":body,"sender":sender,"recipient":recipient,
        "received_at":received_at,"attachments":list(attachments or []),
        "job_number":None,"filing_status":"UNASSIGNED",
    }

def suggest_job_assignment(*, correspondence, candidate_jobs):
    """Suggest only; never silently file ambiguous correspondence."""
    text=f'{correspondence.get("subject","")} {correspondence.get("body","")}'.casefold()
    matches=[]
    for job in candidate_jobs:
        score=0
        reasons=[]
        number=str(job.get("job_number",""))
        address=str(job.get("property_address",""))
        if number and number.casefold() in text:
            score+=100; reasons.append("JOB_NUMBER")
        if address and address.casefold() in text:
            score+=80; reasons.append("PROPERTY_ADDRESS")
        if correspondence.get("sender") and correspondence.get("sender") in job.get("known_contacts",[]):
            score+=30; reasons.append("KNOWN_CONTACT")
        if score:
            matches.append({"job_number":number,"score":score,"reasons":reasons})
    matches.sort(key=lambda x:(-x["score"],x["job_number"]))
    if not matches:
        return {"status":"NO_MATCH","suggested_job_number":None,"requires_confirmation":True}
    unique_top=len(matches)==1 or matches[0]["score"]>matches[1]["score"]
    return {"status":"SUGGESTED_MATCH" if unique_top else "AMBIGUOUS",
            "suggested_job_number":matches[0]["job_number"] if unique_top else None,
            "matches":matches,"requires_confirmation":True}

def assign_correspondence_to_job(*, correspondence, job_number, authorized_by):
    if not authorized_by.strip():
        raise ValueError("filing confirmation required")
    r=dict(correspondence)
    r["attachments"]=list(correspondence.get("attachments",[]))
    r["job_number"]=job_number
    r["filing_status"]="ASSIGNED_CONFIRMED"
    r["assigned_by"]=authorized_by
    return r

def extract_action_candidates(*, correspondence):
    """Low-risk action extraction; candidates require review before becoming tasks."""
    text=f'{correspondence.get("subject","")} {correspondence.get("body","")}'.casefold()
    candidates=[]
    triggers=[
        ("please revise","REVISION_REQUEST"),
        ("please provide","INFORMATION_REQUEST"),
        ("please submit","SUBMISSION_REQUEST"),
        ("follow up","FOLLOW_UP"),
        ("review comment","REVIEW_RESPONSE"),
    ]
    for phrase,kind in triggers:
        if phrase in text:
            candidates.append({"type":kind,"source_correspondence_id":correspondence["correspondence_id"],
                               "requires_human_review":True})
    return candidates

def correspondence_repository_record(*, correspondence):
    if correspondence.get("filing_status")!="ASSIGNED_CONFIRMED":
        raise ValueError("correspondence must be assigned before project filing")
    return {"job_number":correspondence["job_number"],
            "document_area":"CORRESPONDENCE",
            "correspondence_id":correspondence["correspondence_id"],
            "channel":correspondence["channel"],
            "attachments":list(correspondence.get("attachments",[]))}

def communication_policy():
    return {"automatic_ambiguous_job_filing":False,
            "automatic_action_completion":False,
            "action_candidates_require_review":True,
            "phone_notes_supported":True,
            "manual_logging_of_every_communication_required":False}
