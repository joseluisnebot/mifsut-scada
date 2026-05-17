import os
import hmac
import hashlib
import base64
import json
import logging
from datetime import date
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("license")

LICENSE_TOKEN  = os.getenv("LICENSE_TOKEN", "")
LICENSE_SECRET = os.getenv("LICENSE_SECRET", "")


def _verify(token: str, secret: str) -> bool:
    try:
        payload_b64, sig = token.rsplit(".", 1)
        expected = hmac.new(
            secret.encode(), payload_b64.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, sig):
            return False
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "=="))
        exp = date.fromisoformat(payload["exp"])
        return date.today() <= exp
    except Exception:
        return False


def license_ok() -> bool:
    # Sin LICENSE_SECRET configurado → modo libre (desarrollo / demo)
    if not LICENSE_SECRET:
        return True
    return _verify(LICENSE_TOKEN, LICENSE_SECRET)


async def license_middleware(request: Request, call_next):
    exempt = {"/health", "/docs", "/openapi.json", "/redoc"}
    if request.url.path in exempt:
        return await call_next(request)
    if not license_ok():
        logger.warning("License invalid or expired")
        return JSONResponse(status_code=503, content={"detail": "Service unavailable"})
    return await call_next(request)
