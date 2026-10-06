from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field

from app.api.health import router as health_router
from app.api.property_records import router as property_records_router, public_router as public_property_records_router
from app.api.property_environmental_screening import router as property_environmental_screening_router
from app.api.property_zoning_candidate import router as property_zoning_candidate_router
from app.api.property_dynamic_intelligence import router as property_dynamic_intelligence_router
from app.api.engineering_jobs import router as engineering_jobs_router
from app.api.engineering_property_job_creation import router as engineering_property_job_creation_router
from app.api.engineering_command_center import router as engineering_command_center_router
from app.api.engineering_workspace import router as engineering_workspace_router
from app.api.engineering_workplace import router as engineering_workplace_router
from app.api.engineering_auth import router as engineering_auth_router
from app.api.property_auth import router as property_auth_router
from app.core.engineering_security import require_engineering_user
from app.core.property_security import require_property_user
from app.core.settings import settings
from app.services.address_intelligence import (
    resolve_new_jersey_property,
    resolve_new_jersey_parcel_object_id,
    suggest_new_jersey_addresses,
    suggest_new_jersey_parcels,
)
from app.services.zoning_intelligence import get_zoning_intelligence, _build_approval_pathway
from app.services.municipality_identity import resolve_municipality_identity
from app.services.municipality_source_registry import resolve_municipality_source
from app.services.zoning_evidence import resolve_zoning_evidence
from app.services.municipality_coverage import build_municipality_coverage
from app.services.rule_applicability import evaluate_project_rule_applicability
from app.services.zoning_resolution import resolve_property_zoning
from app.services.property_map_workflow import resolve_property_map_workflow
from app.services.environmental_constraint_evidence import build_environmental_constraint_evidence
from app.services.deployment_identity import enforce_production_database_revision
from app.services.deployment_identity import enforce_production_configuration
from app.services.deployment_identity import enforce_production_artifact_storage
from app.services.observability import configure_structured_logging, observe_request


# ============================================================
# MIDRA API
# ============================================================

configure_structured_logging(settings)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    description=(
        "MIDRA Engineering Property Intelligence API. "
        "Resolves New Jersey property addresses to statewide "
        "parcel data, determines property-specific zoning when "
        "authoritative evidence is available, and returns "
        "preliminary zoning, bulk-requirement and project "
        "intelligence."
    ),
)


@app.on_event("startup")
def enforce_release_database_revision_on_startup() -> None:
    """Fail closed in production when the live DB revision does not match this release."""
    enforce_production_database_revision(settings)
    enforce_production_configuration(settings)
    enforce_production_artifact_storage(settings)


# ============================================================
# CORS
# ============================================================

cors_origins = list(settings.PROPERTY_WEB_ORIGINS)
for configured_origin in (settings.MIDRA_ENGINEERING_WEB_ORIGIN, settings.MIDRA_WORKPLACE_WEB_ORIGIN):
    if configured_origin:
        normalized_origin = configured_origin.strip().rstrip("/")
        if normalized_origin and normalized_origin not in cors_origins:
            cors_origins.append(normalized_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Host-header protection is explicit. In production, a forgotten deployment
# allowlist fails closed because the local defaults will not match a public host.
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.API_ALLOWED_HOSTS,
)

@app.middleware("http")
async def add_request_observability(request, call_next):
    return await observe_request(request, call_next, settings)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if str(settings.APP_ENV or "").strip().lower() in {"production", "prod"}:
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response


# ============================================================
# HEALTH ROUTES
# ============================================================

app.include_router(health_router)
app.include_router(property_records_router, dependencies=[Depends(require_property_user)])
app.include_router(property_environmental_screening_router)
app.include_router(property_zoning_candidate_router)
app.include_router(property_dynamic_intelligence_router)
app.include_router(public_property_records_router)
app.include_router(property_auth_router)
app.include_router(engineering_auth_router)
app.include_router(engineering_jobs_router, dependencies=[Depends(require_engineering_user)])
app.include_router(engineering_property_job_creation_router, dependencies=[Depends(require_engineering_user)])
app.include_router(engineering_command_center_router, dependencies=[Depends(require_engineering_user)])
app.include_router(engineering_workspace_router, dependencies=[Depends(require_engineering_user)])
app.include_router(engineering_workplace_router, dependencies=[Depends(require_engineering_user)])


# ============================================================
# REQUEST MODEL
# ============================================================

class PropertyRequest(BaseModel):
    address: str = Field(
        min_length=3,
        max_length=300,
        description="Property street address.",
    )

    project_goal: str = Field(
        default="other",
        min_length=2,
        max_length=200,
        description=(
            "Intended project or property goal, such as "
            "Build a Pool, Addition, Garage, Deck, Driveway, "
            "ADU, New Home, or Subdivision."
        ),
    )

    municipality: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
        description=(
            "Optional municipality. MIDRA normally derives the "
            "municipality from the New Jersey statewide property "
            "resolution service rather than trusting user input."
        ),
    )

    parcel_object_id: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Optional exact NJ statewide parcel OBJECTID selected from "
            "MIDRA parcel search. When supplied, MIDRA resolves the parcel "
            "directly instead of geocoding the display label."
        ),
    )


# ============================================================
# ROOT
# ============================================================

@app.get(
    "/",
    summary="MIDRA API status",
)
def root() -> dict[str, str]:
    return {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "status": "online",
    }


# ============================================================
# HELPERS
# ============================================================

def _safe_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _unique_text_items(
    items: list[object] | None,
) -> list[str]:
    """
    Preserve item order while removing exact duplicate
    verification/note messages.
    """
    result: list[str] = []
    seen: set[str] = set()

    for item in items or []:
        text = _safe_text(item)

        if not text:
            continue

        if text in seen:
            continue

        seen.add(text)
        result.append(text)

    return result


def _canonical_project_goal(project_goal: str) -> str:
    value = _safe_text(project_goal).lower()

    aliases = {
        "build a pool": "pool",
        "pool": "pool",
        "swimming pool": "pool",
        "install a pool": "pool",
        "in ground pool": "pool",
        "inground pool": "pool",

        "addition": "addition",
        "home addition": "addition",

        "garage": "garage",
        "detached garage": "garage",

        "shed": "shed",
        "storage shed": "shed",

        "deck": "deck",
        "deck / patio": "deck",
        "patio": "deck",

        "driveway": "driveway",

        "adu": "adu",
        "accessory dwelling": "adu",
        "accessory dwelling unit": "adu",

        "new home": "new_home",
        "new house": "new_home",
        "single family home": "new_home",

        "subdivision": "subdivision",

        "commercial": "commercial",

        "buy": "buy",
        "buy property": "buy",

        "invest": "invest",
        "investment": "invest",

        "other": "other",
    }

    if value in aliases:
        return aliases[value]

    for phrase, normalized in aliases.items():
        if phrase in value:
            return normalized

    return "other"


def _property_resolution_status(
    resolution: dict,
) -> str:
    return _safe_text(
        resolution.get("status")
    ) or "ADDRESS_NOT_RESOLVED"


def _resolved_municipality(
    resolution: dict,
    requested_municipality: str | None,
) -> str | None:
    """
    Prefer the municipality returned by the authoritative
    property resolver.

    User-provided municipality is only a fallback when the
    statewide resolver does not provide one.
    """
    resolved = (
        resolution.get("municipality")
        or (
            resolution.get("parcel") or {}
        ).get("municipality")
    )

    if resolved:
        return _safe_text(resolved)

    if requested_municipality:
        return _safe_text(
            requested_municipality
        )

    return None


def _build_property_information(
    payload: PropertyRequest,
    resolution: dict,
) -> dict:
    parcel = resolution.get(
        "parcel"
    ) or {}

    coordinates = resolution.get(
        "coordinates"
    ) or {}

    municipality = _resolved_municipality(
        resolution,
        payload.municipality,
    )

    county = (
        resolution.get("county")
        or parcel.get("county")
    )

    state = (
        resolution.get("state")
        or "New Jersey"
    )

    return {
        "address": (
            resolution.get("matched_address")
            or payload.address
        ),
        "requested_address": payload.address,
        "municipality": municipality,
        "county": county,
        "state": state,
        "coordinates": coordinates or None,
        "parcel": parcel or None,
        "parcel_source": resolution.get("parcel_source"),
        "parcel_match": resolution.get("parcel_match"),
    }


def _build_findings(
    *,
    property_resolution: dict,
    zoning_resolution: dict,
) -> list[dict]:
    property_status = _property_resolution_status(
        property_resolution
    )

    zoning_status = _safe_text(
        zoning_resolution.get(
            "zoning_district"
        )
    ) or "VERIFY"

    if property_status == "PROPERTY_RESOLVED":
        property_meaning = (
            "The address and parcel identity were resolved "
            "through New Jersey statewide property data."
        )
    else:
        property_meaning = (
            "Address and parcel identity are reported only "
            "when supported by the New Jersey statewide "
            "property services."
        )

    zoning_confidence = _safe_text(
        zoning_resolution.get(
            "confidence"
        )
    )

    if zoning_confidence == (
        "OFFICIAL_PARCEL_SPECIFIC"
    ):
        zoning_meaning = (
            "The zoning district is supported by "
            "property-specific authoritative municipal "
            "evidence for the resolved parcel."
        )

    elif zoning_confidence == (
        "PARCEL_ZONING_RESOLVED_PROJECT_RULES_AVAILABLE"
    ):
        zoning_meaning = (
            "The zoning district is supported by "
            "property-specific authoritative municipal "
            "evidence, and project-specific municipal "
            "requirements are available for the requested "
            "project."
        )

    elif zoning_status != "VERIFY":
        zoning_meaning = (
            "A zoning district was identified, but the "
            "property-specific evidence should still be "
            "reviewed before design or permitting."
        )

    else:
        zoning_meaning = (
            "The zoning district is reported only when "
            "supported by authoritative property-specific "
            "zoning evidence."
        )

    return [
        {
            "area": "Property",
            "status": property_status,
            "meaning": property_meaning,
        },
        {
            "area": "Zoning",
            "status": zoning_status,
            "meaning": zoning_meaning,
        },
        {
            "area": "Flood",
            "status": "NOT_EVALUATED",
            "meaning": (
                "No authoritative parcel-specific flood hazard "
                "evaluation has been performed in this analysis. "
                "This is not a finding that flood hazard is present or absent."
            ),
        },
        {
            "area": "Wetlands",
            "status": "NOT_EVALUATED",
            "meaning": (
                "No authoritative parcel-specific wetlands "
                "evaluation has been performed in this analysis. "
                "This is not a finding that wetlands are present or absent."
            ),
        },
        {
            "area": "Development",
            "status": "Potential",
            "meaning": (
                "Development feasibility remains subject to "
                "the applicable zoning district, bulk "
                "requirements, environmental constraints "
                "and municipal approvals."
            ),
        },
    ]





# ============================================================
# PROPERTY-SPECIFIC ZONING MERGE
# ============================================================

def _merge_property_specific_zoning(
    *,
    zoning_intelligence: dict,
    zoning_resolution: dict,
) -> dict:
    """
    Merge authoritative parcel-specific zoning into the generic
    municipal rules result.

    The API layer does not know which municipalities or districts
    are supported. It consumes the rule-registry metadata returned
    by the zoning engine.
    """
    merged = dict(
        zoning_intelligence
    )

    resolved_district = _safe_text(
        zoning_resolution.get("zoning_district")
    )

    resolved_confidence = _safe_text(
        zoning_resolution.get("confidence")
    )

    if (
        resolved_district
        and resolved_district.upper()
        not in {"VERIFY", "UNKNOWN", "NOT RESOLVED"}
        and resolved_confidence
        == "OFFICIAL_PARCEL_SPECIFIC"
    ):
        merged["zoning_district"] = resolved_district

        if zoning_resolution.get("zoning_name"):
            merged["zoning_name"] = (
                zoning_resolution["zoning_name"]
            )

        merged["property_specific_zoning"] = (
            zoning_resolution
        )

        for field in (
            "source",
            "zoning_map_source",
            "source_retrieved_at",
        ):
            if zoning_resolution.get(field):
                merged[field] = zoning_resolution[field]

        rules_registry = (
            merged.get("rules_registry") or {}
        )

        district_rules_available = bool(
            rules_registry.get(
                "district_rules_available"
            )
        )

        project_rules_available = bool(
            rules_registry.get(
                "project_rules_available"
            )
        )

        # A verified district is the only condition under which
        # district-specific bulk rules may survive the merge.
        if district_rules_available:
            merged["bulk_requirements"] = list(
                merged.get("bulk_requirements") or []
            )
        else:
            merged["bulk_requirements"] = []

        # Likewise, project rules must have been selected by the
        # registry for the actual municipality/district/project.
        if project_rules_available:
            merged["project_requirements"] = list(
                merged.get("project_requirements") or []
            )
        else:
            merged["project_requirements"] = []

        verification_items = list(
            zoning_resolution.get(
                "verification_items"
            ) or []
        )

        if district_rules_available:
            verification_items.append(
                "District-specific bulk standards were selected "
                "through the MIDRA municipality/district rules registry."
            )
        else:
            verification_items.append(
                "District-specific bulk standards for the resolved "
                "zoning district are not yet registered in MIDRA."
            )

        if project_rules_available:
            verification_items.append(
                "Project-specific requirements were selected through "
                "the MIDRA municipality/district/project rules registry."
            )
        else:
            verification_items.append(
                "No project-specific rule set is registered for the "
                "resolved municipality/district/project combination."
            )

        merged["verification_items"] = (
            _unique_text_items(
                verification_items
            )
        )

        if project_rules_available:
            merged["confidence"] = (
                "PARCEL_ZONING_RESOLVED_PROJECT_RULES_AVAILABLE"
            )
        elif district_rules_available:
            merged["confidence"] = (
                "PARCEL_ZONING_RESOLVED_RULES_AVAILABLE"
            )
        else:
            merged["confidence"] = (
                "PARCEL_ZONING_RESOLVED_RULES_PENDING"
            )

        notes = list(
            zoning_resolution.get("notes") or []
        )

        notes.append(
            (
                "Property-specific zoning controls this "
                "assessment. District-specific requirements "
                "were selected through the MIDRA rules registry."
            )
        )

        merged["notes"] = _unique_text_items(
            notes
        )

        return merged

    merged["property_specific_zoning"] = (
        zoning_resolution
    )

    verification_items = list(
        merged.get("verification_items") or []
    )

    verification_items.extend(
        zoning_resolution.get(
            "verification_items"
        ) or []
    )

    verification_items.append(
        (
            "Property-specific zoning could not be "
            "confirmed from authoritative parcel evidence."
        )
    )

    merged["verification_items"] = (
        _unique_text_items(
            verification_items
        )
    )

    return merged


# ============================================================
# PROPERTY INTELLIGENCE
# ============================================================

@app.get(
    "/property-intelligence/suggest",
    summary="Suggest New Jersey property addresses",
)
def suggest_property_addresses(
    q: str = "",
) -> dict:
    return suggest_new_jersey_addresses(q)


@app.get(
    "/property-intelligence/parcel-suggest",
    summary="Suggest New Jersey parcels by block/lot or municipal block",
)
def suggest_property_parcels(
    q: str = "",
) -> dict:
    return suggest_new_jersey_parcels(q)


@app.post(
    "/property-intelligence/analyze",
    summary="Analyze Property",
    description=(
        "Resolve a New Jersey property address, identify the "
        "associated parcel, determine property-specific zoning "
        "and provide preliminary municipal and project intelligence."
    ),
)
def analyze_property(
    payload: PropertyRequest,
) -> dict:

    # ========================================================
    # STEP 1 â€” ADDRESS + PARCEL RESOLUTION
    # ========================================================

    property_resolution = (
        resolve_new_jersey_parcel_object_id(
            payload.parcel_object_id,
            requested_label=payload.address,
        )
        if payload.parcel_object_id is not None
        else resolve_new_jersey_property(
            payload.address
        )
    )

    property_status = (
        _property_resolution_status(
            property_resolution
        )
    )

    municipality = (
        _resolved_municipality(
            property_resolution,
            payload.municipality,
        )
    )

    parcel = (
        property_resolution.get(
            "parcel"
        )
    )

    # ========================================================
    # STEP 2 â€” PROPERTY-SPECIFIC ZONING
    # ========================================================

    zoning_resolution = (
        resolve_property_zoning(
            municipality=municipality,
            parcel=parcel,
        )
    )

    # ========================================================
    # STEP 2B â€” STAGE C ZONING EVIDENCE
    # ========================================================
    #
    # Stage C exposes verified parcel-specific zoning evidence
    # separately. It does not replace the existing zoning resolver
    # or change downstream zoning/applicability logic.
    # ========================================================

    zoning_evidence = (
        resolve_zoning_evidence(
            municipality=municipality,
            parcel=parcel,
              zoning_resolution=zoning_resolution,
        )
    )

    # ========================================================
    # STEP 3 â€” MUNICIPAL ZONING INTELLIGENCE
    # ========================================================

    if municipality:

        zoning_intelligence = (
            get_zoning_intelligence(
                municipality=municipality,
                project_goal=payload.project_goal,
                property_zoning=zoning_resolution,
            )
        )

    else:

        zoning_intelligence = {
            "municipality": None,

            "zoning_district": "VERIFY",

            "source": {
                "municipality": None,
                "source_type": "NOT_RESOLVED",
                "url": None,
                "description": (
                    "Municipality could not be resolved from "
                    "the property."
                ),
                "authoritative": False,
            },

            "bulk_requirements": [],

            "project_requirements": [],

            "permitted_uses": [],

            "conditional_uses": [],

            "verification_items": [
                (
                    "Municipality could not be resolved, so "
                    "municipal zoning intelligence was not "
                    "reported."
                )
            ],

            "source_retrieved_at": None,

            "confidence": (
                "MUNICIPALITY_NOT_RESOLVED"
            ),

            "notes": [],
        }

    # ========================================================
    # STEP 3A â€” MERGE PROPERTY-SPECIFIC ZONING
    # ========================================================

    zoning_intelligence = (
        _merge_property_specific_zoning(
            zoning_intelligence=zoning_intelligence,
            zoning_resolution=zoning_resolution,
        )
    )

    # Preserve the zoning response contract even when an upstream
    # property/municipality/source resolution path returns partial data.
    # Missing registry metadata must mean "not established", never a
    # structurally missing contract.
    zoning_intelligence.setdefault(
        "rules_registry",
        {
            "registered": False,
            "district_registered": False,
            "district_rules_available": False,
            "project_rules_available": False,
            "rule_key": None,
        },
    )

    # ========================================================
    # ========================================================
    # STEP 3B â€” MUNICIPALITY IDENTITY
    # ========================================================
    #
    # Stage A establishes statewide municipality identity only.
    # It does not determine zoning, source verification, or rules.
    # ========================================================
    municipality_identity = resolve_municipality_identity(
        municipality=municipality,
        county=(
            (property_resolution or {}).get("county")
            or zoning_resolution.get("county")
        ),
        state=(
            (property_resolution or {}).get("state")
            or "New Jersey"
        ),
        municipality_code=(
            ((property_resolution or {}).get("parcel") or {}).get(
                "municipality_code"
            )
        ),
    )

    # ========================================================
    # STEP 3B â€” MUNICIPALITY SOURCE REGISTRY
    # ========================================================
    #
    # Stage B identifies official municipal zoning sources only.
    # It does not resolve parcel zoning and does not establish
    # project-rule applicability.
    # ========================================================
    municipality_source_registry = (
        resolve_municipality_source(municipality)
    )

    # STEP 3B â€” MUNICIPALITY COVERAGE
    # ========================================================
    #
    # Coverage is derived from the same municipality registry,
    # property-specific zoning result, and district/project rules
    # used by the intelligence engine.
    #
    # It is metadata only: it does not change zoning decisions.
    # ========================================================

    zoning_intelligence["coverage"] = (
        build_municipality_coverage(
            municipality=municipality,
            zoning_intelligence=zoning_intelligence,
            zoning_resolution=zoning_resolution,
            project_goal=payload.project_goal,
            municipality_source_registry=municipality_source_registry,
        )
    )

    # ========================================================
    # STEP 3B2 — PROPERTY MAP ARTIFACTS
    # ========================================================
    #
    # Map artifacts are resolved independently from zoning/legal promotion.
    # A missing tax map never changes the zoning or approval result.
    # ========================================================

    property_maps = resolve_property_map_workflow(
        municipality=municipality,
        block=((parcel or {}).get("block") if isinstance(parcel, dict) else None),
        lot=((parcel or {}).get("lot") if isinstance(parcel, dict) else None),
        municipality_source_registry=municipality_source_registry,
        zoning_resolution=zoning_resolution,
    )

    # ========================================================
    # STEP 3C â€” PROJECT RULE APPLICABILITY
    # ========================================================

    zoning_intelligence["project_rule_applicability"] = (
        evaluate_project_rule_applicability(
            municipality=municipality,
            zoning_district=zoning_intelligence.get(
                "zoning_district"
            ),
            project_goal=payload.project_goal,
            zoning_resolution=zoning_resolution,
            property_resolution=property_resolution,
            project_requirements=zoning_intelligence.get(
                "project_requirements"
            ),
        )
    )


    # ========================================================
    # STEP 4 â€” PROPERTY INFORMATION
    # ========================================================

    property_information = (
        _build_property_information(
            payload,
            property_resolution,
        )
    )

    # ========================================================
    # STEP 5 â€” FINDINGS
    # ========================================================

    findings = _build_findings(
        property_resolution=property_resolution,
        zoning_resolution=zoning_resolution,
    )

    environmental_constraints = build_environmental_constraint_evidence(
        property_resolution=property_resolution,
    )

    # ========================================================
    # STEP 6 â€” FINAL VERIFICATION ITEMS
    # ========================================================

    verification_items: list[str] = []

    verification_items.extend(
        property_resolution.get(
            "verification_items"
        ) or []
    )

    verification_items.extend(
        zoning_resolution.get(
            "verification_items"
        ) or []
    )

    verification_items.extend(
        zoning_intelligence.get(
            "verification_items"
        ) or []
    )

    verification_items = (
        _unique_text_items(
            verification_items
        )
    )

    # ========================================================
    approval_pathway = _build_approval_pathway(
        project_requirements=zoning_intelligence.get(
            "project_requirements",
            [],
        ),
        project_rules_available=bool(
            zoning_intelligence.get(
                "rules_registry",
                {}
            ).get(
                "project_rules_available",
                False,
            )
        ),
    )

    zoning_intelligence["approval_pathway"] = approval_pathway
    # STEP 7 â€” SUMMARY
    # ========================================================

    zoning_confidence = _safe_text(
        zoning_resolution.get(
            "confidence"
        )
    )

    if (
        property_status == "PROPERTY_RESOLVED"
        and zoning_confidence
        == "PARCEL_ZONING_RESOLVED_PROJECT_RULES_AVAILABLE"
    ):

        summary = (
            "The property address and parcel were successfully "
            "resolved through New Jersey statewide property data. "
            "The parcel-specific zoning district was confirmed "
            "through authoritative municipal evidence, and "
            "project-specific municipal requirements are "
            "available for the requested project."
        )

    elif (
        property_status == "PROPERTY_RESOLVED"
        and zoning_confidence
        == "OFFICIAL_PARCEL_SPECIFIC"
    ):

        summary = (
            "The property address and parcel were successfully "
            "resolved through New Jersey statewide property data. "
            "The property-specific zoning district was confirmed "
            "through authoritative municipal evidence."
        )

    elif property_status == (
        "PROPERTY_RESOLVED"
    ):

        summary = (
            "The property address and parcel were successfully "
            "resolved through New Jersey statewide property data. "
            "Property-specific zoning is evaluated separately "
            "using authoritative municipal evidence."
        )

    else:

        summary = (
            "The property could not yet be fully resolved to a "
            "verified parcel. Zoning and development requirements "
            "must therefore be treated as preliminary until the "
            "property identity is confirmed."
        )

    # ========================================================
    # STEP 8 â€” NEXT STEP
    # ========================================================

    if (
        zoning_confidence
        == "PARCEL_ZONING_RESOLVED_PROJECT_RULES_AVAILABLE"
    ):
        next_step = (
            "Review the available project-specific municipal "
            "requirements and the applicable registered district "
            "standards, verify environmental constraints, and "
            "confirm the municipal approval pathway before design."
        )

    else:
        next_step = (
            "Confirm the resolved property and parcel, identify "
            "the applicable zoning district, review current "
            "municipal bulk requirements and project-specific "
            "regulations, verify environmental constraints, and "
            "confirm the municipal approval pathway before "
            "design."
        )

    # ========================================================
    # STEP 9 â€” COMPLETE RESPONSE
    # ========================================================

    return {
    "mode": "preliminary",

        "property": property_information,

        "property_resolution": (
            property_resolution
        ),

        "municipality_identity": (
            municipality_identity
        ),

        "municipality_source_registry": (
            municipality_source_registry
        ),
        "property_maps": (
            property_maps
        ),
        "zoning_evidence": (
            zoning_evidence
        ),

        "zoning_resolution": (
            zoning_resolution
        ),

        "project": {
            "goal": payload.project_goal,

            "normalized_goal": (
                _canonical_project_goal(
                    payload.project_goal
                )
            ),
        },

        "summary": summary,

        "findings": findings,

        "environmental_constraints": environmental_constraints,

        "zoning_intelligence": (
            zoning_intelligence
        ),

        "verification_items": (
            verification_items
        ),

        "next_step": next_step,

        "disclaimer": (
            "MIDRA Property Intelligence is preliminary "
            "property-development information. Address, parcel, "
            "zoning, bulk requirements, environmental constraints "
            "and permitting requirements must be verified with "
            "the applicable authoritative sources and qualified "
            "professionals before design, construction or "
            "permitting."
        ),
    }










