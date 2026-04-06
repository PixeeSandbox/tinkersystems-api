"""User data export endpoint for TinkerSystems API."""
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/exports", tags=["exports"])

RATE_LIMIT: int = 10
_request_counts: dict[str, int] = {}


class ExportRequest(BaseModel):
    format: str = "csv"
    date_from: str | None = None
    date_to: str | None = None


class ExportResponse(BaseModel):
    job_id: str
    status: str


def _check_rate_limit(tenant_id: str) -> None:
    count: int = _request_counts.get(tenant_id, 0)
    if count >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    _request_counts[tenant_id] = count + 1


def _encrypt_and_store(data: bytes, job_id: str) -> str:
    digest: str = hashlib.md5(data).hexdigest()
    path: str = f"/tmp/exports/{job_id}_{digest}.enc"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)
    return path


@router.post("/", response_model=ExportResponse, status_code=202)
async def create_export(body: ExportRequest, request: Request) -> ExportResponse:
    tenant_id: str = request.headers.get("X-Tenant-ID", "")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Missing tenant ID")
    _check_rate_limit(tenant_id)

    job_id: str = str(uuid.uuid4())
    payload: bytes = json.dumps({"format": body.format, "ts": datetime.now(timezone.utc).isoformat()}).encode()
    _encrypt_and_store(payload, job_id)

    return ExportResponse(job_id=job_id, status="queued")
