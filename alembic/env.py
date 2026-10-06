from logging.config import fileConfig
import os
from alembic import context
from app.core.settings import settings
from sqlalchemy import engine_from_config, pool
from app.db.base import Base
from app.models.source_version import SourceVersion
from app.models.source_catalog import SourceCatalog
from app.models.source_content import SourceContent
from app.models.engineering_job import EngineeringJob
from app.models.engineering_session import EngineeringSession
from app.models.property_record import PropertyRecord
from app.models.property_analysis_run import PropertyAnalysisRun
from app.models.property_engineering_job_link import PropertyEngineeringJobLink
from app.models.property_engineering_proposal_request import PropertyEngineeringProposalRequest
from app.models.engineering_property_proposal_draft import EngineeringPropertyProposalDraft
from app.models.engineering_property_proposal_review import EngineeringPropertyProposalReview
from app.models.engineering_property_proposal_release import EngineeringPropertyProposalRelease
from app.models.engineering_property_proposal_client_response import EngineeringPropertyProposalClientResponse
from app.models.engineering_property_proposal_job_creation import EngineeringPropertyProposalJobCreation
from app.models.engineering_property_proposal_pdf_artifact import EngineeringPropertyProposalPdfArtifact
from app.models.engineering_property_proposal_delivery import EngineeringPropertyProposalDelivery
from app.models.property_analysis_run import PropertyAnalysisRun

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.render_as_string(hide_password=False).replace("%", "%%"))
target_metadata = Base.metadata

def run_migrations_offline():
    context.configure(url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()


