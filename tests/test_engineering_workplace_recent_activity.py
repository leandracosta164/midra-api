from datetime import datetime, timezone
from types import SimpleNamespace

from app.services.engineering_workplace_portfolio import build_workplace_recent_activity


def obj(**kwargs):
    return SimpleNamespace(**kwargs)


def test_recent_activity_orders_recorded_lifecycle_events_newest_first():
    request=obj(proposal_request_id="pr-1", property_record_id="prop-1", project_goal="Addition", created_at=datetime(2026,10,1,tzinfo=timezone.utc))
    prop=obj(display_address="1 Main St", search_query=None)
    draft=obj(created_at=datetime(2026,10,2,tzinfo=timezone.utc), proposal_number="P-1", proposal_status="DRAFT")
    response=obj(created_at=datetime(2026,10,3,tzinfo=timezone.utc), response_status="ACCEPTED")
    rows=build_workplace_recent_activity([request], {"pr-1":draft}, {}, {}, {"pr-1":response}, {}, {"prop-1":prop})
    assert [x["kind"] for x in rows]==["CLIENT_RESPONSE","PROPOSAL_DRAFT","PROPOSAL_REQUEST"]
    assert rows[0]["href"]=="proposal.html?proposal_request_id=pr-1"
    assert rows[0]["title"]=="1 Main St"


def test_recent_activity_limit_is_bounded():
    requests=[obj(proposal_request_id=f"pr-{i}", property_record_id=f"prop-{i}", project_goal="Test", created_at=datetime(2026,10,1,tzinfo=timezone.utc)) for i in range(4)]
    props={f"prop-{i}":obj(display_address=f"{i} Main St", search_query=None) for i in range(4)}
    rows=build_workplace_recent_activity(requests, {}, {}, {}, {}, {}, props, limit=2)
    assert len(rows)==2
