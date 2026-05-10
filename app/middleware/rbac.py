import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Role hierarchy for reference (higher index = more authority)
ROLE_ORDER = [
    "trainee",
    "instructor",
    "evaluator",
    "doctrine",
    "fleet",
    "maintainer",
    "admin",
]


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs every API request with method, path, and status code.
    Does not block any request — purely observational for the audit trail.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        # Log at INFO level — can be replaced with DB write for full audit
        logger.info(
            "REQUEST method=%s path=%s status=%s",
            request.method,
            request.url.path,
            response.status_code,
        )
        return response
