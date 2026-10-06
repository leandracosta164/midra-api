from app.services.engineering_workplace_portfolio import _workplace_analysis_proposal_traceability


def test_groups_proposals_by_analysis_run_without_promoting_unlinked_rows():
    proposals=[
        {"proposal_request_id":"p-1","analysis_run_id":"a-1","stage":"AWAITING_ENGINEERING_REVIEW"},
        {"proposal_request_id":"p-2","analysis_run_id":"a-2","stage":"READY_FOR_CLIENT_RELEASE"},
        {"proposal_request_id":"p-3","analysis_run_id":"a-1","stage":"ENGINEERING_JOB_CREATED"},
        {"proposal_request_id":"p-4","analysis_run_id":None,"stage":"AWAITING_PROPOSAL_DRAFT"},
    ]
    grouped=_workplace_analysis_proposal_traceability(proposals)
    assert [x["proposal_request_id"] for x in grouped["a-1"]] == ["p-1","p-3"]
    assert [x["proposal_request_id"] for x in grouped["a-2"]] == ["p-2"]
    assert "" not in grouped
    assert "p-4" not in {x["proposal_request_id"] for rows in grouped.values() for x in rows}
