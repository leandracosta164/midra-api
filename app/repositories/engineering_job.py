"""SQLAlchemy repository for MIDRA Engineering Jobs."""
from copy import deepcopy
from datetime import datetime, timezone
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.engineering_job import EngineeringJob

JOB_STATES={"ACTIVE","WAITING","ON_HOLD","READY_FOR_REVIEW","CLOSEOUT","CLOSED"}
SECTIONS={
    "client","property","estimate","workflow","workspace","design",
    "submissions","reviews","correspondence","billing","client_portal","command_center"
}


class SQLAlchemyEngineeringJobRepository:
    def __init__(self, db: Session):
        self.db=db

    def exists(self, job_number: str) -> bool:
        return self.db.get(EngineeringJob,job_number) is not None

    def get(self, job_number: str) -> EngineeringJob:
        job=self.db.get(EngineeringJob,job_number)
        if job is None:
            raise KeyError(job_number)
        return job

    def list_jobs(self, state: str | None=None) -> list[EngineeringJob]:
        stmt=select(EngineeringJob)
        if state:
            stmt=stmt.where(EngineeringJob.state==state)
        stmt=stmt.order_by(EngineeringJob.job_number)
        return list(self.db.scalars(stmt).all())

    def create(self, **values) -> EngineeringJob:
        if self.exists(values["job_number"]):
            raise ValueError("job number already exists")
        job=EngineeringJob(**values)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def change_state(self, *, job_number, state, authorized_by, reason=None):
        if state not in JOB_STATES:
            raise ValueError("unsupported job state")
        if not (authorized_by or "").strip():
            raise ValueError("job state change requires authorization")
        job=self.get(job_number)
        previous=job.state
        events=deepcopy(job.events or [])
        events.append({
            "event_type":"JOB_STATE_CHANGED","from_state":previous,
            "to_state":state,"reason":reason,"authorized_by":authorized_by,
            "occurred_at":datetime.now(timezone.utc).isoformat(),
        })
        job.state=state
        job.events=events
        self._touch(job)
        self.db.commit(); self.db.refresh(job)
        return job

    def connect_section(self, *, job_number, section, reference_id,
                        summary=None, authorized_by=None):
        if section not in SECTIONS:
            raise ValueError("unsupported job section")
        job=self.get(job_number)
        sections=deepcopy(job.sections or {})
        previous=(sections.get(section) or {}).get("reference_id")
        sections[section]={
            "reference_id":reference_id,
            "summary":deepcopy(summary or {}),
            "updated_by":authorized_by,
        }
        events=deepcopy(job.events or [])
        events.append({
            "event_type":"JOB_SECTION_CONNECTED",
            "section":section,
            "reference_id":reference_id,
            "previous_reference_id":previous,
            "summary":(summary or {}).get("description"),
            "authorized_by":authorized_by,
            "occurred_at":datetime.now(timezone.utc).isoformat(),
        })
        job.sections=sections
        job.events=events
        self._touch(job)
        self.db.commit(); self.db.refresh(job)
        return job

    def add_event(self, *, job_number, event_type, reference_id=None, summary=None):
        job=self.get(job_number)
        events=deepcopy(job.events or [])
        events.append({
            "event_type":event_type,"reference_id":reference_id,"summary":summary,
            "occurred_at":datetime.now(timezone.utc).isoformat(),
        })
        job.events=events
        self._touch(job)
        self.db.commit(); self.db.refresh(job)
        return job

    def update_profile(self, *, job_number, project_name, project_type, source,
                       property_address=None, client_id=None, authorized_by, reason=None):
        if not (authorized_by or "").strip():
            raise ValueError("job profile update requires authorization")
        job=self.get(job_number)
        before={
            "project_name":job.project_name,"project_type":job.project_type,
            "source":job.source,"property_address":job.property_address,
            "client_id":job.client_id,
        }
        after={
            "project_name":project_name.strip(),"project_type":project_type.strip(),
            "source":source.strip(),"property_address":property_address or None,
            "client_id":client_id or None,
        }
        changed={k:{"from":before[k],"to":after[k]} for k in before if before[k] != after[k]}
        if not changed:
            return job
        for key,value in after.items():
            setattr(job,key,value)
        events=deepcopy(job.events or [])
        events.append({
            "event_type":"JOB_PROFILE_UPDATED","changes":changed,"reason":reason,
            "authorized_by":authorized_by,
            "occurred_at":datetime.now(timezone.utc).isoformat(),
        })
        job.events=events
        self._touch(job)
        self.db.commit(); self.db.refresh(job)
        return job

    def add_signal(self, *, job_number, signal_type, message, level="NORMAL",
                   waiting_on=None, due_at=None, requires_user_action=False,
                   authorized_by):
        if level not in {"INFO","NORMAL","ATTENTION","URGENT"}:
            raise ValueError("unsupported signal level")
        if signal_type not in {"ACTION","DEPENDENCY","DEADLINE","REVIEW","FOLLOW_UP"}:
            raise ValueError("unsupported signal type")
        job=self.get(job_number)
        sections=deepcopy(job.sections or {})
        cc=deepcopy(sections.get("command_center") or {
            "reference_id":f"CC-{job.job_number}","summary":{},"updated_by":authorized_by
        })
        summary=deepcopy(cc.get("summary") or {})
        signals=deepcopy(summary.get("signals") or [])
        signal_id="SIG-"+secrets.token_hex(6).upper()
        signal={
            "signal_id":signal_id,"type":signal_type,"message":message.strip(),
            "level":level,"waiting_on":waiting_on or None,"due_at":due_at or None,
            "requires_user_action":bool(requires_user_action),"resolved":False,
            "created_by":authorized_by,
            "created_at":datetime.now(timezone.utc).isoformat(),
        }
        signals.append(signal)
        summary["signals"]=signals
        cc["summary"]=summary; cc["updated_by"]=authorized_by
        sections["command_center"]=cc
        events=deepcopy(job.events or [])
        events.append({
            "event_type":"JOB_SIGNAL_CREATED","reference_id":signal_id,
            "summary":message.strip(),"signal_type":signal_type,"level":level,
            "authorized_by":authorized_by,
            "occurred_at":datetime.now(timezone.utc).isoformat(),
        })
        job.sections=sections; job.events=events
        self._touch(job)
        self.db.commit(); self.db.refresh(job)
        return job

    def resolve_signal(self, *, job_number, signal_id, authorized_by, resolution=None):
        job=self.get(job_number)
        sections=deepcopy(job.sections or {})
        cc=deepcopy(sections.get("command_center") or {})
        summary=deepcopy(cc.get("summary") or {})
        signals=deepcopy(summary.get("signals") or [])
        found=False
        for signal in signals:
            if signal.get("signal_id")==signal_id:
                if signal.get("resolved"):
                    raise ValueError("signal is already resolved")
                signal["resolved"]=True
                signal["resolved_by"]=authorized_by
                signal["resolved_at"]=datetime.now(timezone.utc).isoformat()
                signal["resolution"]=resolution
                found=True
                break
        if not found:
            raise KeyError(signal_id)
        summary["signals"]=signals; cc["summary"]=summary; cc["updated_by"]=authorized_by
        sections["command_center"]=cc
        events=deepcopy(job.events or [])
        events.append({
            "event_type":"JOB_SIGNAL_RESOLVED","reference_id":signal_id,
            "summary":resolution,"authorized_by":authorized_by,
            "occurred_at":datetime.now(timezone.utc).isoformat(),
        })
        job.sections=sections; job.events=events
        self._touch(job)
        self.db.commit(); self.db.refresh(job)
        return job

    @staticmethod
    def _touch(job):
        job.version=(job.version or 0)+1
        job.updated_at=datetime.now(timezone.utc)



    def add_deliverable(self, *, job_number, title, deliverable_type, recipient=None,
                        due_at=None, notes=None, authorized_by):
        job=self.get(job_number)
        sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("deliverables") or {
            "reference_id":f"DEL-{job.job_number}","summary":{},"updated_by":authorized_by
        })
        summary=deepcopy(section.get("summary") or {})
        items=deepcopy(summary.get("items") or [])
        deliverable_id="DLV-"+secrets.token_hex(6).upper()
        now=datetime.now(timezone.utc).isoformat()
        item={
            "deliverable_id":deliverable_id,
            "title":title.strip(),
            "deliverable_type":deliverable_type.strip(),
            "recipient":recipient or None,
            "due_at":due_at or None,
            "notes":notes or None,
            "status":"DRAFT",
            "reference":None,
            "created_by":authorized_by,
            "created_at":now,
            "updated_at":now,
        }
        items.append(item)
        summary["items"]=items
        section["summary"]=summary
        section["updated_by"]=authorized_by
        sections["deliverables"]=section
        events=deepcopy(job.events or [])
        events.append({
            "event_type":"DELIVERABLE_CREATED",
            "reference_id":deliverable_id,
            "summary":title.strip(),
            "deliverable_type":deliverable_type.strip(),
            "authorized_by":authorized_by,
            "occurred_at":now,
        })
        job.sections=sections
        job.events=events
        self._touch(job)
        self.db.commit(); self.db.refresh(job)
        return job

    def change_deliverable_status(self, *, job_number, deliverable_id, status,
                                  reference=None, note=None,
                                  professional_action_approved=False, authorized_by):
        allowed={"DRAFT","READY_FOR_REVIEW","ISSUED","SUBMITTED","APPROVED","SUPERSEDED"}
        controlled={"ISSUED","SUBMITTED","APPROVED"}
        if status not in allowed:
            raise ValueError("unsupported deliverable status")
        if status in controlled and not professional_action_approved:
            raise ValueError(
                "explicit professional approval is required for issued, submitted, or approved status"
            )
        job=self.get(job_number)
        sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("deliverables") or {})
        summary=deepcopy(section.get("summary") or {})
        items=deepcopy(summary.get("items") or [])
        target=None
        for item in items:
            if item.get("deliverable_id")==deliverable_id:
                target=item
                break
        if target is None:
            raise KeyError(deliverable_id)
        previous=target.get("status","DRAFT")
        if previous==status and (reference or None)==target.get("reference"):
            return job
        now=datetime.now(timezone.utc).isoformat()
        target["status"]=status
        target["reference"]=reference or target.get("reference")
        target["status_note"]=note or None
        target["updated_by"]=authorized_by
        target["updated_at"]=now
        if status in controlled:
            target["professional_action_approved_by"]=authorized_by
            target["professional_action_approved_at"]=now
        summary["items"]=items
        section["summary"]=summary
        section["updated_by"]=authorized_by
        sections["deliverables"]=section
        events=deepcopy(job.events or [])
        events.append({
            "event_type":"DELIVERABLE_STATUS_CHANGED",
            "reference_id":deliverable_id,
            "summary":target.get("title"),
            "from_status":previous,
            "to_status":status,
            "document_reference":reference,
            "note":note,
            "professional_action_approved":bool(status in controlled),
            "authorized_by":authorized_by,
            "occurred_at":now,
        })
        job.sections=sections
        job.events=events
        self._touch(job)
        self.db.commit(); self.db.refresh(job)
        return job


    def add_document(self, *, job_number, document_id, filename, content_type,
                     category, description, deliverable_id, storage_path,
                     sha256, size_bytes, authorized_by):
        job=self.get(job_number)
        sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("documents") or {
            "reference_id":f"DOC-{job.job_number}","summary":{},"updated_by":authorized_by
        })
        summary=deepcopy(section.get("summary") or {})
        items=deepcopy(summary.get("items") or [])
        if deliverable_id:
            deliverables=((sections.get("deliverables") or {}).get("summary") or {}).get("items") or []
            if not any(d.get("deliverable_id")==deliverable_id for d in deliverables):
                raise ValueError("linked deliverable does not exist")
        now=datetime.now(timezone.utc).isoformat()
        revision={
            "revision":1,"filename":filename,"content_type":content_type,
            "storage_path":storage_path,"sha256":sha256,"size_bytes":size_bytes,
            "description":description,"uploaded_by":authorized_by,"uploaded_at":now,
        }
        item={
            "document_id":document_id,"title":filename,"category":category,
            "deliverable_id":deliverable_id,"current_revision":1,
            "revisions":[revision],"created_by":authorized_by,"created_at":now,
            "updated_at":now,
        }
        items.append(item)
        summary["items"]=items
        section["summary"]=summary; section["updated_by"]=authorized_by
        sections["documents"]=section
        events=deepcopy(job.events or [])
        events.append({
            "event_type":"DOCUMENT_UPLOADED","reference_id":document_id,
            "summary":filename,"category":category,"revision":1,
            "sha256":sha256,"authorized_by":authorized_by,"occurred_at":now,
        })
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job

    def add_document_revision(self, *, job_number, document_id, filename,
                              content_type, description, storage_path,
                              sha256, size_bytes, authorized_by):
        job=self.get(job_number)
        sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("documents") or {})
        summary=deepcopy(section.get("summary") or {})
        items=deepcopy(summary.get("items") or [])
        target=next((d for d in items if d.get("document_id")==document_id),None)
        if target is None:
            raise KeyError(document_id)
        revision=int(target.get("current_revision") or 0)+1
        now=datetime.now(timezone.utc).isoformat()
        target.setdefault("revisions",[]).append({
            "revision":revision,"filename":filename,"content_type":content_type,
            "storage_path":storage_path,"sha256":sha256,"size_bytes":size_bytes,
            "description":description,"uploaded_by":authorized_by,"uploaded_at":now,
        })
        target["title"]=filename; target["current_revision"]=revision
        target["updated_at"]=now; target["updated_by"]=authorized_by
        summary["items"]=items; section["summary"]=summary
        section["updated_by"]=authorized_by; sections["documents"]=section
        events=deepcopy(job.events or [])
        events.append({
            "event_type":"DOCUMENT_REVISION_UPLOADED","reference_id":document_id,
            "summary":filename,"revision":revision,"sha256":sha256,
            "authorized_by":authorized_by,"occurred_at":now,
        })
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job

    def get_document_revision(self, *, job_number, document_id, revision=None):
        job=self.get(job_number)
        items=((((job.sections or {}).get("documents") or {}).get("summary") or {}).get("items") or [])
        target=next((d for d in items if d.get("document_id")==document_id),None)
        if target is None:
            raise KeyError(document_id)
        wanted=int(revision or target.get("current_revision") or 1)
        rev=next((r for r in target.get("revisions",[]) if int(r.get("revision",0))==wanted),None)
        if rev is None:
            raise KeyError(f"{document_id}:{wanted}")
        return target,rev


    def add_review(self, *, job_number, title, reviewer=None, review_date=None,
                   source_document_id=None, authorized_by):
        job=self.get(job_number)
        sections=deepcopy(job.sections or {})
        if source_document_id:
            docs=((((sections.get("documents") or {}).get("summary") or {}).get("items")) or [])
            if not any(d.get("document_id")==source_document_id for d in docs):
                raise ValueError("source document does not exist")
        section=deepcopy(sections.get("reviews") or {
            "reference_id":f"REV-{job.job_number}","summary":{},"updated_by":authorized_by
        })
        summary=deepcopy(section.get("summary") or {})
        items=deepcopy(summary.get("items") or [])
        review_id="REV-"+secrets.token_hex(6).upper()
        now=datetime.now(timezone.utc).isoformat()
        items.append({
            "review_id":review_id,"title":title.strip(),"reviewer":reviewer or None,
            "review_date":review_date or None,"source_document_id":source_document_id,
            "comments":[],"created_by":authorized_by,"created_at":now,"updated_at":now,
        })
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["reviews"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"REVIEW_CREATED","reference_id":review_id,
                       "summary":title.strip(),"authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job

    def add_review_comment(self, *, job_number, review_id, comment_number,
                           comment_text, discipline=None, due_at=None,
                           requires_action=True, authorized_by):
        job=self.get(job_number)
        sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("reviews") or {})
        summary=deepcopy(section.get("summary") or {})
        reviews=deepcopy(summary.get("items") or [])
        review=next((r for r in reviews if r.get("review_id")==review_id),None)
        if review is None: raise KeyError(review_id)
        if any(str(c.get("comment_number")).casefold()==comment_number.strip().casefold()
               for c in review.get("comments",[])):
            raise ValueError("comment number already exists in this review")
        comment_id="RC-"+secrets.token_hex(6).upper()
        now=datetime.now(timezone.utc).isoformat()
        review.setdefault("comments",[]).append({
            "comment_id":comment_id,"comment_number":comment_number.strip(),
            "comment_text":comment_text.strip(),"discipline":discipline or None,
            "due_at":due_at or None,"requires_action":bool(requires_action),
            "status":"OPEN","response_text":None,"resolution_note":None,
            "created_by":authorized_by,"created_at":now,"updated_at":now,
        })
        review["updated_at"]=now
        summary["items"]=reviews; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["reviews"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"REVIEW_COMMENT_CREATED","reference_id":comment_id,
                       "review_id":review_id,"comment_number":comment_number.strip(),
                       "summary":comment_text.strip(),"authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job

    def update_review_comment(self, *, job_number, review_id, comment_id, status,
                              response_text=None, resolution_note=None, authorized_by):
        allowed={"OPEN","IN_PROGRESS","RESPONDED","VERIFIED","NOT_APPLICABLE"}
        if status not in allowed: raise ValueError("unsupported review comment status")
        job=self.get(job_number)
        sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("reviews") or {})
        summary=deepcopy(section.get("summary") or {})
        reviews=deepcopy(summary.get("items") or [])
        review=next((r for r in reviews if r.get("review_id")==review_id),None)
        if review is None: raise KeyError(review_id)
        comment=next((c for c in review.get("comments",[]) if c.get("comment_id")==comment_id),None)
        if comment is None: raise KeyError(comment_id)
        previous=comment.get("status","OPEN")
        now=datetime.now(timezone.utc).isoformat()
        comment["status"]=status
        comment["response_text"]=response_text if response_text is not None else comment.get("response_text")
        comment["resolution_note"]=resolution_note if resolution_note is not None else comment.get("resolution_note")
        comment["updated_by"]=authorized_by; comment["updated_at"]=now
        review["updated_at"]=now
        summary["items"]=reviews; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["reviews"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"REVIEW_COMMENT_STATUS_CHANGED","reference_id":comment_id,
                       "review_id":review_id,"comment_number":comment.get("comment_number"),
                       "from_status":previous,"to_status":status,
                       "summary":response_text or resolution_note or comment.get("comment_text"),
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def add_submission_package(self, *, job_number, title, recipient,
                               submission_type="AGENCY", due_at=None, method=None,
                               deliverable_ids=None, document_ids=None, notes=None,
                               authorized_by):
        job=self.get(job_number)
        sections=deepcopy(job.sections or {})
        deliverables=((((sections.get("deliverables") or {}).get("summary") or {}).get("items")) or [])
        documents=((((sections.get("documents") or {}).get("summary") or {}).get("items")) or [])
        known_deliverables={d.get("deliverable_id") for d in deliverables}
        known_documents={d.get("document_id") for d in documents}
        requested_deliverables=list(dict.fromkeys(deliverable_ids or []))
        requested_documents=list(dict.fromkeys(document_ids or []))
        if any(x not in known_deliverables for x in requested_deliverables):
            raise ValueError("submission package references an unknown deliverable")
        if any(x not in known_documents for x in requested_documents):
            raise ValueError("submission package references an unknown document")
        if not requested_deliverables and not requested_documents:
            raise ValueError("submission package requires at least one deliverable or document")
        section=deepcopy(sections.get("submission_packages") or {
            "reference_id":f"PKG-{job.job_number}","summary":{},"updated_by":authorized_by
        })
        summary=deepcopy(section.get("summary") or {})
        items=deepcopy(summary.get("items") or [])
        package_id="PKG-"+secrets.token_hex(6).upper()
        now=datetime.now(timezone.utc).isoformat()
        items.append({
            "package_id":package_id,"title":title.strip(),"recipient":recipient.strip(),
            "submission_type":submission_type.strip().upper(),"due_at":due_at or None,
            "method":method or None,"deliverable_ids":requested_deliverables,
            "document_ids":requested_documents,"notes":notes or None,
            "status":"PREPARING","submitted_at":None,"reference":None,
            "created_by":authorized_by,"created_at":now,"updated_at":now,
        })
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["submission_packages"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"SUBMISSION_PACKAGE_CREATED","reference_id":package_id,
                       "summary":title.strip(),"recipient":recipient.strip(),
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job

    def change_submission_package_status(self, *, job_number, package_id, status,
                                         submitted_at=None, reference=None, note=None,
                                         professional_approval=False, authorized_by):
        allowed={"PREPARING","READY","SUBMITTED","ACKNOWLEDGED","RETURNED","ACCEPTED","SUPERSEDED"}
        if status not in allowed:
            raise ValueError("unsupported submission package status")
        if status in {"SUBMITTED","ACCEPTED"} and not professional_approval:
            raise ValueError("this submission status requires explicit professional approval")

        # Compatibility route: controlled lifecycle states must use the same gates as
        # the dedicated 14.9-15.5 submission workflow. This prevents the legacy
        # status endpoint from bypassing readiness or external-outcome recording.
        if status in {"READY","SUBMITTED"}:
            job=self.advance_submission_package(
                job_number=job_number,package_id=package_id,status=status,
                authorized_by=authorized_by)
            sections=deepcopy(job.sections or {})
            section=deepcopy(sections.get("submission_packages") or {})
            summary=deepcopy(section.get("summary") or {})
            items=deepcopy(summary.get("items") or [])
            package=next((p for p in items if p.get("package_id")==package_id),None)
            if package is None: raise KeyError(package_id)
            changed=False
            if submitted_at is not None:
                package["submitted_at"]=submitted_at or None; changed=True
            if reference is not None:
                package["reference"]=reference or None; changed=True
            if note is not None:
                package["status_note"]=note or None; changed=True
            if changed:
                package["updated_by"]=authorized_by
                package["updated_at"]=datetime.now(timezone.utc).isoformat()
                summary["items"]=items; section["summary"]=summary
                section["updated_by"]=authorized_by; sections["submission_packages"]=section
                job.sections=sections
                self._touch(job); self.db.commit(); self.db.refresh(job)
            return job

        if status in {"RETURNED","ACCEPTED"}:
            return self.record_submission_outcome(
                job_number=job_number,package_id=package_id,outcome=status,
                reference=reference,notes=note,authorized_by=authorized_by)

        job=self.get(job_number)
        sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("submission_packages") or {})
        summary=deepcopy(section.get("summary") or {})
        items=deepcopy(summary.get("items") or [])
        package=next((p for p in items if p.get("package_id")==package_id),None)
        if package is None: raise KeyError(package_id)
        previous=package.get("status","PREPARING")
        now=datetime.now(timezone.utc).isoformat()
        package["status"]=status
        if submitted_at is not None: package["submitted_at"]=submitted_at or None
        if reference is not None: package["reference"]=reference or None
        if note is not None: package["status_note"]=note or None
        package["updated_by"]=authorized_by; package["updated_at"]=now
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["submission_packages"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"SUBMISSION_PACKAGE_STATUS_CHANGED","reference_id":package_id,
                       "summary":package.get("title"),"from_status":previous,"to_status":status,
                       "recipient":package.get("recipient"),"reference":package.get("reference"),
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def add_dependency(self, *, job_number, title, waiting_on,
                       dependency_type="EXTERNAL", due_at=None, follow_up_at=None,
                       related_review_id=None, related_package_id=None, notes=None,
                       authorized_by):
        job=self.get(job_number)
        sections=deepcopy(job.sections or {})
        if related_review_id:
            reviews=((((sections.get("reviews") or {}).get("summary") or {}).get("items")) or [])
            if not any(r.get("review_id")==related_review_id for r in reviews):
                raise ValueError("dependency references an unknown review")
        if related_package_id:
            packages=((((sections.get("submission_packages") or {}).get("summary") or {}).get("items")) or [])
            if not any(p.get("package_id")==related_package_id for p in packages):
                raise ValueError("dependency references an unknown submission package")
        section=deepcopy(sections.get("dependencies") or {
            "reference_id":f"DEP-{job.job_number}","summary":{},"updated_by":authorized_by
        })
        summary=deepcopy(section.get("summary") or {})
        items=deepcopy(summary.get("items") or [])
        dependency_id="DEP-"+secrets.token_hex(6).upper()
        now=datetime.now(timezone.utc).isoformat()
        items.append({
            "dependency_id":dependency_id,"title":title.strip(),
            "waiting_on":waiting_on.strip(),
            "dependency_type":dependency_type.strip().upper(),
            "due_at":due_at or None,"follow_up_at":follow_up_at or None,
            "related_review_id":related_review_id,
            "related_package_id":related_package_id,
            "notes":notes or None,"status":"WAITING",
            "resolution_note":None,
            "created_by":authorized_by,"created_at":now,"updated_at":now,
        })
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["dependencies"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"DEPENDENCY_CREATED","reference_id":dependency_id,
                       "summary":title.strip(),"waiting_on":waiting_on.strip(),
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job

    def update_dependency(self, *, job_number, dependency_id, status,
                          due_at=None, follow_up_at=None, resolution_note=None,
                          authorized_by):
        allowed={"WAITING","FOLLOW_UP_DUE","RECEIVED","RESOLVED","CANCELLED"}
        if status not in allowed:
            raise ValueError("unsupported dependency status")
        job=self.get(job_number)
        sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("dependencies") or {})
        summary=deepcopy(section.get("summary") or {})
        items=deepcopy(summary.get("items") or [])
        dependency=next((d for d in items if d.get("dependency_id")==dependency_id),None)
        if dependency is None:
            raise KeyError(dependency_id)
        previous=dependency.get("status","WAITING")
        now=datetime.now(timezone.utc).isoformat()
        dependency["status"]=status
        if due_at is not None: dependency["due_at"]=due_at or None
        if follow_up_at is not None: dependency["follow_up_at"]=follow_up_at or None
        if resolution_note is not None: dependency["resolution_note"]=resolution_note or None
        dependency["updated_by"]=authorized_by; dependency["updated_at"]=now
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["dependencies"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"DEPENDENCY_STATUS_CHANGED","reference_id":dependency_id,
                       "summary":dependency.get("title"),"waiting_on":dependency.get("waiting_on"),
                       "from_status":previous,"to_status":status,
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def add_action_item(self, *, job_number, title, action_type="ENGINEERING",
                        owner=None, due_at=None, priority="NORMAL",
                        related_review_id=None, related_package_id=None,
                        related_dependency_id=None, notes=None, authorized_by):
        job=self.get(job_number)
        sections=deepcopy(job.sections or {})
        if related_review_id:
            reviews=((((sections.get("reviews") or {}).get("summary") or {}).get("items")) or [])
            if not any(r.get("review_id")==related_review_id for r in reviews):
                raise ValueError("action item references an unknown review")
        if related_package_id:
            packages=((((sections.get("submission_packages") or {}).get("summary") or {}).get("items")) or [])
            if not any(p.get("package_id")==related_package_id for p in packages):
                raise ValueError("action item references an unknown submission package")
        if related_dependency_id:
            dependencies=((((sections.get("dependencies") or {}).get("summary") or {}).get("items")) or [])
            if not any(d.get("dependency_id")==related_dependency_id for d in dependencies):
                raise ValueError("action item references an unknown dependency")
        allowed_priority={"LOW","NORMAL","HIGH","URGENT"}
        priority=priority.strip().upper()
        if priority not in allowed_priority:
            raise ValueError("unsupported action item priority")
        section=deepcopy(sections.get("action_items") or {
            "reference_id":f"ACT-{job.job_number}","summary":{},"updated_by":authorized_by
        })
        summary=deepcopy(section.get("summary") or {})
        items=deepcopy(summary.get("items") or [])
        action_id="ACT-"+secrets.token_hex(6).upper()
        now=datetime.now(timezone.utc).isoformat()
        items.append({
            "action_id":action_id,"title":title.strip(),
            "action_type":action_type.strip().upper(),"owner":owner or None,
            "due_at":due_at or None,"priority":priority,"status":"OPEN",
            "related_review_id":related_review_id,
            "related_package_id":related_package_id,
            "related_dependency_id":related_dependency_id,
            "notes":notes or None,"completion_note":None,
            "created_by":authorized_by,"created_at":now,"updated_at":now,
        })
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["action_items"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"ACTION_ITEM_CREATED","reference_id":action_id,
                       "summary":title.strip(),"owner":owner or None,
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job

    def update_action_item(self, *, job_number, action_id, status,
                           owner=None, due_at=None, priority=None,
                           completion_note=None, authorized_by):
        allowed_status={"OPEN","IN_PROGRESS","BLOCKED","DONE","CANCELLED"}
        if status not in allowed_status:
            raise ValueError("unsupported action item status")
        if priority is not None:
            priority=priority.strip().upper()
            if priority not in {"LOW","NORMAL","HIGH","URGENT"}:
                raise ValueError("unsupported action item priority")
        job=self.get(job_number)
        sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("action_items") or {})
        summary=deepcopy(section.get("summary") or {})
        items=deepcopy(summary.get("items") or [])
        item=next((a for a in items if a.get("action_id")==action_id),None)
        if item is None: raise KeyError(action_id)
        previous=item.get("status","OPEN")
        now=datetime.now(timezone.utc).isoformat()
        item["status"]=status
        if owner is not None: item["owner"]=owner or None
        if due_at is not None: item["due_at"]=due_at or None
        if priority is not None: item["priority"]=priority
        if completion_note is not None: item["completion_note"]=completion_note or None
        item["updated_by"]=authorized_by; item["updated_at"]=now
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["action_items"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"ACTION_ITEM_STATUS_CHANGED","reference_id":action_id,
                       "summary":item.get("title"),"from_status":previous,"to_status":status,
                       "owner":item.get("owner"),"authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def project_lifecycle_audit_acknowledgements(self, *, job_number):
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        items=deepcopy((((sections.get("lifecycle_audit_acknowledgements") or {}).get("summary") or {}).get("items")) or [])
        return items


    def acknowledge_project_lifecycle_audit(self, *, job_number, acknowledgement_notes, acknowledged_by):
        if not acknowledgement_notes.strip():
            raise ValueError("lifecycle audit acknowledgement requires notes")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        now=datetime.now(timezone.utc).isoformat()
        completion=deepcopy(((sections.get("project_completion") or {}).get("summary") or {}))
        certification=deepcopy(completion.get("certification"))
        post_items=deepcopy((((sections.get("post_completion_work") or {}).get("summary") or {}).get("items")) or [])
        snapshot={
            "completion_status":str((certification or {}).get("status","")).upper() or "NOT_CERTIFIED",
            "certification_count":len(completion.get("certification_history") or []) + (1 if certification else 0),
            "reopen_count":len(completion.get("reopen_history") or []),
            "post_completion_open_count":sum(1 for x in post_items if str(x.get("status","OPEN")).upper() not in {"RESOLVED","CANCELLED"}),
        }
        section=deepcopy(sections.get("lifecycle_audit_acknowledgements") or {
            "reference_id":f"LIFECYCLE-AUDIT-{job.job_number}","summary":{"items":[]},"updated_by":acknowledged_by})
        summary=deepcopy(section.get("summary") or {}); items=deepcopy(summary.get("items") or [])
        acknowledgement_id="LAA-"+secrets.token_hex(6).upper()
        items.append({"acknowledgement_id":acknowledgement_id,
                      "acknowledgement_notes":acknowledgement_notes.strip(),
                      "acknowledged_by":acknowledged_by,"acknowledged_at":now,
                      "audit_snapshot":snapshot})
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=acknowledged_by
        sections["lifecycle_audit_acknowledgements"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"PROJECT_LIFECYCLE_AUDIT_ACKNOWLEDGED",
                       "reference_id":acknowledgement_id,
                       "summary":acknowledgement_notes.strip(),
                       "authorized_by":acknowledged_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def project_lifecycle_audit(self, *, job_number):
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        events=deepcopy(job.events or [])
        completion=deepcopy(((sections.get("project_completion") or {}).get("summary") or {}))
        post_items=deepcopy((((sections.get("post_completion_work") or {}).get("summary") or {}).get("items")) or [])
        closure_items=deepcopy((((sections.get("project_closure") or {}).get("summary") or {}).get("items")) or [])
        archive_items=deepcopy((((sections.get("project_archive") or {}).get("summary") or {}).get("items")) or [])
        closeout_items=deepcopy((((sections.get("closeout") or {}).get("summary") or {}).get("items")) or [])
        punch_items=deepcopy((((sections.get("punch_list") or {}).get("summary") or {}).get("items")) or [])
        certification=deepcopy(completion.get("certification"))
        return {
            "job_number":job.job_number,
            "completion_certification":certification,
            "certification_history":deepcopy(completion.get("certification_history") or []),
            "reopen_history":deepcopy(completion.get("reopen_history") or []),
            "post_completion_work":post_items,
            "project_closure":closure_items,
            "project_archive":archive_items,
            "closeout":closeout_items,
            "punch_list":punch_items,
            "acknowledgements":deepcopy((((sections.get("lifecycle_audit_acknowledgements") or {}).get("summary") or {}).get("items")) or []),
            "lifecycle_events":[e for e in events if str(e.get("event_type","")).upper() in {
                "PROJECT_COMPLETION_CERTIFIED","PROJECT_REOPENED_AFTER_COMPLETION",
                "POST_COMPLETION_WORK_OPENED","POST_COMPLETION_WORK_STATUS_CHANGED",
                "PROJECT_LIFECYCLE_AUDIT_ACKNOWLEDGED"
            }],
        }


    def add_post_completion_work(self, *, job_number, title, work_type="OTHER", description, authorized_by):
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        completion=deepcopy(sections.get("project_completion") or {})
        completion_summary=deepcopy(completion.get("summary") or {})
        certification=deepcopy(completion_summary.get("certification"))
        if not certification or str(certification.get("status","")).upper()!="REOPENED":
            raise ValueError("post-completion work requires an explicitly reopened project")
        work_type=work_type.strip().upper()
        if work_type not in {"CLIENT_REQUEST","CORRECTION","WARRANTY","AGENCY_RESPONSE","ADMINISTRATIVE","OTHER"}:
            raise ValueError("unsupported post-completion work type")
        if not description.strip():
            raise ValueError("post-completion work requires a description")
        now=datetime.now(timezone.utc).isoformat()
        section=deepcopy(sections.get("post_completion_work") or {
            "reference_id":f"POST-COMPLETION-{job.job_number}","summary":{"items":[]},"updated_by":authorized_by})
        summary=deepcopy(section.get("summary") or {}); items=deepcopy(summary.get("items") or [])
        item_id="PCW-"+secrets.token_hex(6).upper()
        item={"item_id":item_id,"title":title.strip(),"work_type":work_type,
              "description":description.strip(),"status":"OPEN","resolution_notes":None,
              "created_by":authorized_by,"created_at":now,"updated_by":authorized_by,"updated_at":now}
        items.append(item); summary["items"]=items
        section["summary"]=summary; section["updated_by"]=authorized_by
        sections["post_completion_work"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"POST_COMPLETION_WORK_OPENED","reference_id":item_id,
                       "summary":title.strip(),"authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job

    def update_post_completion_work(self, *, job_number, item_id, status, resolution_notes=None, authorized_by):
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("post_completion_work") or {})
        summary=deepcopy(section.get("summary") or {}); items=deepcopy(summary.get("items") or [])
        target=next((x for x in items if x.get("item_id")==item_id),None)
        if target is None:
            raise ValueError("post-completion work item not found")
        status=status.strip().upper()
        if status not in {"OPEN","IN_PROGRESS","RESOLVED","CANCELLED"}:
            raise ValueError("unsupported post-completion work status")
        if status=="RESOLVED" and not (resolution_notes or "").strip():
            raise ValueError("resolved post-completion work requires resolution notes")
        now=datetime.now(timezone.utc).isoformat()
        target["status"]=status
        if resolution_notes is not None: target["resolution_notes"]=resolution_notes.strip() or None
        target["updated_by"]=authorized_by; target["updated_at"]=now
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["post_completion_work"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"POST_COMPLETION_WORK_STATUS_CHANGED","reference_id":item_id,
                       "summary":status,"authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def reopen_completed_project(self, *, job_number, reason, authorized_by):
        if not reason.strip():
            raise ValueError("project reopening requires a reason")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("project_completion") or {})
        summary=deepcopy(section.get("summary") or {})
        certification=deepcopy(summary.get("certification"))
        if not certification:
            raise ValueError("only a certified project can be reopened")
        if str(certification.get("status","")).upper()!="CERTIFIED":
            raise ValueError("project completion certification is not active")
        now=datetime.now(timezone.utc).isoformat()
        certification["status"]="REOPENED"
        certification["reopened_by"]=authorized_by
        certification["reopened_at"]=now
        certification["reopen_reason"]=reason.strip()
        summary["certification"]=certification
        history=deepcopy(summary.get("reopen_history") or [])
        history.append({"reason":reason.strip(),"authorized_by":authorized_by,"occurred_at":now})
        summary["reopen_history"]=history
        section["summary"]=summary; section["updated_by"]=authorized_by
        sections["project_completion"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"PROJECT_REOPENED_AFTER_COMPLETION",
                       "reference_id":certification.get("certification_id"),
                       "summary":reason.strip(),
                       "authorized_by":authorized_by,
                       "occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def certify_project_completion(self, *, job_number, certification_type="PROJECT_COMPLETE",
                                   completion_date, certification_notes, authorized_by):
        certification_type=certification_type.strip().upper()
        if certification_type not in {"PROJECT_COMPLETE","ADMINISTRATIVELY_CLOSED"}:
            raise ValueError("unsupported project completion certification type")
        if not certification_notes.strip():
            raise ValueError("project completion certification requires notes")
        job=self.get(job_number); sections=deepcopy(job.sections or {})

        closure_items=((((sections.get("project_closure") or {}).get("summary") or {}).get("items")) or [])
        unresolved_closure=[x for x in closure_items
                            if str(x.get("status","OPEN")).upper() not in {"COMPLETE","WAIVED"}]
        if unresolved_closure:
            raise ValueError("project completion certification requires all project closure items complete or waived")

        archive_items=((((sections.get("project_archive") or {}).get("summary") or {}).get("items")) or [])
        unresolved_archive=[x for x in archive_items
                            if str(x.get("status","PENDING")).upper() not in {"ARCHIVED","EXEMPT"}]
        if unresolved_archive:
            raise ValueError("project completion certification requires all archive records archived or exempt")

        closeout_items=((((sections.get("closeout") or {}).get("summary") or {}).get("items")) or [])
        unresolved_closeout=[x for x in closeout_items
                             if str(x.get("status","OPEN")).upper() not in {"COMPLETE","WAIVED"}]
        if unresolved_closeout:
            raise ValueError("project completion certification requires all closeout items complete or waived")

        punch_items=((((sections.get("punch_list") or {}).get("summary") or {}).get("items")) or [])
        unresolved_punch=[x for x in punch_items
                          if str(x.get("status","OPEN")).upper() not in {"COMPLETE","WAIVED","CANCELLED"}]
        if unresolved_punch:
            raise ValueError("project completion certification requires all punch-list items resolved")

        post_completion_items=((((sections.get("post_completion_work") or {}).get("summary") or {}).get("items")) or [])
        unresolved_post_completion=[x for x in post_completion_items
                                   if str(x.get("status","OPEN")).upper() not in {"RESOLVED","CANCELLED"}]
        if unresolved_post_completion:
            raise ValueError("project completion certification requires all post-completion work resolved or cancelled")

        now=datetime.now(timezone.utc).isoformat()
        section=deepcopy(sections.get("project_completion") or {
            "reference_id":f"COMPLETION-{job.job_number}","summary":{},"updated_by":authorized_by})
        summary=deepcopy(section.get("summary") or {})
        existing=summary.get("certification")
        if existing and str(existing.get("status","")).upper()=="CERTIFIED":
            raise ValueError("project completion has already been certified")
        prior_certifications=deepcopy(summary.get("certification_history") or [])
        if existing:
            prior_certifications.append(deepcopy(existing))
            summary["certification_history"]=prior_certifications
        certification_id="PCC-"+secrets.token_hex(6).upper()
        certification={"certification_id":certification_id,
                       "certification_type":certification_type,
                       "status":"CERTIFIED",
                       "completion_date":completion_date,
                       "certification_notes":certification_notes.strip(),
                       "certified_by":authorized_by,
                       "certified_at":now}
        summary["certification"]=certification
        section["summary"]=summary; section["updated_by"]=authorized_by
        sections["project_completion"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"PROJECT_COMPLETION_CERTIFIED",
                       "reference_id":certification_id,
                       "summary":certification_type,
                       "completion_date":completion_date,
                       "authorized_by":authorized_by,
                       "occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def add_project_closure_item(self, *, job_number, title, closure_type="OTHER",
                                 responsible_party=None, due_at=None, notes=None, authorized_by):
        closure_type=closure_type.strip().upper()
        allowed={"FINAL_INVOICE","CONSULTANT_CLOSEOUT","CLIENT_ACCEPTANCE","PERMIT_CLOSEOUT",
                 "RECORD_TRANSFER","LESSONS_LEARNED","INTERNAL_ADMIN","OTHER"}
        if closure_type not in allowed:
            raise ValueError("unsupported project closure item type")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("project_closure") or {
            "reference_id":f"CLOSURE-{job.job_number}","summary":{},"updated_by":authorized_by})
        summary=deepcopy(section.get("summary") or {}); items=deepcopy(summary.get("items") or [])
        closure_id="PC-"+secrets.token_hex(6).upper()
        now=datetime.now(timezone.utc).isoformat()
        items.append({"closure_id":closure_id,"title":title.strip(),"closure_type":closure_type,
                      "status":"OPEN","responsible_party":responsible_party or None,
                      "due_at":due_at or None,"notes":notes.strip() if notes else None,
                      "completion_notes":None,"created_by":authorized_by,
                      "created_at":now,"updated_at":now})
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["project_closure"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"PROJECT_CLOSURE_ITEM_CREATED","reference_id":closure_id,
                       "summary":title.strip(),"closure_type":closure_type,
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job

    def update_project_closure_item(self, *, job_number, closure_id, status,
                                    completion_notes=None, responsible_party=None,
                                    due_at=None, authorized_by):
        status=status.strip().upper()
        if status not in {"OPEN","IN_PROGRESS","READY_FOR_REVIEW","COMPLETE","WAIVED"}:
            raise ValueError("unsupported project closure item status")
        if status in {"COMPLETE","WAIVED"} and not (completion_notes and completion_notes.strip()):
            raise ValueError("final project closure status requires completion notes")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("project_closure") or {})
        summary=deepcopy(section.get("summary") or {}); items=deepcopy(summary.get("items") or [])
        item=next((x for x in items if x.get("closure_id")==closure_id),None)
        if item is None: raise KeyError(closure_id)
        previous=str(item.get("status","OPEN")).upper()
        now=datetime.now(timezone.utc).isoformat()
        item["status"]=status
        if completion_notes is not None: item["completion_notes"]=completion_notes.strip() or None
        if responsible_party is not None: item["responsible_party"]=responsible_party or None
        if due_at is not None: item["due_at"]=due_at or None
        item["updated_by"]=authorized_by; item["updated_at"]=now
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["project_closure"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"PROJECT_CLOSURE_ITEM_STATUS_CHANGED","reference_id":closure_id,
                       "summary":item.get("title"),"from_status":previous,"to_status":status,
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def add_archive_record(self, *, job_number, title, record_type="OTHER",
                           retention_until=None, storage_reference=None, notes=None, authorized_by):
        record_type=record_type.strip().upper()
        allowed={"CONTRACT","DRAWING","SPECIFICATION","CALCULATION","REPORT","PERMIT",
                 "CORRESPONDENCE","CLOSEOUT","WARRANTY","OTHER"}
        if record_type not in allowed:
            raise ValueError("unsupported archive record type")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("project_archive") or {
            "reference_id":f"ARCHIVE-{job.job_number}","summary":{},"updated_by":authorized_by})
        summary=deepcopy(section.get("summary") or {}); items=deepcopy(summary.get("items") or [])
        archive_id="AR-"+secrets.token_hex(6).upper()
        now=datetime.now(timezone.utc).isoformat()
        items.append({"archive_id":archive_id,"title":title.strip(),"record_type":record_type,
                      "status":"PENDING","retention_until":retention_until or None,
                      "storage_reference":storage_reference or None,
                      "notes":notes.strip() if notes else None,"verification_notes":None,
                      "created_by":authorized_by,"created_at":now,"updated_at":now})
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["project_archive"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"ARCHIVE_RECORD_CREATED","reference_id":archive_id,
                       "summary":title.strip(),"record_type":record_type,
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job

    def update_archive_record(self, *, job_number, archive_id, status, verification_notes=None,
                              retention_until=None, storage_reference=None, authorized_by):
        status=status.strip().upper()
        if status not in {"PENDING","READY_FOR_VERIFICATION","VERIFIED","ARCHIVED","EXEMPT"}:
            raise ValueError("unsupported archive record status")
        if status in {"VERIFIED","ARCHIVED","EXEMPT"} and not (verification_notes and verification_notes.strip()):
            raise ValueError("final archive status requires verification notes")
        if status=="ARCHIVED" and not (storage_reference and storage_reference.strip()):
            raise ValueError("archived record requires storage reference")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("project_archive") or {})
        summary=deepcopy(section.get("summary") or {}); items=deepcopy(summary.get("items") or [])
        item=next((x for x in items if x.get("archive_id")==archive_id),None)
        if item is None: raise KeyError(archive_id)
        previous=str(item.get("status","PENDING")).upper()
        now=datetime.now(timezone.utc).isoformat()
        item["status"]=status
        if verification_notes is not None: item["verification_notes"]=verification_notes.strip() or None
        if retention_until is not None: item["retention_until"]=retention_until or None
        if storage_reference is not None: item["storage_reference"]=storage_reference.strip() or None
        item["updated_by"]=authorized_by; item["updated_at"]=now
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["project_archive"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"ARCHIVE_RECORD_STATUS_CHANGED","reference_id":archive_id,
                       "summary":item.get("title"),"from_status":previous,"to_status":status,
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def add_warranty_issue(self, *, job_number, title, description, location=None,
                           responsible_party=None, priority="NORMAL",
                           warranty_expires_at=None, authorized_by):
        priority=priority.strip().upper()
        if priority not in {"LOW","NORMAL","HIGH","URGENT"}:
            raise ValueError("unsupported warranty issue priority")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("warranty_issues") or {
            "reference_id":f"WARRANTY-{job.job_number}","summary":{},"updated_by":authorized_by})
        summary=deepcopy(section.get("summary") or {}); items=deepcopy(summary.get("items") or [])
        issue_id="WI-"+secrets.token_hex(6).upper()
        now=datetime.now(timezone.utc).isoformat()
        items.append({"issue_id":issue_id,"title":title.strip(),"description":description.strip(),
                      "location":location or None,"responsible_party":responsible_party or None,
                      "priority":priority,"status":"OPEN",
                      "warranty_expires_at":warranty_expires_at or None,
                      "resolution_notes":None,"created_by":authorized_by,
                      "created_at":now,"updated_at":now})
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["warranty_issues"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"WARRANTY_ISSUE_CREATED","reference_id":issue_id,
                       "summary":title.strip(),"priority":priority,
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job

    def update_warranty_issue(self, *, job_number, issue_id, status, resolution_notes=None,
                              responsible_party=None, priority=None,
                              warranty_expires_at=None, authorized_by):
        status=status.strip().upper()
        if status not in {"OPEN","IN_PROGRESS","READY_FOR_VERIFICATION","RESOLVED","CANCELLED"}:
            raise ValueError("unsupported warranty issue status")
        if status=="RESOLVED" and not (resolution_notes and resolution_notes.strip()):
            raise ValueError("resolving warranty issue requires resolution notes")
        if priority is not None:
            priority=priority.strip().upper()
            if priority not in {"LOW","NORMAL","HIGH","URGENT"}:
                raise ValueError("unsupported warranty issue priority")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("warranty_issues") or {})
        summary=deepcopy(section.get("summary") or {}); items=deepcopy(summary.get("items") or [])
        item=next((x for x in items if x.get("issue_id")==issue_id),None)
        if item is None: raise KeyError(issue_id)
        previous=str(item.get("status","OPEN")).upper()
        now=datetime.now(timezone.utc).isoformat()
        item["status"]=status
        if resolution_notes is not None: item["resolution_notes"]=resolution_notes.strip() or None
        if responsible_party is not None: item["responsible_party"]=responsible_party or None
        if priority is not None: item["priority"]=priority
        if warranty_expires_at is not None: item["warranty_expires_at"]=warranty_expires_at or None
        item["updated_by"]=authorized_by; item["updated_at"]=now
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["warranty_issues"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"WARRANTY_ISSUE_STATUS_CHANGED","reference_id":issue_id,
                       "summary":item.get("title"),"from_status":previous,"to_status":status,
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def add_closeout_item(self, *, job_number, title, item_type="OTHER",
                          responsible_party=None, due_at=None, notes=None, authorized_by):
        item_type=item_type.strip().upper()
        allowed_types={"AS_BUILT","O_AND_M","WARRANTY","CERTIFICATE","TRAINING","FINAL_DOCUMENT","OTHER"}
        if item_type not in allowed_types:
            raise ValueError("unsupported closeout item type")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("closeout") or {
            "reference_id":f"CLOSEOUT-{job.job_number}","summary":{},"updated_by":authorized_by})
        summary=deepcopy(section.get("summary") or {}); items=deepcopy(summary.get("items") or [])
        closeout_id="CL-"+secrets.token_hex(6).upper()
        now=datetime.now(timezone.utc).isoformat()
        items.append({"closeout_id":closeout_id,"title":title.strip(),"item_type":item_type,
                      "status":"OPEN","responsible_party":responsible_party or None,
                      "due_at":due_at or None,"notes":notes.strip() if notes else None,
                      "completion_notes":None,"created_by":authorized_by,
                      "created_at":now,"updated_at":now})
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["closeout"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"CLOSEOUT_ITEM_CREATED","reference_id":closeout_id,
                       "summary":title.strip(),"item_type":item_type,
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job

    def update_closeout_item(self, *, job_number, closeout_id, status, completion_notes=None,
                             responsible_party=None, due_at=None, authorized_by):
        status=status.strip().upper()
        if status not in {"OPEN","IN_PROGRESS","READY_FOR_REVIEW","ACCEPTED","WAIVED"}:
            raise ValueError("unsupported closeout item status")
        if status in {"ACCEPTED","WAIVED"} and not (completion_notes and completion_notes.strip()):
            raise ValueError("final closeout status requires completion notes")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("closeout") or {}); summary=deepcopy(section.get("summary") or {})
        items=deepcopy(summary.get("items") or [])
        item=next((x for x in items if x.get("closeout_id")==closeout_id),None)
        if item is None: raise KeyError(closeout_id)
        previous=str(item.get("status","OPEN")).upper()
        now=datetime.now(timezone.utc).isoformat()
        item["status"]=status
        if completion_notes is not None: item["completion_notes"]=completion_notes.strip() or None
        if responsible_party is not None: item["responsible_party"]=responsible_party or None
        if due_at is not None: item["due_at"]=due_at or None
        item["updated_by"]=authorized_by; item["updated_at"]=now
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["closeout"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"CLOSEOUT_ITEM_STATUS_CHANGED","reference_id":closeout_id,
                       "summary":item.get("title"),"from_status":previous,"to_status":status,
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def add_punch_item(self, *, job_number, title, description, location=None,
                       responsible_party=None, priority="NORMAL", due_at=None, authorized_by):
        priority=priority.strip().upper()
        if priority not in {"LOW","NORMAL","HIGH","URGENT"}:
            raise ValueError("unsupported punch item priority")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("punch_list") or {
            "reference_id":f"PUNCH-{job.job_number}","summary":{},"updated_by":authorized_by})
        summary=deepcopy(section.get("summary") or {}); items=deepcopy(summary.get("items") or [])
        punch_id="PI-"+secrets.token_hex(6).upper()
        now=datetime.now(timezone.utc).isoformat()
        items.append({"punch_id":punch_id,"title":title.strip(),"description":description.strip(),
                      "location":location or None,"responsible_party":responsible_party or None,
                      "priority":priority,"status":"OPEN","due_at":due_at or None,
                      "resolution_notes":None,"created_by":authorized_by,
                      "created_at":now,"updated_at":now})
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["punch_list"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"PUNCH_ITEM_CREATED","reference_id":punch_id,
                       "summary":title.strip(),"priority":priority,
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job

    def update_punch_item(self, *, job_number, punch_id, status, resolution_notes=None,
                          responsible_party=None, priority=None, due_at=None, authorized_by):
        status=status.strip().upper()
        if status not in {"OPEN","IN_PROGRESS","READY_FOR_VERIFICATION","CLOSED","CANCELLED"}:
            raise ValueError("unsupported punch item status")
        if status=="CLOSED" and not (resolution_notes and resolution_notes.strip()):
            raise ValueError("closing punch item requires resolution notes")
        if priority is not None:
            priority=priority.strip().upper()
            if priority not in {"LOW","NORMAL","HIGH","URGENT"}:
                raise ValueError("unsupported punch item priority")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("punch_list") or {}); summary=deepcopy(section.get("summary") or {})
        items=deepcopy(summary.get("items") or [])
        item=next((x for x in items if x.get("punch_id")==punch_id),None)
        if item is None: raise KeyError(punch_id)
        previous=str(item.get("status","OPEN")).upper()
        now=datetime.now(timezone.utc).isoformat()
        item["status"]=status
        if resolution_notes is not None: item["resolution_notes"]=resolution_notes.strip() or None
        if responsible_party is not None: item["responsible_party"]=responsible_party or None
        if priority is not None: item["priority"]=priority
        if due_at is not None: item["due_at"]=due_at or None
        item["updated_by"]=authorized_by; item["updated_at"]=now
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["punch_list"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"PUNCH_ITEM_STATUS_CHANGED","reference_id":punch_id,
                       "summary":item.get("title"),"from_status":previous,"to_status":status,
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def add_change_order(self, *, job_number, title, description, requested_by=None,
                         cost_impact=None, schedule_impact=None, authorized_by):
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("change_orders") or {
            "reference_id":f"CHANGE-{job.job_number}","summary":{},"updated_by":authorized_by})
        summary=deepcopy(section.get("summary") or {}); items=deepcopy(summary.get("items") or [])
        change_id="CO-"+secrets.token_hex(6).upper()
        now=datetime.now(timezone.utc).isoformat()
        items.append({"change_id":change_id,"title":title.strip(),"description":description.strip(),
                      "status":"PROPOSED","requested_by":requested_by or None,
                      "cost_impact":cost_impact or None,"schedule_impact":schedule_impact or None,
                      "decision_notes":None,"decided_by":None,"created_by":authorized_by,
                      "created_at":now,"updated_at":now})
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["change_orders"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"CHANGE_ORDER_CREATED","reference_id":change_id,
                       "summary":title.strip(),"authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job

    def update_change_order(self, *, job_number, change_id, status, decision_notes=None,
                            decided_by=None, cost_impact=None, schedule_impact=None, authorized_by):
        status=status.strip().upper()
        allowed={"PROPOSED","UNDER_REVIEW","APPROVED","REJECTED","VOID","IMPLEMENTED"}
        if status not in allowed:
            raise ValueError("unsupported change order status")
        if status in {"APPROVED","REJECTED","VOID","IMPLEMENTED"} and not (decision_notes and decision_notes.strip()):
            raise ValueError("final change order status requires decision notes")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("change_orders") or {}); summary=deepcopy(section.get("summary") or {})
        items=deepcopy(summary.get("items") or [])
        item=next((x for x in items if x.get("change_id")==change_id),None)
        if item is None: raise KeyError(change_id)
        previous=str(item.get("status","PROPOSED")).upper()
        now=datetime.now(timezone.utc).isoformat()
        item["status"]=status
        if decision_notes is not None: item["decision_notes"]=decision_notes.strip() or None
        if decided_by is not None: item["decided_by"]=decided_by or None
        if cost_impact is not None: item["cost_impact"]=cost_impact or None
        if schedule_impact is not None: item["schedule_impact"]=schedule_impact or None
        item["updated_by"]=authorized_by; item["updated_at"]=now
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["change_orders"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"CHANGE_ORDER_STATUS_CHANGED","reference_id":change_id,
                       "summary":item.get("title"),"from_status":previous,"to_status":status,
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def add_submittal(self, *, job_number, title, submittal_type="SHOP_DRAWING",
                      submitted_by=None, due_at=None, notes=None, authorized_by):
        submittal_type=submittal_type.strip().upper()
        if submittal_type not in {"SHOP_DRAWING","PRODUCT_DATA","SAMPLE","CALCULATION","CERTIFICATE","OTHER"}:
            raise ValueError("unsupported submittal type")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("submittals") or {
            "reference_id":f"SUBMITTAL-{job.job_number}","summary":{},"updated_by":authorized_by})
        summary=deepcopy(section.get("summary") or {}); items=deepcopy(summary.get("items") or [])
        submittal_id="SUB-"+secrets.token_hex(6).upper()
        now=datetime.now(timezone.utc).isoformat()
        items.append({"submittal_id":submittal_id,"title":title.strip(),
                      "submittal_type":submittal_type,"status":"RECEIVED",
                      "submitted_by":submitted_by or None,"due_at":due_at or None,
                      "notes":notes or None,"review_notes":None,"reviewed_by":None,
                      "created_by":authorized_by,"created_at":now,"updated_at":now})
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["submittals"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"SUBMITTAL_CREATED","reference_id":submittal_id,
                       "summary":title.strip(),"submittal_type":submittal_type,
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job

    def review_submittal(self, *, job_number, submittal_id, status,
                         review_notes=None, reviewed_by=None, authorized_by):
        status=status.strip().upper()
        allowed={"RECEIVED","UNDER_REVIEW","APPROVED","APPROVED_AS_NOTED","REVISE_RESUBMIT","REJECTED","CLOSED"}
        if status not in allowed:
            raise ValueError("unsupported submittal review status")
        if status in {"APPROVED","APPROVED_AS_NOTED","REVISE_RESUBMIT","REJECTED","CLOSED"} and not (review_notes and review_notes.strip()):
            raise ValueError("final submittal review status requires review notes")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("submittals") or {}); summary=deepcopy(section.get("summary") or {})
        items=deepcopy(summary.get("items") or [])
        item=next((x for x in items if x.get("submittal_id")==submittal_id),None)
        if item is None: raise KeyError(submittal_id)
        previous=str(item.get("status","RECEIVED")).upper()
        now=datetime.now(timezone.utc).isoformat()
        item["status"]=status
        if review_notes is not None: item["review_notes"]=review_notes.strip() or None
        if reviewed_by is not None: item["reviewed_by"]=reviewed_by or None
        item["updated_by"]=authorized_by; item["updated_at"]=now
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["submittals"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"SUBMITTAL_REVIEW_STATUS_CHANGED","reference_id":submittal_id,
                       "summary":item.get("title"),"from_status":previous,"to_status":status,
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def add_rfi(self, *, job_number, subject, question, requested_from=None,
                due_at=None, priority="NORMAL", authorized_by):
        priority=priority.strip().upper()
        if priority not in {"LOW","NORMAL","HIGH","URGENT"}:
            raise ValueError("unsupported RFI priority")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("rfis") or {
            "reference_id":f"RFI-{job.job_number}","summary":{},"updated_by":authorized_by})
        summary=deepcopy(section.get("summary") or {}); items=deepcopy(summary.get("items") or [])
        rfi_id="RFI-"+secrets.token_hex(6).upper()
        now=datetime.now(timezone.utc).isoformat()
        items.append({"rfi_id":rfi_id,"subject":subject.strip(),"question":question.strip(),
                      "requested_from":requested_from or None,"due_at":due_at or None,
                      "priority":priority,"status":"OPEN","response":None,"responded_by":None,
                      "created_by":authorized_by,"created_at":now,"updated_at":now})
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["rfis"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"RFI_CREATED","reference_id":rfi_id,"summary":subject.strip(),
                       "priority":priority,"authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job

    def update_rfi(self, *, job_number, rfi_id, status, response=None, responded_by=None,
                   due_at=None, priority=None, authorized_by):
        status=status.strip().upper()
        if status not in {"OPEN","PENDING_RESPONSE","ANSWERED","CLOSED","CANCELLED"}:
            raise ValueError("unsupported RFI status")
        if priority is not None:
            priority=priority.strip().upper()
            if priority not in {"LOW","NORMAL","HIGH","URGENT"}:
                raise ValueError("unsupported RFI priority")
        if status in {"ANSWERED","CLOSED"} and not (response and response.strip()):
            raise ValueError("answered or closed RFI requires a recorded response")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("rfis") or {}); summary=deepcopy(section.get("summary") or {})
        items=deepcopy(summary.get("items") or [])
        item=next((x for x in items if x.get("rfi_id")==rfi_id),None)
        if item is None: raise KeyError(rfi_id)
        previous=str(item.get("status","OPEN")).upper()
        now=datetime.now(timezone.utc).isoformat()
        item["status"]=status
        if response is not None: item["response"]=response.strip() or None
        if responded_by is not None: item["responded_by"]=responded_by or None
        if due_at is not None: item["due_at"]=due_at or None
        if priority is not None: item["priority"]=priority
        item["updated_by"]=authorized_by; item["updated_at"]=now
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["rfis"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"RFI_STATUS_CHANGED","reference_id":rfi_id,
                       "summary":item.get("subject"),"from_status":previous,"to_status":status,
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def add_field_report(self, *, job_number, title, report_type="SITE_VISIT",
                         observed_at=None, location=None, observations,
                         follow_up_required=False, authorized_by):
        report_type=report_type.strip().upper()
        if report_type not in {"SITE_VISIT","INSPECTION","CONSTRUCTION_OBSERVATION","EXISTING_CONDITIONS","OTHER"}:
            raise ValueError("unsupported field report type")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("field_reports") or {
            "reference_id":f"FIELD-{job.job_number}","summary":{},"updated_by":authorized_by})
        summary=deepcopy(section.get("summary") or {}); items=deepcopy(summary.get("items") or [])
        report_id="FIELD-"+secrets.token_hex(6).upper()
        now=datetime.now(timezone.utc).isoformat()
        items.append({"report_id":report_id,"title":title.strip(),"report_type":report_type,
                      "status":"OPEN","observed_at":observed_at or None,"location":location or None,
                      "observations":observations.strip(),"follow_up_required":bool(follow_up_required),
                      "created_by":authorized_by,"created_at":now,"updated_at":now})
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["field_reports"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"FIELD_REPORT_CREATED","reference_id":report_id,
                       "summary":title.strip(),"report_type":report_type,
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job

    def update_field_report(self, *, job_number, report_id, status,
                            observations=None, follow_up_required=None, authorized_by):
        status=status.strip().upper()
        if status not in {"OPEN","FOLLOW_UP","CLOSED","CANCELLED"}:
            raise ValueError("unsupported field report status")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("field_reports") or {}); summary=deepcopy(section.get("summary") or {})
        items=deepcopy(summary.get("items") or [])
        item=next((x for x in items if x.get("report_id")==report_id),None)
        if item is None: raise KeyError(report_id)
        previous=str(item.get("status","OPEN")).upper()
        now=datetime.now(timezone.utc).isoformat()
        item["status"]=status
        if observations is not None: item["observations"]=observations.strip()
        if follow_up_required is not None: item["follow_up_required"]=bool(follow_up_required)
        item["updated_by"]=authorized_by; item["updated_at"]=now
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["field_reports"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"FIELD_REPORT_STATUS_CHANGED","reference_id":report_id,
                       "summary":item.get("title"),"from_status":previous,"to_status":status,
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def add_meeting(self, *, job_number, title, meeting_type="PROJECT",
                    scheduled_at=None, location=None, attendees=None, notes=None, authorized_by):
        meeting_type=meeting_type.strip().upper()
        if meeting_type not in {"PROJECT","CLIENT","DESIGN","COORDINATION","AGENCY","SITE","CONSTRUCTION","CLOSEOUT","OTHER"}:
            raise ValueError("unsupported meeting type")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("meetings") or {
            "reference_id":f"MEET-{job.job_number}","summary":{},"updated_by":authorized_by})
        summary=deepcopy(section.get("summary") or {}); items=deepcopy(summary.get("items") or [])
        meeting_id="MEET-"+secrets.token_hex(6).upper()
        now=datetime.now(timezone.utc).isoformat()
        items.append({"meeting_id":meeting_id,"title":title.strip(),"meeting_type":meeting_type,
                      "status":"SCHEDULED","scheduled_at":scheduled_at or None,"location":location or None,
                      "attendees":[str(x).strip() for x in (attendees or []) if str(x).strip()],
                      "notes":notes or None,"created_by":authorized_by,"created_at":now,"updated_at":now})
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["meetings"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"MEETING_CREATED","reference_id":meeting_id,"summary":title.strip(),
                       "meeting_type":meeting_type,"authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job

    def update_meeting(self, *, job_number, meeting_id, status,
                       scheduled_at=None, location=None, attendees=None, notes=None, authorized_by):
        status=status.strip().upper()
        if status not in {"SCHEDULED","IN_PROGRESS","COMPLETED","CANCELLED"}:
            raise ValueError("unsupported meeting status")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("meetings") or {}); summary=deepcopy(section.get("summary") or {})
        items=deepcopy(summary.get("items") or [])
        item=next((x for x in items if x.get("meeting_id")==meeting_id),None)
        if item is None: raise KeyError(meeting_id)
        previous=str(item.get("status","SCHEDULED")).upper()
        now=datetime.now(timezone.utc).isoformat()
        item["status"]=status
        if scheduled_at is not None: item["scheduled_at"]=scheduled_at or None
        if location is not None: item["location"]=location or None
        if attendees is not None: item["attendees"]=[str(x).strip() for x in attendees if str(x).strip()]
        if notes is not None: item["notes"]=notes or None
        item["updated_by"]=authorized_by; item["updated_at"]=now
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["meetings"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"MEETING_STATUS_CHANGED","reference_id":meeting_id,
                       "summary":item.get("title"),"from_status":previous,"to_status":status,
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def add_milestone(self, *, job_number, title, milestone_type="PROJECT",
                      due_at=None, owner=None, notes=None, authorized_by):
        milestone_type=milestone_type.strip().upper()
        if milestone_type not in {"PROJECT","DESIGN","CLIENT","PERMIT","AGENCY","CONSTRUCTION","BILLING","CLOSEOUT","OTHER"}:
            raise ValueError("unsupported milestone type")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("milestones") or {
            "reference_id":f"MILE-{job.job_number}","summary":{},"updated_by":authorized_by})
        summary=deepcopy(section.get("summary") or {}); items=deepcopy(summary.get("items") or [])
        milestone_id="MILE-"+secrets.token_hex(6).upper()
        now=datetime.now(timezone.utc).isoformat()
        items.append({"milestone_id":milestone_id,"title":title.strip(),"milestone_type":milestone_type,
                      "status":"OPEN","due_at":due_at or None,"owner":owner or None,
                      "notes":notes or None,"created_by":authorized_by,"created_at":now,"updated_at":now})
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["milestones"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"MILESTONE_CREATED","reference_id":milestone_id,
                       "summary":title.strip(),"milestone_type":milestone_type,
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job

    def update_milestone(self, *, job_number, milestone_id, status,
                         due_at=None, owner=None, notes=None, authorized_by):
        status=status.strip().upper()
        if status not in {"OPEN","IN_PROGRESS","BLOCKED","COMPLETE","CANCELLED"}:
            raise ValueError("unsupported milestone status")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("milestones") or {}); summary=deepcopy(section.get("summary") or {})
        items=deepcopy(summary.get("items") or [])
        item=next((x for x in items if x.get("milestone_id")==milestone_id),None)
        if item is None: raise KeyError(milestone_id)
        previous=str(item.get("status","OPEN")).upper()
        now=datetime.now(timezone.utc).isoformat()
        item["status"]=status
        if due_at is not None: item["due_at"]=due_at or None
        if owner is not None: item["owner"]=owner or None
        if notes is not None: item["notes"]=notes or None
        item["updated_by"]=authorized_by; item["updated_at"]=now
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["milestones"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"MILESTONE_STATUS_CHANGED","reference_id":milestone_id,
                       "summary":item.get("title"),"from_status":previous,"to_status":status,
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def add_correspondence(self, *, job_number, direction, subject, channel="EMAIL",
                           sender=None, recipient=None, occurred_at=None,
                           response_required=False, response_due_at=None,
                           notes=None, authorized_by):
        direction=direction.strip().upper(); channel=channel.strip().upper()
        if direction not in {"INBOUND","OUTBOUND"}:
            raise ValueError("unsupported correspondence direction")
        if channel not in {"EMAIL","PHONE_NOTE","WEBSITE","AGENCY_LETTER","MEETING_NOTE","OTHER"}:
            raise ValueError("unsupported correspondence channel")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("correspondence") or {
            "reference_id":f"COR-{job.job_number}","summary":{},"updated_by":authorized_by})
        summary=deepcopy(section.get("summary") or {}); items=deepcopy(summary.get("items") or [])
        correspondence_id="COR-"+secrets.token_hex(6).upper()
        now=datetime.now(timezone.utc).isoformat()
        items.append({
            "correspondence_id":correspondence_id,"direction":direction,"subject":subject.strip(),
            "channel":channel,"sender":sender or None,"recipient":recipient or None,
            "occurred_at":occurred_at or now,"response_required":bool(response_required),
            "response_due_at":response_due_at or None,
            "response_status":"PENDING" if response_required else "NOT_REQUIRED",
            "notes":notes or None,"created_by":authorized_by,"created_at":now,"updated_at":now})
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["correspondence"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"CORRESPONDENCE_RECORDED","reference_id":correspondence_id,
                       "summary":subject.strip(),"direction":direction,"channel":channel,
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job

    def update_correspondence_response(self, *, job_number, correspondence_id,
                                       response_status, response_due_at=None,
                                       response_note=None, authorized_by):
        response_status=response_status.strip().upper()
        if response_status not in {"PENDING","RESPONDED","CLOSED","NOT_REQUIRED"}:
            raise ValueError("unsupported correspondence response status")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("correspondence") or {})
        summary=deepcopy(section.get("summary") or {}); items=deepcopy(summary.get("items") or [])
        item=next((x for x in items if x.get("correspondence_id")==correspondence_id),None)
        if item is None: raise KeyError(correspondence_id)
        if not item.get("response_required") and response_status not in {"NOT_REQUIRED","CLOSED"}:
            raise ValueError("correspondence does not require a response")
        previous=str(item.get("response_status","PENDING")).upper()
        now=datetime.now(timezone.utc).isoformat()
        item["response_status"]=response_status
        if response_due_at is not None: item["response_due_at"]=response_due_at or None
        if response_note is not None: item["response_note"]=response_note or None
        item["updated_by"]=authorized_by; item["updated_at"]=now
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["correspondence"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"CORRESPONDENCE_RESPONSE_STATUS_CHANGED",
                       "reference_id":correspondence_id,"summary":item.get("subject"),
                       "from_status":previous,"to_status":response_status,
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def add_billing_record(self, *, job_number, billing_type, reference, status="DRAFT",
                           issued_at=None, due_at=None, notes=None, authorized_by):
        billing_type=billing_type.strip().upper()
        status=status.strip().upper()
        if billing_type not in {"INVOICE","APPLICATION","RETAINER","CHANGE_ORDER_BILLING","OTHER"}:
            raise ValueError("unsupported billing type")
        if status not in {"DRAFT","OPEN","ISSUED","PARTIAL","OVERDUE","PAID","VOID"}:
            raise ValueError("unsupported billing status")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("billing") or {
            "reference_id":f"BILL-{job.job_number}","summary":{},"updated_by":authorized_by})
        summary=deepcopy(section.get("summary") or {}); items=deepcopy(summary.get("items") or [])
        billing_id="BILL-"+secrets.token_hex(6).upper()
        now=datetime.now(timezone.utc).isoformat()
        items.append({"billing_id":billing_id,"billing_type":billing_type,"reference":reference.strip(),
                      "status":status,"issued_at":issued_at or None,"due_at":due_at or None,
                      "notes":notes or None,"created_by":authorized_by,"created_at":now,"updated_at":now})
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["billing"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"BILLING_RECORD_CREATED","reference_id":billing_id,
                       "summary":reference.strip(),"billing_type":billing_type,"status":status,
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job

    def update_billing_status(self, *, job_number, billing_id, status, notes=None, authorized_by):
        status=status.strip().upper()
        if status not in {"DRAFT","OPEN","ISSUED","PARTIAL","OVERDUE","PAID","VOID"}:
            raise ValueError("unsupported billing status")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("billing") or {}); summary=deepcopy(section.get("summary") or {})
        items=deepcopy(summary.get("items") or [])
        item=next((x for x in items if x.get("billing_id")==billing_id),None)
        if item is None: raise KeyError(billing_id)
        previous=str(item.get("status","")).upper()
        now=datetime.now(timezone.utc).isoformat()
        item["status"]=status
        if notes is not None: item["notes"]=notes or None
        item["updated_by"]=authorized_by; item["updated_at"]=now
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["billing"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"BILLING_STATUS_CHANGED","reference_id":billing_id,
                       "summary":item.get("reference"),"from_status":previous,"to_status":status,
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def add_client_portal_item(self, *, job_number, title, item_type="DOCUMENT",
                               status="DRAFT", acknowledgement_required=False,
                               client_action_required=False, notes=None, authorized_by):
        item_type=item_type.strip().upper(); status=status.strip().upper()
        if item_type not in {"DOCUMENT","SUBMISSION","REQUEST","NOTICE","UPDATE","OTHER"}:
            raise ValueError("unsupported client portal item type")
        if status not in {"DRAFT","SHARED","PUBLISHED","AVAILABLE","ARCHIVED"}:
            raise ValueError("unsupported client portal status")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("client_portal") or {
            "reference_id":f"PORTAL-{job.job_number}","summary":{},"updated_by":authorized_by})
        summary=deepcopy(section.get("summary") or {}); items=deepcopy(summary.get("items") or [])
        portal_item_id="PORTAL-"+secrets.token_hex(6).upper()
        now=datetime.now(timezone.utc).isoformat()
        items.append({"portal_item_id":portal_item_id,"title":title.strip(),"item_type":item_type,
                      "status":status,"acknowledgement_required":bool(acknowledgement_required),
                      "acknowledgement_status":"PENDING" if acknowledgement_required else "NOT_REQUIRED",
                      "client_action_required":bool(client_action_required),
                      "client_action_status":"PENDING" if client_action_required else "NOT_REQUIRED",
                      "notes":notes or None,"created_by":authorized_by,"created_at":now,"updated_at":now})
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["client_portal"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"CLIENT_PORTAL_ITEM_RECORDED","reference_id":portal_item_id,
                       "summary":title.strip(),"item_type":item_type,"status":status,
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job

    def update_client_portal_item(self, *, job_number, portal_item_id, status=None,
                                  acknowledgement_status=None, client_action_status=None,
                                  notes=None, authorized_by):
        allowed_status={"DRAFT","SHARED","PUBLISHED","AVAILABLE","ARCHIVED"}
        allowed_ack={"PENDING","ACKNOWLEDGED","CLOSED","NOT_REQUIRED"}
        allowed_action={"PENDING","COMPLETE","COMPLETED","CLOSED","NOT_REQUIRED"}
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("client_portal") or {}); summary=deepcopy(section.get("summary") or {})
        items=deepcopy(summary.get("items") or [])
        item=next((x for x in items if x.get("portal_item_id")==portal_item_id),None)
        if item is None: raise KeyError(portal_item_id)
        if status is not None:
            status=status.strip().upper()
            if status not in allowed_status: raise ValueError("unsupported client portal status")
            item["status"]=status
        if acknowledgement_status is not None:
            acknowledgement_status=acknowledgement_status.strip().upper()
            if acknowledgement_status not in allowed_ack: raise ValueError("unsupported acknowledgement status")
            if not item.get("acknowledgement_required") and acknowledgement_status not in {"NOT_REQUIRED","CLOSED"}:
                raise ValueError("item does not require acknowledgement")
            item["acknowledgement_status"]=acknowledgement_status
        if client_action_status is not None:
            client_action_status=client_action_status.strip().upper()
            if client_action_status not in allowed_action: raise ValueError("unsupported client action status")
            if not item.get("client_action_required") and client_action_status not in {"NOT_REQUIRED","CLOSED"}:
                raise ValueError("item does not require client action")
            item["client_action_status"]=client_action_status
        if notes is not None: item["notes"]=notes or None
        now=datetime.now(timezone.utc).isoformat(); item["updated_by"]=authorized_by; item["updated_at"]=now
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["client_portal"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"CLIENT_PORTAL_ITEM_UPDATED","reference_id":portal_item_id,
                       "summary":item.get("title"),"status":item.get("status"),
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def update_document_revision_status(self, *, job_number, document_id, revision_id,
                                        status, notes=None, professional_approval=False,
                                        authorized_by):
        status=status.strip().upper()
        if status not in {"DRAFT","IN_REVIEW","REVISED","READY","ISSUED","SUPERSEDED","VOID"}:
            raise ValueError("unsupported revision status")
        if status=="ISSUED" and not professional_approval:
            raise ValueError("explicit professional approval is required for issued revision status")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("documents") or {}); summary=deepcopy(section.get("summary") or {})
        documents=deepcopy(summary.get("items") or [])
        document=next((x for x in documents if x.get("document_id")==document_id),None)
        if document is None: raise KeyError(document_id)
        revisions=deepcopy(document.get("revisions") or [])
        revision=next((x for x in revisions
                       if str(x.get("revision_id",x.get("revision","")))==str(revision_id)),None)
        if revision is None: raise KeyError(revision_id)
        previous=str(revision.get("status","DRAFT")).upper()
        now=datetime.now(timezone.utc).isoformat()
        revision["status"]=status
        if notes is not None: revision["notes"]=notes or None
        revision["updated_by"]=authorized_by; revision["updated_at"]=now
        document["revisions"]=revisions
        document["current_revision_status"]=status
        document["updated_by"]=authorized_by; document["updated_at"]=now
        summary["items"]=documents; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["documents"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"DOCUMENT_REVISION_STATUS_CHANGED","reference_id":str(revision_id),
                       "document_id":document_id,"summary":document.get("title"),
                       "from_status":previous,"to_status":status,
                       "professional_action_approved":bool(status=="ISSUED"),
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def update_review_cycle_status(self, *, job_number, review_id, status,
                                   notes=None, authorized_by):
        status=status.strip().upper()
        if status not in {"OPEN","IN_REVIEW","CHANGES_REQUIRED","READY_TO_CLOSE","CLOSED","VOID"}:
            raise ValueError("unsupported review cycle status")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("reviews") or {}); summary=deepcopy(section.get("summary") or {})
        reviews=deepcopy(summary.get("items") or [])
        review=next((x for x in reviews if x.get("review_id")==review_id),None)
        if review is None: raise KeyError(review_id)
        previous=str(review.get("status","OPEN")).upper()
        comments=review.get("comments") or []
        if status=="CLOSED":
            unresolved=[c for c in comments if c.get("requires_action",True)
                        and str(c.get("status","OPEN")).upper()
                        not in {"VERIFIED","NOT_APPLICABLE"}]
            if unresolved:
                raise ValueError("review cycle has unresolved actionable comments")
        now=datetime.now(timezone.utc).isoformat()
        review["status"]=status
        if notes is not None: review["notes"]=notes or None
        review["updated_by"]=authorized_by; review["updated_at"]=now
        summary["items"]=reviews; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["reviews"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"REVIEW_CYCLE_STATUS_CHANGED","reference_id":review_id,
                       "summary":review.get("title") or review_id,
                       "from_status":previous,"to_status":status,
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def assess_submission_package_readiness(self, *, job_number, package_id, authorized_by):
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        packages=deepcopy(((((sections.get("submission_packages") or {}).get("summary") or {}).get("items")) or []))
        package=next((p for p in packages if p.get("package_id")==package_id),None)
        if package is None: raise KeyError(package_id)
        deliverables=((((sections.get("deliverables") or {}).get("summary") or {}).get("items")) or [])
        documents=((((sections.get("documents") or {}).get("summary") or {}).get("items")) or [])
        reviews=((((sections.get("reviews") or {}).get("summary") or {}).get("items")) or [])
        blockers=[]
        for did in package.get("deliverable_ids") or []:
            item=next((d for d in deliverables if d.get("deliverable_id")==did),None)
            if item is None:
                blockers.append({"type":"MISSING_DELIVERABLE","reference_id":did})
            elif str(item.get("status","DRAFT")).upper()=="DRAFT":
                blockers.append({"type":"DELIVERABLE_DRAFT","reference_id":did})
        for doc_id in package.get("document_ids") or []:
            doc=next((d for d in documents if d.get("document_id")==doc_id),None)
            if doc is None:
                blockers.append({"type":"MISSING_DOCUMENT","reference_id":doc_id})
                continue
            current=str(doc.get("current_revision") or "")
            rev=next((r for r in doc.get("revisions",[]) if str(r.get("revision",""))==current),None)
            rev_status=str((rev or {}).get("status","")).upper()
            if rev_status not in {"READY","ISSUED"}:
                blockers.append({"type":"DOCUMENT_REVISION_NOT_READY","reference_id":doc_id,
                                 "revision":current or None,"status":rev_status or "UNSET"})
            for review in reviews:
                if review.get("source_document_id")!=doc_id: continue
                unresolved=[c for c in review.get("comments",[]) if c.get("requires_action",True)
                            and str(c.get("status","OPEN")).upper() not in {"VERIFIED","NOT_APPLICABLE"}]
                if unresolved:
                    blockers.append({"type":"UNRESOLVED_REVIEW_COMMENTS",
                                     "reference_id":review.get("review_id"),
                                     "document_id":doc_id,"count":len(unresolved)})
        now=datetime.now(timezone.utc).isoformat()
        package["readiness"]={"status":"READY" if not blockers else "BLOCKED",
                              "blockers":blockers,"assessed_by":authorized_by,"assessed_at":now}
        section=deepcopy(sections.get("submission_packages") or {})
        summary=deepcopy(section.get("summary") or {}); summary["items"]=packages
        section["summary"]=summary; section["updated_by"]=authorized_by; sections["submission_packages"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"SUBMISSION_READINESS_ASSESSED","reference_id":package_id,
                       "summary":package.get("title"),"readiness":package["readiness"]["status"],
                       "blocker_count":len(blockers),"authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def advance_submission_package(self, *, job_number, package_id, status, authorized_by):
        status=status.strip().upper()
        if status not in {"DRAFT","READY","ISSUED","SUBMITTED","RETURNED","ACCEPTED","CLOSED","VOID"}:
            raise ValueError("unsupported submission package status")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("submission_packages") or {})
        summary=deepcopy(section.get("summary") or {}); packages=deepcopy(summary.get("items") or [])
        package=next((p for p in packages if p.get("package_id")==package_id),None)
        if package is None: raise KeyError(package_id)
        previous=str(package.get("status","DRAFT")).upper()
        readiness=package.get("readiness") or {}
        if status in {"READY","ISSUED","SUBMITTED"} and readiness.get("status")!="READY":
            raise ValueError("submission package is not operationally ready")
        now=datetime.now(timezone.utc).isoformat()
        package["status"]=status; package["updated_by"]=authorized_by; package["updated_at"]=now
        summary["items"]=packages; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["submission_packages"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"SUBMISSION_PACKAGE_STATUS_ADVANCED","reference_id":package_id,
                       "summary":package.get("title"),"from_status":previous,"to_status":status,
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def record_submission_outcome(self, *, job_number, package_id, outcome, authorized_by,
                                  reference=None, notes=None):
        outcome=outcome.strip().upper()
        if outcome not in {"ACCEPTED","RETURNED","REJECTED","WITHDRAWN"}:
            raise ValueError("unsupported submission outcome")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("submission_packages") or {})
        summary=deepcopy(section.get("summary") or {}); packages=deepcopy(summary.get("items") or [])
        package=next((p for p in packages if p.get("package_id")==package_id),None)
        if package is None: raise KeyError(package_id)
        current=str(package.get("status","DRAFT")).upper()
        if current not in {"SUBMITTED","RETURNED"}:
            raise ValueError("submission outcome requires a submitted package")
        now=datetime.now(timezone.utc).isoformat()
        package["outcome"]={"status":outcome,"reference":reference or None,"notes":notes or None,
                            "recorded_by":authorized_by,"recorded_at":now}
        package["status"]={"ACCEPTED":"ACCEPTED","RETURNED":"RETURNED","REJECTED":"RETURNED",
                           "WITHDRAWN":"VOID"}[outcome]
        package["updated_by"]=authorized_by; package["updated_at"]=now
        summary["items"]=packages; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["submission_packages"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"SUBMISSION_OUTCOME_RECORDED","reference_id":package_id,
                       "summary":package.get("title"),"outcome":outcome,"external_reference":reference or None,
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def activate_submission_return_work(self, *, job_number, package_id, authorized_by,
                                        owner=None, due_at=None, priority="HIGH", notes=None):
        priority=priority.strip().upper()
        if priority not in {"LOW","NORMAL","HIGH","URGENT"}:
            raise ValueError("unsupported action item priority")
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        packages=((((sections.get("submission_packages") or {}).get("summary") or {}).get("items")) or [])
        package=next((p for p in packages if p.get("package_id")==package_id),None)
        if package is None: raise KeyError(package_id)
        outcome=package.get("outcome") or {}
        if str(package.get("status","")).upper()!="RETURNED" or str(outcome.get("status","")).upper() not in {"RETURNED","REJECTED"}:
            raise ValueError("return work requires a confirmed returned or rejected submission outcome")
        section=deepcopy(sections.get("action_items") or {
            "reference_id":f"ACT-{job.job_number}","summary":{},"updated_by":authorized_by
        })
        summary=deepcopy(section.get("summary") or {}); items=deepcopy(summary.get("items") or [])
        existing=next((a for a in items if a.get("related_package_id")==package_id
                       and a.get("activation_source")=="SUBMISSION_RETURN"
                       and str(a.get("status","OPEN")).upper() not in {"DONE","CANCELLED"}),None)
        if existing is not None:
            raise ValueError("active return-work item already exists for submission package")
        now=datetime.now(timezone.utc).isoformat(); action_id="ACT-"+secrets.token_hex(6).upper()
        items.append({"action_id":action_id,"title":f"Address returned submission: {package.get('title')}",
                      "action_type":"SUBMISSION_RETURN","owner":owner or None,"due_at":due_at or None,
                      "priority":priority,"related_review_id":None,"related_package_id":package_id,
                      "related_dependency_id":None,"notes":notes or outcome.get("notes") or None,
                      "completion_note":None,"status":"OPEN","activation_source":"SUBMISSION_RETURN",
                      "created_by":authorized_by,"created_at":now,"updated_at":now})
        summary["items"]=items; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["action_items"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"SUBMISSION_RETURN_WORK_ACTIVATED","reference_id":action_id,
                       "summary":package.get("title"),"package_id":package_id,
                       "submission_outcome":outcome.get("status"),"authorized_by":authorized_by,
                       "occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def reassess_returned_submission(self, *, job_number, package_id, authorized_by):
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        packages=((((sections.get("submission_packages") or {}).get("summary") or {}).get("items")) or [])
        package=next((p for p in packages if p.get("package_id")==package_id),None)
        if package is None: raise KeyError(package_id)
        if str(package.get("status","")).upper()!="RETURNED":
            raise ValueError("return reassessment requires a returned submission package")
        actions=((((sections.get("action_items") or {}).get("summary") or {}).get("items")) or [])
        tied=[a for a in actions if a.get("related_package_id")==package_id
              and a.get("activation_source")=="SUBMISSION_RETURN"]
        if not tied:
            raise ValueError("returned submission has no recorded return-work item")
        incomplete=[a for a in tied if str(a.get("status","OPEN")).upper()!="DONE"]
        if incomplete:
            raise ValueError("returned submission return work must be completed before reassessment")
        job=self.assess_submission_package_readiness(
            job_number=job_number,package_id=package_id,authorized_by=authorized_by)
        sections=deepcopy(job.sections or {})
        packages=((((sections.get("submission_packages") or {}).get("summary") or {}).get("items")) or [])
        package=next((p for p in packages if p.get("package_id")==package_id),None)
        now=datetime.now(timezone.utc).isoformat()
        events=deepcopy(job.events or [])
        events.append({"event_type":"RETURNED_SUBMISSION_REASSESSED","reference_id":package_id,
                       "summary":package.get("title"),"readiness_status":(package.get("readiness") or {}).get("status"),
                       "authorized_by":authorized_by,"occurred_at":now})
        job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def reopen_submission_for_resubmission(self, *, job_number, package_id, authorized_by,
                                           resubmission_note=None):
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("submission_packages") or {})
        summary=deepcopy(section.get("summary") or {}); packages=deepcopy(summary.get("items") or [])
        package=next((p for p in packages if p.get("package_id")==package_id),None)
        if package is None: raise KeyError(package_id)
        if str(package.get("status","")).upper()!="RETURNED":
            raise ValueError("resubmission cycle requires a returned submission package")
        readiness=package.get("readiness") or {}
        if str(readiness.get("status","")).upper()!="READY":
            raise ValueError("returned submission must be reassessed READY before resubmission cycle")
        actions=((((sections.get("action_items") or {}).get("summary") or {}).get("items")) or [])
        return_work=[a for a in actions if a.get("related_package_id")==package_id
                     and a.get("activation_source")=="SUBMISSION_RETURN"]
        if not return_work:
            raise ValueError("returned submission has no recorded return work")
        incomplete=[a for a in return_work if str(a.get("status","OPEN")).upper()!="DONE"]
        if incomplete:
            raise ValueError("returned submission return work must be completed before reassessment")
        now=datetime.now(timezone.utc).isoformat()
        history=deepcopy(package.get("submission_history") or [])
        prior_outcome=deepcopy(package.get("outcome")) if package.get("outcome") else None
        history.append({"cycle":len(history)+1,"prior_status":"RETURNED","outcome":prior_outcome,
                        "readiness":deepcopy(readiness),"reopened_by":authorized_by,
                        "reopened_at":now,"note":resubmission_note or None})
        package["submission_history"]=history
        package["status"]="READY"
        package["outcome"]=None
        package["updated_by"]=authorized_by; package["updated_at"]=now
        summary["items"]=packages; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["submission_packages"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"SUBMISSION_RESUBMISSION_CYCLE_OPENED","reference_id":package_id,
                       "summary":package.get("title"),"cycle":len(history),
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def close_accepted_submission(self, *, job_number, package_id, authorized_by, closure_note=None):
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        section=deepcopy(sections.get("submission_packages") or {})
        summary=deepcopy(section.get("summary") or {}); packages=deepcopy(summary.get("items") or [])
        package=next((p for p in packages if p.get("package_id")==package_id),None)
        if package is None: raise KeyError(package_id)
        outcome=package.get("outcome") or {}
        if str(package.get("status","")).upper()!="ACCEPTED" or str(outcome.get("status","")).upper()!="ACCEPTED":
            raise ValueError("submission closure requires a confirmed accepted outcome")
        now=datetime.now(timezone.utc).isoformat()
        package["status"]="CLOSED"; package["closure"]={
            "closed_by":authorized_by,"closed_at":now,"note":closure_note or None,
            "accepted_reference":outcome.get("reference")}
        package["updated_by"]=authorized_by; package["updated_at"]=now
        summary["items"]=packages; section["summary"]=summary; section["updated_by"]=authorized_by
        sections["submission_packages"]=section
        events=deepcopy(job.events or [])
        events.append({"event_type":"ACCEPTED_SUBMISSION_CLOSED","reference_id":package_id,
                       "summary":package.get("title"),"accepted_reference":outcome.get("reference"),
                       "authorized_by":authorized_by,"occurred_at":now})
        job.sections=sections; job.events=events
        self._touch(job); self.db.commit(); self.db.refresh(job)
        return job


    def get_submission_lifecycle_summary(self, *, job_number):
        job=self.get(job_number); sections=deepcopy(job.sections or {})
        packages=((((sections.get("submission_packages") or {}).get("summary") or {}).get("items")) or [])
        counts={}
        attention=[]
        for package in packages:
            status=str(package.get("status","DRAFT")).upper()
            counts[status]=counts.get(status,0)+1
            outcome=package.get("outcome") or {}
            if status=="RETURNED":
                actions=((((sections.get("action_items") or {}).get("summary") or {}).get("items")) or [])
                open_return=[a for a in actions if a.get("related_package_id")==package.get("package_id")
                             and a.get("activation_source")=="SUBMISSION_RETURN"
                             and str(a.get("status","OPEN")).upper() not in {"DONE","CANCELLED"}]
                attention.append({"package_id":package.get("package_id"),"title":package.get("title"),
                                  "status":status,"outcome":outcome.get("status"),
                                  "open_return_work":len(open_return)})
        return {"job_number":job.job_number,"package_count":len(packages),
                "status_counts":counts,"attention_packages":attention}

