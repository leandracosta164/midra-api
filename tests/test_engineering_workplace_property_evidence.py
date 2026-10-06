from types import SimpleNamespace
from app.services.engineering_workplace_portfolio import _workplace_recorded_sources


def test_recorded_sources_preserve_candidate_state_and_dedupe():
    analysis={
        "sources":[{"label":"Official zoning","source_url":"https://example.gov/zoning"}],
        "dynamic_intelligence":{
            "zoning":{"candidate":{"record":{"source":{"label":"Official zoning","source_url":"https://example.gov/zoning"}}}},
            "project_rule_candidate":{"source":{"label":"Code","source_url":"https://example.gov/code"}},
        },
    }
    rows=_workplace_recorded_sources(analysis)
    assert len(rows)==2
    code=next(x for x in rows if x["source_url"]=="https://example.gov/code")
    assert code["candidate_only"] is True
    assert code["evidence_role"]=="dynamic_project_rule_candidate"
