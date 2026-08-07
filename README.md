# MIDRA API

Backend services for the MIDRA Property Intelligence Platform.

## Technology Stack

- FastAPI
- PostgreSQL
- PostGIS
- SQLAlchemy
- Alembic

## Run locally

Create a virtual environment.

Install dependencies.

```bash
pip install -r requirements.txt
```

Start the server.

```bash
uvicorn app.main:app --reload
```

Open:

http://127.0.0.1:8000

API Documentation:

http://127.0.0.1:8000/docs

ReDoc:

http://127.0.0.1:8000/redoc