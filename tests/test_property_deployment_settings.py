from app.core.settings import Settings


def make_settings(origins: str) -> Settings:
    return Settings(
        POSTGRES_PASSWORD="validation-only",
        MIDRA_PROPERTY_WEB_ORIGINS=origins,
    )


def test_property_web_origins_are_normalized_and_deduplicated():
    settings=make_settings(
        "https://property.example.com/, https://property.example.com, http://localhost:4322"
    )
    assert settings.PROPERTY_WEB_ORIGINS==[
        "https://property.example.com",
        "http://localhost:4322",
    ]


def test_property_web_origins_ignore_blank_entries():
    settings=make_settings("https://property.example.com, ,")
    assert settings.PROPERTY_WEB_ORIGINS==["https://property.example.com"]
