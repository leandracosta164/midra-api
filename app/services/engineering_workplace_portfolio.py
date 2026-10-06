"""Unified read model for MIDRA Workplace.

Combines the Property-origin Engineering proposal pipeline with the existing
Engineering command-center cards. This is operational context only; it does not
approve proposals, accept professional work, or mutate Engineering jobs.
"""
from __future__ import annotations

from collections import defaultdict
import json
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.property_engineering_proposal_request import PropertyEngineeringProposalRequest
from app.models.engineering_property_proposal_draft import EngineeringPropertyProposalDraft
from app.models.engineering_property_proposal_review import EngineeringPropertyProposalReview
from app.models.engineering_property_proposal_release import EngineeringPropertyProposalRelease
from app.models.engineering_property_proposal_client_response import EngineeringPropertyProposalClientResponse
from app.models.engineering_property_proposal_job_creation import EngineeringPropertyProposalJobCreation
from app.models.property_engineering_job_link import PropertyEngineeringJobLink
from app.models.property_record import PropertyRecord
from app.models.property_analysis_run import PropertyAnalysisRun
from app.models.engineering_job import EngineeringJob
from app.services.engineering_persistent_command_center import persistent_command_center
from app.services.engineering_workspace_dashboard import load_engineering_workspace
from app.services.property_engineering_proposal_context import build_dynamic_engineering_handoff_summary
from app.services.property_verification_delivery import build_delivery_verification_summary


def classify_property_proposal_stage(
    *,
    has_draft: bool = False,
    has_review: bool = False,
    has_release: bool = False,
    client_response: str | None = None,
    engineering_job_number: str | None = None,
) -> dict[str, Any]:
    response=(client_response or "").strip().upper()

    if engineering_job_number:
        return {
            "stage":"ENGINEERING_JOB_CREATED",
            "next_action":"OPEN_ENGINEERING_JOB",
            "attention":"NORMAL",
        }
    if response=="DECLINED":
        return {
            "stage":"CLIENT_DECLINED",
            "next_action":"NONE",
            "attention":"INFO",
        }
    if response=="ACCEPTED":
        return {
            "stage":"READY_FOR_JOB_CREATION",
            "next_action":"CREATE_ENGINEERING_JOB",
            "attention":"ATTENTION",
        }
    if has_release:
        return {
            "stage":"AWAITING_CLIENT_RESPONSE",
            "next_action":"RECORD_CLIENT_RESPONSE",
            "attention":"NORMAL",
        }
    if has_review:
        return {
            "stage":"READY_FOR_CLIENT_RELEASE",
            "next_action":"RELEASE_PROPOSAL_TO_CLIENT",
            "attention":"ATTENTION",
        }
    if has_draft:
        return {
            "stage":"AWAITING_ENGINEERING_REVIEW",
            "next_action":"REVIEW_PROPOSAL_DRAFT",
            "attention":"ATTENTION",
        }
    return {
        "stage":"AWAITING_PROPOSAL_DRAFT",
        "next_action":"GENERATE_PROPOSAL_DRAFT",
        "attention":"ATTENTION",
    }


def _latest_by_request(items: list[Any]) -> dict[str, Any]:
    latest={}
    for item in items:
        request_id=getattr(item,"proposal_request_id",None)
        if not request_id:
            continue
        current=latest.get(request_id)
        if current is None or getattr(item,"created_at",None) > getattr(current,"created_at",None):
            latest[request_id]=item
    return latest



def _workplace_search_label(*values: Any) -> str:
    return " · ".join(str(value).strip() for value in values if value not in (None, ""))


def engineering_workplace_search(
    db: Session,
    query: str,
    *,
    limit: int = 12,
) -> dict[str, Any]:
    """Fast read-only search across Property, proposal, and Engineering records."""
    q=" ".join((query or "").strip().split())
    if len(q) < 2:
        return {
            "status":"MIDRA_WORKPLACE_SEARCH_READY",
            "query":q,
            "results":[],
            "result_count":0,
        }

    safe_limit=max(1,min(int(limit or 12),25))
    pattern=f"%{q}%"
    results: list[dict[str, Any]]=[]

    property_rows=list(db.execute(
        select(PropertyRecord)
        .where(or_(
            PropertyRecord.display_address.ilike(pattern),
            PropertyRecord.search_query.ilike(pattern),
            PropertyRecord.municipality.ilike(pattern),
            PropertyRecord.county.ilike(pattern),
            PropertyRecord.block.ilike(pattern),
            PropertyRecord.lot.ilike(pattern),
        ))
        .order_by(PropertyRecord.updated_at.desc())
        .limit(safe_limit)
    ).scalars().all())

    for record in property_rows:
        results.append({
            "kind":"PROPERTY",
            "title":getattr(record,"display_address",None) or getattr(record,"search_query",None) or "Property",
            "subtitle":_workplace_search_label(
                getattr(record,"municipality",None),
                getattr(record,"county",None),
                f"Block {record.block}" if getattr(record,"block",None) else None,
                f"Lot {record.lot}" if getattr(record,"lot",None) else None,
            ),
            "property_record_id":record.property_record_id,
            "href":f"property.html?property_record_id={record.property_record_id}",
            "property_receipt":None,
        })

    proposal_rows=list(db.execute(
        select(PropertyEngineeringProposalRequest, PropertyRecord, EngineeringPropertyProposalDraft)
        .join(PropertyRecord, PropertyRecord.property_record_id == PropertyEngineeringProposalRequest.property_record_id)
        .outerjoin(
            EngineeringPropertyProposalDraft,
            EngineeringPropertyProposalDraft.proposal_request_id == PropertyEngineeringProposalRequest.proposal_request_id,
        )
        .where(or_(
            PropertyEngineeringProposalRequest.proposal_request_id.ilike(pattern),
            PropertyEngineeringProposalRequest.project_goal.ilike(pattern),
            PropertyEngineeringProposalRequest.customer_name.ilike(pattern),
            PropertyEngineeringProposalRequest.customer_email.ilike(pattern),
            PropertyRecord.display_address.ilike(pattern),
            PropertyRecord.municipality.ilike(pattern),
            PropertyRecord.block.ilike(pattern),
            PropertyRecord.lot.ilike(pattern),
            EngineeringPropertyProposalDraft.proposal_number.ilike(pattern),
        ))
        .order_by(PropertyEngineeringProposalRequest.created_at.desc())
        .limit(safe_limit * 2)
    ).all())

    seen_proposals=set()
    for request, prop, draft in proposal_rows:
        if request.proposal_request_id in seen_proposals:
            continue
        seen_proposals.add(request.proposal_request_id)
        proposal_number=getattr(draft,"proposal_number",None)
        results.append({
            "kind":"PROPOSAL",
            "title":proposal_number or (getattr(prop,"display_address",None) or "Engineering proposal"),
            "subtitle":_workplace_search_label(
                getattr(prop,"display_address",None) if proposal_number else request.project_goal,
                request.customer_name,
                request.project_goal if proposal_number else None,
            ),
            "proposal_request_id":request.proposal_request_id,
            "property_record_id":request.property_record_id,
            "analysis_run_id":request.analysis_run_id,
            "href":f"proposal.html?proposal_request_id={request.proposal_request_id}",
        })

    job_rows=list(db.execute(
        select(EngineeringJob)
        .where(or_(
            EngineeringJob.job_number.ilike(pattern),
            EngineeringJob.project_name.ilike(pattern),
            EngineeringJob.project_type.ilike(pattern),
            EngineeringJob.property_address.ilike(pattern),
            EngineeringJob.client_id.ilike(pattern),
            EngineeringJob.state.ilike(pattern),
        ))
        .order_by(EngineeringJob.updated_at.desc())
        .limit(safe_limit)
    ).scalars().all())

    for job in job_rows:
        results.append({
            "kind":"ENGINEERING_JOB",
            "title":f"{job.job_number} · {job.project_name}",
            "subtitle":_workplace_search_label(
                job.project_type,
                job.state,
                job.property_address,
            ),
            "engineering_job_number":job.job_number,
            "href":f"job.html?job={job.job_number}",
        })

    priority={"ENGINEERING_JOB":0,"PROPOSAL":1,"PROPERTY":2}
    needle=q.casefold()

    def rank(item: dict[str, Any]) -> tuple[int,int,str]:
        title=str(item.get("title") or "")
        subtitle=str(item.get("subtitle") or "")
        starts=0 if title.casefold().startswith(needle) else 1
        contains=0 if needle in title.casefold() else (1 if needle in subtitle.casefold() else 2)
        return (starts,contains,priority.get(str(item.get("kind")),9))

    results.sort(key=rank)
    results=results[:safe_limit]
    return {
        "status":"MIDRA_WORKPLACE_SEARCH_READY",
        "query":q,
        "result_count":len(results),
        "results":results,
        "professional_boundary":{
            "mode":"READ_ONLY_OPERATIONAL_PROJECTION",
            "automatic_professional_action":False,
        },
    }


WORKPLACE_ATTENTION_LEVELS={"INFO":1,"NORMAL":2,"ATTENTION":3,"URGENT":4}


def build_workplace_attention_queue(
    proposals: list[dict[str, Any]],
    engineering_cards: list[dict[str, Any]],
    verification_items: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Merge proposal and Engineering next-actions into one read-only priority queue."""
    queue: list[dict[str, Any]]=[]

    for item in proposals or []:
        attention=str(item.get("attention") or "NORMAL").upper()
        if attention not in {"ATTENTION","URGENT"}:
            continue
        next_action=str(item.get("next_action") or "NONE")
        if next_action=="NONE":
            continue
        prop=item.get("property") or {}
        queue.append({
            "kind":"PROPOSAL",
            "attention":attention,
            "title":prop.get("address") or item.get("proposal_number") or "Engineering proposal",
            "subtitle":item.get("project_goal") or "Project goal not reported",
            "next_action":next_action,
            "message":next_action.replace("_"," ").title(),
            "proposal_request_id":item.get("proposal_request_id"),
            "property_record_id":item.get("property_record_id"),
            "engineering_job_number":item.get("engineering_job_number"),
            "href":f"proposal.html?proposal_request_id={item.get('proposal_request_id')}",
            "occurred_at":item.get("requested_at"),
        })

    for card in engineering_cards or []:
        attention=str(card.get("attention") or "INFO").upper()
        pending=int(card.get("pending_approval_count") or 0)
        next_action=card.get("next_action") or {}
        if attention not in {"ATTENTION","URGENT"} and pending<=0:
            continue
        queue.append({
            "kind":"ENGINEERING_JOB",
            "attention":"URGENT" if attention=="URGENT" else "ATTENTION",
            "title":f"{card.get('job_number') or 'Engineering job'} · {card.get('project_name') or 'Engineering project'}",
            "subtitle":card.get("project_state") or "",
            "next_action":next_action.get("type") or "NO_IMMEDIATE_ACTION",
            "message":next_action.get("message") or "Review Engineering workspace.",
            "engineering_job_number":card.get("job_number"),
            "href":f"job.html?job={card.get('job_number')}",
            "pending_approval_count":pending,
            "open_signal_count":int(card.get("open_signal_count") or 0),
        })

    for item in verification_items or []:
        queue.append(dict(item))

    kind_priority={"ENGINEERING_JOB":0,"PROPOSAL":1,"PROPERTY_VERIFY":2}
    queue.sort(key=lambda item:(
        -WORKPLACE_ATTENTION_LEVELS.get(str(item.get("attention") or "NORMAL"),2),
        kind_priority.get(str(item.get("kind") or ""),9),
        str(item.get("title") or ""),
    ))
    return queue



def build_workplace_verification_attention(
    analysis_runs: list[Any],
    properties: dict[str, Any],
) -> list[dict[str, Any]]:
    """Project unresolved Property VERIFY context into Workplace attention items."""
    rows: list[dict[str, Any]]=[]
    for run in analysis_runs or []:
        analysis=getattr(run,"analysis",None) or {}
        verification=build_delivery_verification_summary(analysis)
        dynamic=build_dynamic_engineering_handoff_summary(analysis)
        explicit_items=(
            list(verification.get("items") or [])
            + list(verification.get("zoning_candidate_items") or [])
            + list(verification.get("environmental_items") or [])
        )
        dynamic_verify=dynamic.get("verification_required") is True
        if not explicit_items and not dynamic_verify:
            continue
        property_id=getattr(run,"property_record_id",None)
        prop=properties.get(property_id)
        reasons=[]
        if explicit_items:
            reasons.append(f"{len(explicit_items)} recorded verification item{'s' if len(explicit_items)!=1 else ''}")
        if dynamic_verify:
            reasons.append("dynamic intelligence remains VERIFY")
        rows.append({
            "kind":"PROPERTY_VERIFY",
            "attention":"ATTENTION",
            "title":getattr(prop,"display_address",None) or getattr(prop,"search_query",None) or "Property verification",
            "subtitle":_workplace_search_label(getattr(prop,"municipality",None),getattr(prop,"county",None)),
            "next_action":"REVIEW_PROPERTY_EVIDENCE",
            "message":"Review " + " and ".join(reasons) + ".",
            "property_record_id":property_id,
            "analysis_run_id":getattr(run,"analysis_run_id",None),
            "href":f"evidence.html?property_record_id={property_id}",
            "occurred_at":_iso(getattr(run,"created_at",None)),
        })
    return rows

def build_workplace_recent_activity(
    requests: list[Any],
    drafts: dict[str, Any],
    reviews: dict[str, Any],
    releases: dict[str, Any],
    responses: dict[str, Any],
    creations: dict[str, Any],
    properties: dict[str, Any],
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Project recorded Property-to-Engineering lifecycle events into one activity feed."""
    rows: list[dict[str, Any]]=[]

    def add(*, kind: str, label: str, request: Any, occurred_at: Any, detail: str | None = None) -> None:
        if occurred_at is None:
            return
        prop=properties.get(getattr(request, "property_record_id", None))
        rows.append({
            "kind":kind,
            "label":label,
            "title":getattr(prop, "display_address", None) or getattr(prop, "search_query", None) or "Property",
            "subtitle":detail or getattr(request, "project_goal", None) or "",
            "occurred_at":_iso(occurred_at),
            "proposal_request_id":getattr(request, "proposal_request_id", None),
            "property_record_id":getattr(request, "property_record_id", None),
            "href":f"proposal.html?proposal_request_id={getattr(request, 'proposal_request_id', '')}",
        })

    for request in requests or []:
        rid=getattr(request, "proposal_request_id", None)
        add(kind="PROPOSAL_REQUEST", label="Proposal requested", request=request, occurred_at=getattr(request, "created_at", None))
        draft=drafts.get(rid)
        if draft:
            add(kind="PROPOSAL_DRAFT", label="Engineering proposal drafted", request=request, occurred_at=getattr(draft, "created_at", None), detail=getattr(draft, "proposal_number", None) or getattr(draft, "proposal_status", None))
        review=reviews.get(rid)
        if review:
            add(kind="ENGINEERING_REVIEW", label="Engineering review recorded", request=request, occurred_at=getattr(review, "created_at", None), detail=getattr(review, "review_status", None))
        release=releases.get(rid)
        if release:
            add(kind="CLIENT_RELEASE", label="Proposal released to client", request=request, occurred_at=getattr(release, "created_at", None), detail=getattr(release, "release_status", None))
        response=responses.get(rid)
        if response:
            add(kind="CLIENT_RESPONSE", label="Client response recorded", request=request, occurred_at=getattr(response, "created_at", None), detail=getattr(response, "response_status", None))
        creation=creations.get(rid)
        if creation:
            add(kind="ENGINEERING_JOB", label="Engineering job created", request=request, occurred_at=getattr(creation, "created_at", None), detail=getattr(creation, "engineering_job_number", None))

    rows.sort(key=lambda item:item.get("occurred_at") or "", reverse=True)
    return rows[:max(1,min(int(limit or 20),50))]


def engineering_workplace_portfolio(db: Session) -> dict[str, Any]:
    requests=list(db.execute(
        select(PropertyEngineeringProposalRequest).order_by(
            PropertyEngineeringProposalRequest.created_at.desc()
        )
    ).scalars().all())

    recent_analysis_rows=list(db.execute(
        select(PropertyAnalysisRun)
        .order_by(PropertyAnalysisRun.created_at.desc())
        .limit(200)
    ).scalars().all())
    latest_analysis_by_property={}
    for run in recent_analysis_rows:
        property_id=getattr(run,"property_record_id",None)
        if property_id and property_id not in latest_analysis_by_property:
            latest_analysis_by_property[property_id]=run

    property_ids={item.property_record_id for item in requests}
    property_ids.update(latest_analysis_by_property)
    properties={}
    if property_ids:
        rows=db.execute(
            select(PropertyRecord).where(PropertyRecord.property_record_id.in_(property_ids))
        ).scalars().all()
        properties={row.property_record_id:row for row in rows}

    drafts=_latest_by_request(list(db.execute(
        select(EngineeringPropertyProposalDraft).order_by(
            EngineeringPropertyProposalDraft.created_at.desc()
        )
    ).scalars().all()))
    reviews=_latest_by_request(list(db.execute(
        select(EngineeringPropertyProposalReview).order_by(
            EngineeringPropertyProposalReview.created_at.desc()
        )
    ).scalars().all()))
    releases=_latest_by_request(list(db.execute(
        select(EngineeringPropertyProposalRelease).order_by(
            EngineeringPropertyProposalRelease.created_at.desc()
        )
    ).scalars().all()))
    responses=_latest_by_request(list(db.execute(
        select(EngineeringPropertyProposalClientResponse).order_by(
            EngineeringPropertyProposalClientResponse.created_at.desc()
        )
    ).scalars().all()))
    creations=_latest_by_request(list(db.execute(
        select(EngineeringPropertyProposalJobCreation).order_by(
            EngineeringPropertyProposalJobCreation.created_at.desc()
        )
    ).scalars().all()))

    proposals=[]
    stage_counts=defaultdict(int)
    for request in requests:
        rid=request.proposal_request_id
        draft=drafts.get(rid)
        review=reviews.get(rid)
        release=releases.get(rid)
        response=responses.get(rid)
        creation=creations.get(rid)
        stage=classify_property_proposal_stage(
            has_draft=draft is not None,
            has_review=review is not None,
            has_release=release is not None,
            client_response=getattr(response,"response_status",None),
            engineering_job_number=getattr(creation,"engineering_job_number",None),
        )
        stage_counts[stage["stage"]]+=1
        prop=properties.get(request.property_record_id)
        proposals.append({
            "proposal_request_id":rid,
            "property_record_id":request.property_record_id,
            "analysis_run_id":request.analysis_run_id,
            "project_goal":request.project_goal,
            "customer_name":request.customer_name,
            "customer_email":request.customer_email,
            "request_status":request.request_status,
            "requested_at":request.created_at.isoformat() if request.created_at else None,
            "property":{
                "address":getattr(prop,"display_address",None) or getattr(prop,"search_query",None),
                "municipality":getattr(prop,"municipality",None),
                "county":getattr(prop,"county",None),
                "block":getattr(prop,"block",None),
                "lot":getattr(prop,"lot",None),
            },
            "engineering_draft_id":getattr(draft,"engineering_draft_id",None),
            "proposal_number":getattr(draft,"proposal_number",None),
            "engineering_review_id":getattr(review,"engineering_review_id",None),
            "engineering_release_id":getattr(release,"engineering_release_id",None),
            "engineering_client_response_id":getattr(response,"engineering_client_response_id",None),
            "client_response_status":getattr(response,"response_status",None),
            "engineering_job_number":getattr(creation,"engineering_job_number",None),
            **stage,
        })

    recent_activity=build_workplace_recent_activity(
        requests, drafts, reviews, releases, responses, creations, properties, limit=20
    )
    command_center=persistent_command_center(db)
    verification_attention=build_workplace_verification_attention(
        list(latest_analysis_by_property.values()),
        properties,
    )
    attention_queue=build_workplace_attention_queue(
        proposals,
        command_center.get("cards",[]),
        verification_attention,
    )
    return {
        "status":"MIDRA_WORKPLACE_PORTFOLIO_READY",
        "proposal_count":len(proposals),
        "proposal_attention_count":sum(
            item["attention"]=="ATTENTION" for item in proposals
        ),
        "proposal_stage_counts":dict(stage_counts),
        "proposals":proposals,
        "attention_queue":attention_queue,
        "attention_queue_count":len(attention_queue),
        "verification_attention_count":len(verification_attention),
        "recent_activity":recent_activity,
        "recent_activity_count":len(recent_activity),
        "engineering":{
            "project_count":command_center.get("project_count",0),
            "needs_attention":command_center.get("needs_attention",0),
            "cards":command_center.get("cards",[]),
        },
        "professional_boundary":{
            "mode":"READ_ONLY_OPERATIONAL_PROJECTION",
            "automatic_professional_action":False,
            "notice":(
                "MIDRA Workplace summarizes recorded proposal and Engineering workflow state. "
                "It does not approve, issue, submit, or professionally accept work."
            ),
        },
    }


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def _proposal_timeline_event(
    *,
    key: str,
    label: str,
    status: str,
    occurred_at: Any = None,
    actor: str | None = None,
    detail: str | None = None,
) -> dict[str, Any]:
    return {
        "key":key,
        "label":label,
        "status":status,
        "occurred_at":_iso(occurred_at),
        "actor":actor,
        "detail":detail,
    }


def engineering_workplace_proposal_detail(
    db: Session,
    proposal_request_id: str,
) -> dict[str, Any]:
    request=db.get(PropertyEngineeringProposalRequest, proposal_request_id)
    if request is None:
        raise KeyError("proposal_request")

    prop=db.get(PropertyRecord, request.property_record_id)
    analysis_run=None
    if request.analysis_run_id:
        analysis_run=db.get(PropertyAnalysisRun, request.analysis_run_id)
        if analysis_run is not None and analysis_run.property_record_id != request.property_record_id:
            analysis_run=None

    def latest(model):
        return db.execute(
            select(model)
            .where(model.proposal_request_id == proposal_request_id)
            .order_by(model.created_at.desc())
        ).scalars().first()

    draft=latest(EngineeringPropertyProposalDraft)
    review=latest(EngineeringPropertyProposalReview)
    release=latest(EngineeringPropertyProposalRelease)
    response=latest(EngineeringPropertyProposalClientResponse)
    creation=latest(EngineeringPropertyProposalJobCreation)

    stage=classify_property_proposal_stage(
        has_draft=draft is not None,
        has_review=review is not None,
        has_release=release is not None,
        client_response=getattr(response,"response_status",None),
        engineering_job_number=getattr(creation,"engineering_job_number",None),
    )

    analysis=(getattr(analysis_run,"analysis",None) or {}) if analysis_run is not None else {}
    dynamic_summary=build_dynamic_engineering_handoff_summary(analysis)
    verification_summary=build_delivery_verification_summary(analysis)

    timeline=[
        _proposal_timeline_event(key="PROPERTY_PROPOSAL_REQUEST",label="Property proposal requested",status="COMPLETE",occurred_at=request.created_at,actor=request.customer_email,detail=request.project_goal),
        _proposal_timeline_event(key="ENGINEERING_PROPOSAL_DRAFT",label="Engineering proposal draft",status="COMPLETE" if draft else "PENDING",occurred_at=getattr(draft,"created_at",None),actor=getattr(draft,"generated_by",None),detail=getattr(draft,"proposal_status",None)),
        _proposal_timeline_event(key="ENGINEERING_REVIEW",label="Engineering review / approval",status="COMPLETE" if review else "PENDING",occurred_at=getattr(review,"created_at",None),actor=getattr(review,"reviewed_by",None),detail=getattr(review,"review_status",None)),
        _proposal_timeline_event(key="CLIENT_RELEASE",label="Proposal released to client",status="COMPLETE" if release else "PENDING",occurred_at=getattr(release,"created_at",None),actor=getattr(release,"released_by",None),detail=getattr(release,"release_status",None)),
        _proposal_timeline_event(key="CLIENT_RESPONSE",label="Client response",status="COMPLETE" if response else "PENDING",occurred_at=getattr(response,"created_at",None),actor=getattr(response,"recorded_by",None),detail=getattr(response,"response_status",None)),
        _proposal_timeline_event(key="ENGINEERING_JOB",label="Engineering job created",status="COMPLETE" if creation else "PENDING",occurred_at=getattr(creation,"created_at",None),actor=getattr(creation,"created_by",None),detail=getattr(creation,"engineering_job_number",None)),
    ]

    return {
        "status":"MIDRA_WORKPLACE_PROPOSAL_DETAIL_READY",
        "proposal_request":{
            "proposal_request_id":request.proposal_request_id,
            "property_record_id":request.property_record_id,
            "analysis_run_id":request.analysis_run_id,
            "project_goal":request.project_goal,
            "customer_name":request.customer_name,
            "customer_email":request.customer_email,
            "customer_phone":request.customer_phone,
            "request_status":request.request_status,
            "requested_at":_iso(request.created_at),
        },
        "property":{
            "address":getattr(prop,"display_address",None) or getattr(prop,"search_query",None),
            "municipality":getattr(prop,"municipality",None),
            "county":getattr(prop,"county",None),
            "block":getattr(prop,"block",None),
            "lot":getattr(prop,"lot",None),
            "property_record_id":request.property_record_id,
            "workplace_href":f"property.html?property_record_id={request.property_record_id}",
            "evidence_href":f"evidence.html?property_record_id={request.property_record_id}",
        },
        "analysis":{
            "analysis_run_id":getattr(analysis_run,"analysis_run_id",None),
            "intelligence_status":getattr(analysis_run,"intelligence_status",None),
            "verification_summary":verification_summary,
            "dynamic_intelligence_summary":dynamic_summary,
        },
        "engineering":{
            "proposal_number":getattr(draft,"proposal_number",None),
            "proposal_id":getattr(draft,"proposal_id",None),
            "draft_status":getattr(draft,"proposal_status",None),
            "review_status":getattr(review,"review_status",None),
            "release_status":getattr(release,"release_status",None),
            "client_response_status":getattr(response,"response_status",None),
            "engineering_job_number":getattr(creation,"engineering_job_number",None),
        },
        "stage":stage,
        "timeline":timeline,
        "professional_boundary":{
            "mode":"READ_ONLY_OPERATIONAL_PROJECTION",
            "automatic_professional_action":False,
            "notice":"MIDRA Workplace displays recorded proposal and Property intelligence context. It does not approve, issue, submit, professionally accept, or automatically create an Engineering job.",
        },
    }


def _workplace_property_identity(record: Any | None) -> dict[str, Any] | None:
    if record is None:
        return None
    return {
        "property_record_id":getattr(record,"property_record_id",None),
        "address":getattr(record,"display_address",None) or getattr(record,"search_query",None),
        "municipality":getattr(record,"municipality",None),
        "county":getattr(record,"county",None),
        "block":getattr(record,"block",None),
        "lot":getattr(record,"lot",None),
        "intelligence_status":getattr(record,"intelligence_status",None),
    }



def _workplace_analysis_proposal_traceability(
    proposals: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Group proposal read models by the immutable Property analysis run they reference."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for proposal in proposals or []:
        analysis_id=str(proposal.get("analysis_run_id") or "").strip()
        if analysis_id:
            grouped[analysis_id].append(proposal)
    return dict(grouped)


def _workplace_analysis_change_comparison(
    *,
    selected_run: Any | None,
    latest_run: Any | None,
    proposals_by_analysis: dict[str, list[dict[str, Any]]],
    jobs_by_analysis: dict[str, list[dict[str, Any]]],
) -> dict[str, Any] | None:
    """Compare recorded metadata only; never reinterpret evidence or professional status."""
    if selected_run is None or latest_run is None:
        return None
    selected_id=str(getattr(selected_run,"analysis_run_id","") or "")
    latest_id=str(getattr(latest_run,"analysis_run_id","") or "")
    selected={
        "analysis_run_id":selected_id,
        "requested_work":getattr(selected_run,"requested_work",None),
        "intelligence_status":getattr(selected_run,"intelligence_status",None),
        "created_at":_iso(getattr(selected_run,"created_at",None)),
        "proposal_count":len(proposals_by_analysis.get(selected_id, [])),
        "engineering_job_count":len(jobs_by_analysis.get(selected_id, [])),
    }
    latest={
        "analysis_run_id":latest_id,
        "requested_work":getattr(latest_run,"requested_work",None),
        "intelligence_status":getattr(latest_run,"intelligence_status",None),
        "created_at":_iso(getattr(latest_run,"created_at",None)),
        "proposal_count":len(proposals_by_analysis.get(latest_id, [])),
        "engineering_job_count":len(jobs_by_analysis.get(latest_id, [])),
    }
    changed=[]
    for key in ("requested_work","intelligence_status","proposal_count","engineering_job_count"):
        if selected.get(key) != latest.get(key):
            changed.append(key)
    return {
        "selected":selected,
        "latest":latest,
        "is_latest":selected_id == latest_id,
        "changed_fields":changed,
        "change_count":len(changed),
        "comparison_mode":"RECORDED_METADATA_ONLY",
    }


def _workplace_analysis_evidence_change_comparison(
    *,
    selected_run: Any | None,
    latest_run: Any | None,
) -> dict[str, Any] | None:
    """Compare recorded evidence metadata only; never reinterpret or promote evidence."""
    if selected_run is None or latest_run is None:
        return None

    def snapshot(run: Any) -> dict[str, Any]:
        analysis=(getattr(run, "analysis", None) or {})
        verification=build_delivery_verification_summary(analysis)
        dynamic=build_dynamic_engineering_handoff_summary(analysis)
        sources=_workplace_recorded_sources(analysis)
        verification_count=sum(len(verification.get(key) or []) for key in (
            "items", "zoning_candidate_items", "environmental_items"
        ))
        return {
            "analysis_run_id":getattr(run, "analysis_run_id", None),
            "verification_status":verification.get("status") or "NO_RECORDED_VERIFICATION_ITEMS",
            "verification_item_count":verification_count,
            "recorded_source_count":len(sources),
            "dynamic_intelligence_available":dynamic.get("available") is True,
            "dynamic_verification_required":dynamic.get("verification_required") is True,
            "source_trust_state":((dynamic.get("source_trust") or {}).get("trust_state")),
            "source_current_status":((dynamic.get("source_trust") or {}).get("current_status")),
        }

    selected=snapshot(selected_run)
    latest=snapshot(latest_run)
    changed=[]
    for key in (
        "verification_status",
        "verification_item_count",
        "recorded_source_count",
        "dynamic_intelligence_available",
        "dynamic_verification_required",
        "source_trust_state",
        "source_current_status",
    ):
        if selected.get(key) != latest.get(key):
            changed.append(key)
    return {
        "selected":selected,
        "latest":latest,
        "is_latest":selected.get("analysis_run_id") == latest.get("analysis_run_id"),
        "changed_fields":changed,
        "change_count":len(changed),
        "comparison_mode":"RECORDED_EVIDENCE_METADATA_ONLY",
    }


def _workplace_analysis_source_change_detail(
    *,
    selected_run: Any | None,
    latest_run: Any | None,
) -> dict[str, Any] | None:
    """Compare recorded source references only; never reinterpret source authority."""
    if selected_run is None or latest_run is None:
        return None

    def source_key(source: dict[str, Any]) -> tuple[str, str, str]:
        return (
            str(source.get("source_url") or "").strip(),
            str(source.get("label") or "").strip(),
            str(source.get("source_type") or "").strip(),
        )

    def normalize(run: Any) -> list[dict[str, Any]]:
        analysis=(getattr(run, "analysis", None) or {})
        rows=[]
        for source in _workplace_recorded_sources(analysis):
            rows.append({
                "label":source.get("label"),
                "source_url":source.get("source_url"),
                "source_type":source.get("source_type"),
                "authority":source.get("authority"),
                "retrieved_at":source.get("retrieved_at"),
                "current_status":source.get("current_status"),
                "evidence_role":source.get("evidence_role"),
                "candidate_only":source.get("candidate_only"),
            })
        return rows

    selected_sources=normalize(selected_run)
    latest_sources=normalize(latest_run)
    selected_map={source_key(item):item for item in selected_sources}
    latest_map={source_key(item):item for item in latest_sources}
    added=[latest_map[key] for key in latest_map.keys() - selected_map.keys()]
    removed=[selected_map[key] for key in selected_map.keys() - latest_map.keys()]
    added.sort(key=lambda item:(str(item.get("label") or ""),str(item.get("source_url") or "")))
    removed.sort(key=lambda item:(str(item.get("label") or ""),str(item.get("source_url") or "")))
    return {
        "selected_analysis_run_id":getattr(selected_run, "analysis_run_id", None),
        "latest_analysis_run_id":getattr(latest_run, "analysis_run_id", None),
        "is_latest":getattr(selected_run, "analysis_run_id", None) == getattr(latest_run, "analysis_run_id", None),
        "added_sources":added,
        "removed_sources":removed,
        "added_source_count":len(added),
        "removed_source_count":len(removed),
        "comparison_mode":"RECORDED_SOURCE_REFERENCES_ONLY",
    }


def _workplace_analysis_verification_item_change_detail(
    *,
    selected_run: Any | None,
    latest_run: Any | None,
) -> dict[str, Any] | None:
    """Compare recorded verification items only; never reinterpret their meaning."""
    if selected_run is None or latest_run is None:
        return None

    categories=(
        ("GENERAL", "items"),
        ("ZONING_CANDIDATE", "zoning_candidate_items"),
        ("ENVIRONMENTAL", "environmental_items"),
    )

    def normalize(run: Any) -> list[dict[str, Any]]:
        analysis=(getattr(run, "analysis", None) or {})
        verification=build_delivery_verification_summary(analysis)
        rows: list[dict[str, Any]]=[]
        for category, key in categories:
            for item in verification.get(key) or []:
                if isinstance(item, dict):
                    text=(
                        item.get("message")
                        or item.get("verification")
                        or item.get("reason")
                        or item.get("label")
                        or json.dumps(item, sort_keys=True, default=str)
                    )
                else:
                    text=str(item)
                rows.append({
                    "category":category,
                    "text":str(text),
                    "recorded_item":item,
                })
        return rows

    def item_key(item: dict[str, Any]) -> tuple[str, str]:
        return (
            str(item.get("category") or ""),
            json.dumps(item.get("recorded_item"), sort_keys=True, default=str),
        )

    selected_items=normalize(selected_run)
    latest_items=normalize(latest_run)
    selected_map={item_key(item):item for item in selected_items}
    latest_map={item_key(item):item for item in latest_items}
    added=[latest_map[key] for key in latest_map.keys() - selected_map.keys()]
    removed=[selected_map[key] for key in selected_map.keys() - latest_map.keys()]
    added.sort(key=lambda item:(str(item.get("category") or ""),str(item.get("text") or "")))
    removed.sort(key=lambda item:(str(item.get("category") or ""),str(item.get("text") or "")))
    return {
        "selected_analysis_run_id":getattr(selected_run, "analysis_run_id", None),
        "latest_analysis_run_id":getattr(latest_run, "analysis_run_id", None),
        "is_latest":getattr(selected_run, "analysis_run_id", None) == getattr(latest_run, "analysis_run_id", None),
        "added_items":added,
        "removed_items":removed,
        "added_item_count":len(added),
        "removed_item_count":len(removed),
        "comparison_mode":"RECORDED_VERIFICATION_ITEMS_ONLY",
    }


def _workplace_analysis_job_traceability(
    proposals_by_analysis: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    """Project Engineering jobs created from proposals back to their source analysis run."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for analysis_id, proposals in (proposals_by_analysis or {}).items():
        jobs: list[dict[str, Any]] = []
        seen: set[str] = set()
        for proposal in proposals or []:
            job_number=str(proposal.get("engineering_job_number") or "").strip()
            if not job_number or job_number in seen:
                continue
            seen.add(job_number)
            jobs.append({
                "engineering_job_number":job_number,
                "proposal_request_id":proposal.get("proposal_request_id"),
                "proposal_number":proposal.get("proposal_number"),
                "project_goal":proposal.get("project_goal"),
                "href":f"job.html?job={job_number}",
            })
        grouped[str(analysis_id)] = jobs
    return grouped


def engineering_workplace_property_detail(
    db: Session,
    property_record_id: str,
    analysis_run_id: str | None = None,
) -> dict[str, Any]:
    """Unified read-only Workplace view for a Property and its Engineering lineage."""
    property_id=(property_record_id or "").strip()
    if not property_id:
        raise KeyError("property_record")

    record=db.get(PropertyRecord, property_id)
    if record is None:
        raise KeyError("property_record")

    analysis_rows=db.execute(
        select(PropertyAnalysisRun)
        .where(PropertyAnalysisRun.property_record_id == property_id)
        .order_by(PropertyAnalysisRun.created_at.desc())
    ).scalars()
    analyses=list(analysis_rows.all())
    if not analyses:
        try:
            legacy_first=analysis_rows.first()
        except Exception:
            legacy_first=None
        if legacy_first is not None:
            analyses=[legacy_first]
    selected_analysis=None
    requested_analysis_id=(analysis_run_id or "").strip()
    if requested_analysis_id:
        selected_analysis=next((run for run in analyses if run.analysis_run_id == requested_analysis_id), None)
        if selected_analysis is None:
            raise KeyError("analysis_run")
    elif analyses:
        selected_analysis=analyses[0]

    requests=list(db.execute(
        select(PropertyEngineeringProposalRequest)
        .where(PropertyEngineeringProposalRequest.property_record_id == property_id)
        .order_by(PropertyEngineeringProposalRequest.created_at.desc())
    ).scalars().all())

    proposal_rows=[]
    for request in requests:
        rid=request.proposal_request_id
        def latest(model):
            return db.execute(
                select(model)
                .where(model.proposal_request_id == rid)
                .order_by(model.created_at.desc())
            ).scalars().first()
        draft=latest(EngineeringPropertyProposalDraft)
        review=latest(EngineeringPropertyProposalReview)
        release=latest(EngineeringPropertyProposalRelease)
        response=latest(EngineeringPropertyProposalClientResponse)
        creation=latest(EngineeringPropertyProposalJobCreation)
        stage=classify_property_proposal_stage(
            has_draft=draft is not None,
            has_review=review is not None,
            has_release=release is not None,
            client_response=getattr(response,"response_status",None),
            engineering_job_number=getattr(creation,"engineering_job_number",None),
        )
        proposal_rows.append({
            "proposal_request_id":rid,
            "analysis_run_id":request.analysis_run_id,
            "project_goal":request.project_goal,
            "customer_name":request.customer_name,
            "request_status":request.request_status,
            "requested_at":_iso(request.created_at),
            "proposal_number":getattr(draft,"proposal_number",None),
            "engineering_job_number":getattr(creation,"engineering_job_number",None),
            **stage,
            "href":f"proposal.html?proposal_request_id={rid}",
        })

    links=list(db.execute(
        select(PropertyEngineeringJobLink)
        .where(
            PropertyEngineeringJobLink.property_record_id == property_id,
            PropertyEngineeringJobLink.link_status == "linked",
        )
        .order_by(PropertyEngineeringJobLink.created_at.desc())
    ).scalars().all())

    linked_jobs=[]
    for link in links:
        job=db.get(EngineeringJob, link.engineering_job_number)
        linked_jobs.append({
            "link_id":link.link_id,
            "engineering_job_number":link.engineering_job_number,
            "project_name":getattr(job,"project_name",None),
            "project_type":getattr(job,"project_type",None),
            "state":getattr(job,"state",None),
            "created_at":_iso(link.created_at),
            "href":f"job.html?job={link.engineering_job_number}",
        })

    proposals_by_analysis=_workplace_analysis_proposal_traceability(proposal_rows)
    jobs_by_analysis=_workplace_analysis_job_traceability(proposals_by_analysis)

    analysis=(getattr(selected_analysis,"analysis",None) or {}) if selected_analysis is not None else {}
    selected_analysis_proposals=(
        proposals_by_analysis.get(getattr(selected_analysis,"analysis_run_id",None), [])
        if selected_analysis is not None else []
    )
    selected_analysis_jobs=(
        jobs_by_analysis.get(getattr(selected_analysis,"analysis_run_id",None), [])
        if selected_analysis is not None else []
    )
    analysis_change_comparison=_workplace_analysis_change_comparison(
        selected_run=selected_analysis,
        latest_run=analyses[0] if analyses else None,
        proposals_by_analysis=proposals_by_analysis,
        jobs_by_analysis=jobs_by_analysis,
    )
    analysis_evidence_change_comparison=_workplace_analysis_evidence_change_comparison(
        selected_run=selected_analysis,
        latest_run=analyses[0] if analyses else None,
    )
    analysis_source_change_detail=_workplace_analysis_source_change_detail(
        selected_run=selected_analysis,
        latest_run=analyses[0] if analyses else None,
    )
    analysis_verification_item_change_detail=_workplace_analysis_verification_item_change_detail(
        selected_run=selected_analysis,
        latest_run=analyses[0] if analyses else None,
    )
    return {
        "status":"MIDRA_WORKPLACE_PROPERTY_DETAIL_READY",
        "property":_workplace_property_identity(record),
        "analysis":{
            "analysis_run_id":getattr(selected_analysis,"analysis_run_id",None),
            "requested_work":getattr(selected_analysis,"requested_work",None),
            "intelligence_status":getattr(selected_analysis,"intelligence_status",None),
            "created_at":_iso(getattr(selected_analysis,"created_at",None)),
            "verification_summary":build_delivery_verification_summary(analysis),
            "dynamic_intelligence_summary":build_dynamic_engineering_handoff_summary(analysis),
            "evidence_href":(f"evidence.html?property_record_id={property_id}&analysis_run_id={selected_analysis.analysis_run_id}" if selected_analysis is not None else f"evidence.html?property_record_id={property_id}"),
        },
        "analysis_history":[{
            "analysis_run_id":run.analysis_run_id,
            "requested_work":run.requested_work,
            "intelligence_status":run.intelligence_status,
            "created_at":_iso(run.created_at),
            "selected":selected_analysis is not None and run.analysis_run_id == selected_analysis.analysis_run_id,
            "proposal_count":len(proposals_by_analysis.get(run.analysis_run_id, [])),
            "proposal_links":[{
                "proposal_request_id":item.get("proposal_request_id"),
                "proposal_number":item.get("proposal_number"),
                "project_goal":item.get("project_goal"),
                "stage":item.get("stage"),
                "engineering_job_number":item.get("engineering_job_number"),
                "href":item.get("href"),
            } for item in proposals_by_analysis.get(run.analysis_run_id, [])],
            "engineering_job_count":len(jobs_by_analysis.get(run.analysis_run_id, [])),
            "engineering_job_links":list(jobs_by_analysis.get(run.analysis_run_id, [])),
            "property_href":f"property.html?property_record_id={property_id}&analysis_run_id={run.analysis_run_id}",
            "evidence_href":f"evidence.html?property_record_id={property_id}&analysis_run_id={run.analysis_run_id}",
        } for run in analyses],
        "analysis_history_count":len(analyses),
        "selected_analysis_proposals":[{
            "proposal_request_id":item.get("proposal_request_id"),
            "proposal_number":item.get("proposal_number"),
            "project_goal":item.get("project_goal"),
            "stage":item.get("stage"),
            "href":item.get("href"),
        } for item in selected_analysis_proposals],
        "selected_analysis_proposal_count":len(selected_analysis_proposals),
        "selected_analysis_engineering_jobs":list(selected_analysis_jobs),
        "selected_analysis_engineering_job_count":len(selected_analysis_jobs),
        "analysis_change_comparison":analysis_change_comparison,
        "analysis_evidence_change_comparison":analysis_evidence_change_comparison,
        "analysis_source_change_detail":analysis_source_change_detail,
        "analysis_verification_item_change_detail":analysis_verification_item_change_detail,
        "proposals":proposal_rows,
        "proposal_count":len(proposal_rows),
        "linked_engineering_jobs":linked_jobs,
        "linked_engineering_job_count":len(linked_jobs),
        "professional_boundary":{
            "mode":"READ_ONLY_OPERATIONAL_PROJECTION",
            "automatic_professional_action":False,
            "notice":(
                "MIDRA Workplace displays recorded Property intelligence, proposal lineage, "
                "and linked Engineering jobs. It does not convert automated analysis into "
                "professional review or acceptance."
            ),
        },
    }


def _workplace_recorded_sources(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect recorded source references without changing their authority state."""
    rows: list[dict[str, Any]]=[]
    seen: set[tuple[str, str]] = set()

    def add(source: Any, *, evidence_role: str | None = None, candidate_only: bool | None = None) -> None:
        if not isinstance(source, dict):
            return
        url=str(source.get("source_url") or source.get("url") or "").strip()
        label=str(source.get("label") or source.get("title") or source.get("source_type") or url or "Recorded source").strip()
        if not url and not label:
            return
        key=(url,label)
        if key in seen:
            return
        seen.add(key)
        rows.append({
            "label":label,
            "source_url":url or None,
            "source_type":source.get("source_type"),
            "authority":source.get("authority"),
            "retrieved_at":source.get("retrieved_at") or source.get("retrieval_date"),
            "current_status":source.get("current_status"),
            "evidence_role":evidence_role or source.get("evidence_role") or source.get("source_role"),
            "candidate_only":candidate_only if candidate_only is not None else source.get("candidate_only"),
        })

    for source in list(analysis.get("sources") or []):
        add(source)

    dynamic=analysis.get("dynamic_intelligence") or {}
    if isinstance(dynamic, dict):
        zoning=((dynamic.get("zoning") or {}).get("candidate") or {}).get("record") or {}
        add(zoning.get("source"), evidence_role="dynamic_zoning_candidate", candidate_only=True)
        project=dynamic.get("project_rule_candidate") or {}
        add(project.get("source"), evidence_role="dynamic_project_rule_candidate", candidate_only=True)
        approval=dynamic.get("approval_pathway_candidate") or {}
        add(approval.get("source"), evidence_role="dynamic_approval_candidate", candidate_only=True)

    package=analysis.get("evidence_package") or analysis.get("master_evidence_package") or {}
    if isinstance(package, dict):
        for artifact in list(package.get("artifacts") or []):
            if isinstance(artifact, dict):
                add(artifact, evidence_role=artifact.get("artifact_type") or "evidence_artifact")
    return rows


def engineering_workplace_property_evidence(
    db: Session,
    property_record_id: str,
    analysis_run_id: str | None = None,
) -> dict[str, Any]:
    """Read-only Workplace evidence and verification projection for a Property."""
    property_id=(property_record_id or "").strip()
    if not property_id:
        raise KeyError("property_record")
    record=db.get(PropertyRecord, property_id)
    if record is None:
        raise KeyError("property_record")
    analysis_rows=db.execute(
        select(PropertyAnalysisRun)
        .where(PropertyAnalysisRun.property_record_id == property_id)
        .order_by(PropertyAnalysisRun.created_at.desc())
    ).scalars()
    analyses=list(analysis_rows.all())
    if not analyses:
        try:
            legacy_first=analysis_rows.first()
        except Exception:
            legacy_first=None
        if legacy_first is not None:
            analyses=[legacy_first]
    selected_analysis=None
    requested_analysis_id=(analysis_run_id or "").strip()
    if requested_analysis_id:
        selected_analysis=next((run for run in analyses if run.analysis_run_id == requested_analysis_id), None)
        if selected_analysis is None:
            raise KeyError("analysis_run")
    elif analyses:
        selected_analysis=analyses[0]
    analysis=(getattr(selected_analysis,"analysis",None) or {}) if selected_analysis is not None else {}
    verification=build_delivery_verification_summary(analysis)
    dynamic=build_dynamic_engineering_handoff_summary(analysis)
    sources=_workplace_recorded_sources(analysis)
    return {
        "status":"MIDRA_WORKPLACE_PROPERTY_EVIDENCE_READY",
        "property":_workplace_property_identity(record),
        "analysis_run_id":getattr(selected_analysis,"analysis_run_id",None),
        "analysis_created_at":_iso(getattr(selected_analysis,"created_at",None)),
        "analysis_history":[{
            "analysis_run_id":run.analysis_run_id,
            "requested_work":run.requested_work,
            "intelligence_status":run.intelligence_status,
            "created_at":_iso(run.created_at),
            "selected":selected_analysis is not None and run.analysis_run_id == selected_analysis.analysis_run_id,
            "property_href":f"property.html?property_record_id={property_id}&analysis_run_id={run.analysis_run_id}",
            "evidence_href":f"evidence.html?property_record_id={property_id}&analysis_run_id={run.analysis_run_id}",
        } for run in analyses],
        "verification_summary":verification,
        "dynamic_intelligence_summary":dynamic,
        "recorded_sources":sources,
        "recorded_source_count":len(sources),
        "professional_boundary":{
            "mode":"READ_ONLY_EVIDENCE_PROJECTION",
            "engineer_reviewed":False,
            "engineer_accepted":False,
            "notice":("Recorded sources, verification items, and dynamic candidate evidence remain "
                      "MIDRA Analysis unless an authorized professional separately reviews and accepts them."),
        },
    }

def engineering_workplace_job_detail(
    db: Session,
    engineering_job_number: str,
) -> dict[str, Any]:
    """Unified read-only Workplace view for an Engineering job and its Property lineage."""
    job_number=(engineering_job_number or "").strip()
    if not job_number:
        raise KeyError("engineering_job")

    workspace=load_engineering_workspace(db,job_number)

    creation=db.execute(
        select(EngineeringPropertyProposalJobCreation)
        .where(EngineeringPropertyProposalJobCreation.engineering_job_number == job_number)
        .order_by(EngineeringPropertyProposalJobCreation.created_at.desc())
    ).scalars().first()

    origin=None
    if creation is not None:
        request=db.get(PropertyEngineeringProposalRequest,creation.proposal_request_id)
        prop=db.get(PropertyRecord,creation.property_record_id)
        origin={
            "source":"MIDRA_PROPERTY",
            "proposal_request_id":creation.proposal_request_id,
            "property_record_id":creation.property_record_id,
            "analysis_run_id":getattr(request,"analysis_run_id",None),
            "project_goal":getattr(request,"project_goal",None),
            "proposal_number":creation.proposal_number,
            "engineering_job_creation_id":creation.engineering_job_creation_id,
            "created_by":creation.created_by,
            "created_at":_iso(creation.created_at),
            "property":_workplace_property_identity(prop),
            "proposal_href":f"proposal.html?proposal_request_id={creation.proposal_request_id}",
            "property_href":f"property.html?property_record_id={creation.property_record_id}",
            "evidence_href":f"evidence.html?property_record_id={creation.property_record_id}",
        }

    links=list(db.execute(
        select(PropertyEngineeringJobLink)
        .where(
            PropertyEngineeringJobLink.engineering_job_number == job_number,
            PropertyEngineeringJobLink.link_status == "linked",
        )
        .order_by(PropertyEngineeringJobLink.created_at.asc())
    ).scalars().all())

    property_ids={item.property_record_id for item in links}
    linked_records={}
    if property_ids:
        rows=db.execute(
            select(PropertyRecord).where(PropertyRecord.property_record_id.in_(property_ids))
        ).scalars().all()
        linked_records={row.property_record_id:row for row in rows}

    linked_properties=[]
    for link in links:
        linked_properties.append({
            "link_id":link.link_id,
            "property_record_id":link.property_record_id,
            "link_status":link.link_status,
            "notes":link.notes,
            "created_by":link.created_by,
            "created_at":_iso(link.created_at),
            "property":_workplace_property_identity(linked_records.get(link.property_record_id)),
            "is_origin_property":bool(
                creation is not None and
                creation.property_record_id == link.property_record_id
            ),
            "property_href":f"property.html?property_record_id={link.property_record_id}",
            "evidence_href":f"evidence.html?property_record_id={link.property_record_id}",
        })

    return {
        "status":"MIDRA_WORKPLACE_JOB_DETAIL_READY",
        "job_number":job_number,
        "workspace":workspace,
        "property_origin":origin,
        "linked_properties":linked_properties,
        "professional_boundary":{
            "mode":"READ_ONLY_OPERATIONAL_PROJECTION",
            "automatic_professional_action":False,
            "notice":(
                "MIDRA Workplace combines recorded Engineering workflow state with "
                "Property/proposal lineage. It does not approve, issue, submit, "
                "professionally accept, or alter Engineering work."
            ),
        },
    }
