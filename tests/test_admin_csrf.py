"""
Regression test for the Piccolo Admin CSRF lockout that broke admin login.

Piccolo's CSRFMiddleware checks the Origin/Referer header only when the request
is served over HTTPS (`request.base_url.is_secure`), and accepts a request only
if that header's hostname appears in `allowed_hosts`. Calliope never set
`allowed_hosts`, which was harmless for years: behind Cloud Run's TLS-terminating
proxy, uvicorn ran with --proxy-headers but without --forwarded-allow-ips, so it
discarded X-Forwarded-Proto and the app believed it was serving plain HTTP. The
referer check was therefore skipped entirely.

Adding --forwarded-allow-ips in #86 made the app correctly see HTTPS, which armed
the check against an empty allowed_hosts -- `hostname in []` is always False -- so
every admin login POST began returning 403 "Referer or origin is incorrect",
regardless of the password.

Run with:
    PINECONE_API_KEY=dummy OPENAI_API_KEY=dummy uv run pytest tests/test_admin_csrf.py
"""

from piccolo_api.csrf.middleware import CSRFMiddleware
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from calliope.settings import settings

PROD_HOST = "calliope.chrisimmel.com"


def _build_client(allowed_hosts: list[str]) -> TestClient:
    """
    A minimal HTTPS app guarded by the same CSRF middleware Piccolo Admin uses.
    """

    async def ok(_request):
        return PlainTextResponse("reached the endpoint")

    app = Starlette(
        routes=[Route("/login/", ok, methods=["GET", "POST"])],
        middleware=[],
    )
    wrapped = CSRFMiddleware(app, allowed_hosts=allowed_hosts)
    return TestClient(wrapped, base_url=f"https://{PROD_HOST}")


def _post_with_origin(client: TestClient, origin: str):
    """
    Perform the CSRF double-submit handshake, then POST from `origin`.
    """
    client.get("/login/")
    token = client.cookies["csrftoken"]
    return client.post(
        "/login/",
        headers={
            "X-CSRFToken": token,
            "Origin": origin,
            "Referer": f"{origin}/admin/",
        },
    )


def test_settings_expose_the_hosts_that_serve_the_admin():
    hosts = settings.admin_allowed_hosts

    assert PROD_HOST in hosts
    assert "calliope-59295831264.us-central1.run.app" in hosts
    # Local development must keep working.
    assert "localhost" in hosts
    assert "127.0.0.1" in hosts


def test_configured_host_passes_the_csrf_referer_check():
    client = _build_client(settings.admin_allowed_hosts)

    response = _post_with_origin(client, f"https://{PROD_HOST}")

    assert response.status_code == 200
    assert response.text == "reached the endpoint"


def test_foreign_origin_is_still_rejected():
    client = _build_client(settings.admin_allowed_hosts)

    response = _post_with_origin(client, "https://evil.example.com")

    assert response.status_code == 403
    assert "Referer or origin is incorrect" in response.text


def test_empty_allowed_hosts_locks_out_the_real_host():
    """
    The original bug: with no allowed_hosts, even the correct origin is refused
    once the app sees the request as HTTPS.
    """
    client = _build_client([])

    response = _post_with_origin(client, f"https://{PROD_HOST}")

    assert response.status_code == 403
    assert "Referer or origin is incorrect" in response.text
