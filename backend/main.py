from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

from api.webhook import router as webhook_router
from api.admin import router as admin_router

load_dotenv()

app = FastAPI()

# ---------------------------------------------------------------------------
# CORS — restrict to your frontend origin in production via FRONTEND_ORIGIN.
# Falls back to allowing all origins in development.
# ---------------------------------------------------------------------------
_origin = os.getenv("FRONTEND_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_origin] if _origin != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router, prefix="/webhook")
app.include_router(admin_router, prefix="/admin", tags=["admin"])


@app.get("/")
def read_root():
    return {"Hello": "World"}
