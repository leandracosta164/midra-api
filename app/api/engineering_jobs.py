"""FastAPI routes for MIDRA Engineering Job operations."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
import secrets
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.engineering_document_storage import decode_content, safe_filename, store, resolve
from app.repositories.engineering_job import SQLAlchemyEngineeringJobRepository
from app.schemas.engineering_job import (
    EngineeringJobCreate, EngineeringJobEventCreate, EngineeringJobRead,
    EngineeringJobSectionConnect, EngineeringJobStateChange,
    EngineeringJobProfileUpdate, EngineeringJobSignalCreate, EngineeringJobSignalResolve,
    EngineeringDeliverableCreate, EngineeringDeliverableStatusChange,
    EngineeringDocumentUpload, EngineeringDocumentRevisionUpload,
    EngineeringReviewCreate, EngineeringReviewCommentCreate, EngineeringReviewCommentUpdate,
    EngineeringSubmissionPackageCreate, EngineeringSubmissionPackageStatusChange,
    EngineeringDependencyCreate, EngineeringDependencyUpdate,
    EngineeringActionItemCreate, EngineeringActionItemUpdate,
    EngineeringLifecycleAuditAcknowledgementCreate, EngineeringLifecycleAuditAcknowledgementRead,
    EngineeringPostCompletionWorkCreate, EngineeringPostCompletionWorkUpdate,
    EngineeringProjectReopenCreate,
    EngineeringProjectCompletionCertificationCreate,
    EngineeringProjectClosureItemCreate, EngineeringProjectClosureItemUpdate,
    EngineeringArchiveRecordCreate, EngineeringArchiveRecordUpdate,
    EngineeringWarrantyIssueCreate, EngineeringWarrantyIssueUpdate,
    EngineeringCloseoutItemCreate, EngineeringCloseoutItemUpdate,
    EngineeringPunchItemCreate, EngineeringPunchItemUpdate,
    EngineeringChangeOrderCreate, EngineeringChangeOrderUpdate,
    EngineeringSubmittalCreate, EngineeringSubmittalReview,
    EngineeringRFICreate, EngineeringRFIUpdate,
    EngineeringFieldReportCreate, EngineeringFieldReportUpdate,
    EngineeringMeetingCreate, EngineeringMeetingUpdate,
    EngineeringMilestoneCreate, EngineeringMilestoneUpdate,
    EngineeringCorrespondenceCreate, EngineeringCorrespondenceResponseUpdate,
    EngineeringBillingCreate, EngineeringBillingStatusUpdate,
    EngineeringClientPortalItemCreate, EngineeringClientPortalItemUpdate,
    EngineeringDocumentRevisionStatusUpdate,
    EngineeringReviewCycleStatusUpdate,
    EngineeringSubmissionReadinessAssess,
    EngineeringSubmissionPackageAdvance,
    EngineeringSubmissionOutcomeRecord,
    EngineeringSubmissionReturnWorkActivate,
    EngineeringReturnedSubmissionReassess,
    EngineeringSubmissionResubmissionOpen,
    EngineeringAcceptedSubmissionClose,
    EngineeringSubmissionLifecycleSummary,
)

router=APIRouter(prefix="/engineering/jobs",tags=["MIDRA Engineering Jobs"])


def repo(db: Session) -> SQLAlchemyEngineeringJobRepository:
    return SQLAlchemyEngineeringJobRepository(db)


@router.post("",response_model=EngineeringJobRead,status_code=status.HTTP_201_CREATED)
def create_job(payload: EngineeringJobCreate, db: Session=Depends(get_db)):
    r=repo(db)
    try:
        return r.create(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=409,detail=str(exc)) from exc


@router.get("",response_model=list[EngineeringJobRead])
def list_jobs(state: str | None=None, db: Session=Depends(get_db)):
    return repo(db).list_jobs(state=state)


@router.get("/{job_number}",response_model=EngineeringJobRead)
def get_job(job_number: str, db: Session=Depends(get_db)):
    try:
        return repo(db).get(job_number)
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc


@router.post("/{job_number}/state",response_model=EngineeringJobRead)
def change_state(job_number: str,payload: EngineeringJobStateChange,
                 db: Session=Depends(get_db)):
    try:
        return repo(db).change_state(job_number=job_number,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc


@router.post("/{job_number}/sections",response_model=EngineeringJobRead)
def connect_section(job_number: str,payload: EngineeringJobSectionConnect,
                    db: Session=Depends(get_db)):
    try:
        return repo(db).connect_section(job_number=job_number,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc


@router.post("/{job_number}/events",response_model=EngineeringJobRead)
def add_event(job_number: str,payload: EngineeringJobEventCreate,
              db: Session=Depends(get_db)):
    try:
        return repo(db).add_event(job_number=job_number,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc


@router.put("/{job_number}/profile",response_model=EngineeringJobRead)
def update_profile(job_number: str,payload: EngineeringJobProfileUpdate,
                   db: Session=Depends(get_db)):
    try:
        return repo(db).update_profile(job_number=job_number,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc


@router.post("/{job_number}/signals",response_model=EngineeringJobRead)
def create_signal(job_number: str,payload: EngineeringJobSignalCreate,
                  db: Session=Depends(get_db)):
    try:
        return repo(db).add_signal(job_number=job_number,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc


@router.post("/{job_number}/signals/{signal_id}/resolve",response_model=EngineeringJobRead)
def resolve_signal(job_number: str,signal_id: str,payload: EngineeringJobSignalResolve,
                   db: Session=Depends(get_db)):
    try:
        return repo(db).resolve_signal(
            job_number=job_number,signal_id=signal_id,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job or signal not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc


@router.post("/{job_number}/deliverables",response_model=EngineeringJobRead)
def create_deliverable(job_number: str,payload: EngineeringDeliverableCreate,
                       db: Session=Depends(get_db)):
    try:
        return repo(db).add_deliverable(job_number=job_number,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc


@router.post("/{job_number}/deliverables/{deliverable_id}/status",
             response_model=EngineeringJobRead)
def change_deliverable_status(job_number: str,deliverable_id: str,
                              payload: EngineeringDeliverableStatusChange,
                              db: Session=Depends(get_db)):
    try:
        return repo(db).change_deliverable_status(
            job_number=job_number,deliverable_id=deliverable_id,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job or deliverable not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc


@router.post("/{job_number}/documents",response_model=EngineeringJobRead)
def upload_document(job_number: str,payload: EngineeringDocumentUpload,
                    db: Session=Depends(get_db)):
    r=repo(db)
    try:
        r.get(job_number)
        filename=safe_filename(payload.filename)
        content=decode_content(payload.content_base64)
        document_id="DOC-"+secrets.token_hex(6).upper()
        storage_path,sha256=store(
            job_number=job_number,document_id=document_id,revision=1,
            filename=filename,content=content)
        return r.add_document(
            job_number=job_number,document_id=document_id,filename=filename,
            content_type=payload.content_type,category=payload.category,
            description=payload.description,deliverable_id=payload.deliverable_id,
            storage_path=storage_path,sha256=sha256,size_bytes=len(content),
            authorized_by=payload.authorized_by)
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc


@router.post("/{job_number}/documents/{document_id}/revisions",
             response_model=EngineeringJobRead)
def upload_document_revision(job_number: str,document_id: str,
                             payload: EngineeringDocumentRevisionUpload,
                             db: Session=Depends(get_db)):
    r=repo(db)
    try:
        target,_=r.get_document_revision(job_number=job_number,document_id=document_id)
        filename=safe_filename(payload.filename)
        content=decode_content(payload.content_base64)
        revision=int(target.get("current_revision") or 0)+1
        storage_path,sha256=store(
            job_number=job_number,document_id=document_id,revision=revision,
            filename=filename,content=content)
        return r.add_document_revision(
            job_number=job_number,document_id=document_id,filename=filename,
            content_type=payload.content_type,description=payload.description,
            storage_path=storage_path,sha256=sha256,size_bytes=len(content),
            authorized_by=payload.authorized_by)
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job or document not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc


@router.get("/{job_number}/documents/{document_id}/download")
def download_document(job_number: str,document_id: str,revision: int | None=None,
                      db: Session=Depends(get_db)):
    try:
        _,rev=repo(db).get_document_revision(
            job_number=job_number,document_id=document_id,revision=revision)
        path=resolve(rev["storage_path"])
        return FileResponse(
            path=str(path),filename=rev["filename"],
            media_type=rev.get("content_type") or "application/octet-stream")
    except (KeyError,FileNotFoundError) as exc:
        raise HTTPException(status_code=404,detail="document file not found") from exc


@router.post("/{job_number}/reviews",response_model=EngineeringJobRead)
def create_review(job_number: str,payload: EngineeringReviewCreate,db: Session=Depends(get_db)):
    try:
        return repo(db).add_review(job_number=job_number,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc


@router.post("/{job_number}/reviews/{review_id}/comments",response_model=EngineeringJobRead)
def create_review_comment(job_number: str,review_id: str,
                          payload: EngineeringReviewCommentCreate,db: Session=Depends(get_db)):
    try:
        return repo(db).add_review_comment(job_number=job_number,review_id=review_id,
                                           **payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job or review not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc


@router.post("/{job_number}/reviews/{review_id}/comments/{comment_id}",
             response_model=EngineeringJobRead)
def update_review_comment(job_number: str,review_id: str,comment_id: str,
                          payload: EngineeringReviewCommentUpdate,db: Session=Depends(get_db)):
    try:
        return repo(db).update_review_comment(job_number=job_number,review_id=review_id,
                                              comment_id=comment_id,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job, review, or comment not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc


@router.post("/{job_number}/submission-packages",response_model=EngineeringJobRead)
def create_submission_package(job_number: str,payload: EngineeringSubmissionPackageCreate,
                              db: Session=Depends(get_db)):
    try:
        return repo(db).add_submission_package(job_number=job_number,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc


@router.post("/{job_number}/submission-packages/{package_id}/status",
             response_model=EngineeringJobRead)
def update_submission_package(job_number: str,package_id: str,
                              payload: EngineeringSubmissionPackageStatusChange,
                              db: Session=Depends(get_db)):
    try:
        return repo(db).change_submission_package_status(
            job_number=job_number,package_id=package_id,**payload.model_dump()
        )
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job or submission package not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc


@router.post("/{job_number}/dependencies",response_model=EngineeringJobRead)
def create_dependency(job_number: str,payload: EngineeringDependencyCreate,
                      db: Session=Depends(get_db)):
    try:
        return repo(db).add_dependency(job_number=job_number,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc


@router.post("/{job_number}/dependencies/{dependency_id}",response_model=EngineeringJobRead)
def update_dependency(job_number: str,dependency_id: str,
                      payload: EngineeringDependencyUpdate,db: Session=Depends(get_db)):
    try:
        return repo(db).update_dependency(
            job_number=job_number,dependency_id=dependency_id,**payload.model_dump()
        )
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job or dependency not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc


@router.post("/{job_number}/action-items",response_model=EngineeringJobRead)
def create_action_item(job_number: str,payload: EngineeringActionItemCreate,
                       db: Session=Depends(get_db)):
    try:
        return repo(db).add_action_item(job_number=job_number,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc


@router.post("/{job_number}/action-items/{action_id}",response_model=EngineeringJobRead)
def update_action_item(job_number: str,action_id: str,
                       payload: EngineeringActionItemUpdate,db: Session=Depends(get_db)):
    try:
        return repo(db).update_action_item(
            job_number=job_number,action_id=action_id,**payload.model_dump()
        )
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job or action item not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.get("/{job_number}/lifecycle-audit/acknowledgements",response_model=list[EngineeringLifecycleAuditAcknowledgementRead])
def project_lifecycle_audit_acknowledgements(job_number: str,db: Session=Depends(get_db)):
    try:
        return repo(db).project_lifecycle_audit_acknowledgements(job_number=job_number)
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc

@router.post("/{job_number}/lifecycle-audit/acknowledge",response_model=EngineeringJobRead)
def acknowledge_project_lifecycle_audit(job_number: str,payload: EngineeringLifecycleAuditAcknowledgementCreate,
                                        db: Session=Depends(get_db)):
    try:
        return repo(db).acknowledge_project_lifecycle_audit(job_number=job_number,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/post-completion-work",response_model=EngineeringJobRead)
def add_post_completion_work(job_number: str,payload: EngineeringPostCompletionWorkCreate,
                             db: Session=Depends(get_db)):
    try:
        return repo(db).add_post_completion_work(job_number=job_number,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.patch("/{job_number}/post-completion-work/{item_id}",response_model=EngineeringJobRead)
def update_post_completion_work(job_number: str,item_id: str,payload: EngineeringPostCompletionWorkUpdate,
                                db: Session=Depends(get_db)):
    try:
        return repo(db).update_post_completion_work(job_number=job_number,item_id=item_id,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/project-completion/reopen",response_model=EngineeringJobRead)
def reopen_completed_project(job_number: str,payload: EngineeringProjectReopenCreate,
                             db: Session=Depends(get_db)):
    try:
        return repo(db).reopen_completed_project(job_number=job_number,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/project-completion/certify",response_model=EngineeringJobRead)
def certify_project_completion(job_number: str,payload: EngineeringProjectCompletionCertificationCreate,
                               db: Session=Depends(get_db)):
    try:
        return repo(db).certify_project_completion(job_number=job_number,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/project-closure",response_model=EngineeringJobRead)
def create_project_closure_item(job_number: str,payload: EngineeringProjectClosureItemCreate,
                                db: Session=Depends(get_db)):
    try:
        return repo(db).add_project_closure_item(job_number=job_number,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/project-closure/{closure_id}",response_model=EngineeringJobRead)
def update_project_closure_item(job_number: str,closure_id: str,
                                payload: EngineeringProjectClosureItemUpdate,
                                db: Session=Depends(get_db)):
    try:
        return repo(db).update_project_closure_item(job_number=job_number,closure_id=closure_id,
                                                    **payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job or project closure item not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/project-archive",response_model=EngineeringJobRead)
def create_archive_record(job_number: str,payload: EngineeringArchiveRecordCreate,
                          db: Session=Depends(get_db)):
    try:
        return repo(db).add_archive_record(job_number=job_number,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/project-archive/{archive_id}",response_model=EngineeringJobRead)
def update_archive_record(job_number: str,archive_id: str,payload: EngineeringArchiveRecordUpdate,
                          db: Session=Depends(get_db)):
    try:
        return repo(db).update_archive_record(job_number=job_number,archive_id=archive_id,
                                              **payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job or archive record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/warranty-issues",response_model=EngineeringJobRead)
def create_warranty_issue(job_number: str,payload: EngineeringWarrantyIssueCreate,
                          db: Session=Depends(get_db)):
    try:
        return repo(db).add_warranty_issue(job_number=job_number,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/warranty-issues/{issue_id}",response_model=EngineeringJobRead)
def update_warranty_issue(job_number: str,issue_id: str,payload: EngineeringWarrantyIssueUpdate,
                          db: Session=Depends(get_db)):
    try:
        return repo(db).update_warranty_issue(job_number=job_number,issue_id=issue_id,
                                              **payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job or warranty issue not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/closeout",response_model=EngineeringJobRead)
def create_closeout_item(job_number: str,payload: EngineeringCloseoutItemCreate,
                         db: Session=Depends(get_db)):
    try:
        return repo(db).add_closeout_item(job_number=job_number,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/closeout/{closeout_id}",response_model=EngineeringJobRead)
def update_closeout_item(job_number: str,closeout_id: str,payload: EngineeringCloseoutItemUpdate,
                         db: Session=Depends(get_db)):
    try:
        return repo(db).update_closeout_item(job_number=job_number,closeout_id=closeout_id,
                                             **payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job or closeout item not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/punch-list",response_model=EngineeringJobRead)
def create_punch_item(job_number: str,payload: EngineeringPunchItemCreate,
                      db: Session=Depends(get_db)):
    try:
        return repo(db).add_punch_item(job_number=job_number,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/punch-list/{punch_id}",response_model=EngineeringJobRead)
def update_punch_item(job_number: str,punch_id: str,payload: EngineeringPunchItemUpdate,
                      db: Session=Depends(get_db)):
    try:
        return repo(db).update_punch_item(job_number=job_number,punch_id=punch_id,
                                          **payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job or punch item not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/change-orders",response_model=EngineeringJobRead)
def create_change_order(job_number: str,payload: EngineeringChangeOrderCreate,
                        db: Session=Depends(get_db)):
    try:
        return repo(db).add_change_order(job_number=job_number,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/change-orders/{change_id}",response_model=EngineeringJobRead)
def update_change_order(job_number: str,change_id: str,payload: EngineeringChangeOrderUpdate,
                        db: Session=Depends(get_db)):
    try:
        return repo(db).update_change_order(job_number=job_number,change_id=change_id,
                                            **payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job or change order not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/submittals",response_model=EngineeringJobRead)
def create_submittal(job_number: str,payload: EngineeringSubmittalCreate,
                     db: Session=Depends(get_db)):
    try:
        return repo(db).add_submittal(job_number=job_number,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/submittals/{submittal_id}/review",response_model=EngineeringJobRead)
def review_submittal(job_number: str,submittal_id: str,payload: EngineeringSubmittalReview,
                     db: Session=Depends(get_db)):
    try:
        return repo(db).review_submittal(job_number=job_number,submittal_id=submittal_id,
                                         **payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job or submittal not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/rfis",response_model=EngineeringJobRead)
def create_rfi(job_number: str,payload: EngineeringRFICreate,db: Session=Depends(get_db)):
    try:
        return repo(db).add_rfi(job_number=job_number,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/rfis/{rfi_id}",response_model=EngineeringJobRead)
def update_rfi(job_number: str,rfi_id: str,payload: EngineeringRFIUpdate,
               db: Session=Depends(get_db)):
    try:
        return repo(db).update_rfi(job_number=job_number,rfi_id=rfi_id,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job or RFI not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/field-reports",response_model=EngineeringJobRead)
def create_field_report(job_number: str,payload: EngineeringFieldReportCreate,
                        db: Session=Depends(get_db)):
    try:
        return repo(db).add_field_report(job_number=job_number,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/field-reports/{report_id}",response_model=EngineeringJobRead)
def update_field_report(job_number: str,report_id: str,payload: EngineeringFieldReportUpdate,
                        db: Session=Depends(get_db)):
    try:
        return repo(db).update_field_report(job_number=job_number,report_id=report_id,
                                            **payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job or field report not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/meetings",response_model=EngineeringJobRead)
def create_meeting(job_number: str,payload: EngineeringMeetingCreate,db: Session=Depends(get_db)):
    try:
        return repo(db).add_meeting(job_number=job_number,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/meetings/{meeting_id}",response_model=EngineeringJobRead)
def update_meeting(job_number: str,meeting_id: str,payload: EngineeringMeetingUpdate,
                   db: Session=Depends(get_db)):
    try:
        return repo(db).update_meeting(job_number=job_number,meeting_id=meeting_id,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job or meeting not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/milestones",response_model=EngineeringJobRead)
def create_milestone(job_number: str,payload: EngineeringMilestoneCreate,
                     db: Session=Depends(get_db)):
    try:
        return repo(db).add_milestone(job_number=job_number,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/milestones/{milestone_id}",response_model=EngineeringJobRead)
def update_milestone(job_number: str,milestone_id: str,payload: EngineeringMilestoneUpdate,
                     db: Session=Depends(get_db)):
    try:
        return repo(db).update_milestone(job_number=job_number,milestone_id=milestone_id,
                                         **payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job or milestone not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/correspondence",response_model=EngineeringJobRead)
def create_correspondence(job_number: str,payload: EngineeringCorrespondenceCreate,
                          db: Session=Depends(get_db)):
    try:
        return repo(db).add_correspondence(job_number=job_number,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/correspondence/{correspondence_id}/response",
             response_model=EngineeringJobRead)
def update_correspondence_response(job_number: str,correspondence_id: str,
                                   payload: EngineeringCorrespondenceResponseUpdate,
                                   db: Session=Depends(get_db)):
    try:
        return repo(db).update_correspondence_response(
            job_number=job_number,correspondence_id=correspondence_id,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job or correspondence not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/billing",response_model=EngineeringJobRead)
def create_billing_record(job_number: str,payload: EngineeringBillingCreate,
                          db: Session=Depends(get_db)):
    try:
        return repo(db).add_billing_record(job_number=job_number,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/billing/{billing_id}/status",response_model=EngineeringJobRead)
def update_billing_status(job_number: str,billing_id: str,payload: EngineeringBillingStatusUpdate,
                          db: Session=Depends(get_db)):
    try:
        return repo(db).update_billing_status(job_number=job_number,billing_id=billing_id,
                                              **payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job or billing record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/client-portal",response_model=EngineeringJobRead)
def create_client_portal_item(job_number: str,payload: EngineeringClientPortalItemCreate,
                              db: Session=Depends(get_db)):
    try:
        return repo(db).add_client_portal_item(job_number=job_number,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/client-portal/{portal_item_id}",response_model=EngineeringJobRead)
def update_client_portal_item(job_number: str,portal_item_id: str,
                              payload: EngineeringClientPortalItemUpdate,
                              db: Session=Depends(get_db)):
    try:
        return repo(db).update_client_portal_item(job_number=job_number,portal_item_id=portal_item_id,
                                                  **payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job or client portal item not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/documents/{document_id}/revisions/{revision_id}/status",
             response_model=EngineeringJobRead)
def update_document_revision_status(job_number: str,document_id: str,revision_id: str,
                                    payload: EngineeringDocumentRevisionStatusUpdate,
                                    db: Session=Depends(get_db)):
    try:
        return repo(db).update_document_revision_status(
            job_number=job_number,document_id=document_id,revision_id=revision_id,
            **payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job, document, or revision not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/reviews/{review_id}/status",response_model=EngineeringJobRead)
def update_review_cycle_status(job_number: str,review_id: str,
                               payload: EngineeringReviewCycleStatusUpdate,
                               db: Session=Depends(get_db)):
    try:
        return repo(db).update_review_cycle_status(
            job_number=job_number,review_id=review_id,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job or review cycle not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/submission-packages/{package_id}/readiness",
             response_model=EngineeringJobRead)
def assess_submission_package_readiness(job_number: str,package_id: str,
                                        payload: EngineeringSubmissionReadinessAssess,
                                        db: Session=Depends(get_db)):
    try:
        return repo(db).assess_submission_package_readiness(
            job_number=job_number,package_id=package_id,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job or submission package not found") from exc

@router.post("/{job_number}/submission-packages/{package_id}/advance",
             response_model=EngineeringJobRead)
def advance_submission_package(job_number: str,package_id: str,
                               payload: EngineeringSubmissionPackageAdvance,
                               db: Session=Depends(get_db)):
    try:
        return repo(db).advance_submission_package(
            job_number=job_number,package_id=package_id,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job or submission package not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/submission-packages/{package_id}/outcome",
             response_model=EngineeringJobRead)
def record_submission_outcome(job_number: str,package_id: str,
                              payload: EngineeringSubmissionOutcomeRecord,
                              db: Session=Depends(get_db)):
    try:
        return repo(db).record_submission_outcome(
            job_number=job_number,package_id=package_id,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job or submission package not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/submission-packages/{package_id}/activate-return-work",
             response_model=EngineeringJobRead)
def activate_submission_return_work(job_number: str,package_id: str,
                                    payload: EngineeringSubmissionReturnWorkActivate,
                                    db: Session=Depends(get_db)):
    try:
        return repo(db).activate_submission_return_work(
            job_number=job_number,package_id=package_id,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job or submission package not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/submission-packages/{package_id}/reassess-return",
             response_model=EngineeringJobRead)
def reassess_returned_submission(job_number: str,package_id: str,
                                 payload: EngineeringReturnedSubmissionReassess,
                                 db: Session=Depends(get_db)):
    try:
        return repo(db).reassess_returned_submission(
            job_number=job_number,package_id=package_id,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job or submission package not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/submission-packages/{package_id}/open-resubmission",
             response_model=EngineeringJobRead)
def reopen_submission_for_resubmission(job_number: str,package_id: str,
                                       payload: EngineeringSubmissionResubmissionOpen,
                                       db: Session=Depends(get_db)):
    try:
        return repo(db).reopen_submission_for_resubmission(
            job_number=job_number,package_id=package_id,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job or submission package not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/{job_number}/submission-packages/{package_id}/close-accepted",
             response_model=EngineeringJobRead)
def close_accepted_submission(job_number: str,package_id: str,
                              payload: EngineeringAcceptedSubmissionClose,
                              db: Session=Depends(get_db)):
    try:
        return repo(db).close_accepted_submission(
            job_number=job_number,package_id=package_id,**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job or submission package not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.get("/{job_number}/submission-lifecycle",
            response_model=EngineeringSubmissionLifecycleSummary)
def submission_lifecycle_summary(job_number: str,db: Session=Depends(get_db)):
    try:
        return repo(db).get_submission_lifecycle_summary(job_number=job_number)
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc

