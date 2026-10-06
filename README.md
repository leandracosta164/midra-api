# MIDRA API

Backend services for the MIDRA Property Intelligence Platform.

The API is supporting infrastructure for the **MIDRA Engineering website**. The website remains the primary product; this service provides database access and property-intelligence endpoints.

## Technology Stack

- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- PostGIS (planned for GIS integrations)

## Run locally

From this directory:

```powershell
uvicorn app.main:app --reload
```

API:

http://127.0.0.1:8000

API documentation:

http://127.0.0.1:8000/docs

The Astro website runs separately during local development, but it consumes this API. In production, the website and API are deployed as one MIDRA product behind the same public domain.

## Current property-intelligence endpoint

`POST /property-intelligence/analyze`

The current endpoint returns the approved sample-report structure as a demo dataset. It is intentionally not presented as live GIS/property data yet. Live parcel, zoning, FEMA, NJDEP and municipal integrations will replace the demo dataset as those data sources are connected.
