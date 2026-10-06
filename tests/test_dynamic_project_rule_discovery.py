from app.services.dynamic_project_rule_discovery import (
    discover_dynamic_project_rule_candidate,
    extract_project_rule_evidence,
)


def _source(content, **overrides):
    source = {
        "source_url": "https://example.gov/zoning",
        "label": "Zoning Ordinance",
        "source_role": "zoning_ordinance",
        "authority_tier": "likely_municipal_or_state_domain",
        "evidence_status": "DISCOVERED_CANDIDATE",
        "discovery_source": "https://www.nj.gov/dca/news/news/2023/20230613.shtml",
        "content": content,
        "authoritative": False,
        "legal_control_confirmed": False,
    }
    source.update(overrides)
    return source


def test_discovers_explicit_district_project_rule():
    result = discover_dynamic_project_rule_candidate(
        municipality="Example Township",
        zoning_district="R-20",
        project_goal="pool",
        source_documents=[
            _source("R-20 Residential Zone. Permitted accessory uses include private swimming pools.")
        ],
    )
    assert result["status"] == "PROJECT_RULE_EVIDENCE_DISCOVERED"
    assert result["requirements"][0]["evidence_type"] == "MUNICIPAL_ORDINANCE_TEXT"
    assert result["source"]["source_url"] == "https://example.gov/zoning"


def test_does_not_infer_from_project_term_alone():
    result = extract_project_rule_evidence(
        municipality="Example Township",
        zoning_district="R-20",
        project_goal="pool",
        source_document=_source("R-20 Residential Zone. Swimming pools are discussed in this chapter."),
    )
    assert result["status"] == "VERIFY"
    assert result["reason"] == "PERMISSION_CONTEXT_NOT_CONFIRMED"


def test_requires_district_match():
    result = extract_project_rule_evidence(
        municipality="Example Township",
        zoning_district="R-20",
        project_goal="pool",
        source_document=_source("R-30 Residential Zone. Permitted accessory uses include swimming pools."),
    )
    assert result["status"] == "VERIFY"
    assert result["reason"] == "ZONING_DISTRICT_NOT_FOUND"


def test_requires_source_content():
    result = discover_dynamic_project_rule_candidate(
        municipality="Example Township",
        zoning_district="R-20",
        project_goal="pool",
        source_documents=[_source("")],
    )
    assert result["status"] == "VERIFY"
    assert result["reason"] == "NO_PROJECT_RULE_EVIDENCE"


def test_candidate_never_promotes_authority():
    result = discover_dynamic_project_rule_candidate(
        municipality="Example Township",
        zoning_district="R-20",
        project_goal="pool",
        source_documents=[
            _source(
                "R-20 Residential Zone. Permitted accessory uses include swimming pools.",
                authoritative=True,
                legal_control_confirmed=True,
            )
        ],
    )
    assert result["status"] == "PROJECT_RULE_EVIDENCE_DISCOVERED"
    assert result["evidence_status"] == "CANDIDATE_ONLY"


def test_follows_referenced_district_accessory_uses():
    content = (
        "§ 430-16 R-M Residential Zone. "
        "R-M(M) Mid-Rise Residential. "
        "Permitted accessory uses: all accessory uses as permitted in the R-60 Zone, subject to all regulations. "
        "§ 430-13 R-60 Residential Zone. "
        "Permitted accessory uses: private recreational facilities, such as swimming pools."
    )
    result = discover_dynamic_project_rule_candidate(
        municipality="Example City",
        zoning_district="R-M(M)",
        project_goal="pool",
        source_documents=[_source(content)],
    )
    assert result["status"] == "PROJECT_RULE_EVIDENCE_DISCOVERED"
    assert "Referenced district evidence" in result["requirements"][0]["excerpt"]


def test_reference_without_permission_signal_does_not_promote():
    content = (
        "§ 430-16 R-M(M) Residential Zone. All accessory uses as permitted in the R-60 Zone. "
        "§ 430-13 R-60 Residential Zone. Swimming pools are discussed elsewhere."
    )
    result = discover_dynamic_project_rule_candidate(
        municipality="Example City",
        zoning_district="R-M(M)",
        project_goal="pool",
        source_documents=[_source(content)],
    )
    assert result["status"] == "VERIFY"
    assert result["reason"] == "NO_PROJECT_RULE_EVIDENCE"
