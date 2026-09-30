import mimetypes
from pathlib import Path

from django.conf import settings
from django.db import connection
from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.http import require_GET


def _safe_frontend_path(relative_path: str) -> Path:
    root = Path(settings.FRONTEND_DIST_DIR).resolve()
    target = (root / relative_path).resolve()

    try:
        target.relative_to(root)
    except ValueError as exc:
        raise Http404("Not found") from exc

    return target


@require_GET
def frontend_file(request, path: str = ""):
    """
    Serve the verified static frontend without rewriting its HTML, CSS, JS,
    routes, or runtime fetch paths.

    This is intentionally a compatibility bridge for the first Django phase.
    """
    relative_path = path or "index.html"
    target = _safe_frontend_path(relative_path)

    if target.is_dir():
        target = target / "index.html"

    if not target.is_file():
        raise Http404("Not found")

    content_type, encoding = mimetypes.guess_type(target.name)
    response = FileResponse(
        target.open("rb"),
        content_type=content_type or "application/octet-stream",
    )

    if encoding:
        response["Content-Encoding"] = encoding

    if target.suffix.lower() in {".html", ".json"}:
        response["Cache-Control"] = "no-cache"

    return response



@require_GET
def healthz(request):
    return JsonResponse(
        {
            "status": "ok",
            "service": "bet_tracker",
        }
    )


@require_GET
def readyz(request):
    database_status = "ok"
    frontend_status = "ok"

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        database_status = "error"

    frontend_index = (
        Path(settings.FRONTEND_DIST_DIR) / "index.html"
    )

    if not frontend_index.is_file():
        frontend_status = "error"

    ready = (
        database_status == "ok"
        and frontend_status == "ok"
    )

    return JsonResponse(
        {
            "status": "ok" if ready else "unavailable",
            "database": database_status,
            "frontend": frontend_status,
        },
        status=200 if ready else 503,
    )
