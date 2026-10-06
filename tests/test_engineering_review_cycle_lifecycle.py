from types import SimpleNamespace
from app.repositories.engineering_job import SQLAlchemyEngineeringJobRepository

class FakeDB:
    def commit(self): pass
    def refresh(self, job): pass

def repo_for(job):
    r=object.__new__(SQLAlchemyEngineeringJobRepository); r.db=FakeDB()
    r.get=lambda n: job if n==job.job_number else (_ for _ in ()).throw(KeyError(n))
    return r

def job():
    return SimpleNamespace(job_number="ENG-147",project_name="Review Ops",project_type="SITE",
        source="TEST",property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",
        version=14,sections={},events=[])

def create_review(r,j):
    r.add_review(job_number=j.job_number,title="30 Percent Review",authorized_by="Leandra")
    return j.sections["reviews"]["summary"]["items"][0]["review_id"]

def test_review_cycle_progression_is_recorded():
    j=job(); r=repo_for(j); rid=create_review(r,j)
    r.update_review_cycle_status(job_number=j.job_number,review_id=rid,status="IN_REVIEW",
        notes="Review underway",authorized_by="Leandra")
    assert j.sections["reviews"]["summary"]["items"][0]["status"]=="IN_REVIEW"
    assert j.events[-1]["event_type"]=="REVIEW_CYCLE_STATUS_CHANGED"

def test_review_cannot_close_with_unresolved_comments():
    j=job(); r=repo_for(j); rid=create_review(r,j)
    r.add_review_comment(job_number=j.job_number,review_id=rid,comment_number="1",
        comment_text="Revise grading note",authorized_by="Leandra")
    try:
        r.update_review_cycle_status(job_number=j.job_number,review_id=rid,status="CLOSED",
            authorized_by="Leandra")
    except ValueError as exc:
        assert "unresolved actionable comments" in str(exc)
    else:
        raise AssertionError("review closed with unresolved comment")

def test_review_can_close_after_comments_verified():
    j=job(); r=repo_for(j); rid=create_review(r,j)
    r.add_review_comment(job_number=j.job_number,review_id=rid,comment_number="1",
        comment_text="Revise grading note",authorized_by="Leandra")
    cid=j.sections["reviews"]["summary"]["items"][0]["comments"][0]["comment_id"]
    r.update_review_comment(job_number=j.job_number,review_id=rid,comment_id=cid,status="VERIFIED",
        authorized_by="Leandra")
    r.update_review_cycle_status(job_number=j.job_number,review_id=rid,status="CLOSED",
        authorized_by="Leandra")
    assert j.sections["reviews"]["summary"]["items"][0]["status"]=="CLOSED"
