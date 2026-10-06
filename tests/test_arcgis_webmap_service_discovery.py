from app.services.arcgis_webmap_service_discovery import discover_arcgis_webmap_services


def test_discovers_explicit_feature_service_and_district_field():
    result = discover_arcgis_webmap_services(
        {
            "operationalLayers": [
                {
                    "title": "Perth Amboy Zoning",
                    "url": "https://services7.arcgis.com/example/arcgis/rest/services/Zoning/FeatureServer/0",
                    "itemId": "3c1ccbb8999b4dbfb5e08ed7d252d226",
                    "layerType": "ArcGISFeatureLayer",
                    "layerDefinition": {
                        "fieldConfigurations": [
                            {"alias": "Zone District", "name": "Zone_code"},
                        ]
                    },
                }
            ]
        }
    )
    assert result["status"] == "WEBMAP_SERVICES_DISCOVERED"
    assert result["layers"][0]["district_field"] == "Zone_code"
    assert result["layers"][0]["item_id"] == "3c1ccbb8999b4dbfb5e08ed7d252d226"


def test_ignores_non_feature_service_and_missing_url():
    result = discover_arcgis_webmap_services(
        {
            "operationalLayers": [
                {"title": "Basemap", "url": "https://example.com/MapServer"},
                {"title": "No URL"},
            ]
        }
    )
    assert result == {"status": "WEBMAP_FEATURE_SERVICES_NOT_FOUND", "layers": []}


def test_never_infers_service_from_item_id():
    result = discover_arcgis_webmap_services(
        {"operationalLayers": [{"itemId": "3c1ccbb8999b4dbfb5e08ed7d252d226", "title": "Zoning"}]}
    )
    assert result["layers"] == []


def test_handles_missing_operational_layers():
    result = discover_arcgis_webmap_services({})
    assert result["status"] == "WEBMAP_OPERATIONAL_LAYERS_NOT_FOUND"
