"""Phase 5.55 — historical fee intelligence for MIDRA Engineering."""
from decimal import Decimal

def _money(v):
    return Decimal(str(v)).quantize(Decimal("0.01"))

def create_pricing_history_entry(*, job_number, project_type, approved_fee,
                                 confirmed_hours, complexity="STANDARD",
                                 additional_service_revenue=0,
                                 completed=True):
    return {
        "job_number": job_number,
        "project_type": project_type,
        "complexity": complexity,
        "approved_fee": _money(approved_fee),
        "additional_service_revenue": _money(additional_service_revenue),
        "confirmed_hours": Decimal(str(confirmed_hours)).quantize(Decimal("0.01")),
        "completed": bool(completed),
    }

def build_pricing_library(*, entries):
    """Only completed jobs become historical pricing evidence."""
    usable = [dict(e) for e in entries if e.get("completed")]
    return {
        "visibility": "MIDRA_ENGINEERING_PRIVATE",
        "entries": usable,
        "count": len(usable),
    }

def recommend_fee(*, project_type, complexity, library):
    matches = [
        e for e in library.get("entries", [])
        if e.get("project_type") == project_type and e.get("complexity") == complexity
    ]
    if not matches:
        return {
            "project_type": project_type,
            "complexity": complexity,
            "status": "INSUFFICIENT_HISTORICAL_DATA",
            "recommended_fee": None,
            "automatic_fee_setting": False,
            "send_authorized": False,
            "requires_human_review": True,
        }

    fees = [e["approved_fee"] + e.get("additional_service_revenue", Decimal("0")) for e in matches]
    avg_fee = (sum(fees, Decimal("0")) / len(fees)).quantize(Decimal("0.01"))
    total_hours = sum((e.get("confirmed_hours", Decimal("0")) for e in matches), Decimal("0"))
    total_revenue = sum(fees, Decimal("0"))
    avg_revenue_per_hour = None if total_hours == 0 else (total_revenue / total_hours).quantize(Decimal("0.01"))

    return {
        "project_type": project_type,
        "complexity": complexity,
        "status": "HISTORICAL_GUIDANCE_AVAILABLE",
        "recommended_fee": avg_fee,
        "sample_size": len(matches),
        "historical_average_revenue_per_hour": avg_revenue_per_hour,
        "basis_job_numbers": [e["job_number"] for e in matches],
        "automatic_fee_setting": False,
        "send_authorized": False,
        "requires_human_review": True,
    }

def approve_fee_for_proposal(*, recommendation, selected_fee, authorized_by):
    if not authorized_by.strip():
        raise ValueError("fee approval requires authorized human")
    return {
        "project_type": recommendation["project_type"],
        "selected_fee": _money(selected_fee),
        "historical_recommendation": recommendation.get("recommended_fee"),
        "approved_by": authorized_by,
        "status": "FEE_APPROVED_FOR_PROPOSAL_DRAFT",
        "send_authorized": False,
    }

def pricing_policy():
    return {
        "uses_own_completed_job_history": True,
        "automatic_fee_setting": False,
        "automatic_proposal_sending": False,
        "human_can_override_recommendation": True,
        "insufficient_data_must_be_disclosed": True,
    }
