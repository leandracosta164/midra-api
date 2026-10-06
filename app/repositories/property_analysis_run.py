import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.property_analysis_run import PropertyAnalysisRun

class SQLAlchemyPropertyAnalysisRunRepository:
    def __init__(self, db: Session): self.db=db
    def append(self, *, property_record_id: str, analysis: dict) -> PropertyAnalysisRun:
        run=PropertyAnalysisRun(
            analysis_run_id=str(uuid.uuid4()), property_record_id=property_record_id,
            requested_work=str(analysis.get("requested_work") or analysis.get("project_goal") or "").strip() or None,
            intelligence_status="MIDRA_ANALYSIS", analysis=analysis, created_at=datetime.now(timezone.utc))
        self.db.add(run); self.db.commit(); self.db.refresh(run); return run
    def get(self, property_record_id: str, analysis_run_id: str) -> PropertyAnalysisRun:
        run=self.db.get(PropertyAnalysisRun, analysis_run_id)
        if run is None or run.property_record_id != property_record_id:
            raise KeyError("analysis_run")
        return run

    def list(self, property_record_id: str, *, limit: int=25) -> list[PropertyAnalysisRun]:
        stmt=(select(PropertyAnalysisRun).where(PropertyAnalysisRun.property_record_id==property_record_id)
              .order_by(PropertyAnalysisRun.created_at.desc()).limit(max(1,min(limit,100))))
        return list(self.db.scalars(stmt).all())
