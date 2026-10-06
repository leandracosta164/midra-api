"""Phase 5.77 — unified project origin and MIDRA Property → Engineering handoff.

All intake channels normalize into one Engineering request model while preserving where
the opportunity came from and reusing verified MIDRA Property information when present.
"""

SOURCES={"MIDRA_PROPERTY","ENGINEERING_WEBSITE","PHONE_MANUAL","EMAIL_MANUAL","OTHER"}

def create_project_request(*, request_id, source, property_address, requested_work,
                           client_name=None, property_analysis_id=None,
                           property_analysis=None):
    if source not in SOURCES:
        raise ValueError("unsupported project source")
    if source=="MIDRA_PROPERTY" and not property_analysis_id:
        raise ValueError("MIDRA Property request requires analysis reference")
    return {
        "request_id":request_id,"source":source,"property_address":property_address,
        "requested_work":requested_work,"client_name":client_name,
        "property_analysis_id":property_analysis_id,
        "property_analysis":dict(property_analysis or {}),
        "engineering_fields":{},
        "status":"NEW_REQUEST",
    }

def prefill_engineering_request(*, request):
    """Reuse known facts; never pretend unknown intake fields are complete."""
    r=_copy(request)
    analysis=r.get("property_analysis",{})
    fields={
        "property_address":{"value":r["property_address"],"source":r["source"],
                            "confidence":"CONFIRMED_INPUT"},
        "requested_work":{"value":r["requested_work"],"source":r["source"],
                          "confidence":"CONFIRMED_INPUT"},
    }
    reusable={
        "municipality":"municipality",
        "block":"block",
        "lot":"lot",
        "zoning_district":"zoning_district",
        "property_constraints":"property_constraints",
        "likely_approvals":"likely_approvals",
    }
    for target,key in reusable.items():
        if key in analysis and analysis[key] not in (None,"",[]):
            fields[target]={"value":analysis[key],"source":"MIDRA_PROPERTY",
                            "confidence":"ANALYSIS_DERIVED"}
    r["engineering_fields"]=fields
    r["status"]="PREFILLED_REQUIRES_REVIEW"
    return r

def add_manual_intake_field(*, request, field, value, entered_by):
    if not (entered_by or "").strip():
        raise ValueError("manual entry user required")
    r=_copy(request)
    r.setdefault("engineering_fields",{})[field]={
        "value":value,"source":"MANUAL_INTAKE","confidence":"USER_ENTERED",
        "entered_by":entered_by,
    }
    return r

def confirm_engineering_intake(*, request, authorized_by):
    if not (authorized_by or "").strip():
        raise ValueError("intake confirmation required")
    if not request.get("engineering_fields",{}).get("property_address"):
        raise ValueError("property address required")
    if not request.get("engineering_fields",{}).get("requested_work"):
        raise ValueError("requested work required")
    r=_copy(request)
    r["status"]="READY_FOR_ESTIMATING"
    r["confirmed_by"]=authorized_by
    return r

def convert_to_engineering_lead(*, request, lead_id, authorized_by):
    if request.get("status")!="READY_FOR_ESTIMATING":
        raise ValueError("request must be confirmed before lead conversion")
    if not (authorized_by or "").strip():
        raise ValueError("lead conversion authorization required")
    return {
        "lead_id":lead_id,"request_id":request["request_id"],
        "source":request["source"],"property_address":request["property_address"],
        "requested_work":request["requested_work"],
        "property_analysis_id":request.get("property_analysis_id"),
        "prefilled_fields":{k:dict(v) for k,v in request["engineering_fields"].items()},
        "status":"ESTIMATING",
    }

def intake_efficiency_view(*, request):
    fields=request.get("engineering_fields",{})
    reused=sum(v.get("source")=="MIDRA_PROPERTY" for v in fields.values())
    manual=sum(v.get("source")=="MANUAL_INTAKE" for v in fields.values())
    return {"source":request["source"],"field_count":len(fields),
            "property_fields_reused":reused,"manual_fields":manual}

def _copy(request):
    r=dict(request)
    r["property_analysis"]=dict(request.get("property_analysis",{}))
    r["engineering_fields"]={k:dict(v) for k,v in request.get("engineering_fields",{}).items()}
    return r

def handoff_policy():
    return {
        "all_sources_normalize_to_one_engineering_request":True,
        "source_is_preserved":True,
        "midra_property_data_is_reused_not_retyped":True,
        "phone_requests_support_manual_entry":True,
        "unknown_fields_are_not_invented":True,
        "engineering_intake_requires_confirmation":True,
    }
