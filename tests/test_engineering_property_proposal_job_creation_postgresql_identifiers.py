from pathlib import Path
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex
from app.models.engineering_property_proposal_job_creation import EngineeringPropertyProposalJobCreation

def test_postgresql_identifiers_fit_limit():
    assert len(EngineeringPropertyProposalJobCreation.__tablename__) <= 63
    for index in EngineeringPropertyProposalJobCreation.__table__.indexes:
        assert index.name and len(index.name) <= 63
        str(CreateIndex(index).compile(dialect=postgresql.dialect()))
    for constraint in EngineeringPropertyProposalJobCreation.__table__.constraints:
        if constraint.name:
            assert len(constraint.name) <= 63

def test_migration_uses_explicit_short_index_names():
    migration=Path(__file__).parents[1]/"alembic/versions/20261003_16_engineering_property_proposal_job_creations.py"
    text=migration.read_text(encoding="utf-8")
    for name in ["ix_epp_job_create_property","ix_epp_job_create_request","ix_epp_job_create_response","ix_epp_job_create_job","uq_epp_job_create_response","uq_epp_job_create_request","uq_epp_job_create_job"]:
        assert name in text and len(name)<=63
