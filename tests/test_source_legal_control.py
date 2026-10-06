from app.services.source_legal_control import evaluate_legal_control_text


def test_empty_content_never_establishes_legal_control():
    result = evaluate_legal_control_text(content="")
    assert result["status"] == "LEGAL_CONTROL_NOT_ESTABLISHED"
    assert result["legal_control_confirmed"] is False


def test_official_link_language_alone_is_not_legal_control():
    result = evaluate_legal_control_text(
        content="View the City's official zoning map using our interactive GIS application."
    )
    assert result["status"] == "LEGAL_CONTROL_NOT_ESTABLISHED"
    assert result["legal_control_confirmed"] is False


def test_explicit_adoption_without_final_authority_remains_unconfirmed():
    result = evaluate_legal_control_text(
        content='The City adopts the Official Land Use Map, entitled "Official Land Use Map of the City, November 2014".'
    )
    assert "EXPLICIT_MAP_ADOPTION" in result["signals"]
    assert result["legal_control_confirmed"] is False


def test_explicit_adoption_and_final_authority_create_evidence_candidate_only():
    content = """
    The City adopts the Official Land Use Map, entitled "Official Land Use Map of the City of Perth Amboy, November, 2014".
    The original Map, in whatever physical or electronic format it exists, of the Official Zoning Map maintained in the
    office of the Municipal Clerk shall be used as the final authority as to the current status of zoning districts.
    """
    result = evaluate_legal_control_text(content=content, source_url="https://example.test/code")
    assert result["status"] == "LEGAL_CONTROL_EVIDENCE_DISCOVERED"
    assert result["legal_control_confirmed"] is False
    assert result["requires_target_identity_match"] is True
    assert "EXPLICIT_MAP_ADOPTION" in result["signals"]
    assert "EXPLICIT_FINAL_AUTHORITY_STATEMENT" in result["signals"]
    assert "Official Land Use Map" in result["controlling_instrument"]
