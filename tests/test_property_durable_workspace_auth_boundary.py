from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_durable_property_router_requires_property_user():
    main=(ROOT/"app/main.py").read_text(encoding="utf-8")
    assert "from app.core.property_security import require_property_user" in main
    assert "app.include_router(property_records_router, dependencies=[Depends(require_property_user)])" in main


def test_public_property_intelligence_routes_are_not_wrapped_by_property_session_dependency():
    main=(ROOT/"app/main.py").read_text(encoding="utf-8")
    assert "app.include_router(property_environmental_screening_router)" in main
    assert "app.include_router(property_zoning_candidate_router)" in main
    assert "dependencies=[Depends(require_property_user)])\napp.include_router(property_environmental_screening_router)" in main
