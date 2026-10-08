import secrets
from urllib.parse import urlsplit

from fastapi import Request
from starlette.responses import JSONResponse


def validate_host(host: str) -> None:
    if host != "127.0.0.1":
        raise ValueError("ReelHive UI binds only to 127.0.0.1")


async def protect(request: Request, call_next, token: str):
    try:
        host = urlsplit("http://" + request.headers.get("host", ""))
        valid_host = host.hostname in {"127.0.0.1", "localhost"} and not host.username and not host.password
        port = host.port or 80
    except ValueError:
        valid_host, port = False, 80
    if not valid_host:
        return JSONResponse({"detail": "Invalid Host"}, status_code=403)
    if request.url.path.startswith("/api"):
        supplied = request.headers.get("authorization", "").removeprefix("Bearer ") or request.query_params.get(
            "token", ""
        )
        if not supplied or not secrets.compare_digest(supplied, token):
            return JSONResponse({"detail": "Launch token required"}, status_code=401)
        origin = request.headers.get("origin")
        allowed = {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}
        if port == 80:
            allowed |= {"http://127.0.0.1", "http://localhost"}
        if (origin and origin not in allowed) or (request.method in {"POST", "PUT", "DELETE", "PATCH"} and not origin):
            return JSONResponse({"detail": "Invalid Origin"}, status_code=403)
        if request.method in {"POST", "PUT", "PATCH"}:
            limit, data = 11 * 1024 * 1024, bytearray()
            async for chunk in request.stream():
                data.extend(chunk)
                if len(data) > limit:
                    return JSONResponse({"detail": "Request exceeds 11 MB"}, status_code=413)
            request._body = bytes(data)
    response = await call_next(request)
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api") else "no-cache"
    return response
