"""Phase 5.54 — low-friction project time and profitability intelligence."""
from decimal import Decimal

def _money(v): return Decimal(str(v)).quantize(Decimal("0.01"))
def _hours(v): return Decimal(str(v)).quantize(Decimal("0.01"))

def record_effort(*,job_number,effort_id,hours,activity,source="AUTOMATIC",hourly_cost=None,confirmed=False):
    h=_hours(hours)
    if h < 0: raise ValueError("hours cannot be negative")
    if source not in {"AUTOMATIC","MANUAL","IMPORTED"}: raise ValueError("unsupported effort source")
    return {"job_number":job_number,"effort_id":effort_id,"hours":h,"activity":activity,"source":source,
            "hourly_cost":None if hourly_cost is None else _money(hourly_cost),"confirmed":confirmed}

def suggest_effort_from_activity(*,job_number,effort_id,activity,duration_minutes):
    """Use activity already captured by MIDRA; suggestion remains reviewable."""
    return record_effort(job_number=job_number,effort_id=effort_id,
        hours=Decimal(str(duration_minutes))/Decimal("60"),activity=activity,
        source="AUTOMATIC",confirmed=False)

def confirm_effort(*,effort,authorized_by):
    if not authorized_by.strip(): raise ValueError("authorized reviewer required")
    r=dict(effort); r["confirmed"]=True; r["confirmed_by"]=authorized_by; return r

def profitability_summary(*,job_number,contracted_revenue,efforts,complimentary_value=0):
    scoped=[e for e in efforts if e.get("job_number")==job_number and e.get("confirmed")]
    hours=sum((e["hours"] for e in scoped),Decimal("0"))
    known_cost=sum((e["hours"]*e["hourly_cost"] for e in scoped if e.get("hourly_cost") is not None),Decimal("0"))
    revenue=_money(contracted_revenue)
    return {"job_number":job_number,"contracted_revenue":revenue,"confirmed_hours":hours,
            "known_labor_cost":known_cost.quantize(Decimal("0.01")),
            "gross_contribution_before_overhead":(revenue-known_cost).quantize(Decimal("0.01")),
            "revenue_per_confirmed_hour":None if hours==0 else (revenue/hours).quantize(Decimal("0.01")),
            "complimentary_service_value":_money(complimentary_value),
            "profitability_status":"INSUFFICIENT_COST_DATA" if any(e.get("hourly_cost") is None for e in scoped) else "CALCULATED"}

def pricing_insight(*,project_type,summaries):
    valid=[s for s in summaries if s.get("confirmed_hours",0)>0]
    if not valid: return {"project_type":project_type,"status":"INSUFFICIENT_DATA","requires_action":False}
    avg=sum((s["revenue_per_confirmed_hour"] for s in valid if s["revenue_per_confirmed_hour"] is not None),Decimal("0"))/len(valid)
    return {"project_type":project_type,"status":"INTERNAL_INSIGHT","average_revenue_per_hour":avg.quantize(Decimal("0.01")),
            "requires_action":False,"automatic_fee_change":False}

def time_capture_policy():
    return {"mandatory_timer":False,"mandatory_daily_timesheet":False,
            "preferred_sources":["MIDRA_ACTIVITY","OPTIONAL_MANUAL_ENTRY","AUTHORIZED_IMPORT"],
            "automatic_entries_require_review":True}
