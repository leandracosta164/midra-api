"""Durable MIDRA Property records. Separate from Property Intelligence analysis routes."""
from hashlib import sha256
import json
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.property_security import require_property_user
from app.core.engineering_security import require_engineering_user
from app.core.settings import settings
from app.repositories.property_record import SQLAlchemyPropertyRecordRepository
from app.repositories.property_analysis_run import SQLAlchemyPropertyAnalysisRunRepository
from app.repositories.property_engineering_job_link import SQLAlchemyPropertyEngineeringJobLinkRepository
from app.repositories.property_engineering_proposal_request import SQLAlchemyPropertyEngineeringProposalRequestRepository
from app.repositories.engineering_property_proposal_draft import SQLAlchemyEngineeringPropertyProposalDraftRepository
from app.repositories.engineering_property_proposal_review import SQLAlchemyEngineeringPropertyProposalReviewRepository
from app.repositories.engineering_property_proposal_release import SQLAlchemyEngineeringPropertyProposalReleaseRepository
from app.repositories.engineering_property_proposal_client_response import SQLAlchemyEngineeringPropertyProposalClientResponseRepository
from app.repositories.engineering_property_proposal_job_creation import SQLAlchemyEngineeringPropertyProposalJobCreationRepository
from app.repositories.engineering_property_proposal_pdf_artifact import SQLAlchemyEngineeringPropertyProposalPdfArtifactRepository
from app.repositories.engineering_property_proposal_delivery import SQLAlchemyEngineeringPropertyProposalDeliveryRepository
from app.models.property_analysis_run import PropertyAnalysisRun
from app.models.engineering_property_proposal_release import EngineeringPropertyProposalRelease
from app.models.engineering_property_proposal_review import EngineeringPropertyProposalReview
from app.services.property_delivery_orchestration import build_property_delivery_bundle
from app.services.property_report_pdf import render_property_report_pdf
from app.services.property_verification_delivery import build_delivery_verification_summary
from app.services.property_engineering_proposal_context import build_property_engineering_proposal_context
from app.services.property_engineering_proposal_lifecycle import classify_property_engineering_proposal_lifecycle
from app.services.property_engineering_intake_bridge import build_property_engineering_intake_bridge
from app.services.property_engineering_proposal_draft_bridge import build_property_engineering_proposal_draft
from app.services.property_engineering_proposal_review_bridge import approve_property_engineering_proposal_draft
from app.services.property_engineering_proposal_release_bridge import release_property_engineering_proposal_to_client
from app.services.property_engineering_proposal_client_response_bridge import record_property_engineering_proposal_client_response
from app.services.engineering_proposal_release import create_proposal_release_snapshot
from app.services.engineering_proposal_pdf_artifact import build_proposal_pdf_artifact_manifest
from app.services.engineering_proposal_pdf_renderer import render_proposal_pdf
from app.services.engineering_proposal_pdf_repository import InMemoryProposalPdfStore, persist_rendered_proposal_pdf, retrieve_proposal_pdf
from app.services.engineering_property_proposal_delivery_bridge import deliver_durable_property_proposal_pdf
from app.services.engineering_proposal_email_transport import SMTPProposalDeliveryTransport
from app.services.engineering_proposal_client_portal import create_client_proposal_token, verify_client_proposal_token
from app.schemas.property_record import (
    PropertyAnalysisRunRead, PropertyEngineeringJobLinkCreate, PropertyEngineeringJobLinkRead,
    PropertyEngineeringProposalRequestCreate, PropertyEngineeringProposalRequestRead,
    PropertyEngineeringProposalRequestHistoryRead, PropertyEngineeringProposalRequestContextRead,
    PropertyEngineeringProposalPublicIntakeCreate, PropertyEngineeringProposalPublicIntakeRead,
    PropertyEngineeringProposalDraftCreate, EngineeringPropertyProposalDraftRead, EngineeringPropertyProposalReviewRead, PropertyEngineeringProposalApprovalRead, EngineeringPropertyProposalReleaseRead, PropertyEngineeringProposalReleaseActionRead, EngineeringPropertyProposalPdfArtifactRead, PropertyEngineeringProposalPdfArtifactActionRead, PropertyEngineeringProposalClientResponseCreate, EngineeringPropertyProposalClientResponseRead, PropertyEngineeringProposalClientResponseActionRead, PropertyEngineeringProposalDeliveryCreate, EngineeringPropertyProposalDeliveryRead, PropertyEngineeringProposalDeliveryActionRead, PropertyEngineeringProposalStatusTransition, PropertyPublicReportCreate, PropertyRecordRead, PropertyRecordUpsert,
)

router = APIRouter(prefix="/property-records", tags=["MIDRA Property Records"])
public_router = APIRouter(prefix="/property-records", tags=["MIDRA Property Public Records"])


@public_router.post(
    "/public/proposal-intake",
    response_model=PropertyEngineeringProposalPublicIntakeRead,
    status_code=status.HTTP_201_CREATED,
)
def create_public_engineering_proposal_intake(
    payload: PropertyEngineeringProposalPublicIntakeCreate,
    db: Session = Depends(get_db),
):
    """Persist public Property Intelligence only as part of an explicit proposal handoff."""
    record = repo(db).upsert_from_analysis(
        search_query=payload.search_query,
        analysis=payload.analysis,
    )
    run = SQLAlchemyPropertyAnalysisRunRepository(db).append(
        property_record_id=record.property_record_id,
        analysis=payload.analysis,
    )
    proposal = SQLAlchemyPropertyEngineeringProposalRequestRepository(db).create(
        property_record_id=record.property_record_id,
        analysis_run_id=run.analysis_run_id,
        project_goal=payload.project_goal,
        customer_name=payload.customer_name,
        customer_email=payload.customer_email,
        customer_phone=payload.customer_phone,
    )
    return {
        "property_record": record,
        "proposal_request": proposal,
    }


def _public_report_identity(payload: PropertyPublicReportCreate) -> dict:
    analysis = dict(payload.analysis or {})
    prop = dict(analysis.get("property") or {})
    resolution = dict(analysis.get("property_resolution") or {})
    parcel = dict(prop.get("parcel") or resolution.get("parcel") or {})
    municipality = str(prop.get("municipality") or resolution.get("municipality") or "").strip()
    if not municipality:
        raise HTTPException(
            status_code=422,
            detail="resolved municipality is required before MIDRA can generate a Property PDF report",
        )
    display_address = str(
        prop.get("address")
        or resolution.get("matched_address")
        or payload.search_query
        or ""
    ).strip()
    digest = sha256(
        json.dumps(analysis, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()[:16].upper()
    return {
        "property_record_id": f"public-{digest}",
        "address": display_address,
        "municipality": municipality,
        "county": str(prop.get("county") or parcel.get("county") or resolution.get("county") or "").strip() or None,
        "block": str(parcel.get("block") or "").strip() or None,
        "lot": str(parcel.get("lot") or "").strip() or None,
        "analysis_id": f"PUBLIC-{digest}",
    }


def _build_public_report_bundle(payload: PropertyPublicReportCreate) -> dict:
    profile = str(payload.report_profile or "preliminary").strip().lower()
    if profile not in {"preliminary", "complete"}:
        raise HTTPException(status_code=422, detail="report_profile must be preliminary or complete")
    analysis = dict(payload.analysis or {})
    identity = _public_report_identity(payload)
    property_data = {key: value for key, value in identity.items() if key != "analysis_id"}
    project_goal = str(
        payload.project_goal
        or analysis.get("requested_work")
        or analysis.get("project_goal")
        or ""
    ).strip()
    bundle = build_property_delivery_bundle(
        analysis_id=identity["analysis_id"],
        property_record=property_data,
        project_goal=project_goal,
        sources=_delivery_sources_from_analysis(analysis),
        environmental_screening=_delivery_environmental_screening_from_analysis(analysis),
        zoning_candidate_evidence=_delivery_zoning_candidate_from_analysis(analysis),
        dynamic_intelligence_evidence=_delivery_dynamic_intelligence_from_analysis(analysis),
        verification_summary=build_delivery_verification_summary(analysis),
        report_profile=profile,
        analysis_snapshot=analysis,
    )
    bundle["product"] = "MIDRA_PROPERTY"
    bundle["branding"] = "MIDRA_PROPERTY"
    bundle["public_browser_export"] = True
    bundle["professional_boundary"] = {
        "status": "MIDRA_ANALYSIS",
        "engineer_reviewed": False,
        "engineer_accepted": False,
        "notice": "Public report export does not constitute engineer review or acceptance.",
    }
    return bundle


@public_router.post("/public/delivery-report.pdf")
def create_public_property_delivery_report_pdf(payload: PropertyPublicReportCreate):
    """Render the current public browser analysis as a PDF without creating a durable record."""
    bundle = _build_public_report_bundle(payload)
    rendered = render_property_report_pdf(delivery_bundle=bundle)
    return Response(
        content=rendered["pdf_bytes"],
        media_type=rendered["mime_type"],
        headers={
            "Content-Disposition": f'attachment; filename="{rendered["filename"]}"',
            "X-MIDRA-Report-SHA256": rendered["pdf_sha256"],
            "X-MIDRA-Analysis-Id": str(rendered.get("analysis_id") or ""),
            "X-MIDRA-Persistence": "browser-only",
        },
    )


def repo(db: Session) -> SQLAlchemyPropertyRecordRepository:
    return SQLAlchemyPropertyRecordRepository(db)


@router.get("", response_model=list[PropertyRecordRead])
def list_recent_property_records(limit: int = 25, db: Session = Depends(get_db)):
    """List durable Property-owned records for the standalone research workspace."""
    return repo(db).list_recent(limit=limit)


@router.get("/search", response_model=list[PropertyRecordRead])
def search_property_records(q: str, limit: int = 10, db: Session = Depends(get_db)):
    """Search all durable Property records for prior research matches."""
    return repo(db).search(query=q, limit=limit)


@router.post("", response_model=PropertyRecordRead, status_code=status.HTTP_200_OK)
def upsert_property_record(payload: PropertyRecordUpsert, db: Session = Depends(get_db)):
    record = repo(db).upsert_from_analysis(search_query=payload.search_query, analysis=payload.analysis)
    SQLAlchemyPropertyAnalysisRunRepository(db).append(property_record_id=record.property_record_id, analysis=payload.analysis)
    return record



@router.get("/admin/proposal-requests", response_model=list[PropertyEngineeringProposalRequestHistoryRead])
def list_admin_engineering_proposal_requests(
    limit: int = 100,
    request_status: str | None = None,
    db: Session = Depends(get_db),
    _property_admin: str = Depends(require_property_user),
):
    """Administrative recent proposal queue across durable Property records."""
    proposals=SQLAlchemyPropertyEngineeringProposalRequestRepository(db)
    normalized_status=(request_status or "").strip().upper()
    items=(
        proposals.list_all_by_status(normalized_status, limit=limit)
        if normalized_status
        else proposals.list_all(limit=limit)
    )
    return [
        {
            "proposal_request_id": item.proposal_request_id,
            "property_record_id": item.property_record_id,
            "analysis_run_id": item.analysis_run_id,
            "project_goal": item.project_goal,
            "customer_name": item.customer_name,
            "customer_email": item.customer_email,
            "customer_phone": item.customer_phone,
            "request_status": item.request_status,
            "source_product": item.source_product,
            "destination_product": item.destination_product,
            "created_at": item.created_at,
            "proposal_lifecycle": classify_property_engineering_proposal_lifecycle(item.request_status),
        }
        for item in items
    ]


@public_router.get("/engineering/proposal-requests", response_model=list[PropertyEngineeringProposalRequestHistoryRead])
def list_engineering_authenticated_proposal_queue(
    limit: int = 100,
    request_status: str | None = None,
    db: Session = Depends(get_db),
    engineering_user: str = Depends(require_engineering_user),
):
    """Engineering-authenticated Property-origin proposal queue.

    This is an operational read model only. It does not mutate proposal status,
    approve/release/send proposals, record client responses, or create jobs.
    """
    _ = engineering_user
    proposals = SQLAlchemyPropertyEngineeringProposalRequestRepository(db)
    normalized_status = (request_status or "").strip().upper()
    items = (
        proposals.list_all_by_status(normalized_status, limit=limit)
        if normalized_status
        else proposals.list_all(limit=limit)
    )
    return [
        {
            "proposal_request_id": item.proposal_request_id,
            "property_record_id": item.property_record_id,
            "analysis_run_id": item.analysis_run_id,
            "project_goal": item.project_goal,
            "customer_name": item.customer_name,
            "customer_email": item.customer_email,
            "customer_phone": item.customer_phone,
            "request_status": item.request_status,
            "source_product": item.source_product,
            "destination_product": item.destination_product,
            "created_at": item.created_at,
            "proposal_lifecycle": classify_property_engineering_proposal_lifecycle(item.request_status),
        }
        for item in items
    ]


@router.get("/{property_record_id}", response_model=PropertyRecordRead)
def get_property_record(property_record_id: str, db: Session = Depends(get_db)):
    try:
        return repo(db).get(property_record_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="property record not found") from exc


@router.get("/{property_record_id}/analyses", response_model=list[PropertyAnalysisRunRead])
def list_property_analysis_history(property_record_id: str, limit: int = 25, db: Session = Depends(get_db)):
    try:
        repo(db).get(property_record_id)
        return SQLAlchemyPropertyAnalysisRunRepository(db).list(property_record_id, limit=limit)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="property record not found") from exc


@router.get("/{property_record_id}/analyses/{analysis_run_id}", response_model=PropertyAnalysisRunRead)
def get_property_analysis_run(
    property_record_id: str,
    analysis_run_id: str,
    db: Session = Depends(get_db),
):
    """Resolve one exact durable Property analysis run without substituting the latest run."""
    try:
        repo(db).get(property_record_id)
        return SQLAlchemyPropertyAnalysisRunRepository(db).get(property_record_id, analysis_run_id)
    except KeyError as exc:
        detail = (
            "property analysis run not found"
            if exc.args and exc.args[0] == "analysis_run"
            else "property record not found"
        )
        raise HTTPException(status_code=404, detail=detail) from exc


@router.get("/{property_record_id}/engineering-links", response_model=list[PropertyEngineeringJobLinkRead])
def list_property_engineering_links(property_record_id: str, db: Session = Depends(get_db), _property_admin: str = Depends(require_property_user)):
    try:
        return SQLAlchemyPropertyEngineeringJobLinkRepository(db).list(property_record_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="property record not found") from exc


@router.post("/{property_record_id}/engineering-links", response_model=PropertyEngineeringJobLinkRead, status_code=status.HTTP_200_OK)
def link_property_to_engineering_job(property_record_id: str, payload: PropertyEngineeringJobLinkCreate, db: Session = Depends(get_db), _property_admin: str = Depends(require_property_user)):
    try:
        return SQLAlchemyPropertyEngineeringJobLinkRepository(db).link(
            property_record_id=property_record_id,
            engineering_job_number=payload.engineering_job_number,
            created_by=payload.created_by,
            notes=payload.notes,
        )
    except KeyError as exc:
        if exc.args and exc.args[0] == "engineering_job":
            raise HTTPException(status_code=404, detail="engineering job not found") from exc
        raise HTTPException(status_code=404, detail="property record not found") from exc


@router.delete("/{property_record_id}/engineering-links/{engineering_job_number}", response_model=PropertyEngineeringJobLinkRead)
def unlink_property_from_engineering_job(property_record_id: str, engineering_job_number: str, db: Session = Depends(get_db), _property_admin: str = Depends(require_property_user)):
    try:
        return SQLAlchemyPropertyEngineeringJobLinkRepository(db).unlink(
            property_record_id=property_record_id, engineering_job_number=engineering_job_number
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="active property/job link not found") from exc


@router.get("/{property_record_id}/engineering-proposal-requests", response_model=list[PropertyEngineeringProposalRequestHistoryRead])
def list_engineering_proposal_requests(property_record_id: str, db: Session = Depends(get_db), _property_admin: str = Depends(require_property_user)):
    try:
        items = SQLAlchemyPropertyEngineeringProposalRequestRepository(db).list(property_record_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="property record not found") from exc
    return [
        {
            "proposal_request_id": item.proposal_request_id,
            "property_record_id": item.property_record_id,
            "analysis_run_id": item.analysis_run_id,
            "project_goal": item.project_goal,
            "customer_name": item.customer_name,
            "customer_email": item.customer_email,
            "customer_phone": item.customer_phone,
            "request_status": item.request_status,
            "source_product": item.source_product,
            "destination_product": item.destination_product,
            "created_at": item.created_at,
            "proposal_lifecycle": classify_property_engineering_proposal_lifecycle(item.request_status),
        }
        for item in items
    ]

@public_router.post("/{property_record_id}/engineering-proposal-requests", response_model=PropertyEngineeringProposalRequestRead, status_code=status.HTTP_201_CREATED)
def request_engineering_proposal(property_record_id: str, payload: PropertyEngineeringProposalRequestCreate, db: Session = Depends(get_db)):
    """Record an explicit Property -> Engineering proposal request. This never creates an Engineering job."""
    try:
        return SQLAlchemyPropertyEngineeringProposalRequestRepository(db).create(
            property_record_id=property_record_id,
            analysis_run_id=payload.analysis_run_id,
            project_goal=payload.project_goal,
            customer_name=payload.customer_name,
            customer_email=payload.customer_email,
            customer_phone=payload.customer_phone,
        )
    except KeyError as exc:
        if exc.args and exc.args[0] == "analysis":
            raise HTTPException(status_code=400, detail="analysis run does not belong to this property") from exc
        raise HTTPException(status_code=404, detail="property record not found") from exc


@router.patch(
    "/{property_record_id}/engineering-proposal-requests/{proposal_request_id}/status",
    response_model=PropertyEngineeringProposalRequestHistoryRead,
)
def transition_engineering_proposal_request_status(
    property_record_id: str,
    proposal_request_id: str,
    payload: PropertyEngineeringProposalStatusTransition,
    db: Session = Depends(get_db),

    _property_admin: str = Depends(require_property_user),
):
    """Apply one guarded proposal lifecycle transition.

    This endpoint changes only the durable proposal-request status. It never creates
    an Engineering job and never marks Property Intelligence engineer-reviewed or accepted.
    """
    proposals = SQLAlchemyPropertyEngineeringProposalRequestRepository(db)
    try:
        item = proposals.transition_status(
            property_record_id=property_record_id,
            proposal_request_id=proposal_request_id,
            expected_current_status=payload.expected_current_status,
            next_status=payload.next_status,
        )
    except KeyError as exc:
        detail = (
            "engineering proposal request not found"
            if exc.args and exc.args[0] == "proposal_request"
            else "property record not found"
        )
        raise HTTPException(status_code=404, detail=detail) from exc
    except ValueError as exc:
        if exc.args and exc.args[0] == "proposal_status_changed":
            raise HTTPException(
                status_code=409,
                detail="proposal request status changed; refresh durable context before retrying",
            ) from exc
        raise HTTPException(
            status_code=409,
            detail="proposal status transition is not allowed by the durable lifecycle guard",
        ) from exc

    return {
        "proposal_request_id": item.proposal_request_id,
        "property_record_id": item.property_record_id,
        "analysis_run_id": item.analysis_run_id,
        "project_goal": item.project_goal,
        "customer_name": item.customer_name,
        "customer_email": item.customer_email,
        "customer_phone": item.customer_phone,
        "request_status": item.request_status,
        "source_product": item.source_product,
        "destination_product": item.destination_product,
        "created_at": item.created_at,
        "proposal_lifecycle": classify_property_engineering_proposal_lifecycle(item.request_status),
    }


@public_router.get(
    "/{property_record_id}/engineering-proposal-requests/{proposal_request_id}/context",
    response_model=PropertyEngineeringProposalRequestContextRead,
)
def get_engineering_proposal_request_context(
    property_record_id: str,
    proposal_request_id: str,
    db: Session = Depends(get_db),
):
    """Resolve the durable proposal request back to its Property analysis context.

    This shared-platform reference does not create an Engineering job and does not
    convert Property Intelligence into an engineer-reviewed or accepted determination.
    """
    proposals = SQLAlchemyPropertyEngineeringProposalRequestRepository(db)
    try:
        item = proposals.get(property_record_id, proposal_request_id)
        record = repo(db).get(property_record_id)
    except KeyError as exc:
        detail = (
            "engineering proposal request not found"
            if exc.args and exc.args[0] == "proposal_request"
            else "property record not found"
        )
        raise HTTPException(status_code=404, detail=detail) from exc

    run = None
    if item.analysis_run_id:
        run = db.get(PropertyAnalysisRun, item.analysis_run_id)
        if run is None or run.property_record_id != property_record_id:
            raise HTTPException(
                status_code=409,
                detail="referenced Property analysis is unavailable or no longer belongs to this property",
            )

    job_creation=SQLAlchemyEngineeringPropertyProposalJobCreationRepository(db).get_for_proposal_optional(
        property_record_id=property_record_id,
        proposal_request_id=proposal_request_id,
    )
    return build_property_engineering_proposal_context(
        proposal_request=item,
        property_record=record,
        analysis_run=run,
        engineering_job_creation=job_creation,
    )


@public_router.get(
    "/{property_record_id}/engineering-proposal-requests/{proposal_request_id}/engineering-intake"
)
def get_engineering_property_proposal_intake(
    property_record_id: str,
    proposal_request_id: str,
    db: Session = Depends(get_db),
    engineering_user: str = Depends(require_engineering_user),
):
    """Resolve one exact Property proposal into the protected Engineering intake.

    Engineering authentication is required. This is a shared-platform reference
    to the exact durable Property analysis and evidence; it never creates a job.
    """
    proposals=SQLAlchemyPropertyEngineeringProposalRequestRepository(db)
    try:
        item=proposals.get(property_record_id,proposal_request_id)
        record=repo(db).get(property_record_id)
    except KeyError as exc:
        detail=(
            "engineering proposal request not found"
            if exc.args and exc.args[0]=="proposal_request"
            else "property record not found"
        )
        raise HTTPException(status_code=404,detail=detail) from exc

    if not item.analysis_run_id:
        raise HTTPException(
            status_code=409,
            detail="proposal request has no exact durable analysis; Engineering intake requires analysis lineage",
        )

    run=db.get(PropertyAnalysisRun,item.analysis_run_id)
    if run is None or run.property_record_id != property_record_id:
        raise HTTPException(
            status_code=409,
            detail="referenced Property analysis is unavailable or no longer belongs to this property",
        )

    bundle=get_property_delivery_bundle(
        property_record_id=property_record_id,
        analysis_run_id=run.analysis_run_id,
        report_profile="complete",
        db=db,
    )
    property_data={
        "property_record_id":record.property_record_id,
        "address":record.display_address or record.search_query,
        "municipality":record.municipality,
        "county":record.county,
        "block":record.block,
        "lot":record.lot,
    }
    proposal_data={
        "proposal_request_id":item.proposal_request_id,
        "property_record_id":item.property_record_id,
        "analysis_run_id":item.analysis_run_id,
        "project_goal":item.project_goal,
        "customer_name":item.customer_name,
        "customer_email":item.customer_email,
        "customer_phone":item.customer_phone,
        "request_status":item.request_status,
    }
    return build_property_engineering_intake_bridge(
        proposal_request=proposal_data,
        property_record=property_data,
        analysis_id=run.analysis_run_id,
        analysis_snapshot=dict(run.analysis or {}),
        evidence_package=dict(bundle.get("master_evidence_package") or {}),
        engineering_user=engineering_user,
    )


@public_router.post(
    "/{property_record_id}/engineering-proposal-requests/{proposal_request_id}/engineering-draft"
)
def create_engineering_property_proposal_draft(
    property_record_id: str,
    proposal_request_id: str,
    payload: PropertyEngineeringProposalDraftCreate,
    db: Session = Depends(get_db),
    engineering_user: str = Depends(require_engineering_user),
):
    """Generate a private review-required Engineering proposal draft.

    The exact durable Property proposal/analysis lineage is reused. Service prices
    are supplied explicitly by the authenticated Engineering user; MIDRA Property
    never invents or commits Engineering pricing. This does not approve/send the
    proposal and does not create an Engineering job.
    """
    try:
        intake_bridge = get_engineering_property_proposal_intake(
            property_record_id=property_record_id,
            proposal_request_id=proposal_request_id,
            db=db,
            engineering_user=engineering_user,
        )
        draft = build_property_engineering_proposal_draft(
            intake_bridge=intake_bridge,
            engineering_user=engineering_user,
            proposal_number=payload.proposal_number,
            proposal_date=payload.proposal_date,
            project_name=payload.project_name,
            services=payload.services,
            exclusions=payload.exclusions,
            terms=payload.terms,
        )
        saved = SQLAlchemyEngineeringPropertyProposalDraftRepository(db).create(
            property_record_id=property_record_id,
            proposal_request_id=proposal_request_id,
            draft_snapshot=draft,
            generated_by=engineering_user,
        )
        result = dict(draft)
        result.update({
            "engineering_draft_id": saved.engineering_draft_id,
            "durable_workspace_status": "ENGINEERING_PROPOSAL_DRAFT_SAVED",
            "durable_created_at": saved.created_at.isoformat(),
        })
        return result
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@public_router.get(
    "/{property_record_id}/engineering-proposal-requests/{proposal_request_id}/engineering-drafts",
    response_model=list[EngineeringPropertyProposalDraftRead],
)
def list_engineering_property_proposal_drafts(
    property_record_id: str,
    proposal_request_id: str,
    db: Session = Depends(get_db),
    engineering_user: str = Depends(require_engineering_user),
):
    """List durable private Engineering proposal drafts for one exact Property request."""
    _ = engineering_user
    try:
        return SQLAlchemyEngineeringPropertyProposalDraftRepository(db).list(
            property_record_id=property_record_id,
            proposal_request_id=proposal_request_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="engineering proposal request not found") from exc


@public_router.get(
    "/{property_record_id}/engineering-proposal-requests/{proposal_request_id}/engineering-drafts/{engineering_draft_id}",
    response_model=EngineeringPropertyProposalDraftRead,
)
def get_engineering_property_proposal_draft(
    property_record_id: str,
    proposal_request_id: str,
    engineering_draft_id: str,
    db: Session = Depends(get_db),
    engineering_user: str = Depends(require_engineering_user),
):
    """Resolve one exact durable Engineering proposal draft snapshot."""
    _ = engineering_user
    try:
        return SQLAlchemyEngineeringPropertyProposalDraftRepository(db).get(
            property_record_id=property_record_id,
            proposal_request_id=proposal_request_id,
            engineering_draft_id=engineering_draft_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="engineering proposal draft not found") from exc


@public_router.post(
    "/{property_record_id}/engineering-proposal-requests/{proposal_request_id}/engineering-drafts/{engineering_draft_id}/approve",
    response_model=PropertyEngineeringProposalApprovalRead,
    status_code=status.HTTP_201_CREATED,
)
def approve_engineering_property_proposal_draft(
    property_record_id: str,
    proposal_request_id: str,
    engineering_draft_id: str,
    db: Session = Depends(get_db),
    engineering_user: str = Depends(require_engineering_user),
):
    """Authorize one exact private Engineering proposal draft for separate client release.

    Approval is Engineering-only and atomically advances the Property proposal request
    to PROPOSAL_GENERATED. It does not send the proposal and does not create a job.
    """
    try:
        draft=SQLAlchemyEngineeringPropertyProposalDraftRepository(db).get(
            property_record_id=property_record_id,
            proposal_request_id=proposal_request_id,
            engineering_draft_id=engineering_draft_id,
        )
        approved=approve_property_engineering_proposal_draft(
            draft_snapshot=dict(draft.draft_snapshot or {}),
            engineering_user=engineering_user,
        )
        review=SQLAlchemyEngineeringPropertyProposalReviewRepository(db).create_approval(
            property_record_id=property_record_id,
            proposal_request_id=proposal_request_id,
            engineering_draft_id=engineering_draft_id,
            approved_snapshot=approved,
            reviewed_by=engineering_user,
        )
        proposal_request=SQLAlchemyPropertyEngineeringProposalRequestRepository(db).get(
            property_record_id, proposal_request_id
        )
        return {
            "review": review,
            "proposal_request_status": proposal_request.request_status,
            "proposal_lifecycle": classify_property_engineering_proposal_lifecycle(
                proposal_request.request_status
            ),
            "engineering_job_created": False,
        }
    except KeyError as exc:
        detail="engineering proposal draft not found" if exc.args and exc.args[0]=="engineering_draft" else "engineering proposal request not found"
        raise HTTPException(status_code=404, detail=detail) from exc
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@public_router.get(
    "/{property_record_id}/engineering-proposal-requests/{proposal_request_id}/engineering-reviews",
    response_model=list[EngineeringPropertyProposalReviewRead],
)
def list_engineering_property_proposal_reviews(
    property_record_id: str,
    proposal_request_id: str,
    db: Session = Depends(get_db),
    engineering_user: str = Depends(require_engineering_user),
):
    """List immutable authorized Engineering approval records for one Property request."""
    _ = engineering_user
    return SQLAlchemyEngineeringPropertyProposalReviewRepository(db).list(
        property_record_id=property_record_id,
        proposal_request_id=proposal_request_id,
    )




@public_router.post(
    "/{property_record_id}/engineering-proposal-requests/{proposal_request_id}/engineering-reviews/{engineering_review_id}/release",
    response_model=PropertyEngineeringProposalReleaseActionRead,
    status_code=status.HTTP_201_CREATED,
)
def release_engineering_property_proposal_to_client(
    property_record_id: str,
    proposal_request_id: str,
    engineering_review_id: str,
    db: Session = Depends(get_db),
    engineering_user: str = Depends(require_engineering_user),
):
    """Record the separate authorized client-release action for an approved proposal.

    This action records release/sent state only. The Property proposal lifecycle remains
    PROPOSAL_GENERATED while awaiting an explicit client response. No Engineering job is
    created and the underlying Property analysis is not marked Engineer Accepted.
    """
    review=db.get(EngineeringPropertyProposalReview, engineering_review_id)
    if review is None or review.property_record_id != property_record_id or review.proposal_request_id != proposal_request_id:
        raise HTTPException(status_code=404, detail="engineering proposal review not found")

    try:
        released=release_property_engineering_proposal_to_client(
            approved_snapshot=dict(review.approved_snapshot or {}),
            engineering_user=engineering_user,
        )
        release=SQLAlchemyEngineeringPropertyProposalReleaseRepository(db).create_release(
            property_record_id=property_record_id,
            proposal_request_id=proposal_request_id,
            engineering_review_id=engineering_review_id,
            released_snapshot=released,
            released_by=engineering_user,
        )
        proposal_request=SQLAlchemyPropertyEngineeringProposalRequestRepository(db).get(
            property_record_id, proposal_request_id
        )
        return {
            "release":release,
            "proposal_request_status":proposal_request.request_status,
            "proposal_lifecycle":classify_property_engineering_proposal_lifecycle(proposal_request.request_status),
            "engineering_job_created":False,
            "client_approved":False,
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="engineering proposal review or request not found") from exc
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@public_router.get(
    "/{property_record_id}/engineering-proposal-requests/{proposal_request_id}/engineering-releases",
    response_model=list[EngineeringPropertyProposalReleaseRead],
)
def list_engineering_property_proposal_releases(
    property_record_id: str,
    proposal_request_id: str,
    db: Session = Depends(get_db),
    engineering_user: str = Depends(require_engineering_user),
):
    """List immutable Engineering client-release records for one exact Property request."""
    _=engineering_user
    return SQLAlchemyEngineeringPropertyProposalReleaseRepository(db).list(
        property_record_id=property_record_id,
        proposal_request_id=proposal_request_id,
    )


@public_router.post(
    "/{property_record_id}/engineering-proposal-requests/{proposal_request_id}/engineering-releases/{engineering_release_id}/proposal-pdf",
    response_model=PropertyEngineeringProposalPdfArtifactActionRead,
    status_code=status.HTTP_201_CREATED,
)
def materialize_engineering_property_proposal_pdf(
    property_record_id: str,
    proposal_request_id: str,
    engineering_release_id: str,
    db: Session = Depends(get_db),
    engineering_user: str = Depends(require_engineering_user),
):
    """Persist the exact client-safe proposal PDF for one released Property-origin proposal.

    This is an explicit Engineering action. It stores immutable exact PDF bytes for later
    controlled delivery; it does not email the client, accept the proposal, create a job,
    or mark the Property analysis Engineer Accepted. Repeated calls are idempotent.
    """
    release=db.get(EngineeringPropertyProposalRelease, engineering_release_id)
    if (
        release is None
        or release.property_record_id != property_record_id
        or release.proposal_request_id != proposal_request_id
    ):
        raise HTTPException(status_code=404, detail="engineering proposal release not found")

    artifact_repo=SQLAlchemyEngineeringPropertyProposalPdfArtifactRepository(db)
    existing=artifact_repo.get_for_release(engineering_release_id)
    if existing is not None:
        return {
            "artifact": existing,
            "immutable": True,
            "exact_bytes_persisted": True,
            "automatic_send": False,
        }

    review=db.get(EngineeringPropertyProposalReview, release.engineering_review_id)
    if (
        review is None
        or review.property_record_id != property_record_id
        or review.proposal_request_id != proposal_request_id
    ):
        raise HTTPException(status_code=409, detail="approved Engineering proposal review lineage is unavailable")

    try:
        client_release=create_proposal_release_snapshot(
            proposal=dict(review.approved_snapshot or {}),
            released_by=engineering_user,
        )
        manifest=build_proposal_pdf_artifact_manifest(release=client_release)
        rendered=render_proposal_pdf(artifact=manifest)
        transient=InMemoryProposalPdfStore()
        stored=persist_rendered_proposal_pdf(rendered=rendered, store=transient)
        stored=retrieve_proposal_pdf(artifact_id=stored["artifact_id"], store=transient)
        artifact=artifact_repo.create_from_record(
            engineering_release_id=engineering_release_id,
            property_record_id=property_record_id,
            proposal_request_id=proposal_request_id,
            proposal_id=release.proposal_id,
            created_by=engineering_user,
            record=stored,
        )
        return {
            "artifact": artifact,
            "immutable": True,
            "exact_bytes_persisted": True,
            "automatic_send": False,
        }
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@public_router.get(
    "/{property_record_id}/engineering-proposal-requests/{proposal_request_id}/engineering-releases/{engineering_release_id}/proposal-pdf/metadata",
    response_model=EngineeringPropertyProposalPdfArtifactRead,
)
def get_engineering_property_proposal_pdf_metadata(
    property_record_id: str,
    proposal_request_id: str,
    engineering_release_id: str,
    db: Session = Depends(get_db),
    engineering_user: str = Depends(require_engineering_user),
):
    """Return durable immutable proposal-PDF metadata without returning the PDF bytes."""
    _=engineering_user
    item=SQLAlchemyEngineeringPropertyProposalPdfArtifactRepository(db).get_for_release(engineering_release_id)
    if item is None or item.property_record_id != property_record_id or item.proposal_request_id != proposal_request_id:
        raise HTTPException(status_code=404, detail="durable proposal PDF artifact not found")
    return item


@public_router.get(
    "/{property_record_id}/engineering-proposal-requests/{proposal_request_id}/engineering-releases/{engineering_release_id}/proposal-pdf",
)
def download_engineering_property_proposal_pdf(
    property_record_id: str,
    proposal_request_id: str,
    engineering_release_id: str,
    db: Session = Depends(get_db),
    engineering_user: str = Depends(require_engineering_user),
):
    """Download the exact durably stored PDF bytes; never silently re-render."""
    _=engineering_user
    repo=SQLAlchemyEngineeringPropertyProposalPdfArtifactRepository(db)
    item=repo.get_for_release(engineering_release_id)
    if item is None or item.property_record_id != property_record_id or item.proposal_request_id != proposal_request_id:
        raise HTTPException(status_code=404, detail="durable proposal PDF artifact not found")
    try:
        data=repo.exact_bytes(item)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    headers={"Content-Disposition": f'attachment; filename="{item.filename}"', "X-MIDRA-PDF-SHA256": item.pdf_sha256}
    return Response(content=data, media_type=item.mime_type, headers=headers)

@public_router.post(
    "/{property_record_id}/engineering-proposal-requests/{proposal_request_id}/engineering-releases/{engineering_release_id}/deliver",
    response_model=PropertyEngineeringProposalDeliveryActionRead,
    status_code=status.HTTP_201_CREATED,
)
def deliver_engineering_property_proposal_to_client(
    property_record_id: str,
    proposal_request_id: str,
    engineering_release_id: str,
    payload: PropertyEngineeringProposalDeliveryCreate,
    db: Session = Depends(get_db),
    engineering_user: str = Depends(require_engineering_user),
):
    """Email the exact durable proposal PDF after an explicit Engineering-authorized send action.

    This transport action never re-renders the PDF, never records client acceptance,
    never creates an Engineering job, and never marks Property analysis as Engineer Accepted.
    """
    if payload.explicit_send_authorized is not True:
        raise HTTPException(status_code=409, detail="explicit authorized send action is required")
    proposal_request=SQLAlchemyPropertyEngineeringProposalRequestRepository(db).get(property_record_id, proposal_request_id)
    release=db.get(EngineeringPropertyProposalRelease, engineering_release_id)
    if (
        release is None
        or release.property_record_id != property_record_id
        or release.proposal_request_id != proposal_request_id
    ):
        raise HTTPException(status_code=404, detail="engineering proposal release not found")
    artifact_repo=SQLAlchemyEngineeringPropertyProposalPdfArtifactRepository(db)
    artifact=artifact_repo.get_for_release(engineering_release_id)
    if artifact is None or artifact.property_record_id != property_record_id or artifact.proposal_request_id != proposal_request_id:
        raise HTTPException(status_code=409, detail="durable proposal PDF artifact must be created before delivery")
    try:
        response_secret=settings.MIDRA_PROPOSAL_RESPONSE_SECRET or settings.MIDRA_PROPERTY_AUTH_SECRET or ""
        response_token=create_client_proposal_token(
            secret=response_secret,
            property_record_id=property_record_id,
            proposal_request_id=proposal_request_id,
            engineering_release_id=engineering_release_id,
            recipient=proposal_request.customer_email,
            ttl_seconds=max(1,int(settings.MIDRA_PROPOSAL_RESPONSE_TTL_DAYS))*86400,
        )
        public_origin=(settings.MIDRA_PROPERTY_PUBLIC_ORIGIN or (settings.PROPERTY_WEB_ORIGINS[0] if settings.PROPERTY_WEB_ORIGINS else "")).rstrip("/")
        if not public_origin:
            raise ValueError("MIDRA Property public origin is not configured for client proposal response")
        response_query=urlencode({
            "property_record_id":property_record_id,
            "proposal_request_id":proposal_request_id,
            "engineering_release_id":engineering_release_id,
            "token":response_token,
        })
        response_url=f"{public_origin}/proposal-response?{response_query}"
        transport=SMTPProposalDeliveryTransport(
            host=settings.MIDRA_PROPOSAL_EMAIL_HOST or "",
            port=settings.MIDRA_PROPOSAL_EMAIL_PORT,
            from_email=settings.MIDRA_PROPOSAL_EMAIL_FROM or "",
            username=settings.MIDRA_PROPOSAL_EMAIL_USERNAME,
            password=settings.MIDRA_PROPOSAL_EMAIL_PASSWORD,
            use_tls=settings.MIDRA_PROPOSAL_EMAIL_USE_TLS,
            use_ssl=settings.MIDRA_PROPOSAL_EMAIL_USE_SSL,
            response_url=response_url,
        )
        delivery_snapshot=deliver_durable_property_proposal_pdf(
            artifact=artifact,
            recipient=proposal_request.customer_email,
            authorized_by=engineering_user,
            explicit_send_authorized=True,
            artifact_repo=artifact_repo,
            transport=transport,
        )
        delivery=SQLAlchemyEngineeringPropertyProposalDeliveryRepository(db).create_sent(
            artifact=artifact,
            authorized_by=engineering_user,
            delivery=delivery_snapshot,
        )
        return {
            "delivery": delivery,
            "exact_pdf_bytes_sent": True,
            "automatic_send": False,
            "client_response_recorded": False,
            "engineering_job_created": False,
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="proposal PDF artifact not found") from exc
    except (ValueError, PermissionError, RuntimeError, OSError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@public_router.get(
    "/{property_record_id}/engineering-proposal-requests/{proposal_request_id}/engineering-deliveries",
    response_model=list[EngineeringPropertyProposalDeliveryRead],
)
def list_engineering_property_proposal_deliveries(
    property_record_id: str,
    proposal_request_id: str,
    engineering_release_id: str | None = None,
    db: Session = Depends(get_db),
    engineering_user: str = Depends(require_engineering_user),
):
    """List the append-only audit ledger of confirmed proposal transport events."""
    _=engineering_user
    SQLAlchemyPropertyEngineeringProposalRequestRepository(db).get(property_record_id, proposal_request_id)
    return SQLAlchemyEngineeringPropertyProposalDeliveryRepository(db).list(
        property_record_id=property_record_id,
        proposal_request_id=proposal_request_id,
        engineering_release_id=engineering_release_id,
    )


def _client_portal_release(*, db: Session, property_record_id: str, proposal_request_id: str, engineering_release_id: str, token: str):
    proposal_request=SQLAlchemyPropertyEngineeringProposalRequestRepository(db).get(property_record_id, proposal_request_id)
    release=db.get(EngineeringPropertyProposalRelease, engineering_release_id)
    if release is None or release.property_record_id != property_record_id or release.proposal_request_id != proposal_request_id:
        raise HTTPException(status_code=404, detail="proposal not found")
    secret=settings.MIDRA_PROPOSAL_RESPONSE_SECRET or settings.MIDRA_PROPERTY_AUTH_SECRET or ""
    try:
        verify_client_proposal_token(token=token,secret=secret,property_record_id=property_record_id,proposal_request_id=proposal_request_id,engineering_release_id=engineering_release_id,recipient=proposal_request.customer_email)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return proposal_request,release


@public_router.get("/public/proposal-response")
def get_public_engineering_proposal_response_portal(property_record_id: str,proposal_request_id: str,engineering_release_id: str,token: str,db: Session = Depends(get_db)):
    """Return only client-safe proposal response context after signed-link verification."""
    proposal_request,release=_client_portal_release(db=db,property_record_id=property_record_id,proposal_request_id=proposal_request_id,engineering_release_id=engineering_release_id,token=token)
    responses=SQLAlchemyEngineeringPropertyProposalClientResponseRepository(db).list(property_record_id=property_record_id,proposal_request_id=proposal_request_id)
    existing=next((item for item in responses if item.engineering_release_id==engineering_release_id),None)
    artifact=SQLAlchemyEngineeringPropertyProposalPdfArtifactRepository(db).get_for_release(engineering_release_id)
    return {"proposal_number":release.proposal_number,"project_goal":proposal_request.project_goal,"client_name":proposal_request.customer_name,"response_status":getattr(existing,"response_status",None) or "AWAITING_CLIENT_RESPONSE","can_respond":existing is None and release.release_status=="SENT_AWAITING_CLIENT_RESPONSE","exact_pdf_available":artifact is not None,"engineering_job_created":False,"professional_boundary":"Client acceptance authorizes proposal acceptance only; Engineering job creation remains a separate authorized Engineering action."}


@public_router.get("/public/proposal-response.pdf")
def download_public_engineering_proposal_response_pdf(property_record_id: str,proposal_request_id: str,engineering_release_id: str,token: str,db: Session = Depends(get_db)):
    """Return the exact durable released PDF to the signed client portal; never re-render."""
    _client_portal_release(db=db,property_record_id=property_record_id,proposal_request_id=proposal_request_id,engineering_release_id=engineering_release_id,token=token)
    repo=SQLAlchemyEngineeringPropertyProposalPdfArtifactRepository(db)
    artifact=repo.get_for_release(engineering_release_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="durable proposal PDF not found")
    try:
        data=repo.exact_bytes(artifact)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return Response(content=data,media_type=artifact.mime_type,headers={"Content-Disposition":f'inline; filename="{artifact.filename}"',"X-MIDRA-PDF-SHA256":artifact.pdf_sha256})


@public_router.post("/public/proposal-response", response_model=PropertyEngineeringProposalClientResponseActionRead, status_code=status.HTTP_201_CREATED)
def submit_public_engineering_proposal_response(property_record_id: str,proposal_request_id: str,engineering_release_id: str,token: str,payload: PropertyEngineeringProposalClientResponseCreate,db: Session = Depends(get_db)):
    """Record an explicit signed client ACCEPTED/DECLINED response; never create an Engineering job."""
    proposal_request,release=_client_portal_release(db=db,property_record_id=property_record_id,proposal_request_id=proposal_request_id,engineering_release_id=engineering_release_id,token=token)
    try:
        response_snapshot=record_property_engineering_proposal_client_response(released_snapshot=dict(release.released_snapshot or {}),response_status=payload.response_status,engineering_user=f"CLIENT:{proposal_request.customer_email}")
        response=SQLAlchemyEngineeringPropertyProposalClientResponseRepository(db).create_response(property_record_id=property_record_id,proposal_request_id=proposal_request_id,engineering_release_id=engineering_release_id,response_snapshot=response_snapshot,recorded_by=f"CLIENT_SELF_SERVICE:{proposal_request.customer_email}")
        refreshed=SQLAlchemyPropertyEngineeringProposalRequestRepository(db).get(property_record_id,proposal_request_id)
        return {"client_response":response,"proposal_request_status":refreshed.request_status,"proposal_lifecycle":classify_property_engineering_proposal_lifecycle(refreshed.request_status),"engineering_job_created":False,"engineering_job_creation_eligible":refreshed.request_status=="CLIENT_APPROVED"}
    except (ValueError,PermissionError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@public_router.post(
    "/{property_record_id}/engineering-proposal-requests/{proposal_request_id}/engineering-releases/{engineering_release_id}/client-response",
    response_model=PropertyEngineeringProposalClientResponseActionRead,
    status_code=status.HTTP_201_CREATED,
)
def record_engineering_property_proposal_client_response(
    property_record_id: str,
    proposal_request_id: str,
    engineering_release_id: str,
    payload: PropertyEngineeringProposalClientResponseCreate,
    db: Session = Depends(get_db),
    engineering_user: str = Depends(require_engineering_user),
):
    """Record one explicit client acceptance/decline against the exact released proposal.

    Acceptance advances the Property proposal lifecycle to CLIENT_APPROVED, making a
    future authorized Engineering job-creation action eligible. It does not create a job
    and does not mark the underlying Property analysis Engineer Accepted.
    """
    release_repo=SQLAlchemyEngineeringPropertyProposalReleaseRepository(db)
    try:
        release=db.get(EngineeringPropertyProposalRelease, engineering_release_id)
        if (
            release is None
            or release.property_record_id != property_record_id
            or release.proposal_request_id != proposal_request_id
        ):
            raise KeyError("engineering_release")
        response_snapshot=record_property_engineering_proposal_client_response(
            released_snapshot=dict(release.released_snapshot or {}),
            response_status=payload.response_status,
            engineering_user=engineering_user,
        )
        response=SQLAlchemyEngineeringPropertyProposalClientResponseRepository(db).create_response(
            property_record_id=property_record_id,
            proposal_request_id=proposal_request_id,
            engineering_release_id=engineering_release_id,
            response_snapshot=response_snapshot,
            recorded_by=engineering_user,
        )
        proposal_request=SQLAlchemyPropertyEngineeringProposalRequestRepository(db).get(
            property_record_id, proposal_request_id
        )
        return {
            "client_response":response,
            "proposal_request_status":proposal_request.request_status,
            "proposal_lifecycle":classify_property_engineering_proposal_lifecycle(
                proposal_request.request_status
            ),
            "engineering_job_created":False,
            "engineering_job_creation_eligible":(
                proposal_request.request_status=="CLIENT_APPROVED"
            ),
        }
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail="engineering proposal release or request not found",
        ) from exc
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@public_router.get(
    "/{property_record_id}/engineering-proposal-requests/{proposal_request_id}/engineering-client-responses",
    response_model=list[EngineeringPropertyProposalClientResponseRead],
)
def list_engineering_property_proposal_client_responses(
    property_record_id: str,
    proposal_request_id: str,
    db: Session = Depends(get_db),
    engineering_user: str = Depends(require_engineering_user),
):
    """List immutable client-response records for one exact Property proposal request."""
    _=engineering_user
    return SQLAlchemyEngineeringPropertyProposalClientResponseRepository(db).list(
        property_record_id=property_record_id,
        proposal_request_id=proposal_request_id,
    )


def _delivery_environmental_screening_from_analysis(analysis: dict) -> dict:
    """Preserve only environmental screening evidence already stored with the analysis.

    This helper never performs a fresh external query and never converts screening
    evidence into a regulatory determination.
    """
    environmental = (analysis or {}).get("environmental_constraints") or {}
    if environmental.get("status") != "SCREENING_EVALUATED":
        return {}

    result = {
        "status": "SCREENING_EVALUATED",
        "professional_boundary": dict(environmental.get("professional_boundary") or {}),
    }
    for kind in ("wetlands", "flood"):
        screening = environmental.get(kind) or {}
        if not isinstance(screening, dict) or not screening:
            continue
        result[kind] = {
            "status": screening.get("status"),
            "screening_result": screening.get("screening_result"),
            "mapped_intersection": screening.get("mapped_intersection"),
            "regulatory_determination": screening.get("regulatory_determination") is True,
            "actual_flood_risk_calculated": screening.get("actual_flood_risk_calculated") is True,
            "source": dict(screening.get("source") or {}),
            "evidence": list(screening.get("evidence") or []),
            "limitations": list(screening.get("limitations") or []),
            "reason": screening.get("reason"),
        }
    return result


def _delivery_zoning_candidate_from_analysis(analysis: dict) -> dict:
    """Preserve only candidate zoning geometry already stored with the analysis."""
    candidate_evidence = (analysis or {}).get("zoning_candidate_geometry") or {}
    if candidate_evidence.get("candidate_only") is not True:
        return {}
    candidate = candidate_evidence.get("candidate") or {}
    record = candidate.get("record") or {}
    if not isinstance(record, dict) or not record:
        return {
            "status": str(candidate_evidence.get("status") or "VERIFY"),
            "candidate_only": True,
            "reason": candidate_evidence.get("reason"),
            "professional_boundary": dict(candidate_evidence.get("professional_boundary") or {}),
            "candidate": None,
        }
    return {
        "status": str(candidate_evidence.get("status") or "VERIFY"),
        "candidate_only": True,
        "reason": candidate_evidence.get("reason"),
        "professional_boundary": dict(candidate_evidence.get("professional_boundary") or {}),
        "candidate": {
            "status": candidate.get("status"),
            "record": {
                "municipality": record.get("municipality"),
                "block": record.get("block"),
                "lot": record.get("lot"),
                "zoning_district": record.get("zoning_district"),
                "evidence_type": record.get("evidence_type"),
                "mapped_geometries": list(record.get("mapped_geometries") or []),
                "geometry_role": record.get("geometry_role"),
                "geometry_definitive": False,
                "source": dict(record.get("source") or {}),
            },
        },
    }


def _delivery_dynamic_intelligence_from_analysis(analysis: dict) -> dict:
    """Preserve already-saved dynamic evidence without changing its promotion state."""
    dynamic = (analysis or {}).get("dynamic_intelligence") or {}
    if not isinstance(dynamic, dict) or not dynamic:
        return {}

    zoning = dict(dynamic.get("zoning") or {})
    candidate = dict(zoning.get("candidate") or {})
    record = dict(candidate.get("record") or {})
    rule = dict(dynamic.get("project_rule_candidate") or {})
    applicability = dict(dynamic.get("project_applicability") or {})
    approval_candidate = dict(dynamic.get("approval_pathway_candidate") or {})
    approval = dict(dynamic.get("approval_pathway") or {})

    return {
        "status": dynamic.get("status"),
        "project_intent": dict(dynamic.get("project_intent") or {}),
        "dynamic_promotable": dynamic.get("dynamic_promotable") is True,
        "reason": dynamic.get("reason"),
        "zoning": {
            "promotion": dict(zoning.get("promotion") or {}),
            "candidate": {
                "status": candidate.get("status"),
                "record": {
                    "municipality": record.get("municipality"),
                    "block": record.get("block"),
                    "lot": record.get("lot"),
                    "zoning_district": record.get("zoning_district"),
                    "evidence_type": record.get("evidence_type"),
                    "geometry_role": record.get("geometry_role"),
                    "geometry_definitive": False,
                    "source": dict(record.get("source") or {}),
                } if record else None,
            },
        },
        "project_rule_candidate": {
            "status": rule.get("status"),
            "municipality": rule.get("municipality"),
            "zoning_district": rule.get("zoning_district"),
            "project_goal": rule.get("project_goal"),
            "requirements": list(rule.get("requirements") or []),
            "source": dict(rule.get("source") or {}),
            "authoritative": rule.get("authoritative") is True,
            "legal_control_confirmed": rule.get("legal_control_confirmed") is True,
        } if rule else None,
        "project_applicability": applicability,
        "approval_pathway_candidate": approval_candidate or None,
        "approval_pathway": approval,
        "source_trust_summary": dict(dynamic.get("source_trust_summary") or {}),
        "professional_boundary": dict(dynamic.get("professional_boundary") or {}),
    }


def _delivery_sources_from_analysis(analysis: dict) -> list[dict]:
    """Normalize only already-resolved map evidence for the mature delivery service.

    This does not discover or promote sources. Missing/weak evidence stays absent
    from the delivery artifact set rather than being invented.
    """
    result: list[dict] = []
    maps = (analysis or {}).get("property_maps") or {}
    for key, role in (("zoning_map", "zoning_map"), ("tax_map", "tax_map")):
        item = maps.get(key) or {}
        url = str(item.get("source_url") or "").strip()
        if not url.startswith(("http://", "https://")):
            continue
        source = dict(item.get("source") or {})
        source.update({
            "label": source.get("label") or ("Zoning Map" if role == "zoning_map" else "Tax Map"),
            "source_url": url,
            "source_role": role,
            "authoritative": item.get("official_source_verified") is True or source.get("authoritative") is True,
            "authority_verified": source.get("authority_verified") is True,
            "municipal_official_link_verified": source.get("municipal_official_link_verified") is True,
            "tax_map_sheet": item.get("tax_map_sheet") or source.get("tax_map_sheet"),
            "block": item.get("block") or maps.get("block"),
            "lot": item.get("lot") or maps.get("lot"),
        })
        result.append(source)

    dynamic = (analysis or {}).get("dynamic_intelligence") or {}
    dynamic_sources = [
        ((dynamic.get("zoning") or {}).get("candidate") or {}).get("record") or {},
        dynamic.get("project_rule_candidate") or {},
        dynamic.get("approval_pathway_candidate") or dynamic.get("approval_pathway") or {},
    ]
    for item in dynamic_sources:
        source = dict((item or {}).get("source") or {})
        url = str(source.get("source_url") or source.get("url") or "").strip()
        if not url.startswith(("http://", "https://")):
            continue
        source.setdefault("label", source.get("title") or "Dynamic municipal evidence")
        source.setdefault("source_role", source.get("source_role") or "dynamic_municipal_evidence")
        source["dynamic_evidence"] = True
        source["candidate_only"] = dynamic.get("dynamic_promotable") is not True
        result.append(source)
    return result


@router.get("/{property_record_id}/delivery-report.pdf")
def get_property_delivery_report_pdf(
    property_record_id: str,
    analysis_run_id: str | None = None,
    report_profile: str = "preliminary",
    db: Session = Depends(get_db),
):
    """Download a PDF for the exact durable Property analysis/report profile."""
    bundle=get_property_delivery_bundle(
        property_record_id=property_record_id,
        analysis_run_id=analysis_run_id,
        report_profile=report_profile,
        db=db,
    )
    rendered=render_property_report_pdf(delivery_bundle=bundle)
    return Response(
        content=rendered["pdf_bytes"],
        media_type=rendered["mime_type"],
        headers={
            "Content-Disposition":f'attachment; filename="{rendered["filename"]}"',
            "X-MIDRA-Report-SHA256":rendered["pdf_sha256"],
            "X-MIDRA-Analysis-Id":str(rendered.get("analysis_id") or ""),
        },
    )


@router.get("/{property_record_id}/delivery-bundle")
def get_property_delivery_bundle(
    property_record_id: str,
    analysis_run_id: str | None = None,
    report_profile: str = "preliminary",
    db: Session = Depends(get_db),
):
    """Compose the existing MIDRA Property evidence/report delivery contract.

    Delivery is presentation of an existing durable analysis. It does not create
    an Engineering handoff and does not constitute engineer review or acceptance.
    """
    record = db.get(PropertyRecord, property_record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="property record not found")

    if analysis_run_id:
        run = db.get(PropertyAnalysisRun, analysis_run_id)
        if run is None or run.property_record_id != property_record_id:
            raise HTTPException(status_code=400, detail="analysis run does not belong to this property")
    else:
        runs = SQLAlchemyPropertyAnalysisRunRepository(db).list(property_record_id, limit=1)
        if not runs:
            raise HTTPException(status_code=409, detail="property record has no saved analysis")
        run = runs[0]

    profile = str(report_profile or "preliminary").strip().lower()
    if profile not in {"preliminary", "complete"}:
        raise HTTPException(status_code=422, detail="report_profile must be preliminary or complete")

    analysis = dict(run.analysis or {})
    property_data = {
        "property_record_id": record.property_record_id,
        "address": record.display_address or record.search_query,
        "municipality": record.municipality,
        "county": record.county,
        "block": record.block,
        "lot": record.lot,
    }
    if not str(record.municipality or "").strip():
        raise HTTPException(status_code=409, detail="municipality must be resolved before delivery")

    bundle = build_property_delivery_bundle(
        analysis_id=run.analysis_run_id,
        property_record=property_data,
        project_goal=str(run.requested_work or analysis.get("requested_work") or analysis.get("project_goal") or ""),
        sources=_delivery_sources_from_analysis(analysis),
        environmental_screening=_delivery_environmental_screening_from_analysis(analysis),
        zoning_candidate_evidence=_delivery_zoning_candidate_from_analysis(analysis),
        dynamic_intelligence_evidence=_delivery_dynamic_intelligence_from_analysis(analysis),
        verification_summary=build_delivery_verification_summary(analysis),
        report_profile=profile,
        analysis_snapshot=analysis,
    )
    # Product naming at the public boundary follows the standalone MIDRA Property product.
    bundle["product"] = "MIDRA_PROPERTY"
    bundle["branding"] = "MIDRA_PROPERTY"
    bundle["professional_boundary"] = {
        "status": "MIDRA_ANALYSIS",
        "engineer_reviewed": False,
        "engineer_accepted": False,
        "notice": "Delivery does not constitute engineer review or acceptance.",
    }
    return bundle
