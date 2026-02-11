"""
Operations dashboard for AutoSRE demo (Phase 2).

Provides: login, services list, service detail with Deployments panel and Rollback.
Health endpoint returns degraded until rollback is executed (for recovery verification).
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"

# In-memory state: after POST rollback, health becomes healthy (deterministic demo)
_rollback_done = False

SERVICES = [
    {"id": "checkout", "name": "Checkout"},
    {"id": "payments", "name": "Payments"},
]

DEPLOYMENTS_BY_SERVICE = {
    "checkout": [
        {"version": "v1.4.2", "timestamp": "2025-02-11T10:00:00Z", "status": "deployed"},
        {"version": "v1.4.1", "timestamp": "2025-02-11T09:30:00Z", "status": "deployed"},
    ],
    "payments": [
        {"version": "v2.0.1", "timestamp": "2025-02-11T09:00:00Z", "status": "deployed"},
    ],
}

app = FastAPI(title="AutoSRE Operations Dashboard", version="0.1.0")


class LoginBody(BaseModel):
    """Demo login (any credentials accepted)."""

    username: str = "demo"
    password: str = "demo"


class RollbackBody(BaseModel):
    """Rollback request body."""

    to_version: str


@app.get("/")
def index():
    """Serve login page."""
    return FileResponse(STATIC_DIR / "login.html")


@app.get("/services")
def services_page():
    """Serve services list page."""
    return FileResponse(STATIC_DIR / "services.html")


@app.get("/services/{service_id}")
def service_detail_page(service_id: str):
    """Serve service detail page (Deployments panel with Rollback)."""
    if service_id not in [s["id"] for s in SERVICES]:
        raise HTTPException(status_code=404, detail="Service not found")
    return FileResponse(STATIC_DIR / "service.html")


@app.post("/api/login")
def api_login(body: LoginBody):
    """Demo login: accept any credentials, redirect to services."""
    return RedirectResponse(url="/services", status_code=303)


@app.get("/api/services")
def api_services():
    """List services."""
    return {"services": SERVICES}


@app.get("/api/services/{service_id}")
def api_service_detail(service_id: str):
    """Service detail with deployments."""
    if service_id not in [s["id"] for s in SERVICES]:
        raise HTTPException(status_code=404, detail="Service not found")
    deployments = DEPLOYMENTS_BY_SERVICE.get(service_id, [])
    name = next(s["name"] for s in SERVICES if s["id"] == service_id)
    return {"id": service_id, "name": name, "deployments": deployments}


@app.get("/api/services/{service_id}/deployments")
def api_deployments(service_id: str):
    """List deployments for a service."""
    if service_id not in DEPLOYMENTS_BY_SERVICE:
        raise HTTPException(status_code=404, detail="Service not found")
    return {"deployments": DEPLOYMENTS_BY_SERVICE[service_id]}


@app.post("/api/services/{service_id}/rollback")
def api_rollback(service_id: str, body: RollbackBody):
    """Execute rollback to given version; sets health to healthy for demo."""
    global _rollback_done
    if service_id not in [s["id"] for s in SERVICES]:
        raise HTTPException(status_code=404, detail="Service not found")
    _rollback_done = True
    return {"ok": True, "rolled_back_to": body.to_version}


@app.get("/api/health")
def api_health():
    """Health/metrics: degraded until rollback has been executed (for recovery verification)."""
    status = "healthy" if _rollback_done else "degraded"
    return {"status": status}


def reset_demo_state():
    """Reset rollback state (for repeated demo runs)."""
    global _rollback_done
    _rollback_done = False


# Mount static assets (CSS, etc.) if needed later
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=3000)
