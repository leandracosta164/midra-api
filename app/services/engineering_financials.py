"""Phase 5.52 — lightweight project financial and revenue foundation."""
from decimal import Decimal

def _money(v): return Decimal(str(v)).quantize(Decimal("0.01"))

def create_job_financial_record(*,job_number,accepted_proposal_id,approved_fee):
    fee=_money(approved_fee)
    if fee < 0: raise ValueError("approved fee cannot be negative")
    return {"job_number":job_number,"accepted_proposal_id":accepted_proposal_id,
            "base_approved_fee":fee,"additional_services":[],"invoices":[],"payments":[]}

def add_additional_service(*,record,service_id,description,fee,authorized_by):
    if not authorized_by.strip(): raise ValueError("authorization required")
    r=_copy(record); r["additional_services"].append({"service_id":service_id,"description":description,
        "fee":_money(fee),"authorized_by":authorized_by}); return r

def record_invoice(*,record,invoice_id,amount):
    r=_copy(record); r["invoices"].append({"invoice_id":invoice_id,"amount":_money(amount)}); return r

def record_payment(*,record,payment_id,amount,invoice_id=None):
    r=_copy(record); r["payments"].append({"payment_id":payment_id,"amount":_money(amount),"invoice_id":invoice_id}); return r

def financial_summary(*,record):
    contracted=record["base_approved_fee"]+sum((x["fee"] for x in record["additional_services"]),Decimal("0"))
    invoiced=sum((x["amount"] for x in record["invoices"]),Decimal("0"))
    paid=sum((x["amount"] for x in record["payments"]),Decimal("0"))
    return {"job_number":record["job_number"],"contracted_fee":contracted,"invoiced":invoiced,"paid":paid,
            "uninvoiced":contracted-invoiced,"outstanding_invoice_balance":invoiced-paid}

def portfolio_revenue_view(*,records):
    summaries=[financial_summary(record=r) for r in records]
    return {"visibility":"MIDRA_ENGINEERING_PRIVATE","jobs":summaries,
            "totals":{"contracted":sum((x["contracted_fee"] for x in summaries),Decimal("0")),
                      "invoiced":sum((x["invoiced"] for x in summaries),Decimal("0")),
                      "paid":sum((x["paid"] for x in summaries),Decimal("0")),
                      "outstanding":sum((x["outstanding_invoice_balance"] for x in summaries),Decimal("0"))}}

def _copy(r):
    return {**r,"additional_services":[dict(x) for x in r["additional_services"]],
            "invoices":[dict(x) for x in r["invoices"]],"payments":[dict(x) for x in r["payments"]]}
