from app.services.property_map_workflow import (
    _flatten_registry_sources,
    resolve_property_map_workflow,
)


def test_registry_zoning_map_is_exposed_as_zoning_map_artifact():
    registry = {
        "sources": {
            "zoning_map": {
                "url": "https://example.gov/ZoningMap.pdf",
                "source_type": "municipal_zoning_map",
                "authoritative": True,
            }
        }
    }
    result = resolve_property_map_workflow(
        municipality="Example Township",
        block="10",
        lot="2",
        municipality_source_registry=registry,
        zoning_resolution=None,
    )
    assert result["zoning_map"]["status"] == "RESOLVED"
    assert result["zoning_map"]["source_url"] == "https://example.gov/ZoningMap.pdf"
    assert result["tax_map"]["status"] == "VERIFY"


def test_registry_tax_map_sheet_is_preserved_when_explicit():
    registry = {
        "sources": {
            "tax_map": {
                "url": "https://example.gov/taxmaps/sheet-7.pdf",
                "source_type": "municipal_tax_map",
                "authoritative": True,
                "tax_map_sheet": "7",
                "block": "10",
                "lot": "2",
            }
        }
    }
    result = resolve_property_map_workflow(
        municipality="Example Township",
        block="10",
        lot="2",
        municipality_source_registry=registry,
        zoning_resolution=None,
    )
    assert result["tax_map"]["status"] == "RESOLVED"
    assert result["tax_map"]["tax_map_sheet"] == "7"
    assert result["tax_map"]["sheet_status"] == "RESOLVED"


def test_non_map_registry_sources_do_not_become_map_artifacts():
    sources = _flatten_registry_sources({
        "sources": {
            "zoning_page": {
                "url": "https://example.gov/zoning",
                "source_type": "municipal_land_use_page",
                "authoritative": True,
            }
        }
    })
    result = resolve_property_map_workflow(
        municipality="Example Township",
        block="10",
        lot="2",
        municipality_source_registry={"sources": {
            "zoning_page": {
                "url": "https://example.gov/zoning",
                "source_type": "municipal_land_use_page",
                "authoritative": True,
            }
        }},
        zoning_resolution=None,
    )
    assert sources[0]["source_role"] is None
    assert result["zoning_map"]["status"] == "VERIFY"
    assert result["tax_map"]["status"] == "VERIFY"

def test_official_zoning_page_is_not_promoted_to_zoning_map():
    result = resolve_property_map_workflow(
        municipality="Example Township",
        block="10",
        lot="2",
        municipality_source_registry={
            "sources": {
                "zoning_page": {
                    "url": "https://example.gov/zoning",
                    "source_type": "municipal_land_use_page",
                    "authoritative": True,
                }
            }
        },
        zoning_resolution=None,
    )
    assert result["zoning_map"]["status"] == "VERIFY"
    assert result["zoning_map"]["reason"] == "NO_EXPLICIT_ZONING_MAP_SOURCE"
