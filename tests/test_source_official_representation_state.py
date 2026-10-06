from app.services.source_official_representation_state import confirm_catalog_official_representation


URL = "https://example.maps.arcgis.com/apps/instant/basic/index.html?appid=0123456789abcdef0123456789abcdef"


class Row:
    municipality = "Example Township"
    source_url = URL
    active = True
    authoritative = False
    legal_control_confirmed = False
    evidence_status = "DISCOVERED_CANDIDATE"


class DB:
    def __init__(self, row):
        self.row = row
        self.commits = 0

    def scalar(self, _statement):
        return self.row

    def commit(self):
        self.commits += 1


def evidence(**updates):
    value = {
        "status": "OFFICIAL_ZONING_REPRESENTATION_VERIFIED",
        "authority_verified": True,
        "legal_control_confirmed": False,
        "target_source": {"source_url": URL},
    }
    value.update(updates)
    return value


def test_verified_official_representation_promotes_authority_only():
    row = Row()
    db = DB(row)
    result = confirm_catalog_official_representation(
        db=db, municipality="Example Township", target_source_url=URL, evidence=evidence()
    )
    assert result["status"] == "SOURCE_AUTHORITY_PROMOTED"
    assert row.authoritative is True
    assert row.legal_control_confirmed is False
    assert db.commits == 1


def test_unverified_representation_cannot_promote_authority():
    row = Row()
    db = DB(row)
    result = confirm_catalog_official_representation(
        db=db,
        municipality="Example Township",
        target_source_url=URL,
        evidence=evidence(status="OFFICIAL_REPRESENTATION_NOT_VERIFIED", authority_verified=False),
    )
    assert result["status"] == "SOURCE_AUTHORITY_NOT_PROMOTED"
    assert row.authoritative is False
    assert db.commits == 0


def test_representation_evidence_cannot_smuggle_legal_control_promotion():
    row = Row()
    db = DB(row)
    result = confirm_catalog_official_representation(
        db=db,
        municipality="Example Township",
        target_source_url=URL,
        evidence=evidence(legal_control_confirmed=True),
    )
    assert result["status"] == "SOURCE_AUTHORITY_NOT_PROMOTED"
    assert result["reason"] == "REPRESENTATION_EVIDENCE_MUST_NOT_ASSERT_LEGAL_CONTROL"
    assert row.authoritative is False
    assert row.legal_control_confirmed is False
    assert db.commits == 0
