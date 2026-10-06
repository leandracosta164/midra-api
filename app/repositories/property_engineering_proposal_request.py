import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.property_record import PropertyRecord
from app.models.property_analysis_run import PropertyAnalysisRun
from app.models.property_engineering_proposal_request import PropertyEngineeringProposalRequest

class SQLAlchemyPropertyEngineeringProposalRequestRepository:
    def __init__(self, db: Session):
        self.db=db

    def _property(self, property_record_id: str) -> PropertyRecord:
        record=self.db.get(PropertyRecord, property_record_id)
        if record is None: raise KeyError("property")
        return record

    def list(self, property_record_id: str) -> list[PropertyEngineeringProposalRequest]:
        self._property(property_record_id)
        stmt=(select(PropertyEngineeringProposalRequest)
              .where(PropertyEngineeringProposalRequest.property_record_id==property_record_id)
              .order_by(PropertyEngineeringProposalRequest.created_at.desc()))
        return list(self.db.scalars(stmt))


    def list_all(self, limit: int = 100) -> "list[PropertyEngineeringProposalRequest]":
        safe=max(1,min(int(limit),250))
        stmt=(select(PropertyEngineeringProposalRequest)
              .order_by(PropertyEngineeringProposalRequest.created_at.desc())
              .limit(safe))
        return list(self.db.scalars(stmt))

    def list_all_by_status(
        self,
        request_status: str,
        limit: int = 100,
    ) -> "list[PropertyEngineeringProposalRequest]":
        safe=max(1,min(int(limit),250))
        normalized_status=str(request_status or "").strip().upper()
        if not normalized_status:
            return self.list_all(limit=safe)
        stmt=(select(PropertyEngineeringProposalRequest)
              .where(PropertyEngineeringProposalRequest.request_status==normalized_status)
              .order_by(PropertyEngineeringProposalRequest.created_at.desc())
              .limit(safe))
        return list(self.db.scalars(stmt))

    def get(self, property_record_id: str, proposal_request_id: str) -> PropertyEngineeringProposalRequest:
        self._property(property_record_id)
        item=self.db.get(PropertyEngineeringProposalRequest, proposal_request_id)
        if item is None or item.property_record_id != property_record_id:
            raise KeyError("proposal_request")
        return item

    def transition_status(
        self,
        *,
        property_record_id: str,
        proposal_request_id: str,
        expected_current_status: str,
        next_status: str,
    ) -> PropertyEngineeringProposalRequest:
        item = self.get(property_record_id, proposal_request_id)
        expected = str(expected_current_status or "").strip().upper()
        current = str(item.request_status or "").strip().upper()
        target = str(next_status or "").strip().upper()
        if current != expected:
            raise ValueError("proposal_status_changed")
        from app.services.property_engineering_proposal_lifecycle import (
            validate_property_engineering_proposal_transition,
        )
        transition = validate_property_engineering_proposal_transition(current, target)
        if transition.get("transition_permitted") is not True:
            raise ValueError("proposal_transition_not_allowed")
        item.request_status = target
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def create(self, *, property_record_id: str, analysis_run_id: str | None,
               project_goal: str, customer_name: str, customer_email: str,
               customer_phone: str | None=None) -> PropertyEngineeringProposalRequest:
        self._property(property_record_id)
        analysis_id=(analysis_run_id or "").strip() or None
        if analysis_id:
            run=self.db.get(PropertyAnalysisRun, analysis_id)
            if run is None or run.property_record_id != property_record_id:
                raise KeyError("analysis")
        item=PropertyEngineeringProposalRequest(
            proposal_request_id=str(uuid.uuid4()),
            property_record_id=property_record_id,
            analysis_run_id=analysis_id,
            project_goal=project_goal.strip(),
            customer_name=customer_name.strip(),
            customer_email=customer_email.strip(),
            customer_phone=(customer_phone or "").strip() or None,
            request_status="REQUESTED",
            source_product="MIDRA_PROPERTY",
            destination_product="MIDRA_ENGINEERING",
        )
        self.db.add(item); self.db.commit(); self.db.refresh(item)
        return item
