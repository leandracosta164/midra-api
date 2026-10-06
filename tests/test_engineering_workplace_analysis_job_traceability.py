from app.services.engineering_workplace_portfolio import _workplace_analysis_job_traceability


def test_projects_created_engineering_jobs_back_to_source_analysis_without_duplicates():
    grouped=_workplace_analysis_job_traceability({
        "a-1":[
            {"proposal_request_id":"p-1","proposal_number":"P-001","engineering_job_number":"ENG-001"},
            {"proposal_request_id":"p-2","proposal_number":"P-002","engineering_job_number":"ENG-001"},
            {"proposal_request_id":"p-3","proposal_number":"P-003","engineering_job_number":None},
        ],
        "a-2":[
            {"proposal_request_id":"p-4","project_goal":"Addition","engineering_job_number":"ENG-002"},
        ],
    })
    assert [x["engineering_job_number"] for x in grouped["a-1"]] == ["ENG-001"]
    assert grouped["a-1"][0]["href"] == "job.html?job=ENG-001"
    assert grouped["a-2"][0]["proposal_request_id"] == "p-4"
