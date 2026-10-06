"""Phase 5.50 — Engineering templates, response letters and checklist automation."""
from __future__ import annotations

AUTO_FILL_THRESHOLD = 1.0


def register_engineering_template(*, template_id: str, name: str, artifact_id: str,
                                  template_type: str, approved_by: str) -> dict:
    if any(not str(v or "").strip() for v in
           (template_id, name, artifact_id, template_type, approved_by)):
        raise ValueError("template registration requires complete identity")
    return {
        "template_id": template_id, "name": name, "artifact_id": artifact_id,
        "template_type": template_type, "approved_by": approved_by,
        "status": "ACTIVE",
    }


def draft_review_response(*, comment: dict, evidence: list[dict]) -> dict:
    """Draft only when project evidence supports a response; never claim closure."""
    verified = [e for e in evidence if e.get("verified") is True]
    if not verified:
        return {
            "comment_id": comment["comment_id"],
            "draft_status": "ADDITIONAL_INFORMATION_REQUIRED",
            "response_text": None,
            "evidence": [],
            "requires_human_review": True,
        }
    refs = ", ".join(e.get("reference", e.get("artifact_id", "project evidence"))
                     for e in verified)
    return {
        "comment_id": comment["comment_id"],
        "draft_status": "DRAFT_READY",
        "response_text": f"Response prepared based on verified project information: {refs}.",
        "evidence": [dict(e) for e in verified],
        "requires_human_review": True,
    }


def generate_response_letter_draft(*, job: dict, template: dict,
                                   review_reference: str,
                                   responses: list[dict]) -> dict:
    return {
        "job_number": job["job_number"],
        "template_id": template["template_id"],
        "template_artifact_id": template["artifact_id"],
        "document_type": "ENGINEERING_RESPONSE_LETTER",
        "review_reference": review_reference,
        "responses": [dict(r) for r in responses],
        "status": "DRAFT_REQUIRES_REVIEW",
        "final": False,
    }


def municipal_checklist_search_request(*, municipality: str, project_type: str,
                                       job_number: str) -> dict:
    """Contract for official-source checklist discovery; actual web retrieval is external."""
    return {
        "job_number": job_number,
        "municipality": municipality,
        "project_type": project_type,
        "source_requirement": "OFFICIAL_MUNICIPAL_OR_AGENCY_SOURCE",
        "action": "FIND_MUNICIPAL_CHECKLIST",
    }


def prefill_checklist(*, checklist_fields: list[dict],
                      verified_project_data: dict[str, dict]) -> dict:
    fields = []
    for field in checklist_fields:
        key = field["key"]
        datum = verified_project_data.get(key)
        if datum and datum.get("confidence") == AUTO_FILL_THRESHOLD and datum.get("verified") is True:
            fields.append({
                **field, "value": datum.get("value"), "status": "AUTO_FILLED_VERIFIED",
                "source": datum.get("source"), "requires_user_input": False,
            })
        else:
            fields.append({
                **field, "value": None, "status": "REQUIRES_REVIEW_OR_INPUT",
                "source": None, "requires_user_input": True,
            })
    return {
        "fields": fields,
        "auto_filled_count": sum(f["status"] == "AUTO_FILLED_VERIFIED" for f in fields),
        "requires_attention_count": sum(f["requires_user_input"] for f in fields),
        "status": "DRAFT_REQUIRES_REVIEW",
    }


def finalize_generated_document(*, draft: dict, authorized_by: str) -> dict:
    if not authorized_by.strip():
        raise ValueError("finalization requires authorized human review")
    result = dict(draft)
    result["status"] = "FINAL"
    result["final"] = True
    result["authorized_by"] = authorized_by
    return result
