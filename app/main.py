from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="MIDRA API",
    description="Property Intelligence Platform API",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "application": "MIDRA API",
        "version": "1.0.0",
        "status": "online",
        "message": "Welcome to the MIDRA Property Intelligence Platform"
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy"
    }