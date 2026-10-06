from app.services.engineering_workplace_portfolio import build_workplace_attention_queue

def test_attention_queue_merges_and_prioritizes_jobs_and_proposals():
    proposals=[
        {"proposal_request_id":"p1","property_record_id":"r1","project_goal":"pool","requested_at":"2026-01-01","attention":"ATTENTION","next_action":"REVIEW_PROPOSAL_DRAFT","property":{"address":"1 Main St"}},
        {"proposal_request_id":"p2","property_record_id":"r2","project_goal":"shed","attention":"NORMAL","next_action":"RECORD_CLIENT_RESPONSE","property":{"address":"2 Main St"}},
    ]
    cards=[
        {"job_number":"26-001","project_name":"Warehouse","project_state":"ACTIVE","attention":"URGENT","pending_approval_count":1,"open_signal_count":2,"next_action":{"type":"APPROVAL_REQUIRED","message":"Approve submission"}},
        {"job_number":"26-002","project_name":"House","project_state":"ACTIVE","attention":"INFO","pending_approval_count":0,"next_action":{"type":"NO_IMMEDIATE_ACTION","message":"None"}},
    ]
    rows=build_workplace_attention_queue(proposals,cards)
    assert [r["kind"] for r in rows]==["ENGINEERING_JOB","PROPOSAL"]
    assert rows[0]["attention"]=="URGENT"
    assert rows[0]["href"]=="job.html?job=26-001"
    assert rows[1]["href"]=="proposal.html?proposal_request_id=p1"

def test_pending_engineering_approval_enters_queue_even_without_attention_level():
    rows=build_workplace_attention_queue([],[
        {"job_number":"26-003","project_name":"Site","attention":"NORMAL","pending_approval_count":1,"next_action":{"type":"APPROVAL_REQUIRED","message":"Review approval"}}
    ])
    assert len(rows)==1
    assert rows[0]["kind"]=="ENGINEERING_JOB"
    assert rows[0]["attention"]=="ATTENTION"

def test_non_actionable_items_are_excluded():
    rows=build_workplace_attention_queue([
        {"proposal_request_id":"p1","attention":"INFO","next_action":"NONE","property":{}},
        {"proposal_request_id":"p2","attention":"NORMAL","next_action":"OPEN_ENGINEERING_JOB","property":{}},
    ],[])
    assert rows==[]
