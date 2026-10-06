import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.mark.parametrize(
    "address,expected_municipality,expected_district,expected_status,expected_count",
    [
        (
            "922 State Highway 33, Freehold, NJ 07728",
            "HOWELL TWP",
            "HD-4",
            "PARTIALLY_APPLICABLE",
            7,
        ),
        (
            "1979 Township Drive, Marlboro, NJ 07746",
            "MARLBORO TWP",
            "CF",
            "VERIFY",
            5,
        ),
    ],
)
def test_property_intelligence_regression(
    address,
    expected_municipality,
    expected_district,
    expected_status,
    expected_count,
):
    response = client.post(
        "/property-intelligence/analyze",
        json={
            "address": address,
            "project_goal": "pool",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["zoning_evidence"]["municipality"] == expected_municipality
    assert data["zoning_evidence"]["zoning_district"] == expected_district
    assert data["zoning_evidence"]["status"] == "ZONING_RESOLVED"
    assert data["zoning_evidence"]["evidence_type"] == "OFFICIAL_PARCEL_SPECIFIC"
    assert data["zoning_evidence"]["authoritative"] is True

    applicability = data["zoning_intelligence"]["project_rule_applicability"]

    assert applicability["status"] == expected_status
    assert applicability["evaluated_requirement_count"] == expected_count

def test_marlboro_cf_pool_rule_is_explicitly_registered():
    from app.services.zoning_intelligence import _get_registered_rule_set

    rule_set = _get_registered_rule_set(
        "Marlboro Township",
        "CF",
        "pool",
    )

    assert rule_set["registered"] is True
    assert rule_set["district_registered"] is True
    assert rule_set["project_handler"] is not None
    assert rule_set["project_handler"].__name__ == "_build_marlboro_pool_requirements"
    assert rule_set["rule_key"] == "marlboro township:CF:pool"

def test_marlboro_cf_municipal_facility_classification():
    response = client.post(
        "/property-intelligence/analyze",
        json={
            "address": "1979 Township Drive, Marlboro, NJ 07746",
            "project_goal": "pool",
        },
    )

    assert response.status_code == 200

    data = response.json()

    parcel = data["property_resolution"]["parcel"]

    assert parcel["property_class"] == "15C"
    assert parcel["building_description"] == "MUNICIPAL BLDG"

    applicability = data["zoning_intelligence"]["project_rule_applicability"]

    assert applicability["status"] == "VERIFY"
    assert applicability["evaluated_requirement_count"] == 5

    residential_requirement = next(
        item
        for item in applicability["requirements"]
        if item["requirement"] == "Residential building prerequisite"
    )

    assert residential_requirement["status"] == "NOT_APPLICABLE"
    assert residential_requirement["applicable"] is False

def test_registry_not_applicable_decision_is_respected():
    from app.services.rule_applicability import (
        evaluate_requirement_applicability,
    )

    result = evaluate_requirement_applicability(
        municipality="Example Township",
        zoning_district="R-1",
        project_goal="pool",
        requirement={
            "requirement": "Example exclusion",
            "registry_applicability": "NOT_APPLICABLE",
        },
    )

    assert result["status"] == "NOT_APPLICABLE"
    assert result["applicable"] is False


def test_registry_applicable_decision_is_respected():
    from app.services.rule_applicability import (
        evaluate_requirement_applicability,
    )

    result = evaluate_requirement_applicability(
        municipality="Example Township",
        zoning_district="R-1",
        project_goal="pool",
        requirement={
            "requirement": "Example requirement",
            "registry_applicability": "APPLICABLE",
        },
    )

    assert result["status"] == "APPLICABLE"
    assert result["applicable"] is True


def test_municipal_facility_override_beats_registry_applicable():
    from app.services.rule_applicability import (
        evaluate_requirement_applicability,
    )

    result = evaluate_requirement_applicability(
        municipality="Marlboro Township",
        zoning_district="CF",
        project_goal="pool",
        property_resolution={
            "parcel": {
                "property_class": "15C",
                "building_description": "MUNICIPAL BLDG",
            }
        },
        requirement={
            "requirement": "Residential building prerequisite",
            "applies_to": "Private permanent residential pool",
            "registry_applicability": "APPLICABLE",
        },
    )

    assert result["status"] == "NOT_APPLICABLE"
    assert result["applicable"] is False

def test_unresolved_district_does_not_receive_marlboro_pool_rules():
    from app.services.zoning_intelligence import _get_registered_rule_set

    rule_set = _get_registered_rule_set(
        "Marlboro Township",
        "VERIFY",
        "pool",
    )

    assert rule_set["registered"] is True
    assert rule_set["district_registered"] is False
    assert rule_set["project_handler"] is None
    assert rule_set["rule_key"] is None

def test_marlboro_cf_coverage_reports_project_rules_available():
    response = client.post(
        "/property-intelligence/analyze",
        json={
            "address": "1979 Township Drive, Marlboro, NJ 07746",
            "project_goal": "pool",
        },
    )

    assert response.status_code == 200

    coverage = response.json()["zoning_intelligence"]["coverage"]

    assert coverage["status"] == "PROJECT_RULES_AVAILABLE"
    assert coverage["municipality_registered"] is True
    assert coverage["zoning_resolution_supported"] is True
    assert coverage["district_rules_supported"] is False
    assert coverage["project_rules_supported"] is True
    assert coverage["zoning_district"] == "CF"


def test_unresolved_marlboro_district_cannot_claim_project_coverage():
    from app.services.municipality_coverage import build_municipality_coverage

    result = build_municipality_coverage(
        municipality="Marlboro Township",
        zoning_intelligence={
            "municipality": "MARLBORO TWP",
            "zoning_district": "VERIFY",
            "bulk_requirements": [],
            "project_requirements": [],
        },
        zoning_resolution={
            "zoning_district": "VERIFY",
            "confidence": "VERIFY",
        },
        project_goal="pool",
    )

    assert result["status"] == "REGISTERED"
    assert result["municipality_registered"] is True
    assert result["zoning_resolution_supported"] is False
    assert result["district_rules_supported"] is False
    assert result["project_rules_supported"] is False
    assert result["zoning_district"] == "VERIFY"


def test_unregistered_municipality_cannot_claim_any_coverage():
    from app.services.municipality_coverage import build_municipality_coverage

    result = build_municipality_coverage(
        municipality="Example Township",
        zoning_intelligence={
            "municipality": "Example Township",
            "zoning_district": "R-1",
            "bulk_requirements": [{"requirement": "Example"}],
            "project_requirements": [{"requirement": "Example"}],
        },
        zoning_resolution={
            "zoning_district": "R-1",
            "confidence": "OFFICIAL_PARCEL_SPECIFIC",
        },
        project_goal="pool",
    )

    assert result["status"] == "UNREGISTERED"
    assert result["municipality_registered"] is False
    assert result["zoning_resolution_supported"] is False
    assert result["district_rules_supported"] is False
    assert result["project_rules_supported"] is False


def test_api_exposes_registry_and_coverage_contract_for_howell_hd4():
    response = client.post(
        "/property-intelligence/analyze",
        json={
            "address": "922 State Highway 33, Freehold, NJ 07728",
            "project_goal": "pool",
        },
    )

    assert response.status_code == 200

    data = response.json()
    zoning = data["zoning_intelligence"]
    registry = zoning["rules_registry"]
    coverage = zoning["coverage"]

    assert registry["registered"] is True
    assert registry["district_registered"] is True
    assert registry["rule_key"] == "howell township:HD-4:pool"
    assert registry["project_rules_available"] is True

    assert coverage["status"] == "PROJECT_RULES_AVAILABLE"
    assert coverage["municipality_registered"] is True
    assert coverage["zoning_resolution_supported"] is True
    assert coverage["project_rules_supported"] is True
    assert coverage["zoning_district"] == "HD-4"

    assert zoning["project_rule_applicability"]["status"] == (
        "PARTIALLY_APPLICABLE"
    )
    assert zoning["project_rule_applicability"][
        "evaluated_requirement_count"
    ] == 7


def test_api_exposes_registry_and_coverage_contract_for_marlboro_cf():
    response = client.post(
        "/property-intelligence/analyze",
        json={
            "address": "1979 Township Drive, Marlboro, NJ 07746",
            "project_goal": "pool",
        },
    )

    assert response.status_code == 200

    data = response.json()
    zoning = data["zoning_intelligence"]
    registry = zoning["rules_registry"]
    coverage = zoning["coverage"]

    assert registry["registered"] is True
    assert registry["district_registered"] is True
    assert registry["rule_key"] == "marlboro township:CF:pool"
    assert registry["project_rules_available"] is True

    assert coverage["status"] == "PROJECT_RULES_AVAILABLE"
    assert coverage["municipality_registered"] is True
    assert coverage["zoning_resolution_supported"] is True
    assert coverage["project_rules_supported"] is True
    assert coverage["zoning_district"] == "CF"

    assert zoning["project_rule_applicability"]["status"] == "VERIFY"
    assert zoning["project_rule_applicability"][
        "evaluated_requirement_count"
    ] == 5

def test_registry_supported_and_unsupported_matrix():
    from app.services.zoning_intelligence import _get_registered_rule_set

    cases = [
        (
            "Howell Township",
            "HD-4",
            "pool",
            True,
            True,
            True,
            "howell township:HD-4:pool",
        ),
        (
            "Marlboro Township",
            "CF",
            "pool",
            True,
            True,
            True,
            "marlboro township:CF:pool",
        ),
        (
            "Marlboro Township",
            "R-20",
            "pool",
            True,
            True,
            True,
            "marlboro township:R-20:pool",
        ),
        (
            "Marlboro Township",
            "VERIFY",
            "pool",
            True,
            False,
            False,
            None,
        ),
        (
            "Example Township",
            "R-1",
            "pool",
            False,
            False,
            False,
            None,
        ),
    ]

    for (
        municipality,
        district,
        project,
        expected_registered,
        expected_district_registered,
        expected_project_handler,
        expected_rule_key,
    ) in cases:
        result = _get_registered_rule_set(
            municipality,
            district,
            project,
        )

        assert result["registered"] is expected_registered
        assert (
            result["district_registered"]
            is expected_district_registered
        )
        assert (
            result["project_handler"] is not None
        ) is expected_project_handler
        assert result["rule_key"] == expected_rule_key

def test_registry_supported_and_unsupported_matrix():
    from app.services.zoning_intelligence import _get_registered_rule_set

    cases = [
        (
            "Howell Township",
            "HD-4",
            "pool",
            True,
            True,
            True,
            "howell township:HD-4:pool",
        ),
        (
            "Marlboro Township",
            "CF",
            "pool",
            True,
            True,
            True,
            "marlboro township:CF:pool",
        ),
        (
            "Marlboro Township",
            "R-20",
            "pool",
            True,
            True,
            True,
            "marlboro township:R-20:pool",
        ),
        (
            "Marlboro Township",
            "VERIFY",
            "pool",
            True,
            False,
            False,
            None,
        ),
        (
            "Example Township",
            "R-1",
            "pool",
            False,
            False,
            False,
            None,
        ),
    ]

    for (
        municipality,
        district,
        project,
        expected_registered,
        expected_district_registered,
        expected_project_handler,
        expected_rule_key,
    ) in cases:
        result = _get_registered_rule_set(
            municipality,
            district,
            project,
        )

        assert result["registered"] is expected_registered
        assert (
            result["district_registered"]
            is expected_district_registered
        )
        assert (
            result["project_handler"] is not None
        ) is expected_project_handler
        assert result["rule_key"] == expected_rule_key


def test_registry_never_creates_rule_key_without_registered_match():
    from app.services.zoning_intelligence import _get_registered_rule_set

    cases = [
        ("Marlboro Township", "VERIFY", "pool"),
        ("Marlboro Township", "CF", "unknown_project"),
        ("Example Township", "R-1", "pool"),
        ("Example Township", "VERIFY", "pool"),
    ]

    for municipality, district, project in cases:
        result = _get_registered_rule_set(
            municipality,
            district,
            project,
        )

        assert result["rule_key"] is None
        assert result["project_handler"] is None

        if district.upper() == "VERIFY":
            assert result["district_registered"] is False

def test_registry_never_creates_rule_key_without_registered_match():
    from app.services.zoning_intelligence import _get_registered_rule_set

    cases = [
        ("Marlboro Township", "VERIFY", "pool"),
        ("Marlboro Township", "CF", "unknown_project"),
        ("Example Township", "R-1", "pool"),
        ("Example Township", "VERIFY", "pool"),
    ]

    for municipality, district, project in cases:
        result = _get_registered_rule_set(
            municipality,
            district,
            project,
        )

        assert result["rule_key"] is None
        assert result["project_handler"] is None

        if district.upper() == "VERIFY":
            assert result["district_registered"] is False

def test_api_unknown_project_cannot_expose_registered_cf_pool_rules():
    response = client.post(
        "/property-intelligence/analyze",
        json={
            "address": "1979 Township Drive, Marlboro, NJ 07746",
            "project_goal": "unknown_project",
        },
    )

    assert response.status_code == 200

    data = response.json()
    zoning = data["zoning_intelligence"]

    assert zoning["zoning_district"] == "CF"
    assert zoning["rules_registry"]["registered"] is True
    assert zoning["rules_registry"]["district_registered"] is True
    assert zoning["rules_registry"]["project_rules_available"] is False
    assert zoning["rules_registry"]["rule_key"] is None

    assert zoning["project_requirements"] == []

    applicability = zoning["project_rule_applicability"]

    assert applicability["status"] == "NO_RULES_AVAILABLE"
    assert applicability["applicable"] is False
    assert applicability["evaluated_requirement_count"] == 0
    assert applicability["requirements"] == []


def test_api_unresolved_marlboro_district_cannot_expose_pool_rules():
    from app.services.municipality_coverage import build_municipality_coverage

    result = build_municipality_coverage(
        municipality="Marlboro Township",
        zoning_intelligence={
            "municipality": "MARLBORO TWP",
            "zoning_district": "VERIFY",
            "bulk_requirements": [],
            "project_requirements": [],
        },
        zoning_resolution={
            "zoning_district": "VERIFY",
            "confidence": "VERIFY",
        },
        project_goal="pool",
    )

    assert result["status"] == "REGISTERED"
    assert result["municipality_registered"] is True
    assert result["zoning_resolution_supported"] is False
    assert result["district_rules_supported"] is False
    assert result["project_rules_supported"] is False
    assert result["zoning_district"] == "VERIFY"

def test_registry_contract_has_no_invalid_project_handlers_or_verify_districts():
    from app.services.zoning_intelligence import MUNICIPAL_RULES_REGISTRY

    for municipality, config in MUNICIPAL_RULES_REGISTRY.items():
        districts = config.get("districts", {})
        projects = config.get("projects", {})

        assert municipality
        assert isinstance(districts, dict)
        assert isinstance(projects, dict)

        # VERIFY is an unresolved state, not a registered district.
        assert "VERIFY" not in districts

        for district, district_config in districts.items():
            assert district
            assert district.upper() != "VERIFY"
            assert isinstance(district_config, dict)

            bulk_handler = district_config.get("bulk")

            if bulk_handler is not None:
                assert callable(bulk_handler)

        for project, project_config in projects.items():
            assert project
            assert isinstance(project_config, dict)

            project_districts = project_config.get(
                "districts",
                {},
            )

            assert isinstance(project_districts, dict)
            assert "VERIFY" not in project_districts

            for district, handler in project_districts.items():
                assert district in districts
                assert district.upper() != "VERIFY"
                assert callable(handler)


def test_registry_rule_key_requires_actual_registered_project_handler():
    from app.services.zoning_intelligence import (
        MUNICIPAL_RULES_REGISTRY,
        _get_registered_rule_set,
    )

    for municipality, config in MUNICIPAL_RULES_REGISTRY.items():
        for district in config.get("districts", {}):
            for project in config.get("projects", {}):
                result = _get_registered_rule_set(
                    municipality,
                    district,
                    project,
                )

                handler = (
                    config["projects"][project]
                    .get("districts", {})
                    .get(district)
                )

                if handler is None:
                    assert result["project_handler"] is None
                    assert result["rule_key"] is None
                else:
                    assert result["project_handler"] is handler
                    assert (
                        result["rule_key"]
                        == f"{municipality}:{district}:{project}"
                    )


def test_registry_lookup_cannot_create_rule_key_for_unknown_project():
    from app.services.zoning_intelligence import (
        MUNICIPAL_RULES_REGISTRY,
        _get_registered_rule_set,
    )

    for municipality, config in MUNICIPAL_RULES_REGISTRY.items():
        for district in config.get("districts", {}):
            result = _get_registered_rule_set(
                municipality,
                district,
                "__definitely_unregistered_project__",
            )

            assert result["project_handler"] is None
            assert result["rule_key"] is None

def test_final_zoning_contract_matrix():
    from app.services.zoning_intelligence import _get_registered_rule_set

    cases = [
        (
            "Howell Township",
            "HD-4",
            "pool",
            True,
            True,
            True,
            "howell township:HD-4:pool",
        ),
        (
            "Marlboro Township",
            "CF",
            "pool",
            True,
            True,
            True,
            "marlboro township:CF:pool",
        ),
        (
            "Marlboro Township",
            "R-20",
            "pool",
            True,
            True,
            True,
            "marlboro township:R-20:pool",
        ),
        (
            "Marlboro Township",
            "VERIFY",
            "pool",
            True,
            False,
            False,
            None,
        ),
        (
            "Marlboro Township",
            "CF",
            "unknown_project",
            True,
            True,
            False,
            None,
        ),
        (
            "Example Township",
            "R-1",
            "pool",
            False,
            False,
            False,
            None,
        ),
    ]

    for (
        municipality,
        district,
        project,
        expected_registered,
        expected_district_registered,
        expected_project_supported,
        expected_rule_key,
    ) in cases:
        result = _get_registered_rule_set(
            municipality,
            district,
            project,
        )

        assert result["registered"] is expected_registered
        assert (
            result["district_registered"]
            is expected_district_registered
        )
        assert (
            result["project_handler"] is not None
        ) is expected_project_supported
        assert result["rule_key"] == expected_rule_key

        if not expected_project_supported:
            assert result["project_handler"] is None
            assert result["rule_key"] is None

def test_api_response_rule_metadata_is_consistent_with_exposed_requirements():
    cases = [
        (
            "922 State Highway 33, Freehold, NJ 07728",
            "pool",
            "HD-4",
            "howell township:HD-4:pool",
            True,
            7,
            "PARTIALLY_APPLICABLE",
        ),
        (
            "1979 Township Drive, Marlboro, NJ 07746",
            "pool",
            "CF",
            "marlboro township:CF:pool",
            True,
            5,
            "VERIFY",
        ),
        (
            "1979 Township Drive, Marlboro, NJ 07746",
            "unknown_project",
            "CF",
            None,
            False,
            0,
            "NO_RULES_AVAILABLE",
        ),
    ]

    for (
        address,
        project_goal,
        expected_district,
        expected_rule_key,
        expected_project_rules,
        expected_count,
        expected_applicability,
    ) in cases:
        response = client.post(
            "/property-intelligence/analyze",
            json={
                "address": address,
                "project_goal": project_goal,
            },
        )

        assert response.status_code == 200

        zoning = response.json()["zoning_intelligence"]
        registry = zoning["rules_registry"]
        applicability = zoning["project_rule_applicability"]

        assert zoning["zoning_district"] == expected_district
        assert registry["rule_key"] == expected_rule_key
        assert (
            registry["project_rules_available"]
            is expected_project_rules
        )

        requirements = zoning["project_requirements"] or []

        assert len(requirements) == expected_count
        assert (
            applicability["evaluated_requirement_count"]
            == expected_count
        )
        assert applicability["status"] == expected_applicability

        if not expected_project_rules:
            assert requirements == []
            assert applicability["applicable"] is False
            assert applicability["requirements"] == []


def test_api_response_never_reports_project_rules_without_a_rule_key():
    response = client.post(
        "/property-intelligence/analyze",
        json={
            "address": "1979 Township Drive, Marlboro, NJ 07746",
            "project_goal": "unknown_project",
        },
    )

    assert response.status_code == 200

    zoning = response.json()["zoning_intelligence"]
    registry = zoning["rules_registry"]

    assert registry["project_rules_available"] is False
    assert registry["project_handler"] if "project_handler" in registry else True
    assert registry["rule_key"] is None
    assert zoning["project_requirements"] == []

def test_coverage_status_cannot_claim_project_rules_without_project_requirements():
    from app.services.municipality_coverage import build_municipality_coverage

    result = build_municipality_coverage(
        municipality="Howell Township",
        zoning_intelligence={
            "municipality": "HOWELL TWP",
            "zoning_district": "HD-4",
            "bulk_requirements": [],
            "project_requirements": [],
            "rules_registry": {
                "registered": True,
                "district_registered": True,
                "district_rules_available": True,
                "project_rules_available": True,
                "rule_key": "howell township:HD-4:pool",
            },
        },
        zoning_resolution={
            "zoning_district": "HD-4",
            "confidence": "OFFICIAL_PARCEL_SPECIFIC",
        },
        project_goal="pool",
    )

    assert result["municipality_registered"] is True
    assert result["zoning_resolution_supported"] is True
    assert result["project_rules_supported"] is False
    assert result["status"] != "PROJECT_RULES_AVAILABLE"


def test_coverage_status_claims_project_rules_only_when_requirements_exist():
    from app.services.municipality_coverage import build_municipality_coverage

    result = build_municipality_coverage(
        municipality="Howell Township",
        zoning_intelligence={
            "municipality": "HOWELL TWP",
            "zoning_district": "HD-4",
            "bulk_requirements": [],
            "project_requirements": [
                {"requirement": "Pool setback"},
            ],
            "rules_registry": {
                "registered": True,
                "district_registered": True,
                "district_rules_available": False,
                "project_rules_available": True,
                "rule_key": "howell township:HD-4:pool",
            },
        },
        zoning_resolution={
            "zoning_district": "HD-4",
            "confidence": "OFFICIAL_PARCEL_SPECIFIC",
        },
        project_goal="pool",
    )

    assert result["municipality_registered"] is True
    assert result["zoning_resolution_supported"] is True
    assert result["project_rules_supported"] is True
    assert result["status"] == "PROJECT_RULES_AVAILABLE"

def test_approval_pathway_contract_matrix():
    cases = [
        (
            "922 State Highway 33, Freehold, NJ 07728",
            "pool",
            "HD-4",
            "howell township:HD-4:pool",
            True,
            "AVAILABLE",
            "SITE_PLAN_APPROVAL",
            1,
        ),
        (
            "1979 Township Drive, Marlboro, NJ 07746",
            "pool",
            "CF",
            "marlboro township:CF:pool",
            True,
            "VERIFY",
            None,
            0,
        ),
        (
            "1979 Township Drive, Marlboro, NJ 07746",
            "unknown_project",
            "CF",
            None,
            False,
            "VERIFY",
            None,
            0,
        ),
    ]

    for (
        address,
        project,
        expected_district,
        expected_rule_key,
        expected_project_rules,
        expected_status,
        expected_primary,
        expected_requirement_count,
    ) in cases:
        response = client.post(
            "/property-intelligence/analyze",
            json={
                "address": address,
                "project_goal": project,
            },
        )

        assert response.status_code == 200

        zoning = response.json()["zoning_intelligence"]
        registry = zoning["rules_registry"]
        pathway = zoning["approval_pathway"]

        assert zoning["zoning_district"] == expected_district
        assert registry["rule_key"] == expected_rule_key
        assert (
            registry["project_rules_available"]
            is expected_project_rules
        )

        assert pathway["status"] == expected_status
        assert pathway["primary_pathway"] == expected_primary
        assert len(pathway["requirements"]) == expected_requirement_count

        if expected_primary is None:
            assert pathway["reviewing_bodies"] == []
            assert pathway["requirements"] == []
            assert pathway["source"] is None


def test_approval_pathway_never_infers_pathway_from_zoning_alone():
    response = client.post(
        "/property-intelligence/analyze",
        json={
            "address": "1979 Township Drive, Marlboro, NJ 07746",
            "project_goal": "unknown_project",
        },
    )

    assert response.status_code == 200

    zoning = response.json()["zoning_intelligence"]
    pathway = zoning["approval_pathway"]

    assert pathway["status"] == "VERIFY"
    assert pathway["primary_pathway"] is None
    assert pathway["possible_alternative"] is None
    assert pathway["reviewing_bodies"] == []
    assert pathway["requirements"] == []

def test_approval_pathway_has_single_service_owned_builder():
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[1]
    app_root = project_root / "app"

    definitions = []

    for source_file in app_root.rglob("*.py"):
        text = source_file.read_text(encoding="utf-8")
        if "def _build_approval_pathway(" in text:
            definitions.append(source_file)

    assert definitions == [
        project_root
        / "app"
        / "services"
        / "zoning_intelligence.py"
    ]


def test_main_uses_service_owned_approval_pathway_builder():
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[1]
    main_text = (
        project_root / "app" / "main.py"
    ).read_text(encoding="utf-8")

    assert (
        "from app.services.zoning_intelligence import "
        "get_zoning_intelligence, _build_approval_pathway"
    ) in main_text

    assert "_build_approval_pathway(" in main_text

def test_available_approval_pathway_preserves_authoritative_provenance():
    response = client.post(
        "/property-intelligence/analyze",
        json={
            "address": "922 State Highway 33, Freehold, NJ 07728",
            "project_goal": "pool",
        },
    )

    assert response.status_code == 200

    pathway = response.json()["zoning_intelligence"]["approval_pathway"]

    assert pathway["status"] == "AVAILABLE"
    assert pathway["requirements"]
    assert pathway["source"] is not None

    source = pathway["source"]

    assert source["source"]
    assert source["source_url"]
    assert source["authoritative"] is True

    for requirement in pathway["requirements"]:
        assert requirement["source"]
        assert requirement["source_url"]
        assert requirement["authoritative"] is True

        verification = requirement.get("verification")

        if verification:
            assert verification in pathway["verification_items"]


def test_verify_approval_pathway_has_no_unbacked_provenance():
    response = client.post(
        "/property-intelligence/analyze",
        json={
            "address": "1979 Township Drive, Marlboro, NJ 07746",
            "project_goal": "pool",
        },
    )

    assert response.status_code == 200

    pathway = response.json()["zoning_intelligence"]["approval_pathway"]

    assert pathway["status"] == "VERIFY"
    assert pathway["primary_pathway"] is None
    assert pathway["possible_alternative"] is None
    assert pathway["reviewing_bodies"] == []
    assert pathway["requirements"] == []
    assert pathway["source"] is None


def test_building_description_does_not_prove_municipal_facility():
    from app.services.rule_applicability import (
        evaluate_requirement_applicability,
    )

    result = evaluate_requirement_applicability(
        municipality="Howell Township",
        zoning_district="HD-4",
        project_goal="pool",
        property_resolution={
            "parcel": {
                "property_class": "4A",
                "building_description": "THE CABIN",
            }
        },
        requirement={
            "requirement": "Residential building prerequisite",
            "applies_to": "Private permanent residential pool",
            "registry_applicability": "APPLICABLE",
        },
    )

    assert result["status"] == "APPLICABLE"
    assert result["applicable"] is True

def test_parcel_resolution_rejects_low_confidence_identity_match():
    from app.services.address_intelligence import (
        _score_parcel,
    )

    weak_feature = {
        "attributes": {
            "OBJECTID": 999999,
            "PAMS_PIN": "9999_999_99",
            "MUNICIPALITY": "HOWELL TWP",
            "COUNTY": "MONMOUTH",
            "PROPERTY_LOCATION": "984 ROUTE 33",
            "STREET_ADDRESS": "62 BROADWAY",
            "CITY_STATE": "PT PLEASANT BEACH NJ",
            "ZIP_CODE": "08742",
            "BLOCK": "999",
            "LOT": "99",
        }
    }

    score = _score_parcel(
        weak_feature,
        geocoded_city="Freehold",
        geocoded_zip="07728",
        geocoded_address=(
            "922 State Highway 33, Freehold, New Jersey, 07728"
        ),
        longitude=-74.211066428894,
        latitude=40.23130463804,
        search_distance_meters=5,
    )

    assert score < 40



def test_parcel_identity_does_not_follow_building_description():
    response = client.post(
        "/property-intelligence/analyze",
        json={
            "address": "922 State Highway 33, Freehold, NJ 07728",
            "project_goal": "pool",
        },
    )

    assert response.status_code == 200

    parcel = response.json()["property_resolution"]["parcel"]

    assert parcel["building_description"] == "THE CABIN"
    assert parcel["property_class"] == "4A"
    assert parcel["property_use"] == "639"

def test_parcel_resolution_rejects_low_confidence_identity_match():
    from app.services.address_intelligence import (
        _score_parcel,
    )

    weak_feature = {
        "attributes": {
            "OBJECTID": 999999,
            "PAMS_PIN": "9999_999_99",
            "MUNICIPALITY": "HOWELL TWP",
            "COUNTY": "MONMOUTH",
            "PROPERTY_LOCATION": "984 ROUTE 33",
            "STREET_ADDRESS": "62 BROADWAY",
            "CITY_STATE": "PT PLEASANT BEACH NJ",
            "ZIP_CODE": "08742",
            "BLOCK": "999",
            "LOT": "99",
        }
    }

    score = _score_parcel(
        weak_feature,
        geocoded_city="Freehold",
        geocoded_zip="07728",
        geocoded_address=(
            "922 State Highway 33, Freehold, New Jersey, 07728"
        ),
        longitude=-74.211066428894,
        latitude=40.23130463804,
        search_distance_meters=5,
    )

    assert score < 40



def test_parcel_identity_does_not_follow_building_description():
    response = client.post(
        "/property-intelligence/analyze",
        json={
            "address": "922 State Highway 33, Freehold, NJ 07728",
            "project_goal": "pool",
        },
    )

    assert response.status_code == 200

    parcel = response.json()["property_resolution"]["parcel"]

    assert parcel["building_description"] == "THE CABIN"
    assert parcel["property_class"] == "4A"
    assert parcel["property_use"] == "639"


def test_existing_property_record_semantics_remain_protected():
    response = client.post(
        "/property-intelligence/analyze",
        json={
            "address": "922 State Highway 33, Freehold, NJ 07728",
            "project_goal": "pool",
        },
    )

    assert response.status_code == 200

    data = response.json()

    property_resolution = data["property_resolution"]
    parcel = property_resolution["parcel"]

    assert parcel["building_description"] == "THE CABIN"
    assert parcel["property_class"] == "4A"
    assert parcel["property_use"] == "639"

    zoning = data["zoning_intelligence"]

    assert zoning["zoning_district"] == "HD-4"



def test_parcel_identity_evidence_surfaces_address_conflicts():
    response = client.post(
        "/property-intelligence/analyze",
        json={
            "address": "922 State Highway 33, Freehold, NJ 07728",
            "project_goal": "pool",
        },
    )

    assert response.status_code == 200

    property_resolution = response.json()["property_resolution"]

    parcel_match = property_resolution["parcel_match"]

    assert parcel_match["status"] == "PARCEL_FOUND"
    assert parcel_match["match_score"] == 50
    assert parcel_match["candidate_count"] == 8

    evidence = parcel_match["identity_evidence"]

    assert evidence["match_score"] == 50
    assert evidence["search_distance_meters"] == 5
    assert evidence["address_field_conflict"] is True
    assert (
        evidence["identity_status"]
        == "CONTRADICTORY_ADDRESS_FIELDS"
    )

    assert evidence["parcel_property_location"] == "984 ROUTE 33"
    assert evidence["parcel_street_address"] == "62 BROADWAY"
    assert evidence["parcel_zip"] == "08742"


def test_parcel_identity_evidence_preserves_geocoder_identity():
    response = client.post(
        "/property-intelligence/analyze",
        json={
            "address": "922 State Highway 33, Freehold, NJ 07728",
            "project_goal": "pool",
        },
    )

    assert response.status_code == 200

    parcel_match = response.json()[
        "property_resolution"
    ]["parcel_match"]

    evidence = parcel_match["identity_evidence"]

    assert (
        evidence["geocoder_address"]
        == "922 State Highway 33, Freehold, New Jersey, 07728"
    )

    assert evidence["geocoder_city"] == "Freehold"
    assert evidence["geocoder_zip"] == "07728"


