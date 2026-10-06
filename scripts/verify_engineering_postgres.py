"""Controlled PostgreSQL smoke verification for MIDRA Engineering Jobs.

Creates one clearly marked temporary job through the real repository, verifies persistence
and lifecycle operations, then deletes it in a finally block so production data remains clean.
"""
from app.db.session import SessionLocal
from app.models.engineering_job import EngineeringJob
from app.repositories.engineering_job import SQLAlchemyEngineeringJobRepository

JOB="__MIDRA_SMOKE_6_6__"

db=SessionLocal()
try:
    existing=db.get(EngineeringJob,JOB)
    if existing:
        db.delete(existing); db.commit()

    repo=SQLAlchemyEngineeringJobRepository(db)
    job=repo.create(
        job_number=JOB,
        project_name="MIDRA Engineering Smoke Verification",
        project_type="SYSTEM_TEST",
        source="SYSTEM_TEST",
        property_address=None,
        client_id=None,
    )
    assert job.job_number==JOB
    assert repo.exists(JOB)

    job=repo.connect_section(
        job_number=JOB,section="workflow",reference_id="SMOKE-WF",
        summary={"purpose":"database verification"},authorized_by="system-test")
    assert job.sections["workflow"]["reference_id"]=="SMOKE-WF"

    job=repo.change_state(
        job_number=JOB,state="WAITING",authorized_by="system-test",
        reason="smoke verification")
    assert job.state=="WAITING"
    assert job.events[-1]["event_type"]=="JOB_STATE_CHANGED"

    job=repo.add_event(
        job_number=JOB,event_type="SMOKE_VERIFIED",
        reference_id="M6.6",summary="PostgreSQL repository path verified")
    assert job.events[-1]["event_type"]=="SMOKE_VERIFIED"

    print("POSTGRES ENGINEERING JOB SMOKE TEST: PASS")
    print("job_number:",job.job_number)
    print("state:",job.state)
    print("version:",job.version)
    print("workflow_reference:",job.sections["workflow"]["reference_id"])
    print("event_count:",len(job.events))
finally:
    try:
        obj=db.get(EngineeringJob,JOB)
        if obj:
            db.delete(obj); db.commit()
        print("TEMPORARY SMOKE JOB CLEANUP: PASS")
    finally:
        db.close()
